from types import SimpleNamespace

from vision.features import finger_scores, hand_scale, palm_center


def hand_points():
    # Synthetic upright hand-like geometry for smoke testing only.
    xy = [
        (0.50,0.80),(0.43,0.72),(0.40,0.63),(0.37,0.57),(0.34,0.52),
        (0.46,0.62),(0.46,0.48),(0.46,0.38),(0.46,0.27),
        (0.50,0.60),(0.50,0.44),(0.50,0.34),(0.50,0.23),
        (0.54,0.62),(0.54,0.49),(0.54,0.40),(0.54,0.31),
        (0.58,0.65),(0.59,0.54),(0.59,0.46),(0.59,0.39),
    ]
    return [SimpleNamespace(x=x, y=y, z=0.0) for x, y in xy]


def test_geometry_is_finite():
    points = hand_points()
    assert hand_scale(points) > 0
    assert len(palm_center(points)) == 2
    assert 0 <= finger_scores(points, "index").extension <= 1
