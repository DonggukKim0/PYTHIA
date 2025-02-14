#!/usr/bin/env python3
import shutil
from datetime import datetime
import subprocess
import pathlib
import os 
os.umask(0)

MAINGENERATOR = "PYTHIA" # name of optns file, must be placed in the same folder of this script
USER_MAIL = "dongguk.kim@cern.ch"
USER_SCRIPT = ""
POST_SCRIPT = ""

## Default values
inputFiles=f"pythia_config.cmnd"
totalEvents = 1000
print(f"Total events: {totalEvents}")

# Below should not be modified ##########################################
now=datetime.now().strftime("%Y%m%d_%H%M%S")
workDir=f"{now}_{MAINGENERATOR}"
mainDir=os.path.dirname(os.path.realpath(__file__))

## Preparing the run
# Make paths
pathlib.Path(f"{mainDir}/{workDir}/macro").mkdir(parents=True, exist_ok=True)
pathlib.Path(f"{mainDir}/{workDir}/out").mkdir(parents=True, exist_ok=True)
pathlib.Path(f"{mainDir}/{workDir}/logs").mkdir(parents=True, exist_ok=True)

for number in range(totalEvents):
    pathlib.Path(f"{mainDir}/{workDir}/out/{number}").mkdir(parents=True, exist_ok=True)

# Copy input files
shutil.copy(inputFiles, f"{mainDir}/{workDir}/macro/")


# Make run.sh file (main macro)
fRunScript = open(f"{mainDir}/{workDir}/macro/run.sh", "a")
fRunScript.write(f"""#!/bin/bash

echo "INIT! $1 $2 $3 $4 $5"

source alienv_envset.sh

RANDOM_SEED=$(od -vAn -N4 -tu4 < /dev/urandom | tr -d " ")
RANDOM_SEED=$(( RANDOM_SEED % 10001 ))

./pythia $RANDOM_SEED AnalysisResults.root

ls -althr # Check the output files before finish
echo "DONE!"
""")
fRunScript.close()

# Make some condor input files
# Executable              = {workDir}/macro/{runMacro}
# transfer_input_files    = {runMacro},{inputFiles}
fCondorSub = open(f"{mainDir}/{workDir}/macro/condor.sub", "a")
fCondorSub.write(f"""Universe                = vanilla
Executable              = {workDir}/macro/run.sh
Accounting_Group        = group_alice
JobBatchName		    = {workDir}_$(process)
Log                     = {workDir}/logs/$(process).log
Output                  = {workDir}/$(process).out
Error                   = {workDir}/$(process).error

request_memory          = 512MB
request_disk            = 512MB
transfer_input_files    = alienv_envset.sh,pythia,run.sh,{inputFiles}
transfer_output_files   = AnalysisResults.root
arguments               = "$(Opt) $(process)"
should_transfer_files   = YES
when_to_transfer_output = ON_EXIT
periodic_remove = (CurrentTime - EnteredCurrentStatus) > 86400
output_destination      = file://{mainDir}/{workDir}/out/$(process)/

Queue {totalEvents} Opt in ({MAINGENERATOR})
""")
fCondorSub.close()

fCondorDag = open(f"{mainDir}/{workDir}/macro/condor.dag", "a")
fCondorDag.write(f"""JOB A {workDir}/macro/condor.sub
""")
fCondorDag.close()

process = subprocess.Popen([f'condor_submit_dag -batch-name {MAINGENERATOR}_{totalEvents} -force -notification Always -append "Accounting_Group=group_alice" -append "notify_user={USER_MAIL}" {workDir}/macro/condor.dag'], shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = process.communicate()
print(stdout.decode("utf-8"))
