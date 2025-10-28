"""Trial logic for the Johnston stereopsis experiment."""
from __future__ import annotations

from typing import Dict, Optional

from psychopy import core, visual
from psychopy.hardware import keyboard

from .stimuli import StereoStimulus


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

    stim_left = visual.ImageStim(win_left, image=str(stimulus.left_image), units="deg")
    stim_right = visual.ImageStim(win_right, image=str(stimulus.right_image), units="deg")
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
) -> Dict[str, object]:
    """Run a single Johnston stereopsis trial and return the recorded data."""

    _draw_fixation(win_left, win_right, fixation_duration)

    stims = _prepare_stimuli(win_left, win_right, stimulus)
    kb.clearEvents()
    stim_clock = core.Clock()
    response_key: Optional[str] = None
    rt: Optional[float] = None

    while stim_clock.getTime() < stimulus_duration:
        stims["left"].draw()
        stims["right"].draw()
        win_left.flip()
        win_right.flip()

        for key in kb.getKeys(list(response_mapping.keys()), waitRelease=False):
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
            for key in kb.waitKeys(maxWait=5.0, keyList=list(response_mapping.keys())) or []:
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
    }