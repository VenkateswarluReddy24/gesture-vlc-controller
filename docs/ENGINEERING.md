# Engineering Notes

## Problem Statement

The initial idea is simple:

> Use a webcam to control VLC with hand gestures.

The engineering challenge is that a camera produces a continuous noisy stream, while VLC expects discrete commands.

The design goal became:

> Convert uncertain visual observations into deterministic, explainable and testable control events.

---

## 1. Why not trigger actions directly from classification?

Direct frame-level control causes:

- repeated commands
- flickering gestures
- accidental actions
- sensitivity to momentary landmark errors

Therefore classification and control are intentionally separated.

---

## 2. Why use normalized geometric features?

Raw image coordinates vary with:

- hand distance
- camera position
- image resolution
- user posture

Normalized geometric measurements provide a more stable representation.

This also makes the final classifier small and easy to inspect.

---

## 3. Why an explainable classifier?

This project is a control interface, not primarily a research benchmark.

The final decision logic needs to answer:

> Why did the system call PLAY?

With deterministic geometry-based classification, the answer can be traced to specific landmark relationships and calibrated thresholds.

That is valuable during:

- field debugging
- threshold tuning
- failure analysis
- user calibration

---

## 4. Temporal Stabilization as Signal Processing

Gesture observations can be treated as a noisy temporal signal:

```text
Frame:   1 2 3 4 5 6 7 8
Raw:     O O 1 1 O  1 1 1
```

A temporal confirmation rule prevents an isolated observation from becoming an event.

Conceptually:

```text
raw signal
   ↓
confidence gating
   ↓
temporal filtering
   ↓
stable signal
```

This is analogous to debouncing in embedded systems.

---

## 5. State Machine as the Control Boundary

The state machine creates the boundary between:

```text
"I see something"
```

and:

```text
"perform an action"
```

That boundary makes the system deterministic.

Example:

```text
NONE
  ↓
ONE_FINGER entered
  ↓
PLAY
  ↓
ONE_FINGER held
  ↓
4 s
  ↓
VOLUME_UP
  ↓
repeat while held
  ↓
release
  ↓
NONE
```

---

## 6. Long Hold vs Immediate Command

A single pose can support two semantics:

```text
short interaction → primary command
long interaction  → secondary command
```

This is effectively an interaction-space expansion without adding another gesture.

It also resembles press-vs-hold behavior from conventional user interfaces.

---

## 7. Native VLC Behavior

Playback logic should not be duplicated unnecessarily.

For long jumps, the application invokes VLC's internal long-jump actions.

Therefore:

```text
Gesture system
    = decides WHAT

VLC
    = decides HOW FAR / HOW playback behaves
```

This reduces coupling and keeps playback configuration under VLC's control.

---

## 8. Security Boundary

The VLC interface is local.

Credentials are treated as runtime configuration, not source code.

Published repositories therefore contain:

```text
VLC_PASSWORD=CHANGE_ME
```

rather than a real credential.

---

## 9. Shutdown Handling

`KeyboardInterrupt` can occur while the application is inside the real-time inference loop.

The application explicitly handles `Ctrl+C` and then performs centralized cleanup:

```text
KeyboardInterrupt
    ↓
log shutdown
    ↓
close MediaPipe
    ↓
release camera
    ↓
close VLC session
    ↓
destroy OpenCV windows
    ↓
normal exit
```

This is important for a long-running real-time application.

---

## 10. Testing Philosophy

The system is tested in layers.

### Unit-level

- geometric functions
- classifier
- temporal logic
- state-machine timing
- VLC command mapping

### Integration-level

- complete gesture pipeline
- event generation
- controller dispatch

### Manual hardware/system validation

- webcam
- real VLC instance
- real hand poses
- long-hold timing
- shutdown behavior

This combination provides stronger confidence than relying only on manual demonstration.
