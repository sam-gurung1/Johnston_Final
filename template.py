"""Reusable experiment template utilities.

The :class:`BaseExperiment` class provides lightweight helpers for saving
participant information and trial data.  Students can build new experiments by
extending this class and focusing on task-specific logic.
"""
from __future__ import annotations

import csv
import json
import pickle
from dataclasses import dataclass, field
from typing import Dict, Iterable, List


def convert_color_value(rgb_values: Iterable[int]) -> List[float]:
    """Convert 0-255 RGB values to PsychoPy's -1 to 1 colour range."""

    converted = [((value / 255.0) * 2.0) - 1.0 for value in rgb_values]
    return [round(val, 2) for val in converted]


@dataclass
class BaseExperiment:
    """Core functionality for saving experiment data."""

    experiment_name: str
    data_fields: List[str]
    bg_color: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    monitor_name: str = "Experiment Monitor"
    monitor_width: float = 53
    monitor_distance: float = 70

    def __post_init__(self) -> None:
        self.experiment_data: List[Dict[str, object]] = []
        self.experiment_data_filename: str | None = None
        self.data_lines_written: int = 0
        self.experiment_info: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # File naming helpers
    # ------------------------------------------------------------------
    def _default_filename(self, suffix: str) -> str:
        participant = self.experiment_info.get("Subject Number", "000")
        try:
            subject_code = f"{int(participant):03d}"
        except (TypeError, ValueError):
            subject_code = str(participant)
        return f"{self.experiment_name}_{subject_code}{suffix}"

    # ------------------------------------------------------------------
    # Info saving
    # ------------------------------------------------------------------
    def save_experiment_info(self, filename: str | None = None) -> None:
        """Write the participant information to disk as JSON."""

        output_filename = filename or self._default_filename("_info.json")
        with open(output_filename, "w", encoding="utf-8") as info_file:
            json.dump(self.experiment_info, info_file)

    # ------------------------------------------------------------------
    # CSV handling
    # ------------------------------------------------------------------
    def open_csv_data_file(self, data_filename: str | None = None) -> None:
        """Prepare an empty CSV file with the header row."""

        filename = data_filename or self._default_filename(".csv")
        self.experiment_data_filename = filename
        with open(filename, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(self.data_fields)
        self.data_lines_written = 0

    def update_experiment_data(self, rows: Iterable[Dict[str, object]]) -> None:
        """Append new trial rows to the in-memory store."""

        self.experiment_data.extend(rows)

    def save_data_to_csv(self) -> None:
        """Append all accumulated data rows to the CSV file."""

        if not self.experiment_data_filename:
            self.open_csv_data_file()
        assert self.experiment_data_filename is not None
        with open(self.experiment_data_filename, "a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.data_fields)
            for row in self.experiment_data[self.data_lines_written :]:
                writer.writerow(row)
                self.data_lines_written += 1

    # ------------------------------------------------------------------
    # Pickle summary
    # ------------------------------------------------------------------
    def save_experiment_pickle(self) -> None:
        """Persist the experiment state using pickle for quick inspection."""

        pickle_filename = self._default_filename(".pickle")
        payload = {
            "experiment_name": self.experiment_name,
            "data_fields": self.data_fields,
            "bg_color": self.bg_color,
            "monitor_name": self.monitor_name,
            "monitor_width": self.monitor_width,
            "monitor_distance": self.monitor_distance,
            "experiment_data": self.experiment_data,
            "experiment_data_filename": self.experiment_data_filename,
            "data_lines_written": self.data_lines_written,
            "experiment_info": self.experiment_info,
        }
        with open(pickle_filename, "wb") as pickle_file:
            pickle.dump(payload, pickle_file)


__all__ = ["BaseExperiment", "convert_color_value"]
