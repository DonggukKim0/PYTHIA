#!/bin/bash

# You must run this file after generating simulation result #

# Get current date and time in format YYYYMMDD_HHMMSS
DATETIME=$(date +"%Y%m%d_%H%M%S")

# Create directory with datetime name
mkdir -p $DATETIME

# Example of copying specific files to the new directory
# Replace these with your actual filenames
cp pythia.C $DATETIME/
cp pythia_config.cmnd $DATETIME/
cp merged_AnalysisResults.root $DATETIME/

