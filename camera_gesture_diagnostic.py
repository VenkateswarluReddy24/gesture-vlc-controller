"""Final real-camera gesture diagnostic.

This file does not communicate with VLC.

It is deliberately defensive: an ambiguous classifier result is displayed
as NONE rather than terminating the camera application.
"""

from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter

import cv2

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import CONFIG
from gestures.classifier import Gesture, GestureClassifier
from vision.camera import Camera
from vision.hand_tracker import HandTracker


def draw_landmarks(frame, landmarks, mirrored: bool) -> None:
    """Draw all 21 landmarks aligned with the displayed image."""
    h, w = frame.shape[:2]

    points = []

    for lm in landmarks:
        x = int(float(lm.x) * w)
        y = int(float(lm.y) * h)

        if mirrored:
            x = w - 1 - x

        points.append((x, y))

    connections = [
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (5, 9), (9, 10), (10, 11), (11, 12),
        (9, 13), (13, 14), (14, 15), (15, 16),
        (13, 17), (17, 18), (18, 19), (19, 20),
        (0, 17),
    ]

    for a, b in connections:
        cv2.line(
            frame,
            points[a],
            points[b],
            (180, 180, 180),
            2,
            cv2.LINE_AA,
        )

    for i, (x, y) in enumerate(points):
        cv2.circle(
            frame,
            (x, y),
            5,
            (245, 245, 245),
            -1,
            cv2.LINE_AA,
        )


def put_line(frame, text: str, y: int, scale: float = 0.52, thickness: int = 1) -> int:
    cv2.putText(
        frame,
        text,
        (12, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA,
    )
    return y + 24


def main() -> int:
    camera = None
    tracker = None

    try:
        classifier = GestureClassifier(
            extended_threshold=CONFIG.gestures.finger_extended_threshold,
            folded_threshold=CONFIG.gestures.finger_folded_threshold,
            thumb_extended_threshold=CONFIG.gestures.thumb_extended_threshold,
            thumb_folded_threshold=CONFIG.gestures.thumb_folded_threshold,
        )

        camera = Camera(CONFIG.camera)
        tracker = HandTracker(CONFIG.mediapipe)

        print("REAL CAMERA GESTURE DIAGNOSTIC")
        print("VLC control is disabled.")
        print("Press Q or ESC to quit.")
        print()

        while True:
            frame = camera.read()
            observations = tracker.process(frame)

            display = (
                cv2.flip(frame, 1)
                if CONFIG.camera.mirrored_display
                else frame.copy()
            )

            y = 28
            y = put_line(
                display,
                "REAL CAMERA GESTURE DIAGNOSTIC",
                y,
                0.68,
                2,
            )

            if not observations:
                y = put_line(
                    display,
                    "HAND: NOT DETECTED",
                    y,
                    0.62,
                    2,
                )
            else:
                hand = max(
                    observations,
                    key=lambda item: item.handedness_score,
                )

                draw_landmarks(
                    display,
                    hand.landmarks,
                    CONFIG.camera.mirrored_display,
                )

                # IMPORTANT:
                # A classifier is allowed to reject a frame. Treat a None
                # return defensively so the diagnostic can never crash.
                result = classifier.classify(hand.landmarks)

                if result is None:
                    gesture = Gesture.NONE
                    confidence = 0.0
                    readings = None
                else:
                    gesture = result.gesture
                    confidence = result.confidence
                    readings = result.readings

                y = put_line(
                    display,
                    "HAND: DETECTED",
                    y,
                    0.62,
                    2,
                )

                y = put_line(
                    display,
                    f"HANDEDNESS: {hand.handedness}",
                    y,
                )

                y = put_line(
                    display,
                    f"CLASSIFIER: {gesture.value}",
                    y,
                    0.62,
                    2,
                )

                y = put_line(
                    display,
                    f"CONFIDENCE: {confidence:.3f}",
                    y,
                )

                if readings is not None:
                    for name, value in (
                        ("INDEX", readings.index),
                        ("MIDDLE", readings.middle),
                        ("RING", readings.ring),
                        ("PINKY", readings.pinky),
                        ("THUMB", readings.thumb),
                    ):
                        y = put_line(
                            display,
                            f"{name:<6}: {value:.3f}",
                            y,
                            0.48,
                        )

            cv2.imshow(
                "Gesture VLC - Camera Diagnostic",
                display,
            )

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break

        return 0

    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        return 1

    finally:
        if tracker is not None:
            try:
                tracker.close()
            except Exception:
                pass

        if camera is not None:
            try:
                camera.release()
            except Exception:
                pass

        cv2.destroyAllWindows()


if __name__ == "__main__":
    raise SystemExit(main())
