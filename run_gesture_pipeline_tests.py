from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
# This script may be copied into either project root or scripts/.
PROJECT = ROOT.parent if ROOT.name == "scripts" else ROOT

sys.path.insert(0, str(PROJECT))

from gestures.classifier import Gesture, GestureClassifier
from gestures.temporal import TemporalStabilizer
from gestures.swipe import SwipeDetector
from gestures.state_machine import GestureStateMachine


def load_cases() -> dict:
    candidates = [
        PROJECT / "tests" / "fixtures" / "gesture_landmark_cases.json",
        PROJECT / "gesture_landmark_cases.json",
        ROOT / "gesture_landmark_cases.json",
    ]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError(
        "gesture_landmark_cases.json not found. Put it in tests/fixtures/ or beside this script."
    )


def points(raw):
    return [SimpleNamespace(x=p[0], y=p[1], z=p[2]) for p in raw]


def check(condition: bool, label: str, details: str = "") -> None:
    if condition:
        print(f"PASS | {label}")
    else:
        print(f"FAIL | {label}" + (f" | {details}" if details else ""))
        raise AssertionError(label)


def main() -> int:
    data = load_cases()
    cases = data["cases"]
    classifier = GestureClassifier()

    print("=== 1. STATIC LANDMARK CLASSIFICATION ===")
    for name in ("ONE_FINGER", "TWO_FINGER", "THREE_FINGER"):
        case = cases[name]
        lm = points(case["landmarks"])
        check(len(lm) == 21, f"{name}: 21 landmarks")
        result = classifier.classify(lm)
        check(result.gesture.value == case["expected"], f"{name}: classifier", f"got {result.gesture.value}")
        check(result.confidence >= 0.75, f"{name}: confidence >= 0.75", f"{result.confidence:.3f}")
        print(f"      detected={result.gesture.value}, confidence={result.confidence:.3f}")

    print("\n=== 2. TEMPORAL CONFIRMATION ===")
    temporal = TemporalStabilizer(stability_frames=4, min_confidence=0.75, hysteresis_frames=2)
    now = 100.0
    entered = []
    for i in range(4):
        r = temporal.update(Gesture.ONE_FINGER, 0.92, now=now + i * 0.033)
        if r.entered:
            entered.append(r.gesture)
    check(entered == [Gesture.ONE_FINGER], "ONE_FINGER confirms exactly once")

    print("\n=== 3. HELD-GESTURE DEBOUNCE ===")
    repeats = 0
    for i in range(20):
        r = temporal.update(Gesture.ONE_FINGER, 0.92, now=101.0 + i * 0.033)
        if r.entered:
            repeats += 1
    check(repeats == 0, "Holding ONE_FINGER produces no second confirmation")

    print("\n=== 4. GESTURE TRANSITION ===")
    temporal.reset()
    events = []
    t = 200.0
    for i in range(4):
        r = temporal.update(Gesture.ONE_FINGER, 0.92, now=t + i * .033)
        if r.entered:
            events.append(r.gesture)
    for i in range(4):
        r = temporal.update(Gesture.TWO_FINGER, 0.92, now=t + 1 + i * .033)
        if r.entered:
            events.append(r.gesture)
    check(events == [Gesture.ONE_FINGER, Gesture.TWO_FINGER], "ONE -> TWO confirms without spurious gesture")

    print("\n=== 5. STATE MACHINE ACTIONS ===")
    swipe = SwipeDetector(.18, .65, 550, .16, 1.0, 20, .78)
    sm = GestureStateMachine(
        {"play": .8, "pause": .8, "stop": 1.0, "next": 1.0, "previous": 1.0},
        swipe,
    )
    a1 = sm.update(Gesture.ONE_FINGER, .92, None, now=300.0, gesture_entered=True)
    a2 = sm.update(Gesture.ONE_FINGER, .92, None, now=300.1, gesture_entered=False)
    a3 = sm.update(Gesture.TWO_FINGER, .92, None, now=301.0, gesture_entered=True)
    a4 = sm.update(Gesture.THREE_FINGER, .94, None, now=302.0, gesture_entered=True)
    check(a1 and a1.action == "play", "ONE_FINGER -> play")
    check(a2 is None, "Held ONE_FINGER -> no repeat play")
    check(a3 and a3.action == "pause", "TWO_FINGER -> pause")
    check(a4 and a4.action == "stop", "THREE_FINGER -> stop")

    print("\n=== 6. SWIPE ENGINE ===")
    right = SwipeDetector(.18, .65, 550, .16, 1.0, 20, .78)
    evt = None
    for i, x in enumerate((0.40, 0.47, 0.55, 0.64)):
        evt = right.update(Gesture.OPEN_PALM, x, 0.50, now=400.0 + i * .10, gesture_confidence=.95) or evt
    check(evt is not None and evt.direction == "RIGHT", "Open palm right swipe -> RIGHT")

    left = SwipeDetector(.18, .65, 550, .16, 1.0, 20, .78)
    evt = None
    for i, x in enumerate((0.64, 0.56, 0.48, 0.40)):
        evt = left.update(Gesture.OPEN_PALM, x, 0.50, now=500.0 + i * .10, gesture_confidence=.95) or evt
    check(evt is not None and evt.direction == "LEFT", "Open palm left swipe -> LEFT")

    vertical = SwipeDetector(.18, .65, 550, .16, 1.0, 20, .78)
    evt = None
    for i, y in enumerate((0.40, 0.47, 0.55, 0.64)):
        evt = vertical.update(Gesture.OPEN_PALM, 0.50, y, now=600.0 + i * .10, gesture_confidence=.95) or evt
    check(evt is None, "Vertical movement rejected as swipe")

    print("\n=== RESULT ===")
    print("ALL GESTURE PIPELINE TESTS PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nTEST RUN FAILED: {exc}")
        raise SystemExit(1)
