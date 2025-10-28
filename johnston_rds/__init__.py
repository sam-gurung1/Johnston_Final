"""Utility package for Johnston (1991) stereopsis experiment.

This package exposes helper functions for loading stereo stimuli, running
individual trials, and orchestrating the full PsychoPy experiment.  The module
layout intentionally mirrors the sections of a typical student lab so that
components can be reused independently when building new experiments.
"""

from .config import ExperimentConfig
from .stimuli import load_stimulus_pairs
from .trial import run_stereopsis_trial
from .experiment import JohnstonStereoExperiment
from .cli import main as run_experiment

__all__ = [
    "ExperimentConfig",
    "load_stimulus_pairs",
    "run_stereopsis_trial",
    "JohnstonStereoExperiment",
    "run_experiment",
]
