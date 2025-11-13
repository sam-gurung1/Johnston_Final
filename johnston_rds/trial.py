from __future__ import annotations

import json
from typing import Dict, Iterable, List, Optional, Sequence

from psychopy import core, visual
from psychopy.hardware import keyboard

from .calibration import MONITOR_SPEC, calc_physical_calibration
from .serial_keypad import SerialKeypad
from .stimuli import StereoStimulus


class ExperimentAbort(Exception):
    """Raised when the participant issues a quit command (e.g., presses ESC)."""


DEFAULT_IOD_MM: float = 64.0
DEFAULT_FOCAL_DISTANCE_MM: float = 600.0


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
    iod_candidate = (
        stimulus.iod_mm
        if getattr(stimulus, "iod_mm", None) is not None
        else (metadata.get("iod_mm") if metadata else None)
    )
    focal_candidate = (
        stimulus.focal_distance_mm
        if getattr(stimulus, "focal_distance_mm", None) is not None
        else (metadata.get("focal_distance_mm") if metadata else None)
    )
    iod = (
        float(iod_override_mm)
        if iod_override_mm is not None
        else _coerce_float(iod_candidate, DEFAULT_IOD_MM)
    )
    focal = (
        float(focal_override_mm)
        if focal_override_mm is not None
        else _coerce_float(focal_candidate, DEFAULT_FOCAL_DISTANCE_MM)
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


def _fixation_radius(win: visual.Window) -> float:
    """Return a reasonable fixation marker radius in the window's units."""

    if win.units == "pix":
        return 10.0
    return 0.2


def _draw_fixation(win_left: visual.Window, win_right: visual.Window, duration: float) -> None:
    """Draw a fixation cross in both eyes for ``duration`` seconds."""

    marker_left = visual.Circle(
        win_left,
        radius=_fixation_radius(win_left),
        fillColor="white",
        lineColor="white",
        edges=64,
    )
    marker_right = visual.Circle(
        win_right,
        radius=_fixation_radius(win_right),
        fillColor="white",
        lineColor="white",
        edges=64,
    )
    fixation_left = visual.TextStim(win_left, text="+", height=0.75, color="white")
    fixation_right = visual.TextStim(win_right, text="+", height=0.75, color="white")

    marker_left.draw()
    marker_right.draw()
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


def _draw_stimuli(stims: Dict[str, visual.ImageStim]) -> None:
    stims["left"].draw()
    stims["right"].draw()


def _ensure_window_focus(win: visual.Window) -> None:
    """Try to bring ``win`` to the foreground so participant input is captured."""

    win_handle = getattr(win, "winHandle", None)
    if win_handle is None:
        return
    try:
        win_handle.activate()
    except Exception:
        pass


def _show_prompt_block(
    *,
    stims: Dict[str, visual.ImageStim],
    win_left: visual.Window,
    win_right: visual.Window,
    duration: float,
    response_kb: keyboard.Keyboard | None,
    quit_kb: keyboard.Keyboard | None,
    quit_keys: Sequence[str],
) -> None:
    """Display the prompt for ``duration`` seconds before collecting responses."""

    if duration <= 0:
        return

    block_clock = core.Clock()
    quit_list = list(quit_keys)
    quit_device = quit_kb or response_kb
    while block_clock.getTime() < duration:
        _draw_stimuli(stims)
        win_left.flip()
        win_right.flip()
        if quit_device and quit_list:
            for key in quit_device.getKeys(quit_list, waitRelease=False):
                if key.name in quit_list:
                    raise ExperimentAbort(f"Quit key '{key.name}' pressed")
        core.wait(0.01)


def run_stereopsis_trial(
    *,
    win_left: visual.Window,
    win_right: visual.Window,
    stimulus: StereoStimulus,
    trial_index: int,
    fixation_duration: float,
    stimulus_duration: float,
    prompt_display_duration: float,
    response_mapping: Dict[str, str],
    response_kb: keyboard.Keyboard | None,
    quit_kb: keyboard.Keyboard | None,
    serial_keypad: SerialKeypad | None,
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

    _ensure_window_focus(win_right)
    trial_calibration = _build_trial_calibration(
        stimulus,
        iod_override_mm=iod_override_mm,
        focal_override_mm=focal_override_mm,
    )
    print(f"Trial {trial_index} ({stimulus.stimulus_id}) calibration: {trial_calibration}")

    _draw_fixation(win_left, win_right, fixation_duration)

    stims = _prepare_stimuli(win_left, win_right, stimulus)
    if response_kb:
        response_kb.clearEvents()
    if quit_kb and quit_kb is not response_kb:
        quit_kb.clearEvents()
    stim_clock = core.Clock()
    response_key: Optional[str] = None
    rt: Optional[float] = None

    response_keys: List[str] = list(response_mapping.keys())
    quit_list: List[str] = list(quit_keys)
    quit_device = quit_kb or response_kb

    while stim_clock.getTime() < stimulus_duration:
        stims["left"].draw()
        stims["right"].draw()
        win_left.flip()
        win_right.flip()

        if response_kb:
            for key in response_kb.getKeys(response_keys, waitRelease=False):
                response_key = key.name
                rt = key.rt
                break
        if response_key is not None:
            break
        if serial_keypad:
            serial_key = serial_keypad.poll(response_keys)
            if serial_key is not None:
                response_key = serial_key
                rt = stim_clock.getTime()
                break
        if quit_device and quit_list:
            for key in quit_device.getKeys(quit_list, waitRelease=False):
                if key.name in quit_list:
                    raise ExperimentAbort(f"Quit key '{key.name}' pressed")

    # Show prompt and wait for response if none collected yet
    if response_key is None:
        _show_prompt_block(
            stims=stims,
            win_left=win_left,
            win_right=win_right,
            duration=prompt_display_duration,
            response_kb=response_kb,
            quit_kb=quit_kb,
            quit_keys=quit_keys,
        )
        waiting_clock = core.Clock()
        _ensure_window_focus(win_right)
        while response_key is None:
            _draw_stimuli(stims)
            win_left.flip()
            win_right.flip()
            pressed = []
            if response_kb:
                pressed = response_kb.getKeys(response_keys, waitRelease=False)
            if pressed:
                response_key = pressed[0].name
                rt = stim_clock.getTime() + waiting_clock.getTime()
                break
            if serial_keypad:
                serial_key = serial_keypad.poll(response_keys)
                if serial_key is not None:
                    response_key = serial_key
                    rt = stim_clock.getTime() + waiting_clock.getTime()
                    break
            if quit_device and quit_list:
                for key in quit_device.getKeys(quit_list, waitRelease=False):
                    if key.name in quit_list:
                        raise ExperimentAbort(f"Quit key '{key.name}' pressed")
            core.wait(0.01)

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
