#!/usr/bin/env python3
"""
Scale pThat-dependent ROOT files and combine them into a single output file.

Steps:
1. Read bin configuration from pthat_add_config.json (or a user-specified file).
2. For each enabled bin: open the ROOT file, scale all TH1 objects, keep copies for plotting.
3. Draw the selected histogram from every bin plus their sum on one canvas.
4. Save the scaled copies into temporary files and call the ROOT `hadd` utility to
   build the summed ROOT file alongside a PDF plot.

Use `--input-dir` to point at the directory that contains the ROOT files listed in the config
and `--output-dir`/`--output-name` to select where the combined results are written.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import ROOT  # type: ignore[attr-defined]


ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(0)


@dataclass
class BinConfig:
    name: str
    filename: Path
    include: bool
    use_scale: bool
    scale_factor: float
    color: int
    range_min: Optional[float]
    range_max: Optional[float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scale pThat ROOT files, sum them, and draw comparison plots."
    )
    parser.add_argument(
        "-c",
        "--config",
        default="pthat_add_config.json",
        help="Path to configuration JSON file (default: %(default)s).",
    )
    parser.add_argument(
        "--histogram",
        default=None,
        help="Name of the histogram to draw. Defaults to the first TH1 found.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose logging.",
    )
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Directory that stores the ROOT files listed in the config. "
        "Defaults to the directory containing the config file.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory that will receive the combined ROOT/PDF outputs. "
        "Defaults to the directory containing the config file.",
    )
    parser.add_argument(
        "--output-name",
        default="combined.root",
        help="Output ROOT file name (PDF will use the same stem). "
        "Defaults to %(default)s.",
    )
    return parser.parse_args()


def load_config(path: Path) -> dict:
    with path.open() as handle:
        return json.load(handle)


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def build_bin_configs(raw_config: dict, input_dir: Path) -> List[BinConfig]:
    input_dir = input_dir.resolve()
    color_cycle = [
        ROOT.kRed,
        ROOT.kOrange + 1,
        ROOT.kYellow + 1,
        ROOT.kGreen + 2,
        ROOT.kBlue,
        ROOT.kBlue + 2,
        ROOT.kViolet,
        ROOT.kMagenta + 3,
        ROOT.kBlack,
        ROOT.kGray + 2,
    ]

    bins: List[BinConfig] = []
    for idx, raw_bin in enumerate(raw_config.get("pthat_bins", [])):
        color = color_cycle[idx % len(color_cycle)]
        bins.append(
            BinConfig(
                name=raw_bin["name"],
                filename=(input_dir / raw_bin["file"]).resolve(),
                include=raw_bin.get("include", True),
                use_scale=raw_bin.get("use_scale_factor", False),
                scale_factor=float(raw_bin["scale_factor"]),
                color=color,
                range_min=raw_bin.get("range", {}).get("min"),
                range_max=raw_bin.get("range", {}).get("max"),
            )
        )

    def sort_key(bin_cfg: BinConfig) -> Tuple[float, float]:
        lower = float(bin_cfg.range_min) if bin_cfg.range_min is not None else float("-inf")
        upper = float(bin_cfg.range_max) if bin_cfg.range_max is not None else float("inf")
        return (lower, upper)

    bins.sort(key=sort_key)
    return bins


def open_root_file(path: Path) -> ROOT.TFile:
    root_file = ROOT.TFile.Open(str(path))
    if not root_file or root_file.IsZombie():
        raise RuntimeError(f"Unable to open ROOT file: {path}")
    return root_file


def clone_and_scale_histogram(
    obj: ROOT.TH1, bin_cfg: BinConfig
) -> ROOT.TH1:
    hist = obj.Clone(f"{obj.GetName()}__{bin_cfg.name}")
    hist.SetDirectory(0)
    scale = bin_cfg.scale_factor if bin_cfg.use_scale else 1.0
    hist.Scale(scale)
    hist.SetLineColor(bin_cfg.color)
    hist.SetMarkerColor(bin_cfg.color)
    hist.SetMarkerStyle(20)
    hist.SetMarkerSize(1.0)
    hist.SetLineWidth(2)
    return hist


def create_weighted_copy(source: Path, weight: float, work_dir: Path) -> Path:
    if weight <= 0.0:
        raise RuntimeError(f"Cannot scale file {source} with non-positive weight {weight}.")
    if not source.exists():
        raise RuntimeError(f"Input ROOT file not found: {source}")

    target = Path(work_dir) / f"{source.stem}_weighted.root"

    src_file = ROOT.TFile.Open(str(source), "READ")
    if not src_file or src_file.IsZombie():
        raise RuntimeError(f"Failed to open input file {source} for scaling.")

    target_file = ROOT.TFile(str(target), "RECREATE")
    if not target_file or target_file.IsZombie():
        src_file.Close()
        raise RuntimeError(f"Failed to create temporary file {target} for scaled copy.")

    def recurse_copy(src_dir, dst_dir) -> None:
        for key in src_dir.GetListOfKeys():
            obj = key.ReadObj()
            if obj.InheritsFrom("TDirectory"):
                dst_dir.cd()
                sub_dir = dst_dir.GetDirectory(key.GetName())
                if not sub_dir:
                    sub_dir = dst_dir.mkdir(key.GetName())
                if not sub_dir:
                    raise RuntimeError(
                        f"Failed to create subdirectory '{key.GetName()}' in temporary file {target}."
                    )
                sub_dir.cd()
                recurse_copy(obj, sub_dir)
            else:
                dst_dir.cd()
                clone = obj.Clone()
                if clone.InheritsFrom("TH1"):
                    clone.Scale(weight)
                    if hasattr(clone, "SetDirectory"):
                        clone.SetDirectory(dst_dir)
                clone.Write()

    recurse_copy(src_file, target_file)
    target_file.Write()
    target_file.Close()
    src_file.Close()
    return target


def _iter_histograms_recursively(root_obj, prefix: str = ""):
    for key in root_obj.GetListOfKeys():
        obj = key.ReadObj()
        name = f"{prefix}/{key.GetName()}" if prefix else key.GetName()
        if obj.InheritsFrom("TDirectory"):
            yield from _iter_histograms_recursively(obj, name)
        elif obj.InheritsFrom("TH1"):
            yield name, obj


def _histogram_name_matches(candidate: str, requested: str) -> bool:
    if candidate == requested:
        return True
    if candidate.split("/")[-1] == requested:
        return True
    return False


def _find_positive_minimum(hist: ROOT.TH1) -> Optional[float]:
    minimum: Optional[float] = None
    for bin_idx in range(1, hist.GetNbinsX() + 1):
        value = hist.GetBinContent(bin_idx)
        if value > 0.0:
            if minimum is None or value < minimum:
                minimum = value
    return minimum


def collect_histograms(
    bins: List[BinConfig],
    histogram_to_draw: Optional[str],
    temp_dir: Path,
    debug: bool = False,
) -> Tuple[
    List[Tuple[BinConfig, ROOT.TH1]],
    str,
    List[Path],
    ROOT.TH1,
]:
    histograms_for_plot: List[Tuple[BinConfig, ROOT.TH1]] = []
    selected_histogram: Optional[str] = None
    scaled_files: List[Path] = []
    combined_hist: Optional[ROOT.TH1] = None

    for bin_cfg in bins:
        if not bin_cfg.include:
            if debug:
                print(f"[INFO] Skipping bin {bin_cfg.name} because include is false.")
            continue
        if not bin_cfg.filename.exists():
            if debug:
                print(f"[WARNING] File for bin {bin_cfg.name} not found: {bin_cfg.filename}")
            continue

        weight = bin_cfg.scale_factor if bin_cfg.use_scale else 1.0
        if weight <= 0.0:
            if debug:
                print(f"[WARNING] Skipping bin {bin_cfg.name} due to non-positive weight {weight}.")
            continue

        if debug:
            print(f"[DEBUG] Processing {bin_cfg.filename} with weight {weight}")

        if math.isclose(weight, 1.0, rel_tol=1e-12, abs_tol=1e-12):
            scaled_path = bin_cfg.filename
        else:
            scaled_path = create_weighted_copy(bin_cfg.filename, weight, temp_dir)
        scaled_files.append(scaled_path)

        root_file = open_root_file(bin_cfg.filename)
        try:
            for full_name, obj in _iter_histograms_recursively(root_file):
                if selected_histogram is None:
                    if histogram_to_draw is None or _histogram_name_matches(full_name, histogram_to_draw):
                        selected_histogram = full_name
                if selected_histogram is None or full_name != selected_histogram:
                    obj.Delete()
                    continue

                hist = clone_and_scale_histogram(obj, bin_cfg)
                obj.Delete()
                histograms_for_plot.append((bin_cfg, hist))
                if combined_hist is None:
                    combined_hist = hist.Clone(f"{hist.GetName()}__sum")
                    combined_hist.SetDirectory(0)
                else:
                    combined_hist.Add(hist)
        finally:
            root_file.Close()

    if selected_histogram is None:
        raise RuntimeError("No histogram found in the provided ROOT files.")
    if combined_hist is None or not histograms_for_plot:
        raise RuntimeError(
            f"Selected histogram '{selected_histogram}' was not found in the included bins."
        )

    return histograms_for_plot, selected_histogram, scaled_files, combined_hist


def draw_histograms(
    histogram_name: str,
    histograms_for_plot: List[Tuple[BinConfig, ROOT.TH1]],
    combined_hist: ROOT.TH1,
    output_pdf: Path,
) -> None:
    canvas = ROOT.TCanvas("c_pthat", "pthat overlay", 900, 700)
    canvas.SetLogy(True)
    legend = ROOT.TLegend(0.58, 0.55, 0.88, 0.88)
    legend.SetBorderSize(0)
    legend.SetFillStyle(0)
    legend.SetTextSize(0.03)

    sum_hist = combined_hist.Clone(f"{histogram_name}_sum_display")
    sum_hist.SetDirectory(0)
    sum_hist.SetLineColor(ROOT.kBlack)
    sum_hist.SetMarkerColor(ROOT.kBlack)
    sum_hist.SetMarkerStyle(24)  # open circle
    sum_hist.SetLineWidth(3)
    sum_hist.SetMarkerSize(1.2)

    first_hist: Optional[ROOT.TH1] = None
    min_positive: Optional[float] = None
    max_value: Optional[float] = None

    for idx, (bin_cfg, hist) in enumerate(histograms_for_plot):
        if first_hist is None:
            first_hist = hist
            first_hist.Draw("PE")
        else:
            hist.Draw("PE SAME")
        legend.AddEntry(
            hist,
            f"{bin_cfg.name}"
            + (
                f" (w={bin_cfg.scale_factor:.3g})"
                if bin_cfg.use_scale and bin_cfg.scale_factor != 1.0
                else ""
            ),
            "p",
        )
        max_bin = hist.GetMaximum()
        min_bin = _find_positive_minimum(hist)
        if max_value is None or max_bin > max_value:
            max_value = max_bin
        if min_bin is not None and min_bin > 0:
            if min_positive is None or min_bin < min_positive:
                min_positive = min_bin

    sum_hist.Draw("PE SAME")
    legend.AddEntry(sum_hist, "Sum", "p")
    max_sum = sum_hist.GetMaximum()
    min_sum = _find_positive_minimum(sum_hist)
    if max_value is None or max_sum > max_value:
        max_value = max_sum
    if min_sum is not None and min_sum > 0:
        if min_positive is None or min_sum < min_positive:
            min_positive = min_sum

    axis_hist = first_hist if first_hist is not None else sum_hist
    if axis_hist is not None and max_value is not None:
        min_for_axis = min_positive if (min_positive is not None and min_positive > 0.0) else max_value * 1e-3
        min_for_axis = max(min_for_axis * 0.5, 1e-6)
        max_for_axis = max_value * 2.0 if max_value > 0 else 1.0
        axis_hist.SetMinimum(min_for_axis)
        axis_hist.SetMaximum(max_for_axis)
        axis_hist.GetYaxis().SetRangeUser(min_for_axis, max_for_axis)
        sum_hist.SetMinimum(min_for_axis)
        sum_hist.SetMaximum(max_for_axis)

    canvas.Modified()
    canvas.Update()
    canvas.RedrawAxis()
    legend.Draw()

    ensure_parent_dir(output_pdf)
    canvas.SaveAs(str(output_pdf))
    output_png = output_pdf.with_suffix(".png")
    canvas.SaveAs(str(output_png))


def run_hadd(output_root: Path, scaled_files: List[Path], debug: bool = False) -> None:
    if not scaled_files:
        raise RuntimeError("No scaled ROOT files were produced; cannot run hadd.")
    ensure_parent_dir(output_root)
    cmd = ["hadd", "-f", str(output_root)] + [str(path) for path in scaled_files]
    if debug:
        print(f"[DEBUG] Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    raw_config = load_config(config_path)

    config_dir = config_path.parent.resolve()
    input_dir = Path(args.input_dir).expanduser() if args.input_dir else config_dir
    output_dir = Path(args.output_dir).expanduser() if args.output_dir else config_dir
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()

    if args.debug:
        print(f"[DEBUG] Using input directory: {input_dir}")
        print(f"[DEBUG] Using output directory: {output_dir}")

    bins = build_bin_configs(raw_config, input_dir=input_dir)
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        (
            histograms_for_plot,
            selected_histogram,
            scaled_files,
            combined_hist,
        ) = collect_histograms(
            bins=bins,
            histogram_to_draw=args.histogram,
            temp_dir=tmp_dir,
            debug=args.debug,
        )

        output_name = Path(args.output_name).name  # ensure we only keep the filename part
        output_root = (output_dir / output_name).resolve()
        output_pdf = output_root.with_suffix(".pdf")

        draw_histograms(
            histogram_name=selected_histogram,
            histograms_for_plot=histograms_for_plot,
            combined_hist=combined_hist,
            output_pdf=output_pdf,
        )

        run_hadd(
            output_root=output_root,
            scaled_files=scaled_files,
            debug=args.debug,
        )

    if args.debug:
        print(f"[INFO] Wrote combined ROOT file to {output_root}")
        print(f"[INFO] Wrote comparison plot to {output_pdf}")
        print(f"[INFO] Drawn histogram: {selected_histogram}")


if __name__ == "__main__":
    main()
