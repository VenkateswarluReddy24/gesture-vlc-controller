"""Final calibrated gesture classifier.

Static states:
    NONE
    ONE_FINGER
    TWO_FINGER
    THREE_FINGER
    FOUR_FINGER
    OPEN_PALM

Calibration:
    ONE   : 0.936, 0.643, 0.404, 0.351, thumb 0.474
    TWO   : 0.940, 0.950, 0.378, 0.552, thumb 0.525
    THREE : 0.931, 0.953, 0.928, 0.547, thumb 0.576
    FOUR  : 0.929, 0.947, 0.934, 0.894, thumb ≈0.549
    OPEN  : 0.940, 0.956, 0.974, 0.894, thumb ≈0.676–0.911

The four primary fingers classify 1/2/3/4. The thumb separates
FOUR_FINGER from OPEN_PALM. The thumb is NOT required to be folded
for 1/2/3.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Sequence


class Gesture(str, Enum):
    NONE = "NONE"
    ONE_FINGER = "ONE_FINGER"
    TWO_FINGER = "TWO_FINGER"
    THREE_FINGER = "THREE_FINGER"
    FOUR_FINGER = "FOUR_FINGER"
    OPEN_PALM = "OPEN_PALM"


@dataclass(frozen=True)
class FingerReadings:
    index: float
    middle: float
    ring: float
    pinky: float
    thumb: float


@dataclass(frozen=True)
class ClassificationResult:
    gesture: Gesture
    confidence: float
    readings: FingerReadings


class GestureClassifier:
    """Explainable classifier with calibrated thresholds and compatibility."""

    def __init__(
        self,
        extended_threshold: float = 0.72,
        folded_threshold: float = 0.65,
        thumb_extended_threshold: float = 0.72,
        thumb_folded_threshold: float = 0.45,
        **_: Any,
    ) -> None:
        if not 0.0 <= folded_threshold < extended_threshold <= 1.0:
            raise ValueError(
                "Require 0 <= folded_threshold < extended_threshold <= 1"
            )

        self.extended_threshold = float(extended_threshold)
        self.folded_threshold = float(folded_threshold)
        self.thumb_extended_threshold = float(thumb_extended_threshold)
        self.thumb_folded_threshold = float(thumb_folded_threshold)

        # Real-camera recalibration from the latest test:
        # FOUR_FINGER thumb ≈ 0.549
        # OPEN_PALM   thumb can be ≈ 0.676 in the demonstrated pose
        #             and ≈ 0.911 in the fully open reference pose.
        #
        # 0.62 cleanly separates the observed FOUR and OPEN samples:
        #   0.549 < 0.62 -> FOUR_FINGER
        #   0.676 > 0.62 -> OPEN_PALM
        #
        # Keep this as the calibrated decision boundary until more samples
        # show that the user's camera produces a materially different range.
        self.four_open_thumb_boundary = 0.62

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _readings(self, landmarks: Sequence[Any]) -> FingerReadings:
        from vision.features import finger_scores, thumb_extension_score

        return FingerReadings(
            index=float(finger_scores(landmarks, "index").extension),
            middle=float(finger_scores(landmarks, "middle").extension),
            ring=float(finger_scores(landmarks, "ring").extension),
            pinky=float(finger_scores(landmarks, "pinky").extension),
            thumb=float(thumb_extension_score(landmarks)),
        )

    def _extended_confidence(self, score: float) -> float:
        if score <= self.folded_threshold:
            return 0.0
        if score >= self.extended_threshold:
            return 1.0
        return self._clamp(
            (score - self.folded_threshold)
            / (self.extended_threshold - self.folded_threshold)
        )

    def _folded_confidence(self, score: float) -> float:
        if score <= self.folded_threshold:
            return 1.0
        if score >= self.extended_threshold:
            return 0.0
        return self._clamp(
            (self.extended_threshold - score)
            / (self.extended_threshold - self.folded_threshold)
        )

    def _pattern_confidence(
        self,
        r: FingerReadings,
        pattern: tuple[str, str, str, str],
    ) -> float:
        values = (r.index, r.middle, r.ring, r.pinky)
        scores = []

        for value, state in zip(values, pattern):
            if state == "E":
                scores.append(self._extended_confidence(value))
            else:
                scores.append(self._folded_confidence(value))

        return sum(scores) / 4.0

    def is_one_finger(
        self,
        data: FingerReadings | Sequence[Any],
    ) -> bool:
        r = data if isinstance(data, FingerReadings) else self._readings(data)
        return (
            r.index >= self.extended_threshold
            and r.middle <= self.folded_threshold
            and r.ring <= self.folded_threshold
            and r.pinky <= self.folded_threshold
        )

    def is_two_finger(
        self,
        data: FingerReadings | Sequence[Any],
    ) -> bool:
        r = data if isinstance(data, FingerReadings) else self._readings(data)
        return (
            r.index >= self.extended_threshold
            and r.middle >= self.extended_threshold
            and r.ring <= self.folded_threshold
            and r.pinky <= self.folded_threshold
        )

    def is_three_finger(
        self,
        data: FingerReadings | Sequence[Any],
    ) -> bool:
        r = data if isinstance(data, FingerReadings) else self._readings(data)
        return (
            r.index >= self.extended_threshold
            and r.middle >= self.extended_threshold
            and r.ring >= self.extended_threshold
            and r.pinky <= self.folded_threshold
        )

    def is_four_finger(
        self,
        data: FingerReadings | Sequence[Any],
    ) -> bool:
        r = data if isinstance(data, FingerReadings) else self._readings(data)
        return (
            r.index >= self.extended_threshold
            and r.middle >= self.extended_threshold
            and r.ring >= self.extended_threshold
            and r.pinky >= self.extended_threshold
            and r.thumb < self.four_open_thumb_boundary
        )

    def is_open_palm(
        self,
        data: FingerReadings | Sequence[Any],
    ) -> bool:
        r = data if isinstance(data, FingerReadings) else self._readings(data)
        return (
            r.index >= self.extended_threshold
            and r.middle >= self.extended_threshold
            and r.ring >= self.extended_threshold
            and r.pinky >= self.extended_threshold
            and r.thumb >= self.four_open_thumb_boundary
        )

    def classify(
        self,
        landmarks: Sequence[Any],
    ) -> ClassificationResult:
        """Always returns a ClassificationResult; never returns None."""
        r = self._readings(landmarks)

        candidates: list[tuple[Gesture, float]] = [
            (
                Gesture.ONE_FINGER,
                self._pattern_confidence(r, ("E", "F", "F", "F")),
            ),
            (
                Gesture.TWO_FINGER,
                self._pattern_confidence(r, ("E", "E", "F", "F")),
            ),
            (
                Gesture.THREE_FINGER,
                self._pattern_confidence(r, ("E", "E", "E", "F")),
            ),
            (
                Gesture.FOUR_FINGER,
                self._pattern_confidence(r, ("E", "E", "E", "E")),
            ),
            (
                Gesture.OPEN_PALM,
                self._pattern_confidence(r, ("E", "E", "E", "E")),
            ),
        ]

        adjusted: list[tuple[Gesture, float]] = []

        for gesture, primary_conf in candidates:
            confidence = primary_conf

            if gesture is Gesture.FOUR_FINGER:
                # Four-finger pose: thumb is below the measured open-palm
                # boundary. Use it as a discriminator, not the primary signal.
                if r.thumb >= self.four_open_thumb_boundary:
                    confidence = 0.0
                else:
                    thumb_conf = self._clamp(
                        (self.four_open_thumb_boundary - r.thumb)
                        / self.four_open_thumb_boundary
                    )
                    confidence = 0.80 * primary_conf + 0.20 * thumb_conf

            elif gesture is Gesture.OPEN_PALM:
                if r.thumb < self.four_open_thumb_boundary:
                    confidence = 0.0
                else:
                    thumb_conf = self._clamp(
                        (r.thumb - self.four_open_thumb_boundary)
                        / (1.0 - self.four_open_thumb_boundary)
                    )
                    confidence = 0.80 * primary_conf + 0.20 * thumb_conf

            adjusted.append((gesture, confidence))

        gesture, confidence = max(
            adjusted,
            key=lambda item: item[1],
        )

        # Enforce explicit patterns for high-confidence classification.
        if gesture is Gesture.ONE_FINGER and not self.is_one_finger(r):
            gesture = Gesture.NONE
            confidence = 0.0
        elif gesture is Gesture.TWO_FINGER and not self.is_two_finger(r):
            gesture = Gesture.NONE
            confidence = 0.0
        elif gesture is Gesture.THREE_FINGER and not self.is_three_finger(r):
            gesture = Gesture.NONE
            confidence = 0.0
        elif gesture is Gesture.FOUR_FINGER and not self.is_four_finger(r):
            gesture = Gesture.NONE
            confidence = 0.0
        elif gesture is Gesture.OPEN_PALM and not self.is_open_palm(r):
            gesture = Gesture.NONE
            confidence = 0.0

        if confidence < 0.75:
            return ClassificationResult(
                gesture=Gesture.NONE,
                confidence=0.0,
                readings=r,
            )

        return ClassificationResult(
            gesture=gesture,
            confidence=self._clamp(confidence),
            readings=r,
        )