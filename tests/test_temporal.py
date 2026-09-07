from gestures.classifier import Gesture
from gestures.temporal import TemporalStabilizer


def test_static_gesture_is_not_triggered_until_stable():
    stabilizer = TemporalStabilizer(4, 0.75, 2)
    events = [stabilizer.update(Gesture.TWO_FINGER, 0.95, now=i) for i in range(3)]
    assert all(not e.entered for e in events)
    event = stabilizer.update(Gesture.TWO_FINGER, 0.95, now=3)
    # Hysteresis is intentionally conservative; another consistent frame confirms entry.
    assert not event.entered
    event = stabilizer.update(Gesture.TWO_FINGER, 0.95, now=4)
    assert event.entered
    assert event.gesture is Gesture.TWO_FINGER


def test_holding_gesture_does_not_reenter():
    stabilizer = TemporalStabilizer(3, 0.75, 1)
    entered = [stabilizer.update(Gesture.ONE_FINGER, 0.95, now=i) for i in range(3)]
    assert entered[-1].entered
    later = stabilizer.update(Gesture.ONE_FINGER, 0.95, now=5)
    assert not later.entered
