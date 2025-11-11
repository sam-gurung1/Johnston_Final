from __future__ import annotations

import json
from typing import Dict, Iterable, Optional, Sequence

from psychopy import core, visual
from psychopy.hardware import keyboard

from .calibration import calc_physical_calibration
from .stimuli import StereoStimulus


class ExperimentAbort(Exception):
    """Raised when the participant issues a quit command (e.g., presses ESC)."""


DEFAULT_IOD_MM: float = 64.0
DEFAULT_FOCAL_DISTANCE_MM: float = 1070.0


def _coerce_float(value: object, default: float) -> float:
    """Return ``value`` as a float if numeric, otherwise ``default``."""

    if isinstance(value, (int, float)):
        return float(value)
    return default


def _calibration_inputs(
    stimulus: StereoStimulus,
    iod_override_mm: float | None,
    focal_override_mm: float | None,
) -> tuple[float, float]:
    """Extract IOD and focal distance from overrides or stimulus metadata."""

    metadata = stimulus.metadata or {}
    iod = (
        float(iod_override_mm)
        if iod_override_mm is not None
        else _coerce_float(metadata.get("iod_mm"), DEFAULT_IOD_MM)
    )
    focal = (
        float(focal_override_mm)
        if focal_override_mm is not None
        else _coerce_float(metadata.get("focal_distance_mm"), DEFAULT_FOCAL_DISTANCE_MM)
    )
    return iod, focal


def _build_trial_calibration(
    stimulus: StereoStimulus,
    *,
    iod_override_mm: float | None,
    focal_override_mm: float | None,
) -> Dict[str, float]:
    """Prepare the calibration payload for a single trial."""

    iod, focal = _calibration_inputs(stimulus, iod_override_mm, focal_override_mm)
    hardware = calc_physical_calibration(iod, focal)
    payload: Dict[str, float] = {"iod_mm": iod, "focal_distance_mm": focal}
    payload.update(hardware)
    return payload


def _draw_fixation(win_left: visual.Window, win_right: visual.Window, duration: float) -> None:
    """Draw a fixation cross in both eyes for ``duration`` seconds."""

    fixation_left = visual.TextStim(win_left, text="+", height=0.75, color="white")
    fixation_right = visual.TextStim(win_right, text="+", height=0.75, color="white")

    fixation_left.draw()
    fixation_right.draw()
    win_left.flip()
    win_right.flip()
    core.wait(duration)


def _prepare_stimuli(
    win_left: visual.Window, win_right: visual.Window, stimulus: StereoStimulus
) -> Dict[str, visual.ImageStim]:
    """Create PsychoPy ImageStim objects for the current trial."""

    stim_left = visual.ImageStim(
        win_left,
        image=str(stimulus.left_image),
        units=win_left.units,
    )
    stim_right = visual.ImageStim(
        win_right,
        image=str(stimulus.right_image),
        units=win_right.units,
    )
    return {"left": stim_left, "right": stim_right}


def run_stereopsis_trial(
    *,
    win_left: visual.Window,
    win_right: visual.Window,
    stimulus: StereoStimulus,
    trial_index: int,
    fixation_duration: float,
    stimulus_duration: float,
    response_mapping: Dict[str, str],
    kb: keyboard.Keyboard,
    quit_keys: Sequence[str] = ("escape",),
    log_calibration: bool = False,
    iod_override_mm: float | None = None,
    focal_override_mm: float | None = None,
) -> Dict[str, object]:
    """Run a single Johnston stereopsis trial and return the recorded data.

    Calibration values are recomputed per trial and stored in the returned row.
    ``iod_override_mm``/``focal_override_mm`` take precedence over stimulus metadata.
    Set ``log_calibration`` to ``True`` to echo these values to the PsychoPy console.
    """

    trial_calibration = _build_trial_calibration(
        stimulus,
        iod_override_mm=iod_override_mm,
        focal_override_mm=focal_override_mm,
    )
    if log_calibration:
        print(f"Trial {trial_index} calibration: {trial_calibration}")

    _draw_fixation(win_left, win_right, fixation_duration)

    stims = _prepare_stimuli(win_left, win_right, stimulus)
    kb.clearEvents()
    stim_clock = core.Clock()
    response_key: Optional[str] = None
    rt: Optional[float] = None

    key_list: Iterable[str]
    if quit_keys:
        key_list = list(dict.fromkeys([*response_mapping.keys(), *quit_keys]))
    else:
        key_list = list(response_mapping.keys())

    while stim_clock.getTime() < stimulus_duration:
        stims["left"].draw()
        stims["right"].draw()
        win_left.flip()
        win_right.flip()

        for key in kb.getKeys(key_list, waitRelease=False):
            if key.name in quit_keys:
                raise ExperimentAbort(f"Quit key '{key.name}' pressed")
            response_key = key.name
            rt = key.rt
            break
        if response_key is not None:
            break

    # Show fixation while waiting for response if none collected yet
    if response_key is None:
        _draw_fixation(win_left, win_right, 0)
        waiting_clock = core.Clock()
        while response_key is None:
            for key in kb.waitKeys(maxWait=5.0, keyList=list(key_list)) or []:
                if key.name in quit_keys:
                    raise ExperimentAbort(f"Quit key '{key.name}' pressed")
                response_key = key.name
                rt = stim_clock.getTime() + waiting_clock.getTime()
                break
            if response_key is None:
                # Keep the fixation cross visible while we wait
                fixation_left = visual.TextStim(win_left, text="+", height=0.75, color="white")
                fixation_right = visual.TextStim(win_right, text="+", height=0.75, color="white")
                fixation_left.draw()
                fixation_right.draw()
                win_left.flip()
                win_right.flip()

    response_label = response_mapping.get(response_key, "") if response_key else ""

    return {
        "trial_index": trial_index,
        "stimulus_id": stimulus.stimulus_id,
        "stimulus_label": stimulus.label or "",
        "response_key": response_key or "",
        "response_label": response_label,
        "rt_s": rt if rt is not None else float("nan"),
        "stimulus_duration_s": stimulus_duration,
        "fixation_duration_s": fixation_duration,
        "left_image": str(stimulus.left_image),
        "right_image": str(stimulus.right_image),
        "stimulus_metadata": stimulus.metadata_as_json(),
        "calibration_metadata": json.dumps(trial_calibration, sort_keys=True),
    }


__all__ = ["run_stereopsis_trial", "ExperimentAbort"]
