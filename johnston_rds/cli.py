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
    return parser


def main(argv: list[str] | None = None) -> None:
    """Parse command line options and execute the experiment."""

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    config = ExperimentConfig(
        stimulus_directory=str(args.stimuli),
        results_directory=str(args.data_dir),
    )
    experiment = JohnstonStereoExperiment(config)
    experiment.run()


if __name__ == "__main__":  # pragma: no cover - module level CLI hook
    main(sys.argv[1:])