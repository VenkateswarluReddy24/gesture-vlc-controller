"""MediaPipe Hand Landmarker adapter using the current Tasks Vision API."""
from __future__ import annotations

from pathlib import Path

import cv2
import mediapipe as mp

from config import MediaPipeConfig
from vision.features import hand_scale, palm_center
from vision.landmarks import HandObservation, parse_handedness


class HandTrackerError(RuntimeError):
    """Raised when MediaPipe cannot be initialized."""


class HandTracker:
    def __init__(self, config: MediaPipeConfig) -> None:
        model_path = Path(config.model_path)
        if not model_path.exists():
            raise HandTrackerError(
                f"Hand Landmarker model not found: {model_path}. "
                "Download hand_landmarker.task into models/."
            )

        try:
            base_options = mp.tasks.BaseOptions(model_asset_path=str(model_path))
            options = mp.tasks.vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_hands=config.num_hands,
                min_hand_detection_confidence=config.min_hand_detection_confidence,
                min_hand_presence_confidence=config.min_hand_presence_confidence,
                min_tracking_confidence=config.min_tracking_confidence,
            )
            self._landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)
        except Exception as exc:  # MediaPipe may raise native/runtime exceptions.
            raise HandTrackerError(f"MediaPipe Hand Landmarker initialization failed: {exc}") from exc

        self._timestamp_ms = 0

    def process(self, frame_bgr) -> list[HandObservation]:
        """Run one VIDEO-mode inference and adapt the result into application observations."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        self._timestamp_ms += 33
        result = self._landmarker.detect_for_video(mp_image, self._timestamp_ms)

        observations: list[HandObservation] = []
        for index, landmarks in enumerate(result.hand_landmarks):
            handedness, handedness_score = parse_handedness(result, index)
            observations.append(
                HandObservation(
                    landmarks=landmarks,
                    handedness=handedness,
                    handedness_score=handedness_score,
                    palm_center=palm_center(landmarks),
                    scale=hand_scale(landmarks),
                )
            )
        return observations

    def close(self) -> None:
        self._landmarker.close()
