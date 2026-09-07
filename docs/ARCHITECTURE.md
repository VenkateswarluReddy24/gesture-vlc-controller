# System Architecture

## 1. High-Level Pipeline

```text
┌──────────────────────┐
│       Webcam         │
└──────────┬───────────┘
           │ BGR frames
           ▼
┌──────────────────────┐
│       OpenCV         │
│ Frame acquisition    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│     MediaPipe        │
│  Hand Landmarker     │
└──────────┬───────────┘
           │ 21 landmarks
           ▼
┌──────────────────────┐
│  Feature Extraction  │
│ normalized geometry  │
└──────────┬───────────┘
           │ feature vector
           ▼
┌──────────────────────┐
│ Gesture Classifier   │
│ deterministic rules  │
└──────────┬───────────┘
           │ gesture + confidence
           ▼
┌──────────────────────┐
│ Temporal Stabilizer  │
│ frame confirmation   │
│ confidence filtering │
└──────────┬───────────┘
           │ stable state
           ▼
┌──────────────────────┐
│ Gesture State Machine│
│ edge + hold semantics│
└──────────┬───────────┘
           │ ActionEvent
           ▼
┌──────────────────────┐
│    VLC Controller    │
│ HTTP/Lua abstraction │
└──────────┬───────────┘
           │ authenticated command
           ▼
┌──────────────────────┐
│    VLC Media Player  │
└──────────────────────┘
```

## 2. Layer Responsibilities

### Camera Layer

Responsible for:

- camera initialization
- frame acquisition
- camera configuration
- resource release

It does not know what a gesture means.

### Vision Layer

Responsible for:

- MediaPipe initialization
- hand landmark inference
- handedness / palm center metadata
- vision-side normalization inputs

It does not execute playback commands.

### Feature Layer

Responsible for converting landmarks into normalized geometric measurements.

The output is deliberately compact and interpretable.

### Classifier Layer

Responsible for mapping features to:

```text
ONE_FINGER
TWO_FINGER
THREE_FINGER
FOUR_FINGER
OPEN_PALM
NONE
```

with confidence.

### Temporal Layer

Responsible for converting unstable frame predictions into stable observations.

This is effectively a temporal signal-processing stage.

### State-Machine Layer

Responsible for interaction semantics.

It answers questions such as:

- Did the user just enter ONE_FINGER?
- Has ONE_FINGER been continuously held for 4 seconds?
- Should a hold action repeat?
- Has the user released the gesture?
- Is the action inside its cooldown period?

### Controller Layer

Responsible for translating abstract actions into VLC commands.

The rest of the system therefore never needs to know VLC's HTTP URL format.

---

## 3. Perception-to-Action Contract

The controller is intentionally downstream of the state machine.

```text
Vision does NOT call VLC.

Vision:
    "I see ONE_FINGER with confidence 0.91"

Temporal:
    "ONE_FINGER is stable"

State machine:
    "ONE_FINGER entered → PLAY"

Controller:
    "PLAY → pl_play"
```

Long holds follow the same contract:

```text
OPEN_PALM stable
       ↓
hold timer
       ↓
5.0 seconds reached
       ↓
LONG_FORWARD event
       ↓
VLC native long-jump action
```

---

## 4. Why the State Machine Matters

A naïve implementation often does:

```python
if gesture == ONE_FINGER:
    play()
```

inside the camera loop.

At 30 FPS, that could produce dozens of commands for the same hand pose.

This architecture instead behaves like:

```text
gesture enters
      ↓
one PLAY event
      ↓
gesture remains active
      ↓
no additional PLAY events
      ↓
gesture leaves
      ↓
next entry can trigger PLAY again
```

That makes the system event-driven instead of frame-driven.

---

## 5. Hold Semantics

### Repeatable

```text
ONE_FINGER
   ↓ 4 s
VOLUME_UP
   ↓ every repeat interval
VOLUME_UP
   ↓ every repeat interval
VOLUME_UP
```

### Single-shot

```text
OPEN_PALM
   ↓ 5 s
LONG_FORWARD
   ↓
wait for release
```

This distinction is important because volume is naturally continuous while a large playback jump is naturally discrete.

---

## 6. Four-Finger / Open-Palm Disambiguation

These states are visually close.

The classifier therefore does not rely solely on:

```text
number of extended fingers = 4
```

Instead, it uses calibrated thumb geometry.

Representative measurements:

```text
FOUR_FINGER thumb ≈ 0.549
OPEN_PALM   thumb ≈ 0.676
```

The calibrated decision boundary is approximately:

```text
thumb < 0.62  → FOUR_FINGER
thumb ≥ 0.62  → OPEN_PALM
```

This is an example of using a **discriminative feature specifically for an observed real-world ambiguity**.

---

## 7. Reliability Pipeline

The reliability chain can be viewed as:

```text
Image noise
    ↓
MediaPipe smoothing/tracking
    ↓
geometric normalization
    ↓
confidence threshold
    ↓
multi-frame confirmation
    ↓
hysteresis
    ↓
event/state transition
    ↓
cooldown
    ↓
VLC command
```

Each stage removes a different class of failure.

---

## 8. Failure Boundaries

The architecture also defines failure containment.

```text
Camera failure
    → camera layer

MediaPipe failure
    → vision layer

Classification issue
    → classifier/calibration

Gesture flicker
    → temporal layer

Repeated command
    → state machine

VLC unavailable
    → controller layer

Ctrl+C / shutdown
    → application lifecycle
```

This makes debugging much faster because each symptom maps to a small subsystem.

---

## 9. Extension Strategy

The action interface is intentionally abstract:

```text
play
pause
stop
volume_up
volume_down
long_forward
long_backward
```

That means a future controller can be added without changing the vision stack:

```text
                    ┌→ VLC
Gesture StateMachine ┼→ ROS 2
                    ├→ custom media backend
                    └→ hardware controller
```

The current implementation therefore establishes a reusable control architecture, not just a one-off VLC script.
