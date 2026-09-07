"""OpenCV webcam abstraction."""
from __future__ import annotations

import cv2

from config import CameraConfig


class CameraError(RuntimeError):
    """Raised when the configured webcam cannot be opened or read."""


class Camera:
    def __init__(self, config: CameraConfig) -> None:
        self.config = config
        self.capture = cv2.VideoCapture(config.index, cv2.CAP_DSHOW)
        if not self.capture.isOpened():
            self.capture.release()
            self.capture = cv2.VideoCapture(config.index)
        if not self.capture.isOpened():
            raise CameraError(f"Unable to open webcam index {config.index}.")
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.height)
        self.capture.set(cv2.CAP_PROP_FPS, config.fps)

    def read(self):
        ok, frame = self.capture.read()
        if not ok or frame is None:
            raise CameraError("Webcam frame could not be read.")
        return frame

    def release(self) -> None:
        self.capture.release()
