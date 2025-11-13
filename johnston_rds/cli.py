"""Command line helpers for running the Johnston stereopsis experiment."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .calibration import calc_physical_calibration
from .config import ExperimentConfig
from .experiment import JohnstonStereoExperiment
from .stimuli import DEFAULT_STIMULUS_FOCAL_MM, DEFAULT_STIMULUS_IOD_MM, load_stimulus_pairs

DEFAULT_EXPERIMENTER_SCREEN = ExperimentConfig.__dataclass_fields__[
    "experimenter_screen_index"
].default
DEFAULT_PARTICIPANT_KEYBOARD = ExperimentConfig.__dataclass_fields__[
    "participant_keyboard_name"
].default
DEFAULT_EXPERIMENTER_KEYBOARD = ExperimentConfig.__dataclass_fields__[
    "experimenter_keyboard_name"
].default
DEFAULT_SERIAL_PORT = ExperimentConfig.__dataclass_fields__[
    "participant_serial_port"
].default
DEFAULT_SERIAL_BAUD = ExperimentConfig.__dataclass_fields__[
    "participant_serial_baud"
].default

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
    parser.add_argument(
        "--experimenter-screen-index",
        type=int,
        default=DEFAULT_EXPERIMENTER_SCREEN,
        help=(
            "Screen index used for participant dialogs (default: %(default)s). "
            "Useful when the haploscope display is the OS primary screen."
        ),
    )
    parser.add_argument(
        "--participant-keyboard",
        type=str,
        default=DEFAULT_PARTICIPANT_KEYBOARD,
        help=(
            "Device name for the participant keypad (default: %(default)s which "
            "lets PsychoPy auto-select the primary keyboard)."
        ),
    )
    parser.add_argument(
        "--experimenter-keyboard",
        type=str,
        default=DEFAULT_EXPERIMENTER_KEYBOARD,
        help=(
            "Device name for the experimenter's keyboard used for quit keys "
            "(default: %(default)s meaning reuse the participant keyboard)."
        ),
    )
    parser.add_argument(
        "--participant-serial-port",
        type=str,
        default=DEFAULT_SERIAL_PORT,
        help=(
            "Serial COM port used by the participant keypad (e.g., COM1). "
            "Requires pyserial; if omitted the keypad is ignored."
        ),
    )
    parser.add_argument(
        "--participant-serial-baud",
        type=int,
        default=DEFAULT_SERIAL_BAUD,
        help="Baud rate for the participant serial keypad (default: %(default)s).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Load stimuli, compute calibration values for each, print them, and exit "
            "without launching the PsychoPy experiment."
        ),
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
        experimenter_screen_index=args.experimenter_screen_index,
        participant_keyboard_name=args.participant_keyboard,
        experimenter_keyboard_name=args.experimenter_keyboard,
        participant_serial_port=args.participant_serial_port,
        participant_serial_baud=args.participant_serial_baud,
    )
    if args.dry_run:
        perform_dry_run(config)
        return

    experiment = JohnstonStereoExperiment(config)
    experiment.run()


def perform_dry_run(config: ExperimentConfig) -> None:
    """Print calibration summaries for every stimulus and exit."""

    stimuli = load_stimulus_pairs(config.stimulus_directory)
    if not stimuli:
        print("No stimuli found; nothing to report.")
        return

    def _resolve(value: float | None, override: float | None, default: float) -> float:
        if override is not None:
            return float(override)
        if value is not None:
            return float(value)
        return default

    print(f"Dry-run: {len(stimuli)} stimuli loaded from '{config.stimulus_directory}'.")
    for index, stimulus in enumerate(stimuli, start=1):
        iod = _resolve(stimulus.iod_mm, config.iod_override_mm, DEFAULT_STIMULUS_IOD_MM)
        focal = _resolve(
            stimulus.focal_distance_mm,
            config.focal_override_mm,
            DEFAULT_STIMULUS_FOCAL_MM,
        )
        calibration = calc_physical_calibration(iod, focal)
        print(f"[{index:03}] {stimulus.stimulus_id}")
        print(f"      iod_mm={iod:.2f} | focal_mm={focal:.2f}")
        for key, value in sorted(calibration.items()):
            print(f"      {key:<14}: {value:.4f}")
    print("Dry-run complete.")


if __name__ == "__main__":  # pragma: no cover - module level CLI hook
    main(sys.argv[1:])
