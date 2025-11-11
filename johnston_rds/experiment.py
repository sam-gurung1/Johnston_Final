"""High-level experiment orchestration for the Johnston stereopsis task."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List

from psychopy import core, event, gui, visual
from psychopy.hardware import keyboard

from .config import ExperimentConfig
from .stimuli import load_stimulus_pairs
from .trial import ExperimentAbort, run_stereopsis_trial
from template import BaseExperiment


if TYPE_CHECKING:
    from psychopy.visual.window import Window
    from .stimuli import StereoStimulus
else:  # pragma: no cover - used only for static analysis fallbacks
    Window = Any
    StereoStimulus = Any


class JohnstonStereoExperiment(BaseExperiment):
    """Wrap the Johnston stereopsis task using the reusable BaseExperiment."""

    def __init__(self, config: ExperimentConfig | None = None):
        self.config = config or ExperimentConfig()
        self._global_keys_registered = False
        self._active_windows: Dict[str, Window] | None = None
        super().__init__(
            experiment_name=self.config.experiment_name,
            data_fields=self.config.data_fields,
        )

    # ------------------------------------------------------------------
    # GUI helpers
    # ------------------------------------------------------------------
    def collect_participant_info(self) -> Dict[str, str]:
        """Display an info dialog to collect participant metadata."""

        info = {
            "Participant ID": "",
            "Session": "1",
        }
        dialog = gui.DlgFromDict(info, title="Johnston Stereopsis", fixed=["Session"])
        if not dialog.OK:
            core.quit()
        instruction_dialog = gui.Dlg(title="Instructions")
        instruction_dialog.addText(self.config.instructions_text())
        instruction_dialog.show()
        info["Instructions"] = self.config.instructions_text()
        return info

    # ------------------------------------------------------------------
    # Window creation
    # ------------------------------------------------------------------
    def create_windows(self) -> Dict[str, Window]:
        """Create PsychoPy windows for left and right eyes."""

        common_kwargs = dict(
            size=list(self.config.window_size),
            units=self.config.window_units,
            fullscr=self.config.full_screen,
            allowGUI=False,
            color=list(self.config.background_color),
        )
        win_right = visual.Window(
            **common_kwargs,
            screen=self.config.right_screen_index,
        )
        win_left = visual.Window(
            **common_kwargs,
            screen=self.config.left_screen_index,
        )
        windows = {"left": win_left, "right": win_right}
        self._active_windows = windows
        self._register_global_quit_handler()
        return windows

    def _register_global_quit_handler(self) -> None:
        """Install a global key hook so ESC always shuts down safely."""

        if self._global_keys_registered:
            return

        def _handle_global_quit() -> None:
            print("Global quit key detected. Closing windows and exiting.")
            for win in (self._active_windows or {}).values():
                try:
                    win.close()
                except Exception:
                    pass
            core.quit()

        for key in self.config.quit_keys:
            event.globalKeys.add(key=key, func=_handle_global_quit)
        self._global_keys_registered = True

    # ------------------------------------------------------------------
    # Trial scheduling
    # ------------------------------------------------------------------
    def run_trials(
        self,
        *,
        windows: Dict[str, Window],
        stimuli: Iterable[StereoStimulus],
    ) -> List[Dict[str, object]]:
        """Run each stereopsis trial and return the recorded rows."""

        kb = keyboard.Keyboard()
        trial_data: List[Dict[str, object]] = []

        for index, stimulus in enumerate(stimuli, start=1):
            trial_result = run_stereopsis_trial(
                win_left=windows["left"],
                win_right=windows["right"],
                stimulus=stimulus,
                trial_index=index,
                fixation_duration=self.config.fixation_duration_s,
                stimulus_duration=self.config.stimulus_duration_s,
                response_mapping=self.config.response_keys,
                kb=kb,
                quit_keys=self.config.quit_keys,
                log_calibration=self.config.log_calibration_to_console,
                iod_override_mm=self.config.iod_override_mm,
                focal_override_mm=self.config.focal_override_mm,
            )
            trial_data.append(trial_result)

        return trial_data

    # ------------------------------------------------------------------
    # Data persistence
    # ------------------------------------------------------------------
    def save_results(
        self,
        trial_rows: Iterable[Dict[str, object]],
        *,
        participant_info: Dict[str, str],
    ) -> Path:
        """Save CSV results combining participant info with trial rows."""

        output_dir = Path(self.config.results_directory)
        output_dir.mkdir(parents=True, exist_ok=True)

        participant = participant_info.get("Participant ID", "unknown")
        session = participant_info.get("Session", "1")
        filename = output_dir / f"{self.config.experiment_name}_{participant}_{session}.csv"

        self.open_csv_data_file(data_filename=os.fspath(filename))
        self.update_experiment_data(trial_rows)
        self.save_data_to_csv()

        # Store the participant info alongside the CSV for reference
        info_filename = filename.with_suffix(".json")
        with info_filename.open("w", encoding="utf-8") as info_file:
            json.dump(participant_info, info_file, indent=2)

        return filename

    # ------------------------------------------------------------------
    # Experiment entry point
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Execute the full experiment pipeline."""

        participant_info = self.collect_participant_info()
        subject_number = participant_info.get("Participant ID", "0")
        self.experiment_info["Subject Number"] = subject_number
        self.experiment_info.update(participant_info)
        self.save_experiment_info()

        stimulus_dir = os.fspath(Path(self.config.stimulus_directory))
        stimuli = load_stimulus_pairs(stimulus_dir)

        windows = self.create_windows()
        aborted = False
        try:
            trial_rows = self.run_trials(windows=windows, stimuli=stimuli)
        except ExperimentAbort:
            aborted = True
            trial_rows = []
        finally:
            for win in windows.values():
                win.close()

        if not aborted:
            participant = participant_info.get("Participant ID", "unknown")
            augmented_rows = [
                {**row, "participant": participant}
                for row in trial_rows
            ]

            self.save_results(augmented_rows, participant_info=participant_info)
            self.save_experiment_pickle()

        core.quit()


__all__ = ["JohnstonStereoExperiment"]
