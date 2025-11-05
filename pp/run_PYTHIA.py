#!/usr/bin/env python3
from datetime import datetime
import subprocess
import pathlib
import os
import sys

os.umask(0)

MAINGENERATOR = "run_config_files_13_6_TeV"  # name of optns file, must be placed in the same folder of this script
CONFIG_FILE = "config_files_13_6_TeV"

## Default values
totalEvents = 100
print(f"Total events: {totalEvents}")

# Below should not be modified ##########################################
now = datetime.now().strftime("%Y%m%d_%H%M%S")
mainDir = os.path.dirname(os.path.realpath(__file__))
work_root_name = f"{now}_{MAINGENERATOR}"
work_root = pathlib.Path(mainDir) / work_root_name
macro_root = work_root / "macro"
out_root = work_root / "out"
log_root = work_root / "logs"

for directory in (macro_root, out_root, log_root):
    directory.mkdir(parents=True, exist_ok=True)

config_dir = pathlib.Path(mainDir) / CONFIG_FILE

if not config_dir.is_dir():
    raise FileNotFoundError(f"Config directory not found: {config_dir}")

config_files = sorted(config_dir.glob("*.cmnd"))

if not config_files:
    raise RuntimeError(f"No .cmnd files found in {config_dir}")

for config_path in config_files:
    config_name = config_path.name
    config_stem = config_path.stem

    if "pthat_" in config_stem:
        pthat_suffix = config_stem.split("pthat_", 1)[1]
        output_prefix = f"pthat_{pthat_suffix}"
    else:
        output_prefix = config_stem

    config_macro_dir = macro_root / config_stem
    config_out_dir = out_root / output_prefix
    config_log_dir = log_root / config_stem

    config_macro_dir.mkdir(parents=True, exist_ok=True)
    config_out_dir.mkdir(parents=True, exist_ok=True)
    config_log_dir.mkdir(parents=True, exist_ok=True)

    run_script_path = config_macro_dir / "run.sh"
    run_script_path.write_text(
        f"""#!/bin/bash

echo "INIT! $1 $2 $3 $4 $5"

source alienv_envset.sh

RANDOM_SEED=$(od -vAn -N4 -tu4 < /dev/urandom | tr -d " ")
RANDOM_SEED=$(( RANDOM_SEED % 10001 ))

CONFIG_FILE="{config_name}"
JOB_INDEX=${{2:-0}}
OUTPUT_PREFIX="{output_prefix}"

./pythia $RANDOM_SEED AnalysisResults.root "$CONFIG_FILE"

OUTPUT_FILE="${{OUTPUT_PREFIX}}_AnalysisResults_${{JOB_INDEX}}.root"
cp -f AnalysisResults.root "${{OUTPUT_FILE}}"

ls -althr # Check the output files before finish
echo "DONE!"
""",
        encoding="utf-8",
    )
    run_script_path.chmod(0o775)

    rel_config_path = os.path.relpath(config_path.resolve(), mainDir)

    condor_sub_path = config_macro_dir / "condor.sub"
    condor_sub_path.write_text(
        f"""Universe                = vanilla
Executable              = {work_root_name}/macro/{config_stem}/run.sh
Accounting_Group        = group_alice
JobBatchName            = {work_root_name}_{config_stem}_$(process)
Log                     = {work_root_name}/logs/{config_stem}/$(process).log
Output                  = {work_root_name}/logs/{config_stem}/$(process).out
Error                   = {work_root_name}/logs/{config_stem}/$(process).error

request_memory          = 100MB
request_disk            = 10MB
transfer_input_files    = alienv_envset.sh,pythia,{rel_config_path}
transfer_output_files   = {output_prefix}_AnalysisResults_$(process).root
arguments               = "$(Opt) $(process)"
should_transfer_files   = YES
when_to_transfer_output = ON_EXIT
periodic_remove = (CurrentTime - EnteredCurrentStatus) > 259200
output_destination      = file://{work_root}/out/{output_prefix}/

Queue {totalEvents} Opt in ({MAINGENERATOR})
""",
        encoding="utf-8",
    )

    condor_dag_path = config_macro_dir / "condor.dag"
    condor_dag_path.write_text(
        f"JOB A {work_root_name}/macro/{config_stem}/condor.sub\n", encoding="utf-8"
    )

    submit_cmd = (
        f'condor_submit_dag -batch-name {MAINGENERATOR}_{config_stem}_{totalEvents} '
        f'-force -append "Accounting_Group=group_alice" '
        f'{work_root_name}/macro/{config_stem}/condor.dag'
    )
    process = subprocess.Popen(
        [submit_cmd], shell=True, cwd=mainDir, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    print(stdout.decode("utf-8"))
    if stderr:
        print(stderr.decode("utf-8"), file=sys.stderr)
