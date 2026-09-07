# Portfolio & Interview Guide

## 30-Second Project Pitch

> I built a webcam-only real-time gesture interface for VLC using MediaPipe Hand Landmarker and OpenCV. Instead of directly firing commands from frame-level predictions, I designed a perception-to-action pipeline with normalized hand geometry, explainable gesture classification, temporal stabilization, and a deterministic state machine. The system supports immediate playback controls plus long-hold volume and VLC-native long-jump interactions, with authentication, reconnect handling, automated tests, and clean shutdown behavior.

---

## Resume Entry

### Gesture VLC Controller
**Python, OpenCV, MediaPipe, VLC HTTP/Lua, PyTest**

- Designed a real-time webcam-only human–computer interaction system using 21-point MediaPipe hand landmarks and normalized geometric feature extraction.
- Engineered temporal stabilization, confidence gating, hysteresis, cooldowns, and a deterministic gesture state machine to convert noisy frame predictions into reliable VLC control events.
- Implemented dual-layer interaction semantics with immediate Play/Pause/Stop controls and timed hold gestures for volume and long playback jumps.
- Solved the four-finger vs open-palm ambiguity through real-camera calibration and a discriminative thumb-geometry boundary.
- Integrated VLC through an authenticated local HTTP/Lua control layer with reconnect handling, command logging, and graceful `Ctrl+C` shutdown.
- Validated the control pipeline with automated tests covering geometry, classification, timing, state transitions, and VLC command mapping.

---

## Interview Questions You Should Be Ready For

### Why not use a trained neural network for the final gesture classifier?

Because the project only needs a small, well-defined gesture vocabulary, and deterministic geometry-based classification is easier to inspect, calibrate and validate. MediaPipe already provides the learned perception component; the downstream controller benefits from explicit logic.

### Why temporal stabilization?

Single-frame predictions are not reliable enough for control. Temporal confirmation suppresses transient misclassifications before they reach the state machine.

### Why a state machine?

Because control semantics depend on transitions and time.

A frame tells us what the hand looks like.

A state machine tells us whether that observation means:

- enter
- remain
- hold
- repeat
- release

### How did you solve four fingers vs open palm?

Both states contain four extended primary fingers. The distinguishing feature is calibrated thumb geometry, using real webcam measurements rather than assuming idealized poses.

### Why VLC HTTP instead of keyboard automation?

It creates a clean application boundary and avoids OS-level keyboard simulation. The control layer talks directly to VLC.

### How did you prevent repeated PLAY commands?

PLAY is edge-triggered when the gesture enters the stable state. Holding the pose does not continuously reissue PLAY.

### Why are volume controls repeatable but long jumps single-shot?

Volume behaves naturally as a continuous control. A large playback jump is more useful as a discrete event; repeating it every frame or every short interval could overshoot the intended playback position.

### How do you handle the camera or VLC disappearing?

The relevant subsystem reports failure to the application, the controller attempts reconnect where configured, and resource cleanup remains centralized.

---

## What This Project Signals to a Recruiter

This project demonstrates more than "gesture recognition."

It shows:

- computer vision
- feature engineering
- real-time systems thinking
- temporal signal processing
- deterministic control architecture
- protocol/API integration
- calibration and debugging
- testable modular design
- runtime failure handling

The strongest part of the project is therefore the **architecture and engineering decisions**, not the visual demo alone.

---

## Suggested GitHub Description

```text
Real-time webcam gesture controller for VLC using OpenCV, MediaPipe Hand Landmarker, normalized hand geometry, temporal stabilization, and deterministic state-machine control.
```

## Suggested Topics

```text
computer-vision
opencv
mediapipe
gesture-recognition
python
human-computer-interaction
vlc
real-time-systems
state-machine
automation
robotics
```

---

## Recommended Demo Asset

Record a short screen-and-camera demonstration with the following exact order:

```text
Play
Pause
Stop
Volume Up
Volume Down
Long Forward
Long Backward
Clean Ctrl+C shutdown
```

Overlay a small text label in the video:

```text
Gesture → Stable State → VLC Action
```

That communicates the architecture visually.

---

## Project Positioning

Avoid describing the project as:

> "A Python program that changes VLC using hand gestures."

Prefer:

> "A real-time perception-to-action system that converts webcam hand landmarks into stabilized, stateful media-control events."

The first description emphasizes the application.

The second demonstrates engineering capability.
