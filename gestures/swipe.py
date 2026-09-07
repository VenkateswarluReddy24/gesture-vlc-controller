"""Stable horizontal swipe detector for VLC navigation.

Navigation poses:
    FOUR_FINGER
    OPEN_PALM

Either pose may initiate a horizontal swipe.

A stationary pose does nothing.
Vertical/diagonal movement is rejected.
One valid trajectory generates at most one swipe event per cooldown.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import monotonic

from gestures.classifier import Gesture


class SwipeDirection:
    """Swipe direction constants."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"


@dataclass(frozen=True)
class TrajectoryPoint:
    timestamp: float
    x: float
    y: float


@dataclass(frozen=True)
class SwipeEvent:
    direction: str
    distance: float
    velocity: float
    confidence: float


class SwipeDetector:
    """Detect one intentional horizontal swipe per cooldown window."""

    NAVIGATION_GESTURES = {
        Gesture.FOUR_FINGER,
        Gesture.OPEN_PALM,
    }

    def __init__(
        self,
        min_distance: float,
        min_velocity: float,
        window_ms: int,
        vertical_tolerance: float,
        cooldown: float,
        max_points: int,
        min_open_palm_confidence: float = 0.78,
    ) -> None:
        self.min_distance = float(min_distance)
        self.min_velocity = float(min_velocity)
        self.window = float(window_ms) / 1000.0
        self.vertical_tolerance = float(vertical_tolerance)
        self.cooldown = float(cooldown)
        self.min_navigation_confidence = float(
            min_open_palm_confidence
        )

        self.points: deque[TrajectoryPoint] = deque(
            maxlen=max(5, int(max_points))
        )
        self.last_event = -1e9

    def update(
        self,
        gesture: Gesture,
        palm_x: float,
        palm_y: float,
        now: float | None = None,
        gesture_confidence: float = 1.0,
    ) -> SwipeEvent | None:
        timestamp = (
            monotonic()
            if now is None
            else float(now)
        )

        if (
            gesture not in self.NAVIGATION_GESTURES
            or gesture_confidence
            < self.min_navigation_confidence
        ):
            self.reset()
            return None

        self.points.append(
            TrajectoryPoint(
                timestamp=timestamp,
                x=float(palm_x),
                y=float(palm_y),
            )
        )

        cutoff = timestamp - self.window

        while (
            self.points
            and self.points[0].timestamp < cutoff
        ):
            self.points.popleft()

        if len(self.points) < 3:
            return None

        if timestamp - self.last_event < self.cooldown:
            return None

        start = self.points[0]
        end = self.points[-1]

        dt = end.timestamp - start.timestamp

        if dt <= 0.0:
            return None

        dx = end.x - start.x
        dy = end.y - start.y

        distance = abs(dx)
        velocity = distance / dt

        # Reject mostly-vertical trajectories.
        if abs(dy) > self.vertical_tolerance:
            return None

        if distance < self.min_distance:
            return None

        if velocity < self.min_velocity:
            return None

        direction = (
            SwipeDirection.RIGHT
            if dx > 0.0
            else SwipeDirection.LEFT
        )

        distance_ratio = distance / max(
            self.min_distance,
            1e-6,
        )
        velocity_ratio = velocity / max(
            self.min_velocity,
            1e-6,
        )

        confidence = min(
            1.0,
            0.35
            + min(distance_ratio, 2.0) * 0.18
            + min(velocity_ratio, 2.0) * 0.12
            + float(gesture_confidence) * 0.35,
        )

        self.last_event = timestamp
        self.points.clear()

        return SwipeEvent(
            direction=direction,
            distance=distance,
            velocity=velocity,
            confidence=confidence,
        )

    def reset(self) -> None:
        self.points.clear()