from gestures.classifier import Gesture
from gestures.state_machine import GestureStateMachine
from gestures.swipe import SwipeDetector


def make_machine():
    swipe = SwipeDetector(0.15, 0.4, 600, 0.18, 1.0, 20)
    return GestureStateMachine({"play": 0.8, "pause": 0.8, "stop": 1.0, "next": 1.0, "previous": 1.0}, swipe)


def test_static_action_is_edge_triggered():
    machine = make_machine()
    first = machine.update(Gesture.ONE_FINGER, 0.9, (0.5, 0.5), now=1.0, gesture_entered=True)
    held = machine.update(Gesture.ONE_FINGER, 0.9, (0.5, 0.5), now=1.1, gesture_entered=False)
    assert first.action == "play"
    assert held is None
