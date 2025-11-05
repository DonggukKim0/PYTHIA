#!/usr/bin/env python3
"""
Summarise sigmaGen values from PYTHIA log files.

Given an input directory, the script searches recursively for *.out files,
grabs the last `sigmaGen:` entry in each file, and writes a tab-delimited
summary report. The directory component that contains "pthat" is used as the
identifier so different pT̂-hat bins can be matched to their sigmaGen values.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
import re


SIGMA_RE = re.compile(r"\bsigmaGen:\s*([^\s]+)\s*mb", re.IGNORECASE)


@dataclass
class SigmaRecord:
    pthat_label: str
    sigma_value: str
    log_path: Path


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect sigmaGen values from *.out files within a directory."
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=Path,
        required=True,
        help="Root directory to search for *.out files.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("sigmaGen_summary.txt"),
        help="Path of the output text file (default: sigmaGen_summary.txt).",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Text encoding used when reading log files (default: utf-8).",
    )
    return parser.parse_args(argv)


def find_pthat_label(path: Path) -> str:
    for part in reversed(path.parts[:-1]):  # Ignore the filename itself
        if "pthat" in part.lower():
            return part
    return path.parent.name


def extract_sigma_from_file(file_path: Path, encoding: str) -> Optional[SigmaRecord]:
    try:
        text = file_path.read_text(encoding=encoding, errors="ignore")
    except OSError as exc:
        print(f"[WARN] Failed to read {file_path}: {exc}", file=sys.stderr)
        return None

    matches = list(SIGMA_RE.finditer(text))
    if not matches:
        return None

    last_match = matches[-1]
    pthat_label = find_pthat_label(file_path)
    sigma_value = last_match.group(1)
    return SigmaRecord(pthat_label=pthat_label, sigma_value=sigma_value, log_path=file_path)


def pthat_sort_key(record: SigmaRecord) -> Tuple[float, float, str]:
    label = record.pthat_label.lower()
    match = re.search(r"pthat_([0-9]+)(?:_([0-9]+|infy))?", label)
    if match:
        lower = float(match.group(1))
        upper_group = match.group(2)
        if upper_group is None:
            upper = lower
        elif upper_group == "infy":
            upper = float("inf")
        else:
            upper = float(upper_group)
        return (lower, upper, record.pthat_label)
    return (float("inf"), float("inf"), record.pthat_label)


def collect_sigma_records(root: Path, encoding: str) -> List[SigmaRecord]:
    records: List[SigmaRecord] = []
    for path in root.rglob("*.out"):
        if not path.is_file():
            continue
        record = extract_sigma_from_file(path, encoding)
        if record is not None:
            records.append(record)
    return sorted(records, key=lambda rec: (pthat_sort_key(rec), rec.log_path))


def write_report(records: List[SigmaRecord], output_path: Path) -> None:
    lines = ["pthat_label\tsigmaGen_mb\tlog_file"]
    for record in records:
        rel_path = record.log_path.as_posix()
        lines.append(f"{record.pthat_label}\t{record.sigma_value}\t{rel_path}")

    try:
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Failed to write report to {output_path}: {exc}") from exc


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    root_dir: Path = args.directory

    if not root_dir.exists():
        print(f"[ERROR] Directory not found: {root_dir}", file=sys.stderr)
        return 1
    if not root_dir.is_dir():
        print(f"[ERROR] Not a directory: {root_dir}", file=sys.stderr)
        return 1

    records = collect_sigma_records(root_dir, args.encoding)

    if not records:
        print(f"[WARN] No sigmaGen entries found under {root_dir}", file=sys.stderr)
    else:
        print(f"[INFO] Found {len(records)} sigmaGen entries.")

    try:
        write_report(records, args.output)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"[INFO] Report written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
