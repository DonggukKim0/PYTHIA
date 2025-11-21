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
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import re


SIGMA_RE = re.compile(r"\bsigmaGen:\s*([^\s]+)\s*mb", re.IGNORECASE)


@dataclass
class SigmaRecord:
    pthat_label: str
    sigma_value: str
    log_path: Path


@dataclass
class AggregatedSigmaRecord:
    pthat_label: str
    average_sigma_mb: float
    log_paths: List[Path]


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


def pthat_label_sort_key(label: str) -> Tuple[float, float, str]:
    label_lower = label.lower()
    match = re.search(r"pthat_([0-9]+)(?:_([0-9]+|infy))?", label_lower)
    if match:
        lower = float(match.group(1))
        upper_group = match.group(2)
        if upper_group is None:
            upper = lower
        elif upper_group == "infy":
            upper = float("inf")
        else:
            upper = float(upper_group)
        return (lower, upper, label)
    return (float("inf"), float("inf"), label)


def pthat_sort_key(record: SigmaRecord) -> Tuple[float, float, str]:
    return pthat_label_sort_key(record.pthat_label)


def collect_sigma_records(root: Path, encoding: str) -> List[SigmaRecord]:
    records: List[SigmaRecord] = []
    for path in root.rglob("*.out"):
        if not path.is_file():
            continue
        record = extract_sigma_from_file(path, encoding)
        if record is not None:
            records.append(record)
    return sorted(records, key=lambda rec: (pthat_sort_key(rec), rec.log_path.as_posix()))


def aggregate_sigma_records(records: List[SigmaRecord]) -> List[AggregatedSigmaRecord]:
    grouped: Dict[str, List[SigmaRecord]] = defaultdict(list)
    for record in records:
        grouped[record.pthat_label].append(record)

    aggregated: List[AggregatedSigmaRecord] = []
    for label, recs in grouped.items():
        valid_entries: List[Tuple[float, Path]] = []
        for rec in recs:
            try:
                value = float(rec.sigma_value)
            except ValueError:
                print(
                    f"[WARN] Could not parse sigmaGen value '{rec.sigma_value}' in {rec.log_path}",
                    file=sys.stderr,
                )
                continue
            valid_entries.append((value, rec.log_path))

        if not valid_entries:
            print(
                f"[WARN] No valid sigmaGen values found for {label}; skipping average.",
                file=sys.stderr,
            )
            continue

        avg_sigma = sum(val for val, _ in valid_entries) / len(valid_entries)
        contributing_paths = [
            path for _, path in sorted(valid_entries, key=lambda item: item[1].as_posix())
        ]
        aggregated.append(
            AggregatedSigmaRecord(
                pthat_label=label,
                average_sigma_mb=avg_sigma,
                log_paths=contributing_paths,
            )
        )

    return sorted(
        aggregated,
        key=lambda rec: (pthat_label_sort_key(rec.pthat_label), rec.log_paths[0].as_posix()),
    )


def format_sigma(value: float) -> str:
    return f"{value:.6e}"


def write_report(records: List[AggregatedSigmaRecord], output_path: Path) -> None:
    lines = ["pthat_label\tsigmaGen_mb\tlog_files"]
    for record in records:
        if record.log_paths:
            log_repr = ", ".join(path.as_posix() for path in record.log_paths)
            log_column = f"{len(record.log_paths)} files: {log_repr}"
        else:
            log_column = "0 files"
        lines.append(
            f"{record.pthat_label}\t{format_sigma(record.average_sigma_mb)}\t{log_column}"
        )

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
    aggregated_records = aggregate_sigma_records(records)

    if not records:
        print(f"[WARN] No sigmaGen entries found under {root_dir}", file=sys.stderr)
    elif not aggregated_records:
        print(
            "[WARN] Sigma entries were found, but none produced a valid average.",
            file=sys.stderr,
        )
    else:
        print(
            f"[INFO] Found {len(records)} sigmaGen entries across {len(aggregated_records)} unique pTHat bins."
        )

    try:
        write_report(aggregated_records, args.output)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"[INFO] Report written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
