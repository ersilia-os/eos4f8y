# imports
import os
import csv
import numpy as np
import sys
from faiss import read_index
import tempfile 
from rdkit import Chem
import subprocess
import joblib
import collections

# parse arguments
input_file = sys.argv[1]
output_file = sys.argv[2]

python_path = sys.executable

# current file directory
root = os.path.dirname(os.path.abspath(__file__))
tmp_folder = tempfile.mkdtemp(prefix="ersilia-")

CHECKPOINTS_FOLDER = os.path.join(root, "..", "..", "checkpoints")

sys.path.append(os.path.join(root, "whales"))
import do_whales

# read SMILES from .csv file, assuming one column with header
with open(input_file, "r") as f:
    reader = csv.reader(f)
    next(reader)
    smiles_list = [r[0] for r in reader]


def prepare_molecule(smiles, k=3):
    smi_file = os.path.join(tmp_folder, "molecule.csv")
    with open(smi_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["smiles"])
        writer.writerow([smiles])
    sdf3d_file = os.path.join(tmp_folder, "molecules3d.sdf")
    cmd = "{0} {1}/smi3d/smi3d.py -i {2} -o {3} -n {4}".format(python_path, root, smi_file, sdf3d_file, k)
    print(cmd)
    subprocess.Popen(cmd, shell=True).wait()
    supplier = Chem.SDMolSupplier(sdf3d_file)
    mols = []
    for mol in supplier:
        mols += [mol]
    return mols

# load scalers
scaler0 = joblib.load(os.path.join(CHECKPOINTS_FOLDER, "R0.joblib"))
scaler1 = joblib.load(os.path.join(CHECKPOINTS_FOLDER, "R1.joblib"))
scaler2 = joblib.load(os.path.join(CHECKPOINTS_FOLDER, "R2.joblib"))

# load faiss index
index0 = read_index(os.path.join(CHECKPOINTS_FOLDER, "R0_scaled.index"))
index1 = read_index(os.path.join(CHECKPOINTS_FOLDER, "R1_scaled.index"))
index2 = read_index(os.path.join(CHECKPOINTS_FOLDER, "R2_scaled.index"))

# load molecules smiles
with open(os.path.join(CHECKPOINTS_FOLDER, "reference_smiles.txt"), "r") as f:
    reader = csv.reader(f)
    ref_smiles = []
    for r in reader:
        ref_smiles += [r[0]]

N_NEIGH = 100

# iterate over molecules
outputs = []
for smiles in smiles_list:
    conformers = prepare_molecule(smiles)
    R = []
    for conf in conformers:
        r, lab = do_whales.whales_from_mol(conf)
        R += [r]
    R = np.array(R)
    R0 = scaler0.transform(R)
    R1 = scaler1.transform(R)
    R2 = scaler2.transform(R)

    D0, I0 = index0.search(R0, k=N_NEIGH)
    D1, I1 = index1.search(R1, k=N_NEIGH)
    D2, I2 = index2.search(R2, k=N_NEIGH)

    results_by_index = collections.defaultdict(list)

    for i in range(D0.shape[0]):
        for j in range(D0.shape[1]):
            results_by_index[I0[i,j]] += [D0[i,j]]
    
    for i in range(D1.shape[0]):
        for j in range(D1.shape[1]):
            results_by_index[I1[i,j]] += [D1[i,j]]
    
    for i in range(D2.shape[0]):
        for j in range(D2.shape[1]):
            results_by_index[I2[i,j]] += [D2[i,j]]

    results_by_index = dict((k, np.min(v)) for k,v in results_by_index.items())

    results = sorted(results_by_index.items(), key=lambda x: x[1])[:N_NEIGH]
    results_smiles = [ref_smiles[r[0]] for r in results]
    outputs += [results_smiles]

header = ["smi_{0}".format(str(i).zfill(3)) for i in range(N_NEIGH)]

# check input and output have the same lenght
input_len = len(smiles_list)
output_len = len(outputs)
assert input_len == output_len

# write output in a .csv file
with open(output_file, "w") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    for o in outputs:
        writer.writerow(o)
