from gestures.classifier import Gesture
from gestures.swipe import SwipeDetector, SwipeDirection


def test_right_swipe():
    detector = SwipeDetector(0.15, 0.4, 600, 0.18, 1.0, 20)
    detector.update(Gesture.OPEN_PALM, 0.30, 0.50, now=0.00, gesture_confidence=0.9)
    detector.update(Gesture.OPEN_PALM, 0.45, 0.51, now=0.10, gesture_confidence=0.9)
    event = detector.update(Gesture.OPEN_PALM, 0.58, 0.52, now=0.20, gesture_confidence=0.9)
    assert event is not None
    assert event.direction == SwipeDirection.RIGHT


def test_vertical_motion_does_not_trigger():
    detector = SwipeDetector(0.15, 0.4, 600, 0.08, 1.0, 20)
    detector.update(Gesture.OPEN_PALM, 0.30, 0.30, now=0.00, gesture_confidence=0.9)
    detector.update(Gesture.OPEN_PALM, 0.39, 0.45, now=0.10, gesture_confidence=0.9)
    event = detector.update(Gesture.OPEN_PALM, 0.49, 0.60, now=0.20, gesture_confidence=0.9)
    assert event is None
