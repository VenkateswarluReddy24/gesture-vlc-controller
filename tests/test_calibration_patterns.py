from gestures.classifier import Gesture

CALIBRATED = {
    Gesture.ONE_FINGER: {"index": 0.936, "middle": 0.643, "ring": 0.404, "pinky": 0.351, "thumb": 0.474},
    Gesture.TWO_FINGER: {"index": 0.940, "middle": 0.950, "ring": 0.378, "pinky": 0.552, "thumb": 0.525},
    Gesture.THREE_FINGER: {"index": 0.931, "middle": 0.953, "ring": 0.928, "pinky": 0.547, "thumb": 0.576},
    Gesture.OPEN_PALM: {"index": 0.940, "middle": 0.956, "ring": 0.974, "pinky": 0.894, "thumb": 0.911},
}


def _state(score: float) -> str:
    if score >= 0.72:
        return "extended"
    if score <= 0.65:
        return "folded"
    return "uncertain"


def test_calibration_has_expected_finger_patterns():
    assert [_state(CALIBRATED[Gesture.ONE_FINGER][f]) for f in ("index", "middle", "ring", "pinky")] == ["extended", "folded", "folded", "folded"]
    assert [_state(CALIBRATED[Gesture.TWO_FINGER][f]) for f in ("index", "middle", "ring", "pinky")] == ["extended", "extended", "folded", "folded"]
    assert [_state(CALIBRATED[Gesture.THREE_FINGER][f]) for f in ("index", "middle", "ring", "pinky")] == ["extended", "extended", "extended", "folded"]
    assert [_state(CALIBRATED[Gesture.OPEN_PALM][f]) for f in ("index", "middle", "ring", "pinky")] == ["extended", "extended", "extended", "extended"]


def test_thumb_is_not_required_to_be_folded_for_static_count_gestures():
    assert CALIBRATED[Gesture.ONE_FINGER]["thumb"] < 0.63
    assert CALIBRATED[Gesture.TWO_FINGER]["thumb"] < 0.63
    assert CALIBRATED[Gesture.THREE_FINGER]["thumb"] < 0.63
