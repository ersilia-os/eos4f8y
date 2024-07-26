# imports
import os
import csv
import sys

# parse arguments
input_file = sys.argv[1]
sim_file = sys.argv[2]
output_file = sys.argv[3]

N_SAMPLED = 100

# current file directory
root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(root, "..", "mollib"))
from sampler import MollibSampler

# read SMILES from .csv file, assuming one column with header
with open(input_file, "r") as f:
    reader = csv.reader(f)
    next(reader)  # skip header
    smiles_list = [r[0] for r in reader]

# read similarity matrix from .csv file
with open(sim_file, "r") as f:
    reader = csv.reader(f)
    next(reader)
    R = []
    for r in reader:
        R += [r]

# Perform a similarity search and then sample using Mollib
sampler = MollibSampler()
outputs = []
for i, smiles in enumerate(smiles_list):
    similar_smiles = R[i]
    similar_smiles += [smiles]
    sampled_smiles = sampler.sample(similar_smiles, n=N_SAMPLED)
    outputs += [sampled_smiles]

#check input and output have the same lenght
input_len = len(smiles_list)
output_len = len(outputs)
assert input_len == output_len

# write output in a .csv file
with open(output_file, "w") as f:
    writer = csv.writer(f)
    header = ["mol-{0}".format(i) for i in range(N_SAMPLED)]
    writer.writerow(header)
    for o in outputs:
        writer.writerow(o)