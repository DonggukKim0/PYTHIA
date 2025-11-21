#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: merge_pythia_final.sh -i <root_dir> -o <output_dir> [-p <parallel_jobs>]

Options:
  -i  Directory whose tree contains out/* subfolders with AnalysisResults ROOT files.
  -o  Directory where merged ROOT files will be written.
  -p  Number of parallel hadd jobs to run (default: number of CPU cores).
  -h  Show this help message.

Each subdirectory under an "out" folder containing files that match
*AnalysisResults_*.root is merged into a single ROOT file within <output_dir>.
The merged filename is the subdirectory's basename with a _merged.root suffix.
USAGE
}

err() {
  echo "[ERROR] $*" >&2
}

info() {
  echo "[INFO] $*" >&2
}

format_duration() {
  local total_seconds="${1}"
  local hours=$(( total_seconds / 3600 ))
  local minutes=$(( (total_seconds % 3600) / 60 ))
  local seconds=$(( total_seconds % 60 ))

  if (( hours > 0 )); then
    printf '%dh %02dm %02ds' "${hours}" "${minutes}" "${seconds}"
  elif (( minutes > 0 )); then
    printf '%dm %02ds' "${minutes}" "${seconds}"
  else
    printf '%ds' "${seconds}"
  fi
}

input_dir=""
output_dir=""
parallelism=""

while getopts ":i:o:p:h" opt; do
  case "${opt}" in
    i) input_dir="${OPTARG}" ;;
    o) output_dir="${OPTARG}" ;;
    p) parallelism="${OPTARG}" ;;
    h)
      usage
      exit 0
      ;;
    :) err "Option -${OPTARG} requires an argument"; usage; exit 1 ;;
    \?) err "Unknown option -${OPTARG}"; usage; exit 1 ;;
  esac
done

if [[ -z "${input_dir}" || -z "${output_dir}" ]]; then
  err "Both -i and -o are required"
  usage
  exit 1
fi

if ! command -v hadd >/dev/null 2>&1; then
  err "hadd not found in PATH"
  exit 1
fi

if [[ ! -d "${input_dir}" ]]; then
  err "Input directory not found: ${input_dir}"
  exit 1
fi

mkdir -p "${output_dir}"

if [[ -z "${parallelism}" ]]; then
  if command -v nproc >/dev/null 2>&1; then
    parallelism="$(nproc)"
  else
    parallelism=1
  fi
fi

if ! [[ "${parallelism}" =~ ^[0-9]+$ ]] || (( parallelism < 1 )); then
  err "Parallel jobs must be a positive integer"
  exit 1
fi

search_root="${input_dir%/}"
mapfile -d '' -t analysis_files < <(find "${search_root}" -type f -name '*AnalysisResults_*.root' -print0)

if (( ${#analysis_files[@]} == 0 )); then
  err "No AnalysisResults ROOT files found under ${search_root}"
  exit 1
fi

declare -A seen_dirs=()
declare -a analysis_dirs=()
for file in "${analysis_files[@]}"; do
  dir="$(dirname "${file}")"
  if [[ -z "${seen_dirs[${dir}]+x}" ]]; then
    seen_dirs["${dir}"]=1
    analysis_dirs+=("${dir}")
  fi
done
mapfile -t analysis_dirs < <(printf '%s\n' "${analysis_dirs[@]}" | sort)

if (( ${#analysis_dirs[@]} == 0 )); then
  err "No directories containing AnalysisResults ROOT files found under ${search_root}"
  exit 1
fi

info "Found ${#analysis_dirs[@]} directories to merge"

SECONDS=0

pids=()
declare -A job_labels

take_slot() {
  while (( ${#pids[@]} >= parallelism )); do
    release_oldest
  done
}

release_oldest() {
  local pid="${pids[0]}"
  pids=("${pids[@]:1}")
  local label="${job_labels[$pid]}"
  unset "job_labels[$pid]"
  if ! wait "${pid}"; then
    err "hadd failed for ${label}"
    exit 1
  fi
}

cleanup() {
  local pid
  for pid in "${pids[@]}"; do
    local label="${job_labels[$pid]}"
    if ! wait "${pid}"; then
      err "hadd failed for ${label}"
      exit 1
    fi
    unset "job_labels[$pid]"
  done
}

trap cleanup EXIT

for dir in "${analysis_dirs[@]}"; do
  dir_basename="$(basename "${dir}")"
  rel_dir="${dir#"${search_root}/"}"
  rel_dir="${rel_dir:-${dir_basename}}"

  output_file="${output_dir%/}/${dir_basename}_merged.root"

  readarray -d '' -t root_files < <(find "${dir}" -maxdepth 1 -type f -name '*AnalysisResults_*.root' -print0 | sort -z)

  if (( ${#root_files[@]} == 0 )); then
    info "Skipping ${dir}: no AnalysisResults ROOT files"
    continue
  fi

  take_slot

  info "Merging ${#root_files[@]} files from ${rel_dir} -> ${output_file}"

  (
    if hadd -f "${output_file}" "${root_files[@]}"; then
      info "Finished ${output_file}"
    else
      err "hadd failed for ${dir}"
      exit 1
    fi
  ) &

  pid=$!
  pids+=("${pid}")
  job_labels[${pid}]="${rel_dir}"

done

cleanup
trap - EXIT

elapsed="${SECONDS}"
duration=$(format_duration "${elapsed}")
info "All merges completed in ${duration}"
