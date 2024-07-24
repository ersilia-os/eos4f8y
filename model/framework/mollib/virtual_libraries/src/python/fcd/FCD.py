#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Defines the functions necessary for calculating the Fréchet CHEMBLNET
Distance (FCD) to evaluate generative models for molecules.

The FCD metric calculates the distance between two distributions of molecules.
Typically, we have summary statistics (mean & covariance matrix) of one
of these distributions, while the 2nd distribution is given by the generative 
model.

The FCD is calculated by assuming that X_1 and X_2 are the activations of
the second LSTM layer of the CHEMBLNET for generated samples and real world
samples respectively.
"""

from __future__ import absolute_import, division, print_function

import warnings

import keras.backend as kb
import numpy as np
from keras.models import load_model
from scipy import linalg


def calculate_frechet_distance(mu1, sigma1, mu2, sigma2, eps=1e-6):
    """Numpy implementation of the Fréchet Distance.
    The Fréchet distance between two multivariate Gaussians X_1 ~ N(mu_1, C_1)
    and X_2 ~ N(mu_2, C_2) is
        d^2 = ||mu_1 - mu_2||^2 + Tr(C_1 + C_2 - 2*sqrt(C_1*C_2)).

    Stable version by Dougal J. Sutherland.

    Params:
    -- mu1:    The mean of the activations of preultimate layer of the
               CHEMBLNET ( like returned by the function 'get_predictions')
               for generated samples.
    -- mu2:    The mean of the activations of preultimate layer of the
               CHEMBLNET ( like returned by the function 'get_predictions')
               for real samples.
    -- sigma1: The covariance matrix of the activations of preultimate layer of the
               CHEMBLNET ( like returned by the function 'get_predictions')
               for generated samples.
    -- sigma2: The covariance matrix of the activations of preultimate layer of the
               CHEMBLNET ( like returned by the function 'get_predictions')
               for real samples.

    Returns:
    --   : The Fréchet Distance.
    """

    mu1 = np.atleast_1d(mu1)
    mu2 = np.atleast_1d(mu2)

    sigma1 = np.atleast_2d(sigma1)
    sigma2 = np.atleast_2d(sigma2)

    assert (
        mu1.shape == mu2.shape
    ), "Training and test mean vectors have different lengths"
    assert (
        sigma1.shape == sigma2.shape
    ), "Training and test covariances have different dimensions"

    diff = mu1 - mu2

    # product might be almost singular
    covmean, _ = linalg.sqrtm(sigma1.dot(sigma2), disp=False)
    if not np.isfinite(covmean).all():
        msg = (
            "fid calculation produces singular product; adding %s to diagonal of cov estimates"
            % eps
        )
        warnings.warn(msg)
        offset = np.eye(sigma1.shape[0]) * eps
        covmean = linalg.sqrtm((sigma1 + offset).dot(sigma2 + offset))

    # numerical error might give slight imaginary component
    if np.iscomplexobj(covmean):
        if not np.allclose(np.diagonal(covmean).imag, 0, atol=1e-3):
            m = np.max(np.abs(covmean.imag))
            raise ValueError("Imaginary component {}".format(m))
        covmean = covmean.real

    tr_covmean = np.trace(covmean)

    return diff.dot(diff) + np.trace(sigma1) + np.trace(sigma2) - 2 * tr_covmean


def build_masked_loss(loss_function, mask_value):
    """Builds a loss function that masks based on targets

    Args:
        loss_function: The loss function to mask
        mask_value: The value to mask in the targets

    Returns:
        function: a loss function that acts like loss_function with masked inputs
    """

    def masked_loss_function(y_true, y_pred):
        mask = kb.cast(kb.not_equal(y_true, mask_value), kb.floatx())
        return loss_function(y_true * mask, y_pred * mask)

    return masked_loss_function


def masked_accuracy(y_true, y_pred):
    """An accuracy function that masks based on targets (value: 0.5)

    Args:
        y_true: The true training labels
        y_pred: The predicted labels

    Returns:
        float: the masked accuracy
    """
    a = kb.sum(kb.cast(kb.equal(y_true, kb.round(y_pred)), kb.floatx()))
    c = kb.sum(kb.cast(kb.not_equal(y_true, 0.5), kb.floatx()))
    acc = a / c
    return acc


def get_one_hot(smiles, pad_len=-1):
    one_hot = [
        "C",
        "N",
        "O",
        "H",
        "F",
        "Cl",
        "P",
        "B",
        "Br",
        "S",
        "I",
        "Si",
        "#",
        "(",
        ")",
        "+",
        "-",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "=",
        "[",
        "]",
        "@",
        "c",
        "n",
        "o",
        "s",
        "X",
        ".",
    ]

    smiles = smiles + "."
    if pad_len < 0:
        vec = np.zeros((len(smiles), len(one_hot)))
    else:
        vec = np.zeros((pad_len, len(one_hot)))
    cont = True
    j = 0
    i = 0
    while cont:

        try:
            if smiles[i + 1] in ["r", "i", "l"]:
                sym = smiles[i : i + 2]
                i += 2
            else:
                sym = smiles[i]
                i += 1
        except:
            print(f"smiles[i + 1] not working, value smiles {smiles}")
        if sym in one_hot:
            vec[j, one_hot.index(sym)] = 1
        else:
            vec[j, one_hot.index("X")] = 1
        j += 1
        if smiles[i] == "." or j >= (pad_len - 1) and pad_len > 0:
            vec[j, one_hot.index(".")] = 1
            cont = False
    return vec


def predict_my_generator(smiles_list, batch_size=128, pad_len=350):
    while 1:
        num_smls = len(smiles_list)
        nn = pad_len
        idx_samples = np.arange(num_smls)

        for j in range(int(np.ceil(num_smls / batch_size))):
            idx = idx_samples[j * batch_size : min((j + 1) * batch_size, num_smls)]
            x = []
            for i in range(0, len(idx)):
                x.append(get_one_hot(smiles_list[idx[i]], pad_len=nn))

            yield np.asarray(x) / 35.0


def get_predictions(gen_mol):
    masked_loss_function = build_masked_loss(kb.binary_crossentropy, 0.5)
    # print('loading model...')
    import os

    # this is super hacky to get back the path here to dl the model.h5
    # but well. From: https://stackoverflow.com/questions/7505988/importing-from-a-relative-path-in-python
    path_here = os.path.dirname(__file__)
    model = load_model(
        os.path.join(path_here, "model_FCD_all.h5"),
        custom_objects={
            "masked_loss_function": masked_loss_function,
            "masked_accuracy": masked_accuracy,
        },
    )
    model.pop()  # remove last layer (Dense)
    model.pop()  # remove second last layer (LSTM2)
    # print('calculating activations...')
    return model.predict_generator(
        predict_my_generator(gen_mol, batch_size=128), steps=np.ceil(len(gen_mol) / 128)
    )


if __name__ == "__main__":
    import pandas as pd
    import pickle

    # Load generated molecules
    mols = pd.read_csv("generated_smiles/endogena.smi", header=None)[0].values[
        :5000
    ]  # take at least 5000 molecules

    # Load statistics of random 50,000 chembl molecules, which were not used for training
    d = pickle.load(open("chembl_50k_stats.p", "rb"))

    # get ChEMBLNET activations of generated molecules
    gen_mol_act = get_predictions(mols)
    FCD = calculate_frechet_distance(
        mu1=np.mean(gen_mol_act, axis=0),
        mu2=d["mu_chembl"],
        sigma1=np.cov(gen_mol_act.T),
        sigma2=d["cov_chembl"],
    )
    print("FCD: %.4f" % FCD)
