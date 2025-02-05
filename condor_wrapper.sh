#!/bin/zsh
source ${HOME}/.zshrc
source ${HOME}/cernbox/job/PYTHIA_SERVER_pPb/alienv_envset.sh
export
cd ${HOME}/cernbox/job/PYTHIA_SERVER_pPb
./pythia $1 $2
