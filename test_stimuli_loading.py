"""
Dry-run helper to inspect stimulus metadata and haploscope calibration values.

This script loads a small subset of stereo stimuli (without touching PsychoPy),
derives the physical calibration for each, and prints a compact summary so the
values can be confirmed before running the full experiment.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import types
from typing import Sequence

# Avoid importing johnston_rds.__init__ (which pulls in PsychoPy) by registering
# a lightweight package placeholder before loading submodules directly.
REPO_ROOT = Path(__file__).resolve().parent
PKG_NAME = "johnston_rds"
if PKG_NAME not in sys.modules:
    pkg = types.ModuleType(PKG_NAME)
    pkg.__path__ = [str(REPO_ROOT / PKG_NAME)]
    sys.modules[PKG_NAME] = pkg

from johnston_rds.calibration import calc_physical_calibration
from johnston_rds.stimuli import StereoStimulus, load_stimulus_pairs


DEFAULT_IOD_MM = 64.0
DEFAULT_FOCAL_MM = 1070.0


def coerce_float(value: object, default: float) -> float:
    """Return value as float if numeric, otherwise default."""

    if isinstance(value, (int, float)):
        return float(value)
    return default


def describe_stimulus(stimulus: StereoStimulus) -> None:
    """Print a readable summary for ``stimulus``."""

    metadata = stimulus.metadata or {}
    iod = coerce_float(metadata.get("iod_mm"), DEFAULT_IOD_MM)
    focal = coerce_float(metadata.get("focal_distance_mm"), DEFAULT_FOCAL_MM)
    calibration = calc_physical_calibration(iod, focal)

    print(f"Stimulus: {stimulus.stimulus_id}")
    print(f"  Label        : {stimulus.label or '<none>'}")
    print(f"  Images       : L={stimulus.left_image.name}, R={stimulus.right_image.name}")
    print(f"  Metadata keys: {', '.join(sorted(metadata.keys())) or '<none>'}")
    disparity = getattr(stimulus, "disparity_px", None)
    curvature = getattr(stimulus, "curvature_mm", None)
    print(f"  Disparity    : {disparity if disparity is not None else 'n/a'} px")
    print(f"  Curvature    : {curvature if curvature is not None else 'n/a'} mm")
    print(f"  IOD / Focal  : {iod:.2f} mm / {focal:.2f} mm")
    print("  Calibration :")
    for key in sorted(calibration):
        print(f"    {key:<14} {calibration[key]:.4f}")
    print("-")  # separator


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Return parsed CLI arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stimuli-dir",
        type=Path,
        default=Path("stimuli"),
        help="Folder with stereo PNG pairs and JSON sidecars (default: stimuli)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=2,
        help="Number of stimuli to show (default: 2)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Load a few stimuli and print their calibration summaries."""

    args = parse_args(argv)
    stimuli_dir = args.stimuli_dir
    if not stimuli_dir.exists():
        raise SystemExit(f"Stimulus directory '{stimuli_dir}' not found")

    stimuli = load_stimulus_pairs(stimuli_dir)
    if not stimuli:
        raise SystemExit("No stimuli were loaded; verify the directory contains *_L/_R PNGs.")

    limit = max(1, args.limit)
    for stimulus in stimuli[:limit]:
        describe_stimulus(stimulus)


if __name__ == "__main__":  # pragma: no cover - manual test utility
    main()
