#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import List, Sequence


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Pythia configuration files from a JSON specification."
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the JSON configuration file describing pTHat ranges and events.",
    )
    return parser.parse_args()


def load_json_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def format_setting_value(value: float, precision: int) -> str:
    if value == -1:
        return "-1"
    formatted = f"{value:.{precision}f}".rstrip("0").rstrip(".")
    if "." not in formatted:
        formatted += ".0"
    return formatted


def format_filename_value(value: float, precision: int) -> str:
    if value == -1:
        return "infy"
    formatted = f"{value:.{precision}f}".rstrip("0").rstrip(".")
    return formatted.replace(".", "_")


def build_line(original_line: str, key: str, value: str) -> str:
    comment_text = ""
    line_without_newline = original_line.rstrip("\n")
    if "!" in line_without_newline:
        before_comment, comment = line_without_newline.split("!", 1)
        line_without_newline = before_comment.rstrip()
        comment_text = "!" + comment.rstrip()
    new_line = f"{key} = {value}"
    if comment_text:
        new_line = f"{new_line:<40} {comment_text}"
    return new_line + ("\n" if original_line.endswith("\n") else "")


def update_setting(lines: List[str], key: str, value: str) -> None:
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("!"):
            continue
        if stripped.startswith(f"{key} "):
            lines[index] = build_line(line, key, value)
            return
    raise KeyError(f"Setting '{key}' not found in template.")


def generate_output_filename(base_name: str, pt_min: float, pt_max: float, precision: int) -> str:
    min_token = format_filename_value(pt_min, precision)
    max_token = format_filename_value(pt_max, precision)
    return f"{base_name}_pthat_{min_token}_{max_token}.cmnd"


def ensure_triplet(entry: Sequence[float]) -> Sequence[float]:
    if len(entry) != 3:
        raise ValueError(f"Each pTHat entry must contain [min, max, events], got: {entry}")
    return entry


def main() -> None:
    args = parse_arguments()
    config_path = Path(args.config).expanduser().resolve()
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    config = load_json_config(config_path)
    config_dir = config_path.parent

    default_template_path = Path(config["default_config"])
    if not default_template_path.is_absolute():
        default_template_path = (config_dir / default_template_path).resolve()
    if not default_template_path.is_file():
        raise FileNotFoundError(f"Template file not found: {default_template_path}")

    output_dir = Path(config.get("output_dir", "generated_configs"))
    if not output_dir.is_absolute():
        output_dir = (config_dir / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    precision = int(config.get("precision", 2))

    default_lines = default_template_path.read_text(encoding="utf-8").splitlines(keepends=True)

    default_stem = default_template_path.stem
    if default_stem.startswith("default_"):
        base_name = default_stem[len("default_") :]
    else:
        base_name = default_stem
    if not base_name.startswith("pythia_config"):
        base_name = f"pythia_config_{base_name}"

    pthats_events = config.get("pthats_events", [])
    if not pthats_events:
        raise ValueError("No 'pthats_events' entries found in configuration.")

    for entry in pthats_events:
        pt_min, pt_max, events = ensure_triplet(entry)
        lines = list(default_lines)

        events_value = str(int(events))
        pt_min_value = format_setting_value(pt_min, precision)
        pt_max_value = format_setting_value(pt_max, precision)

        update_setting(lines, "Main:numberOfEvents", events_value)
        update_setting(lines, "PhaseSpace:pTHatMin", pt_min_value)
        update_setting(lines, "PhaseSpace:pTHatMax", pt_max_value)

        output_filename = generate_output_filename(base_name, pt_min, pt_max, precision)
        output_path = output_dir / output_filename
        output_path.write_text("".join(lines), encoding="utf-8")
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
