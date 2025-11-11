"""Configuration helpers for the Johnston stereopsis experiment.

The :class:`ExperimentConfig` dataclass stores the user-editable parameters for
running the PsychoPy dual-screen haploscope task.  Keeping these values in a
separate module makes it easy for students to discover what can be tweaked
without touching the trial or data management code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass
class ExperimentConfig:
    """Container for experiment parameters and runtime options."""

    experiment_name: str = "johnston_stereopsis"
    data_fields: List[str] = field(
        default_factory=lambda: [
            "participant",
            "trial_index",
            "stimulus_id",
            "stimulus_label",
            "response_key",
            "response_label",
            "rt_s",
            "stimulus_duration_s",
            "fixation_duration_s",
            "left_image",
            "right_image",
            "stimulus_metadata",
            "calibration_metadata",
        ]
    )
    stimulus_duration_s: float = 1.5
    fixation_duration_s: float = 0.75
    prompt_display_duration_s: float = 0.75
    response_keys: Dict[str, str] = field(
        default_factory=lambda: {"1": "squashed", "2": "stretched"}
    )
    stimulus_directory: str = "stimuli"
    results_directory: str = "data"
    left_screen_index: int = 1
    right_screen_index: int = 0
    full_screen: bool = True
    window_size: Tuple[int, int] = (1280, 720)
    window_units: str = "pix"
    background_color: Sequence[float] = (0.0, 0.0, 0.0)
    quit_keys: Tuple[str, ...] = ("escape",)
    log_calibration_to_console: bool = False
    iod_override_mm: Optional[float] = None
    focal_override_mm: Optional[float] = None
    use_right_viewport: bool = True
    debug_mode: bool = False
    debug_window_size: Tuple[int, int] = (1024, 768)
    debug_screen_index: int = 0
    debug_iod_mm: Optional[float] = None
    debug_focal_mm: Optional[float] = None

    def instructions_text(self) -> str:
        """Return an instruction string for the on-screen dialog."""

        option_lines = [f"{key} = {label}" for key, label in self.response_keys.items()]
        options = "\n".join(option_lines)
        return (
            "Johnston (1991) Stereo Shape Distortion Task\n\n"
            "Participants judge whether the half-cylinder appears squashed or "
            "stretched.\n\n"
            f"Response keys:\n{options}\n\n"
            "Stimuli are shown for 1.5 s with a fixation cross beforehand.\n"
            "Press ESC at any time to exit early."
        )
    
