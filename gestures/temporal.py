"""Temporal stabilization and edge-triggered gesture confirmation."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import monotonic

from gestures.classifier import Gesture


@dataclass(frozen=True)
class ConfirmedGesture:
    gesture: Gesture
    confidence: float
    entered: bool


class TemporalStabilizer:
    """Confirm gestures only after a stable majority over recent frames."""

    def __init__(
        self,
        stability_frames: int,
        min_confidence: float,
        hysteresis_frames: int,
    ) -> None:
        self.stability_frames = max(3, int(stability_frames))
        self.min_confidence = float(min_confidence)
        self.hysteresis_frames = max(1, int(hysteresis_frames))
        self.history: deque[Gesture] = deque(maxlen=self.stability_frames)
        self.conf_history: deque[float] = deque(maxlen=self.stability_frames)
        self.confirmed = Gesture.NONE
        self.pending: Gesture | None = None
        self.pending_count = 0
        self.last_valid_time = monotonic()

    def update(
        self,
        gesture: Gesture,
        confidence: float,
        now: float | None = None,
    ) -> ConfirmedGesture:
        timestamp = monotonic() if now is None else now

        if gesture is Gesture.NONE or confidence < self.min_confidence:
            self.history.clear()
            self.conf_history.clear()
            self.pending = None
            self.pending_count = 0
            if self.confirmed is not Gesture.NONE:
                previous = self.confirmed
                self.confirmed = Gesture.NONE
                self.last_valid_time = timestamp
                return ConfirmedGesture(previous, 0.0, False)
            self.last_valid_time = timestamp
            return ConfirmedGesture(Gesture.NONE, 0.0, False)

        self.last_valid_time = timestamp
        self.history.append(gesture)
        self.conf_history.append(float(confidence))

        if len(self.history) < self.stability_frames:
            return ConfirmedGesture(self.confirmed, 0.0, False)

        counts: dict[Gesture, int] = {}
        for item in self.history:
            counts[item] = counts.get(item, 0) + 1

        candidate = max(counts, key=counts.get)
        candidate_count = counts[candidate]
        average_confidence = sum(self.conf_history) / len(self.conf_history)

        # Require a strict majority. With 4 frames, 3 identical frames are
        # enough; this avoids the unnecessary fifth-frame delay of the old logic.
        required = self.stability_frames // 2 + 1
        if candidate_count < required:
            return ConfirmedGesture(self.confirmed, average_confidence, False)

        if candidate is self.confirmed:
            self.pending = None
            self.pending_count = 0
            return ConfirmedGesture(
                self.confirmed,
                average_confidence,
                False,
            )

        if self.pending is candidate:
            self.pending_count += 1
        else:
            self.pending = candidate
            self.pending_count = 1

        # For a strict majority candidate we normally confirm immediately. The
        # optional hysteresis adds extra protection for especially noisy transitions.
        if self.pending_count >= self.hysteresis_frames:
            self.confirmed = candidate
            self.pending = None
            self.pending_count = 0
            return ConfirmedGesture(
                candidate,
                average_confidence,
                True,
            )

        return ConfirmedGesture(
            self.confirmed,
            average_confidence,
            False,
        )

    def reset(self) -> None:
        self.history.clear()
        self.conf_history.clear()
        self.confirmed = Gesture.NONE
        self.pending = None
        self.pending_count = 0
        self.last_valid_time = monotonic()
