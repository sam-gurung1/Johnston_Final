"""Utility package for Johnston (1991) stereopsis experiment.

This package exposes helper functions for loading stereo stimuli, running
individual trials, and orchestrating the full PsychoPy experiment.  The module
layout intentionally mirrors the sections of a typical student lab so that
components can be reused independently when building new experiments.
"""

from .calibration import (
    MIN_FOCAL_DISTANCE,
    MIN_IOD,
    calc_arm_rotations,
    calc_display_positions,
    calc_eye_positions,
    calc_physical_calibration,
)
from .config import ExperimentConfig
from .stimuli import load_stimulus_pairs
from .trial import ExperimentAbort, run_stereopsis_trial
from .experiment import JohnstonStereoExperiment
from .cli import main as run_experiment

__all__ = [
    "ExperimentConfig",
    "load_stimulus_pairs",
    "run_stereopsis_trial",
    "JohnstonStereoExperiment",
    "run_experiment",
    "ExperimentAbort",
    "calc_display_positions",
    "calc_eye_positions",
    "calc_arm_rotations",
    "calc_physical_calibration",
    "MIN_FOCAL_DISTANCE",
    "MIN_IOD",
]