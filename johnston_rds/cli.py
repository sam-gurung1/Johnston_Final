"""Command line helpers for running the Johnston stereopsis experiment."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import ExperimentConfig
from .experiment import JohnstonStereoExperiment


def build_arg_parser() -> argparse.ArgumentParser:
    """Create an argument parser exposing minimal runtime options."""

    parser = argparse.ArgumentParser(
        description=(
            "Launch the Johnston (1991) stereopsis task. "
            "By default the script expects a 'stimuli' folder next to the code."
        )
    )
    parser.add_argument(
        "--stimuli",
        type=Path,
        default=Path("stimuli"),
        help=(
            "Directory containing left/right PNG pairs (default: %(default)s). "
            "Relative paths are resolved from the current working directory."
        ),
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Folder where CSV/JSON/pickle outputs will be saved (default: %(default)s).",
    )
    parser.add_argument(
        "--iod-mm",
        type=float,
        default=None,
        help="Override the interpupillary distance (mm) for all trials.",
    )
    parser.add_argument(
        "--focal-distance-mm",
        type=float,
        default=None,
        help="Override the haploscope focal distance (mm) for all trials.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable single-screen debug mode with centered windows.",
    )
    parser.add_argument(
        "--debug-iod-mm",
        type=float,
        default=None,
        help="IOD value used when debug mode is active (fallback if --iod-mm not supplied).",
    )
    parser.add_argument(
        "--debug-focal-distance-mm",
        type=float,
        default=None,
        help="Focal distance used when debug mode is active (fallback if --focal-distance-mm not supplied).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Parse command line options and execute the experiment."""

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    config = ExperimentConfig(
        stimulus_directory=str(args.stimuli),
        results_directory=str(args.data_dir),
        iod_override_mm=args.iod_mm,
        focal_override_mm=args.focal_distance_mm,
        debug_mode=args.debug,
        debug_iod_mm=args.debug_iod_mm,
        debug_focal_mm=args.debug_focal_distance_mm,
    )
    experiment = JohnstonStereoExperiment(config)
    experiment.run()


if __name__ == "__main__":  # pragma: no cover - module level CLI hook
    main(sys.argv[1:])
