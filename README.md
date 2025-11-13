# Johnston Stereopsis Experiment

This repository bundles a PsychoPy implementation of the Johnston (1991) stereopsis task plus a few helper scripts for inspecting stimuli and calibration values. The goal of this README is to give new lab members – even if they are still getting comfortable with Python/PsychoPy – enough context to set up the environment, understand the code layout, and run the experiment safely.

---

## Repository layout

| Path | Purpose |
|------|---------|
| `run_johnston_stereopsis.py` | Thin wrapper that launches the experiment (equivalent to `python -m johnston_rds`). |
| `johnston_rds/` | Main package containing configuration, calibration math, trial logic, CLI entry point, etc. |
| `stimuli/` | Left/right PNG pairs plus optional JSON sidecars. Populate this with your rendered cylinder stimuli. |
| `template.py` | Generic BaseExperiment helpers used by multiple lab projects (CSV logging, info dialogs, etc.). |
| `test_stimuli_loading.py` | Dry‑run utility that prints metadata/calibration info for a sampling of stimuli without invoking PsychoPy. |

Key modules inside `johnston_rds/`:

- `config.py` – user‑tweakable parameters (screen indices, durations, debug flags, etc.).
- `calibration.py` – math for mapping IOD/focal distances to the haploscope’s mechanical positions.
- `experiment.py` – orchestration layer that loads stimuli, opens windows, runs trials, and saves results.
- `trial.py` – single‑trial routine (fixation → stimulus → prompt → response).
- `cli.py` – argument parser so you can select debug mode, override IOD/focal distances, choose data directories, etc.

---

## Getting started

1. **Create a Python environment**
   ```powershell
   py -3.10 -m venv .venv
   .\.venv\Scripts\activate
   pip install psychopy
   ```
   (Install any additional dependencies your lab standardizes on – e.g., `numpy`, `pandas`, etc. – but PsychoPy is the only hard requirement for this repo.)

2. **Populate the stimuli folder**  
   Place your stereo image pairs (named `*_L.png` and `*_R.png`) inside `stimuli/`. If you have metadata (curvature, disparity, etc.), add JSON files with the same base name (e.g., `stim_convex_mild.json`). You can verify things load correctly via:
   ```powershell
   python test_stimuli_loading.py --limit 5
   ```

3. **Create a PsychoPy monitor profile**  
   Open PsychoPy → Tools → Monitor Center, click **New**, enter `testMonitor` (or whatever name you plan to use), and fill in physical width/height (in cm) plus screen resolution. Save it. This prevents warnings like “Monitor specification not found. Creating a temporary one…”. If you choose a different monitor name, update `monitor_name` in `johnston_rds/config.py` or pass it in when creating `ExperimentConfig` yourself.

4. **Plan your screen layout**
   - `left_screen_index` / `right_screen_index` default to 1/0 (matching the Johnston haploscope arrangement). Adjust if your OS numbers monitors differently.
   - `experimenter_screen_index` controls where the info dialogs appear. Use the CLI flag `--experimenter-screen-index` if the participant display is the OS “primary” monitor and you want dialogs on the third monitor, for example.

5. **Run the experiment**
   ```powershell
   python run_johnston_stereopsis.py --stimuli stimuli --data-dir data
   ```
   Useful flags:
- `--debug` – single-screen mode (both eyes centered, no viewports, windowed). Great for quick checks without dual monitors.
- `--iod-mm` / `--focal-distance-mm` – override the mechanical settings that feed the calibration math.
- `--experimenter-screen-index` – choose which monitor displays the participant info and instruction dialogs.
- `--participant-keyboard` / `--experimenter-keyboard` – optional device names (as reported by `psychopy.hardware.keyboard.getDevices()`) if you want a dedicated keypad for responses and a different keyboard for ESC.
- `--dry-run` – skip PsychoPy entirely; just load stimuli, compute calibration values for each (honouring metadata/defaults), print them, and exit. Handy for verifying JSON sidecars before lab time.

### Trial counts & breaks

By default the task runs the first **60** stimuli it finds. After the first **30** trials the code automatically inserts a two-minute break so participants can rest. A countdown timer is shown on both screens during the break; pressing the `3` key resumes early. Adjust these values in `ExperimentConfig` (`max_trials`, `break_after_trials`, `break_duration_s`, `break_resume_key`, and `break_message`) if you need a different schedule.

---

## How the experiment flows

1. `run_johnston_stereopsis.py` imports `johnston_rds.cli` and calls `main()`.
2. `cli.py` parses command‑line arguments and instantiates `ExperimentConfig` with those values.
3. `ExperimentConfig` feeds into `JohnstonStereoExperiment` (`experiment.py`):
   - Collects participant info via PsychoPy dialogs (`collect_participant_info`).
   - Loads stimuli (`stimuli.load_stimulus_pairs`).
   - Creates two PsychoPy windows (`create_windows`), applying viewports if you’re using the haploscope hardware.
   - Runs `run_trials`, which simply loops over stimuli and calls `trial.run_stereopsis_trial` for each one.
4. `trial.py` handles:
   - Fixation cross display.
   - Stimulus presentation to left/right windows.
   - Prompt text (“Does the shape appear squashed or stretched?”) plus response capture via PsychoPy’s keyboard device.
   - ESC detection (with a clean shutdown) and frame timing.
   - Returning a results dictionary (response key, RT, metadata, calibration measurements, etc.).
5. After all trials, `experiment.py` writes CSV/JSON outputs, pickles experiment state via `template.BaseExperiment`, and closes PsychoPy.

---

## Debugging tips

- **No stimulus showing up?** Ensure you’re not stuck in the prompt loop waiting for a response. In debug mode (`--debug`), the windows are windowed and you can see both eyes on one monitor. Outside debug mode, the right viewport is a narrow strip; make sure you’ve set the correct screen indices so each window lands on its monitor.
- **Monitor warnings** mean PsychoPy fell back to a temporary profile. Double‑check the monitor name or create one via Monitor Center.
- **Unknown key code warnings** indicate PsychoPy saw an input device it didn’t recognize. Confirm you’re using the intended keyboard (via `--participant-keyboard`) and that the keypad enumerates as an HID keyboard. If it behaves like a serial device, you’ll need a hardware adapter that presents keypresses as standard keyboard events.
- **Force quit** – ESC always works thanks to `event.globalKeys` and the trial quit logic. If the experiment seems frozen, press ESC on the experimenter keyboard.

---

## Extending the experiment

- **Changing timing** – Edit the durations in `ExperimentConfig` (`stimulus_duration_s`, `fixation_duration_s`, `prompt_display_duration_s`). They propagate everywhere automatically.
- **Adding new stimuli metadata** – Update the loader in `stimuli.py` if you want to parse new JSON fields, and log them via `trial.py` or `experiment.py` as needed.
- **Alternate response mappings** – Modify `response_keys` in `ExperimentConfig`. The instructions dialog pulls from that dict, so participants always see the correct key labels.

---

## Need help?

If PsychoPy throws errors about missing libraries or monitor specs, run the app once outside this repo to make sure it initializes properly (PsychoPy will create preference folders, etc.). For deeper issues (OpenGL, screen ordering, custom hardware), document your OS + GPU + PsychoPy version and share logs with the lab’s technical lead. This README stays intentionally high‑level so you can extend it as the project evolves. Happy experimenting! 🎯
