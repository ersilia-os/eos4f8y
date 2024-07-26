python $1/code/similarity_search.py $2 $1/sim.csv
python $1/code/generation.py $2 $1/sim.csv $3
rm $1/sim.csv
