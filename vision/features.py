"""Reusable normalized hand geometry features."""
from __future__ import annotations

from dataclasses import dataclass
from math import acos, degrees, hypot
from typing import Sequence

import numpy as np

# MediaPipe landmark indices.
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

FINGER_INDICES = {
    "index": (INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP),
    "middle": (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP),
    "ring": (RING_MCP, RING_PIP, RING_DIP, RING_TIP),
    "pinky": (PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP),
}


@dataclass(frozen=True)
class NormalizedHand:
    points: np.ndarray
    scale: float
    palm_center: tuple[float, float]


@dataclass(frozen=True)
class FingerScores:
    extension: float
    straightness: float
    tip_reach: float
    combined: float


def _xy(point: object) -> np.ndarray:
    return np.array([float(point.x), float(point.y)], dtype=np.float32)


def _distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def _angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    ba = a - b
    bc = c - b
    denom = float(np.linalg.norm(ba) * np.linalg.norm(bc))
    if denom <= 1e-9:
        return 180.0
    cosine = float(np.dot(ba, bc) / denom)
    cosine = max(-1.0, min(1.0, cosine))
    return degrees(acos(cosine))


def hand_scale(points: Sequence[object]) -> float:
    """Return a stable scale estimate based on wrist-to-middle-MCP and palm width."""
    wrist = _xy(points[WRIST])
    middle_mcp = _xy(points[MIDDLE_MCP])
    palm_width = _distance(_xy(points[INDEX_MCP]), _xy(points[PINKY_MCP]))
    return max(0.5 * (_distance(wrist, middle_mcp) + palm_width), 1e-5)


def palm_center(points: Sequence[object]) -> tuple[float, float]:
    """Return the geometric center of wrist and four MCP joints."""
    idx = [WRIST, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]
    arr = np.array([_xy(points[i]) for i in idx], dtype=np.float32)
    center = arr.mean(axis=0)
    return float(center[0]), float(center[1])


def normalize_landmarks(points: Sequence[object]) -> NormalizedHand:
    """Translate the wrist to the origin and scale the hand geometry."""
    arr = np.array([[float(p.x), float(p.y), float(p.z)] for p in points], dtype=np.float32)
    origin = arr[WRIST].copy()
    translated = arr - origin
    scale = hand_scale(points)
    translated[:, :2] /= scale
    translated[:, 2] /= scale
    return NormalizedHand(points=translated, scale=scale, palm_center=palm_center(points))


def finger_scores(points: Sequence[object], finger: str) -> FingerScores:
    """Compute explainable extension scores for index/middle/ring/pinky."""
    mcp_i, pip_i, dip_i, tip_i = FINGER_INDICES[finger]
    mcp = _xy(points[mcp_i])
    pip = _xy(points[pip_i])
    dip = _xy(points[dip_i])
    tip = _xy(points[tip_i])
    wrist = _xy(points[WRIST])
    scale = hand_scale(points)

    pip_angle = _angle(mcp, pip, dip)
    dip_angle = _angle(pip, dip, tip)
    straightness = min(pip_angle / 170.0, dip_angle / 170.0, 1.0)
    reach = _distance(tip, wrist) / (scale * 3.1)
    tip_reach = max(0.0, min(reach, 1.0))
    extension = max(0.0, min((straightness * 0.72) + (tip_reach * 0.28), 1.0))
    folded = max(0.0, min((1.0 - extension) + 0.1, 1.0))
    combined = extension if extension >= 0.5 else 1.0 - folded
    return FingerScores(extension=extension, straightness=straightness, tip_reach=tip_reach, combined=combined)


def thumb_extension_score(points: Sequence[object]) -> float:
    """Estimate thumb extension using MCP/IP alignment and tip reach from the palm."""
    mcp = _xy(points[THUMB_MCP])
    ip = _xy(points[THUMB_IP])
    tip = _xy(points[THUMB_TIP])
    wrist = _xy(points[WRIST])
    index_mcp = _xy(points[INDEX_MCP])
    scale = hand_scale(points)
    joint_angle = _angle(mcp, ip, tip)
    span = _distance(tip, index_mcp) / (scale * 2.0)
    reach = _distance(tip, wrist) / (scale * 2.9)
    alignment = min(joint_angle / 165.0, 1.0)
    outward = min(span, 1.0)
    return max(0.0, min((alignment * 0.5) + (outward * 0.3) + (reach * 0.2), 1.0))


def all_finger_scores(points: Sequence[object]) -> dict[str, FingerScores]:
    return {name: finger_scores(points, name) for name in FINGER_INDICES}
