"""Calibration helpers for the Johnston haploscope hardware.

This module converts the original C++ helper routines that shipped with the
haploscope into a standalone Python API.  The functions mirror the historical
workflow: provide an interpupillary distance (IOD) and focal distance and the
helpers report the appropriate display translations, eye positions, and mirror
arm rotation angle.  Keeping the math here makes it easy for the PsychoPy
experiment (or other calibration utilities) to reuse the calculations without
pulling in OpenGL or user-interface code.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# Physical state constants
# ---------------------------------------------------------------------------

MIN_FOCAL_DISTANCE: float = 387.5
MIN_IOD: float = 56.0
DISPLAY_LEFT_ZERO: float = 551.0
DISPLAY_RIGHT_ZERO: float = 1.0
EYE_LEFT_ZERO: float = 31.5
EYE_RIGHT_ZERO: float = 91.0


def calc_display_positions(focal_distance: float) -> Tuple[float, float]:
    """Return the left/right display carriage positions for ``focal_distance``.

    Parameters
    ----------
    focal_distance:
        Requested distance from the mirrors to the focal plane in millimetres.

    Returns
    -------
    tuple
        ``(left_position, right_position)`` in the same millimetres used in the
        original rig.  Values decrease/increase symmetrically as the focal
        distance moves away from :data:`MIN_FOCAL_DISTANCE`.
    """

    distance_change = abs(focal_distance) - MIN_FOCAL_DISTANCE
    left_pos = DISPLAY_LEFT_ZERO - distance_change
    right_pos = DISPLAY_RIGHT_ZERO + distance_change
    return left_pos, right_pos


def calc_eye_positions(iod: float) -> Tuple[float, float]:
    """Return mirror eye positions for a given interpupillary distance."""

    distance_change = (abs(iod) - MIN_IOD) / 2.0
    left_pos = EYE_LEFT_ZERO - distance_change
    right_pos = EYE_RIGHT_ZERO + distance_change
    return left_pos, right_pos


def calc_arm_rotations(iod: float, focal_distance: float) -> float:
    """Return the mirror arm rotation angle in degrees.

    The value is derived from the same trigonometric relationship as the
    original C++ helper, but includes a guard to avoid division-by-zero when the
    focal distance is zero or extremely small.
    """

    if abs(focal_distance) < 1e-6:
        raise ValueError("Focal distance must be non-zero for arm rotation calculation")

    angle_rad = math.atan(0.5 * iod / focal_distance)
    return math.degrees(angle_rad)


def calc_physical_calibration(iod: float, focal_distance: float) -> Dict[str, float]:
    """Return a dict summarising all physical calibration values.

    The dictionary keys mirror the console output of the legacy C++ routines so
    that downstream tooling (including lab notebooks) can reuse the same field
    names.
    """

    display_left, display_right = calc_display_positions(focal_distance)
    eye_left, eye_right = calc_eye_positions(iod)
    angle = calc_arm_rotations(iod, focal_distance)
    return {
        "DISPLAY_LEFT": display_left,
        "DISPLAY_RIGHT": display_right,
        "EYE_LEFT": eye_left,
        "EYE_RIGHT": eye_right,
        "ANGLE": angle,
    }


# ---------------------------------------------------------------------------
# Monitor and viewport metadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MonitorSpec:
    """Physical monitor dimensions (in pixels and millimetres)."""

    px_width: int = 3840
    px_height: int = 2160
    mm_width: int = 343
    mm_height: int = 187


@dataclass(frozen=True)
class Viewport:
    """Viewport bounds for the left and right monitors."""

    start_x: int
    start_y: int
    end_x: int
    end_y: int


MONITOR_SPEC = MonitorSpec()
LEFT_VIEWPORT = Viewport(start_x=0, start_y=218, end_x=MONITOR_SPEC.px_width, end_y=MONITOR_SPEC.px_height)
RIGHT_VIEWPORT = Viewport(
    start_x=MONITOR_SPEC.px_width - 55,
    start_y=210,
    end_x=MONITOR_SPEC.px_width,
    end_y=MONITOR_SPEC.px_height,
)

TIMER_MS: float = 33.3

__all__ = [
    "MIN_FOCAL_DISTANCE",
    "MIN_IOD",
    "DISPLAY_LEFT_ZERO",
    "DISPLAY_RIGHT_ZERO",
    "EYE_LEFT_ZERO",
    "EYE_RIGHT_ZERO",
    "calc_display_positions",
    "calc_eye_positions",
    "calc_arm_rotations",
    "calc_physical_calibration",
    "MonitorSpec",
    "Viewport",
    "MONITOR_SPEC",
    "LEFT_VIEWPORT",
    "RIGHT_VIEWPORT",
    "TIMER_MS",
]