"""Stimulus loading utilities for Johnston stereopsis task.

The loader expects stereo image pairs saved as PNG files with suffixes
``_L.png`` and ``_R.png``.  Optional JSON sidecar files can be used to attach
parameters (for example, cylinder curvature) to each stimulus.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class StereoStimulus:
    """Metadata for a single left/right image pair."""

    stimulus_id: str
    left_image: Path
    right_image: Path
    label: Optional[str] = None
    metadata: Dict[str, object] | None = None
    disparity_px: Optional[float] = None
    curvature_mm: Optional[float] = None

    def metadata_as_json(self) -> str:
        """Return the metadata dictionary as a compact JSON string."""

        if not self.metadata:
            return "{}"
        return json.dumps(self.metadata, sort_keys=True)


def _infer_label(stimulus_id: str, metadata: Dict[str, object] | None) -> Optional[str]:
    """Derive a human-readable label from metadata or the stimulus id."""

    if metadata and "label" in metadata:
        return str(metadata["label"])
    if "squash" in stimulus_id.lower():
        return "squashed"
    if "stretch" in stimulus_id.lower():
        return "stretched"
    return None


def _read_sidecar(metadata_path: Path) -> Dict[str, object]:
    """Return metadata stored in ``metadata_path`` if it exists."""

    if not metadata_path.exists():
        return {}
    with metadata_path.open("r", encoding="utf-8") as meta_file:
        loaded: Any = json.load(meta_file)
    if not isinstance(loaded, dict):
        raise TypeError(
            f"Stimulus sidecar '{metadata_path.name}' must contain a JSON object."
        )
    return loaded


def _extract_numeric(metadata: Dict[str, object], key: str) -> Optional[float]:
    """Extract ``key`` from metadata if numeric, coerced to float."""

    value = metadata.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def load_stimulus_pairs(directory: str | os.PathLike[str]) -> List[StereoStimulus]:
    """Load left/right stereo image pairs from ``directory``.

    Parameters
    ----------
    directory:
        Folder that contains PNG images of the stereo pairs.  The loader looks
        for filenames ending in ``_L.png`` and automatically searches for the
        matching ``_R.png``.  If a JSON file with the same base name exists it
        will be parsed and attached as metadata.

    Returns
    -------
    list of :class:`StereoStimulus`
        One entry per stereo pair, sorted alphabetically by stimulus id.
    """

    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(
            f"Stimulus directory '{directory}' does not exist. Please create it "
            "and add your pre-rendered PNG pairs before running the experiment."
        )

    left_images: Iterable[Path] = sorted(directory.glob("*_L.png"))
    stimuli: List[StereoStimulus] = []

    for left_image in left_images:
        base_name = left_image.stem[:-2] if left_image.stem.endswith("_L") else left_image.stem
        right_image = directory / f"{base_name}_R.png"
        if not right_image.exists():
            raise FileNotFoundError(
                f"Right-eye image missing for '{left_image.name}'. Expected "
                f"'{right_image.name}'."
            )

        metadata_path = directory / f"{base_name}.json"
        metadata_dict = _read_sidecar(metadata_path)
        disparity_px = _extract_numeric(metadata_dict, "disparity_px")
        curvature_mm = _extract_numeric(metadata_dict, "curvature_mm")

        metadata_payload: Optional[Dict[str, object]] = dict(metadata_dict) if metadata_dict else None

        label = _infer_label(base_name, metadata_payload)
        stimuli.append(
            StereoStimulus(
                stimulus_id=base_name,
                left_image=left_image,
                right_image=right_image,
                label=label,
                metadata=metadata_payload,
                disparity_px=disparity_px,
                curvature_mm=curvature_mm,
            )
        )

    if not stimuli:
        raise RuntimeError(
            "No stereo stimuli were found. Ensure PNG pairs are named '*_L.png' "
            "and '*_R.png' inside the stimulus directory."
        )

    return stimuli
