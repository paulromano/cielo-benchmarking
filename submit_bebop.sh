#!/bin/bash

#SBATCH --nodes=2
#SBATCH --time=01:00:00
#SBATCH --partition=bdwall
#SBATCH --account=OPENMCVALIDATION
#SBATCH --job-name=openmc-benchmarks
#SBATCH --mail-user=promano@anl.gov
#SBATCH --mail-type=BEGIN,END,FAIL

# Setup environment (slurm doesn't run a shell, so no bashrc/profile by default
source $HOME/.bashrc
conda activate py38

# Determine number of MPI ranks
NUM_RANKS=$((SLURM_JOB_NUM_NODES * 2))

# Run job
python -u run_benchmarks.py \
  --cross_sections $HOME/data/hdf5/endfb80_hdf5/cross_sections.xml \
  --mpi_args "srun -N $SLURM_JOB_NUM_NODES -n $NUM_RANKS --cpu-bind=socket"
