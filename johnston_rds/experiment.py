"""High-level experiment orchestration for the Johnston stereopsis task."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Tuple

from psychopy import core, event, gui, visual
from psychopy.hardware import keyboard

from .calibration import LEFT_VIEWPORT, MONITOR_SPEC, RIGHT_VIEWPORT, Viewport
from .config import ExperimentConfig
from .serial_keypad import SerialKeypad
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
        if self.config.debug_mode:
            if self.config.iod_override_mm is None and self.config.debug_iod_mm is not None:
                self.config.iod_override_mm = self.config.debug_iod_mm
            if (
                self.config.focal_override_mm is None
                and self.config.debug_focal_mm is not None
            ):
                self.config.focal_override_mm = self.config.debug_focal_mm
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
        dialog_pos = self._experimenter_dialog_position()
        dialog = gui.DlgFromDict(
            info,
            title="Johnston Stereopsis",
            fixed=["Session"],
            screen=-1,
            show=False,
        )
        self._apply_dialog_position(dialog, dialog_pos)
        dialog.show()
        if not dialog.OK:
            core.quit()
        instruction_dialog = gui.Dlg(title="Instructions", screen=-1)
        self._apply_dialog_position(instruction_dialog, dialog_pos)
        instruction_dialog.addText(self.config.instructions_text())
        instruction_dialog.show()
        info["Instructions"] = self.config.instructions_text()
        return info

    # ------------------------------------------------------------------
    # Window creation
    # ------------------------------------------------------------------
    def create_windows(self) -> Dict[str, Window]:
        """Create PsychoPy windows for left and right eyes."""

        window_kwargs = self._window_kwargs()
        win_left = visual.Window(
            **window_kwargs["left"],
            screen=self._left_screen_index(),
        )
        win_right = visual.Window(
            **window_kwargs["right"],
            screen=self._right_screen_index(),
        )

        if not self.config.debug_mode and self.config.use_right_viewport:
            self._apply_window_viewport(win_right, RIGHT_VIEWPORT)
            self._apply_window_viewport(win_left, LEFT_VIEWPORT)

        windows = {"left": win_left, "right": win_right}
        self._active_windows = windows
        self._register_global_quit_handler()
        return windows

    def _window_kwargs(self) -> Dict[str, Dict[str, object]]:
        """Return window kwargs per eye (handles debug + viewport sizing)."""

        base_kwargs = dict(
            units=self.config.window_units,
            allowGUI=self.config.debug_mode,
            color=list(self.config.background_color),
            waitBlanking=not self.config.debug_mode,
        )

        fullscreen_flag = self.config.full_screen and not self.config.debug_mode
        if self.config.debug_mode:
            size = list(self.config.debug_window_size)
            left_kwargs = {**base_kwargs, "size": size, "fullscr": False}
            right_kwargs = {**base_kwargs, "size": size, "fullscr": False}
        else:
            left_size = self._viewport_size(LEFT_VIEWPORT)
            right_size = (
                self._viewport_size(RIGHT_VIEWPORT)
                if self.config.use_right_viewport
                else (MONITOR_SPEC.px_width, MONITOR_SPEC.px_height)
            )
            if fullscreen_flag:
                left_size = (MONITOR_SPEC.px_width, MONITOR_SPEC.px_height)
                right_size = (MONITOR_SPEC.px_width, MONITOR_SPEC.px_height)
            left_kwargs = {
                **base_kwargs,
                "size": list(left_size),
                "fullscr": fullscreen_flag,
            }
            right_kwargs = {
                **base_kwargs,
                "size": list(right_size),
                "fullscr": fullscreen_flag,
            }

        return {"left": left_kwargs, "right": right_kwargs}

    def _left_screen_index(self) -> int:
        if self.config.debug_mode:
            return self.config.debug_screen_index
        return self.config.left_screen_index

    def _right_screen_index(self) -> int:
        if self.config.debug_mode:
            return self.config.debug_screen_index
        return self.config.right_screen_index

    @staticmethod
    def _viewport_size(viewport: Viewport) -> Tuple[int, int]:
        return viewport.end_x - viewport.start_x, viewport.end_y - viewport.start_y

    def _apply_window_viewport(self, window: Window, viewport: Viewport) -> None:
        """Configure PsychoPy viewport/scissor rectangles for the given window."""

        width, height = self._viewport_size(viewport)
        if width <= 0 or height <= 0:
            raise ValueError("Viewport width/height must be positive")
        bounds = [
            viewport.start_x,
            viewport.start_y,
            width,
            height,
        ]
        window.viewport = bounds
        window.scissor = bounds
        window.scissorTest = True

    def _experimenter_dialog_position(self) -> Tuple[int, int] | None:
        """Return a dialog position anchored to the experimenter's monitor."""

        screen_index = self.config.experimenter_screen_index
        if screen_index < 0:
            return None
        try:
            from psychopy.gui import qtgui

            qtgui.ensureQtApp()
            app = qtgui.qtapp
            screens = app.screens() if app is not None else []
            target = screens[screen_index]
            geometry = target.availableGeometry()
        except Exception:
            return None
        # offset a little from the top-left to avoid hiding behind taskbars
        return geometry.x() + 120, geometry.y() + 120

    @staticmethod
    def _apply_dialog_position(dialog: gui.Dlg, position: Tuple[int, int] | None) -> None:
        """Assign a manual window position before showing the dialog."""

        if position is not None:
            dialog.pos = position

    @staticmethod
    def _create_keyboard(
        device_name: str | None,
        *,
        allow_disable: bool = False,
    ) -> keyboard.Keyboard | None:
        """Return a PsychoPy keyboard device (or None if disabled)."""

        if isinstance(device_name, str):
            normalized = device_name.strip().lower()
            if allow_disable and normalized in {"", "none", "disabled"}:
                return None
            if normalized in {"", "default", "auto"}:
                return keyboard.Keyboard()
            return keyboard.Keyboard(deviceName=device_name)
        # No name supplied: use default keyboard
        return keyboard.Keyboard()

    def _create_serial_keypad(self) -> SerialKeypad | None:
        """Instantiate the serial keypad if configured."""

        port = self.config.participant_serial_port
        if not port:
            return None
        try:
            return SerialKeypad(
                port=port,
                baudrate=self.config.participant_serial_baud,
            )
        except Exception as exc:
            print(f"Warning: could not open serial keypad on {port}: {exc}")
            return None

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
        serial_keypad: SerialKeypad | None,
    ) -> List[Dict[str, object]]:
        """Run each stereopsis trial and return the recorded rows."""

        response_kb = self._create_keyboard(
            self.config.participant_keyboard_name,
            allow_disable=True,
        )
        if response_kb is None and serial_keypad is None:
            raise RuntimeError(
                "No participant input device configured. Set --participant-keyboard or --participant-serial-port."
            )
        quit_kb = self._create_keyboard(
            self.config.experimenter_keyboard_name,
            allow_disable=False,
        )
        trial_data: List[Dict[str, object]] = []

        for index, stimulus in enumerate(stimuli, start=1):
            trial_result = run_stereopsis_trial(
                win_left=windows["left"],
                win_right=windows["right"],
                stimulus=stimulus,
                trial_index=index,
                fixation_duration=self.config.fixation_duration_s,
                stimulus_duration=self.config.stimulus_duration_s,
                prompt_display_duration=self.config.prompt_display_duration_s,
                response_mapping=self.config.response_keys,
                response_kb=response_kb,
                quit_kb=quit_kb,
                serial_keypad=serial_keypad,
                quit_keys=self.config.quit_keys,
                log_calibration=self.config.log_calibration_to_console,
                iod_override_mm=self.config.iod_override_mm,
                focal_override_mm=self.config.focal_override_mm,
            )
            trial_data.append(trial_result)

        return trial_data

    def _run_break(self, windows: Dict[str, Window]) -> None:
        """Display a break screen with a timer and optional resume key."""

        duration = max(1.0, float(self.config.break_duration_s))
        resume_key = (self.config.break_resume_key or "").strip()
        message = self.config.break_message.format(key=resume_key or "any key")

        kb = keyboard.Keyboard()
        timer = core.Clock()
        wrap_left = windows["left"].size[0] * 0.8 if windows["left"].units == "pix" else None
        wrap_right = windows["right"].size[0] * 0.8 if windows["right"].units == "pix" else None
        text_left = visual.TextStim(
            windows["left"],
            text="",
            color="white",
            height=0.75 if windows["left"].units != "pix" else 32,
            wrapWidth=wrap_left,
        )
        text_right = visual.TextStim(
            windows["right"],
            text="",
            color="white",
            height=0.75 if windows["right"].units != "pix" else 32,
            wrapWidth=wrap_right,
        )
        while True:
            remaining = max(0.0, duration - timer.getTime())
            line = f"{message}\n\nTime remaining: {int(round(remaining))} s"
            text_left.text = line
            text_right.text = line
            text_left.draw()
            text_right.draw()
            windows["left"].flip()
            windows["right"].flip()
            if resume_key:
                for key in kb.getKeys([resume_key], waitRelease=False):
                    if key.name == resume_key:
                        return
            if remaining <= 0:
                break
            core.wait(0.1)

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
        max_trials = max(1, self.config.max_trials)
        stimuli = stimuli[:max_trials]

        serial_keypad = self._create_serial_keypad()
        windows = self.create_windows()
        aborted = False
        trial_rows: List[Dict[str, object]] = []
        try:
            break_after = self.config.break_after_trials
            if 0 < break_after < len(stimuli):
                first_block = stimuli[:break_after]
                second_block = stimuli[break_after:]
            else:
                first_block = stimuli
                second_block = []

            trial_rows.extend(
                self.run_trials(
                    windows=windows,
                    stimuli=first_block,
                    serial_keypad=serial_keypad,
                )
            )
            if second_block:
                self._run_break(windows)
                trial_rows.extend(
                    self.run_trials(
                        windows=windows,
                        stimuli=second_block,
                        serial_keypad=serial_keypad,
                    )
                )
        except ExperimentAbort:
            aborted = True
            trial_rows = []
        finally:
            for win in windows.values():
                win.close()
            if serial_keypad:
                serial_keypad.close()

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
