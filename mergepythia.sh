#!/bin/bash

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <mergefolder> <filename>"
  echo "Example: $0 20250214_144807 merged_AnalysisResults.root"
  exit 1
fi

mergefolder=$1
filename=$2

cd "$mergefolder" || { echo "Failed to change directory to $mergefolder"; exit 1; }

files=$(find "$PWD" -name "$filename")
nFiles=$(echo "$files" | wc -w)
echo "Total files found: $nFiles"

hadd double_merged_AnalysisResults.root $files
