from argparse import ArgumentParser
import os
from pathlib import Path
from subprocess import run, STDOUT, PIPE
import time

import openmc

current_time = time.strftime("%Y-%m-%d-%H%M%S")

parser = ArgumentParser()
parser.add_argument('--directory', default=current_time)
parser.add_argument("--cross_sections", type=Path)
parser.add_argument("--threshold", type=float, default=0.001)
parser.add_argument("--mpi_args", default="")
args = parser.parse_args()

benchmark_list = "benchmarks/lists/pst-short"
particles = 10000
max_batches = 10000
batches = 150
inactive = 50
code = "openmc"
basedir = Path(args.directory).resolve()
mpi_args = args.mpi_args.split()

# Change to correct directory
basedir.mkdir(exist_ok=True)
os.chdir(basedir)

# Remove previous results if they exist
Path(basedir / 'results').unlink(missing_ok=True)

# Get copy of benchmarks repository and switch to nndc branch
run(["git", "clone", "https://github.com/mit-crpg/benchmarks.git"])

# Get benchmark directories
with open(benchmark_list, 'r') as fh:
    benchmarks = [Path(line.strip()) for line in fh]

# Set cross sections
env = os.environ.copy()
if args.cross_sections is not None:
    env["OPENMC_CROSS_SECTIONS"] = args.cross_sections

for i, benchmark in enumerate(benchmarks):
    print(f"{i + 1} {benchmark} ", end="")
    os.chdir(basedir / "benchmarks" / benchmark)

    # Modify settings based on inputs
    settings = openmc.Settings.from_xml("settings.xml")
    settings.particles = particles
    settings.batches = 150
    settings.inactive = 50
    settings.trigger_max_batches = max_batches
    settings.trigger_active = True
    settings.keff_trigger = {'type': 'std_dev', 'threshold': args.threshold}
    settings.export_to_xml()

    # Re-generate materials if Python script is present
    genmat_script = Path("generate_materials.py")
    if genmat_script.is_file():
        run(["python", "generate_materials.py"])

    # Run OpenMC
    result = run(
        mpi_args + ["openmc"],
        env=env,
        stdout=PIPE,
        stderr=STDOUT,
        text=True,
    )

    # Write output to file
    with open(f"output_{current_time}", "w") as fh:
        fh.write(result.stdout)

    # Determine last statepoint
    t_last = 0
    last_statepoint = None
    for sp in Path().glob('statepoint.*.h5'):
        mtime = sp.stat().st_mtime
        if mtime >= t_last:  # >= allows for poor clock resolution
            t_last = mtime
            last_statepoint = sp

    # Write to results file
    if last_statepoint is not None:
        with openmc.StatePoint(last_statepoint) as sp:
            keff = sp.k_combined

        print(f"{keff.n:.5f} ± {keff.s:.5f}")
        with open(basedir / "results", "a") as results:
            results.write(f"{benchmark} {keff.nominal_value} {keff.std_dev}\n")
    else:
        print("")
