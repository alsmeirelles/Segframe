#!/bin/bash
#SBATCH -p GPU-shared
#SBATCH -N 1
#SBATCH -t 30:00:00
#SBATCH --gpus=1
#SBATCH --mail-type=ALL
#SBATCH --mail-user=alsmeirelles@gmail.com

#echo commands to stdout
#set -x

DIRID="ENS-160"
#export PYTHONPATH=$HOME/.local/lib/python3.6/site-packages:/pylon5/ac3uump/alsm/lib64/python3.6/site-packages:$PYTHONPATH

cd /ocean/projects/asc130006p/alsm/active-learning/Segframe

echo '[VIRTUALENV]'
source /ocean/projects/asc130006p/alsm/venv/bin/activate

#Load CUDA and set LD_LIBRARY_PATH
module load cuda/10.0.0
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/ocean/projects/asc130006p/alsm/venv/lib64/cuda-10.0.0

echo '[START] training'
date +"%D %T"

time python3 main.py -i -v --al -strategy EnsembleTrainer -predst /ocean/projects/asc130006p/alsm/active-learning/data/nds300 -split 0.90 0.01 0.09 -net EFInception -data CellRep -init_train 500 -ac_steps 20 -emodels 3 -ac_function kmng_uncert -un_function ensemble_bald -acquire 200 -d -e 50 -b 128 -tdim 240 240 -clusters 20 -out logs/ -cpu 15 -gpu 1 -tn -sv -nsw -wpath results/$DIRID -model_dir results/$DIRID -logdir results/$DIRID -cache results/$DIRID -pca 50 -sample 2000 -wsi_split 5 -pred_size 15000 -load_train -spool 2 -k -f1 30 -tnet EFInception -tnpred 2 -phi 3 -tnphi 2 -lr 0.0001  

#-plw -lyf 103 

#-tnet EFInception -tnpred 2 -phi 3 -tnphi 2 -f1 30 -lr 0.0001 

#-wsilist TCGA-BL-A13J-01Z-00 TCGA-FR-A728-01Z-00 TCGA-EE-A2MH-01Z-00 TCGA-C5-A1MH-01Z-00 TCGA-US-A77G-01Z-00 -wsimax 1.0 1.0 1.0 1.0 0.5

echo '[FINAL] done training'

deactivate 

date +"%D %T"


