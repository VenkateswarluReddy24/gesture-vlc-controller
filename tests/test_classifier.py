from types import SimpleNamespace

from gestures.classifier import GestureClassifier, Gesture


def _points():
    # A deliberately folded/neutral hand-like set is sufficient to assert that
    # the classifier returns one of the supported states without exceptions.
    coords = [(0.5,0.8)] * 21
    return [SimpleNamespace(x=x, y=y, z=0.0) for x, y in coords]


def test_classifier_returns_supported_gesture():
    result = GestureClassifier().classify(_points())
    assert result.gesture in set(Gesture)
    assert 0.0 <= result.confidence <= 1.0
