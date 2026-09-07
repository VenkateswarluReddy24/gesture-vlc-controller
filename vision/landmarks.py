"""Landmark result adaptation and stable hand geometry."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HandObservation:
    landmarks: object
    handedness: str
    handedness_score: float
    palm_center: tuple[float, float]
    scale: float


def parse_handedness(result: object, hand_index: int) -> tuple[str, float]:
    """Extract handedness label and score from a MediaPipe result."""
    try:
        category = result.handedness[hand_index][0]
        return str(category.category_name), float(category.score)
    except (AttributeError, IndexError, TypeError):
        return "Unknown", 0.0
