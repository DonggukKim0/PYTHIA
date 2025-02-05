#!/usr/bin/bash

SUBMISSION_TEMPLATE="
executable		= \${JOB_EXE}
arguments		= \${JOB_ARG}

should_transfer_files	= IF_NEEDED
when_to_transfer_output	= ON_EXIT

initialdir		= \${JOB_DIR}/job_\$(Process)

request_cpus	= 1
request_memory	= 512M 
request_disk	= 256M

#num_retries	= 2
output		= out.txt
log		= log.txt
error		= err.txt

queue \${JOB_SIZE}
"

set -e

watch() {
  while [ 1 ]; do
    JOB_STATUS=$(condor_q);
    LINES=$(printf "${JOB_STATUS}" | wc -l | tr -d ' ');
    LINES=$((LINES + 1))
    printf "\\033[${LINES}F\\033[0J";
    printf "${JOB_STATUS}"
    printf "\nEXIT: Ctrl + C"
    sleep 1;
  done
}

if [ "$1" == "-w" ]; then
  watch;
  exit
elif [ $# -le 2 ] || [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  echo "This shell script wraps around condor_submit command and provides simple interface."
  echo "It registers N condor jobs executing EXE and result will be stored in DIR."
  echo "usage: $> bash  $0  EXE  DIR  N  [arguments]"
  echo "arguments for executable will be:
\$1=\"EXE\"   (absolute path to executable)
\$2=\"DIR\"   (path where result will be stored)
\$3=\"N\"     (which is an integer that will create jobs with job number ranging [0, N - 1])\"
\$@=\"[arguments]\""
  exit 1
fi

########################################################
# environment variables                                #
########################################################

# paths should be absoulte path
export JOB_EXE=$(readlink -f $1)
export JOB_DIR=$2
export JOB_SIZE=$3
export JOB_ARG=""'$RANDOM_INTEGER(0, 10000)'" AnalysisResults"'$(Process)'".root"

if [ -z ${JOB_EXE} ]; then
  echo "$0: invalid EXE"
  exit 1
fi

echo "arguments for executable:
\$1=\"${JOB_EXE}\"
\$2=\"${JOB_DIR}\"
\$3=\"${JOB_SIZE}\" (an integer ranges from [0, $((JOB_SIZE - 1))])
\$@=\"${@:4:256}\"
"

POSTPROCESS_EXE=""

########################################################
# job directory                                        #
########################################################
TEMP=$(basename ${JOB_EXE})

mkdir -p ${JOB_DIR}

chmod -R 775 ${JOB_DIR}
for i in $(seq 0 $((JOB_SIZE - 1)))
do
  mkdir $JOB_DIR/job_$i
done
echo "job directories are created in ${JOB_DIR}"

sleep 1

########################################################
# submit                                               #
########################################################

TEMPLATE_FILE=$(mktemp /tmp/condor.template.XXXX) || exit 2
SUBMIT_FILE=$(mktemp /tmp/condor.sub.XXXX) || exit 2
printf '%b\n' "${SUBMISSION_TEMPLATE}" > ${TEMPLATE_FILE}
envsubst < ${TEMPLATE_FILE} > ${SUBMIT_FILE}

BATCH_NAMES=$(condor_submit ${SUBMIT_FILE} | grep cluster | sed 's/.*cluster \([0-9]*\)./\1/')
echo "batch '${BATCH_NAMES}' submitted"
echo ""
rm ${TEMPLATE_FILE}

########################################################
# postprocess                                          #
########################################################
if [[ "$POSTPROCESS_EXE" == "" && "$WAIT_JOB_COMPLETION" == "" ]]; then
  #rm $BATCH_NAME_FILE
  echo "all jobs are submitted."
  exit
fi

# wait until jobs are finished
WAIT=1
COUNT=0
echo "waiting for jobs to be finished"
condor_q
while [ $WAIT -eq 1 ];
do
  RET=$(condor_q | grep "ID: " | sed 's/.* ID: \([0-9]*\) .*/\1/' | tr '\n' ' ' | grep -E $BATCH_NAMES > /dev/null; echo $?)
  if [ $RET -eq 1 ]; then
    WAIT=0
  fi
  JOB_STATUS=$(condor_q);
  LINES=$(printf "${JOB_STATUS}" | wc -l | tr -d ' ');
  LINES=$((LINES + 1))
  printf "\\033[${LINES}F\\033[0J";
  printf "${JOB_STATUS}"
  printf "\nexit waiting: Ctrl + C"
  sleep 1;
done

if [ "$POSTPROCESS_EXE" == "" ]; then
  exit
fi

echo "post-processing"
bash -c "$POSTPROCESS_EXE"

# echo "post-processing example"
#
# export FILENAME=output_merged
# touch $FILENAME
# for i in $(seq 0 $((JOB_SIZE - 1)))
# do
#   cat ${FILES_1[$i]} >> $FILENAME
# done
# echo "finished"
