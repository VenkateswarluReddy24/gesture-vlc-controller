# 🖐️ Gesture VLC Controller

<p align="center">
  <strong>Real-Time Webcam Human–Computer Interaction for VLC Media Player</strong><br>
  MediaPipe Hand Tracking • Explainable Gesture Recognition • Temporal Stabilization • Deterministic State Machine • VLC HTTP/Lua
</p>

<p align="center">
  <a href="#-overview">Overview</a> •
  <a href="#-controls">Controls</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-engineering-highlights">Engineering</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-testing">Testing</a> •
  <a href="#-project-structure">Structure</a>
</p>

<p align="center">

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer_Vision-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Hand_Landmarker-FF6F00?style=for-the-badge)
![VLC](https://img.shields.io/badge/VLC-HTTP%2FLua-FF6B00?style=for-the-badge&logo=vlcmediaplayer&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-13_Passing-2EA44F?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-2EA44F?style=for-the-badge)

</p>

---

## 🎯 Project at a Glance

**Gesture VLC Controller** is a real-time, webcam-only human–computer interaction system that converts hand gestures into reliable VLC Media Player commands.

The project is intentionally designed as a **perception-to-action system**, not a single computer-vision script:

```text
Webcam
   ↓
OpenCV Frame Acquisition
   ↓
MediaPipe Hand Landmarker
   ↓
21 Hand Landmarks
   ↓
Normalized Geometric Features
   ↓
Explainable Gesture Classifier
   ↓
Temporal Stabilization
   ↓
Deterministic Gesture State Machine
   ↓
VLC HTTP/Lua Controller
   ↓
VLC Media Player
```

The controller requires only a standard webcam and VLC. It does **not** rely on OS-level keyboard simulation, mouse automation, browser automation, or dedicated gesture hardware.

---

## ✨ Why This Project Is Interesting

The main challenge is not simply recognizing a hand.

A practical gesture interface has to answer a much harder question:

> **How do you convert a noisy, frame-by-frame visual signal into a reliable, deterministic control event?**

This project addresses that problem explicitly.

It was engineered around:

- noisy landmark observations
- frame-to-frame gesture flicker
- confidence filtering
- temporal confirmation
- hysteresis and cooldown protection
- edge-triggered actions
- long-hold interaction semantics
- four-finger vs open-palm ambiguity
- VLC authentication and reconnect handling
- clean runtime shutdown
- automated validation

The result is a modular control pipeline in which **perception, decision-making, temporal behavior, and action execution are separated**.

---

# 🖐️ Controls

| Gesture | Interaction | Action |
|---|---:|---|
| ☝ **One Finger** | Immediate | ▶️ Play |
| ✌ **Two Fingers** | Immediate | ⏸️ Pause |
| 🤟 **Three Fingers** | Immediate | ⏹️ Stop |
| ☝ **One Finger** | Hold 4 seconds | 🔊 Volume Up |
| ✌ **Two Fingers** | Hold 4 seconds | 🔉 Volume Down |
| 🖐 **Open Palm** | Hold 5 seconds | ⏩ Long Forward Jump |
| 🖖 **Four Fingers** | Hold 5 seconds | ⏪ Long Backward Jump |

### Interaction model

The same gesture can have different behavior depending on **time**:

```text
ONE_FINGER
├── immediate      → PLAY
└── 4-second hold  → VOLUME UP

TWO_FINGER
├── immediate      → PAUSE
└── 4-second hold  → VOLUME DOWN

THREE_FINGER
└── immediate      → STOP

OPEN_PALM
└── 5-second hold  → VLC LONG FORWARD

FOUR_FINGER
└── 5-second hold  → VLC LONG BACKWARD
```

This expands the control vocabulary without requiring a large number of visually distinct gestures.

---

# 🧠 Architecture

## High-Level System

```text
┌──────────────────────────┐
│          Webcam          │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│          OpenCV          │
│     Frame Acquisition    │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│        MediaPipe         │
│     Hand Landmarker      │
└────────────┬─────────────┘
             │
       21 landmarks
             │
             ▼
┌──────────────────────────┐
│    Feature Extraction    │
│  Normalized Hand Geometry │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│   Gesture Classifier     │
│  Explainable / Rules     │
└────────────┬─────────────┘
             │
      gesture + confidence
             │
             ▼
┌──────────────────────────┐
│   Temporal Stabilizer    │
│ Confidence + Confirmation│
└────────────┬─────────────┘
             │
       stable gesture
             │
             ▼
┌──────────────────────────┐
│    Gesture State Machine │
│ Entry / Hold / Repeat    │
└────────────┬─────────────┘
             │
         ActionEvent
             │
             ▼
┌──────────────────────────┐
│      VLC Controller      │
│    HTTP / Lua Layer      │
└────────────┬─────────────┘
             │
        authenticated
           request
             │
             ▼
┌──────────────────────────┐
│      VLC Media Player    │
└──────────────────────────┘
```

For the detailed system design, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

# 🔬 Engineering Highlights

## 1. Explainable Gesture Recognition

MediaPipe performs the learned hand-landmark estimation.

The final gesture decision is deliberately **deterministic and interpretable**.

Instead of using raw image coordinates directly, the system converts landmarks into normalized geometric measurements representing finger extension.

That provides:

- scale-aware features
- easier threshold calibration
- fast inference
- transparent decision logic
- easier debugging

Conceptually:

```text
Image
  ↓
Learned perception
  ↓
Landmarks
  ↓
Geometric features
  ↓
Deterministic decision
```

This separation also makes it much easier to diagnose whether an error comes from **vision** or from **control logic**.

---

## 2. Real-Camera Calibration

The classifier was tuned using measured webcam observations rather than relying only on idealized textbook finger poses.

Representative calibrated values:

| Gesture | Index | Middle | Ring | Pinky | Thumb |
|---|---:|---:|---:|---:|---:|
| One Finger | 0.936 | 0.643 | 0.404 | 0.351 | 0.474 |
| Two Finger | 0.940 | 0.950 | 0.378 | 0.552 | 0.525 |
| Three Finger | 0.931 | 0.953 | 0.928 | 0.547 | 0.576 |
| Four Finger | 0.929 | 0.947 | 0.934 | 0.894 | 0.549 |
| Open Palm | 0.948 | 0.958 | 0.945 | 0.906 | 0.676 |

These values are included as engineering evidence of the calibration process, not as a universal accuracy benchmark.

---

## 3. Four-Finger vs Open-Palm Disambiguation

One of the most interesting classification problems is:

```text
FOUR_FINGER ≈ OPEN_PALM
```

Both contain four extended primary fingers.

The system therefore uses **thumb geometry as a discriminative feature**.

Representative measurements:

```text
FOUR_FINGER thumb ≈ 0.549
OPEN_PALM   thumb ≈ 0.676
```

The calibrated boundary used by the classifier is approximately:

```text
thumb < 0.62  → FOUR_FINGER
thumb ≥ 0.62  → OPEN_PALM
```

This is an example of solving an observed real-world ambiguity through targeted feature engineering.

---

## 4. Temporal Stabilization

A single frame should not be allowed to trigger a media command.

The control pipeline therefore treats classification as a noisy temporal signal:

```text
Raw predictions
     ↓
Confidence filtering
     ↓
Multi-frame confirmation
     ↓
Stable gesture
```

Conceptually:

```text
Frame:    1   2   3   4   5   6   7
Raw:      O   O   1   1   O   1   1
                         ↓
                 temporal filtering
                         ↓
                    stable state
```

This is conceptually similar to debouncing in embedded systems: transient observations are not immediately promoted to control events.

---

## 5. Deterministic State Machine

A naïve implementation might do this inside the camera loop:

```python
if gesture == ONE_FINGER:
    play()
```

At real-time frame rates, that can send many commands for the same gesture.

The state machine instead makes control **event-driven**:

```text
NONE
  ↓
ONE_FINGER entered
  ↓
PLAY
  ↓
ONE_FINGER remains held
  ↓
(no additional PLAY)
  ↓
ONE_FINGER released
  ↓
NONE
```

The state machine tracks:

- gesture entry
- active gesture
- hold duration
- repeatable vs single-shot actions
- cooldowns
- gesture release

---

## 6. Long-Hold Interaction

Long-hold behavior adds a second temporal dimension to the interface.

```text
GESTURE ENTERED
      │
      ▼
  hold timer
      │
      ▼
threshold reached?
   ┌──┴──┐
  NO    YES
   │      │
 wait   action
          │
          ├── repeatable
          │
          └── single-shot
```

### Repeatable controls

```text
ONE_FINGER
    ↓ 4s
VOLUME_UP
    ↓
VOLUME_UP
    ↓
VOLUME_UP
```

### Single-shot controls

```text
OPEN_PALM
    ↓ 5s
LONG_FORWARD
    ↓
wait for release
```

This distinction prevents a large playback jump from firing repeatedly during a single hold.

---

# 🎛️ VLC Integration

The system communicates with VLC through its local HTTP/Lua interface.

The application deliberately uses an abstraction boundary:

```text
Gesture logic
     ↓
abstract action
     ↓
VLC controller
     ↓
HTTP/Lua request
     ↓
VLC
```

Examples of abstract actions:

```text
play
pause
stop
volume_up
volume_down
long_forward
long_backward
```

### Why this architecture?

The gesture subsystem should not know VLC's URL structure or HTTP command syntax.

Likewise, the VLC controller should not know anything about MediaPipe landmarks.

This separation gives the project a cleaner dependency structure and makes the controller layer replaceable.

### VLC-native long jump

The long forward/backward controls use VLC's own internal long-jump actions rather than implementing an independent seek distance in Python.

Therefore:

```text
Gesture system
    = decides WHAT action is requested

VLC
    = remains authoritative for playback behavior
```

This keeps the application's playback policy aligned with VLC's configured behavior.

---

# 🛡️ Reliability & Failure Handling

## VLC failures

The controller explicitly handles:

- connection failure
- authentication failure
- reconnect attempts
- optional VLC auto-start
- command failure logging

## Vision failures

The runtime handles:

- no hand detected
- transient hand loss
- confidence rejection
- gesture reset
- reacquisition

## Application lifecycle

The application handles:

- normal `Q` / `Esc` exit
- terminal `Ctrl+C`
- camera release
- MediaPipe cleanup
- VLC HTTP session cleanup
- OpenCV window destruction

A `Ctrl+C` interrupt is converted into a controlled shutdown rather than leaving an avoidable traceback.

---

# 🔐 Security

The VLC password is treated as **runtime configuration**, not source code.

Never commit:

```text
.env
real credentials
secrets
```

Use:

```text
VLC_PASSWORD=CHANGE_ME
```

in the published example configuration.

A local environment variable can override the placeholder value.

---

# 🧪 Testing

The project uses layered testing.

### Unit-level validation

Covers:

- normalized geometric features
- gesture classification
- calibrated gesture patterns
- four-finger / open-palm disambiguation
- temporal stabilization
- state-machine timing
- cooldown behavior
- long-hold behavior
- VLC command mapping

### Integration validation

The full gesture pipeline has been exercised from:

```text
landmarks
   ↓
features
   ↓
classifier
   ↓
temporal layer
   ↓
state machine
   ↓
action event
```

### Runtime validation

The system was also tested with:

- real webcam input
- real VLC instance
- real hand poses
- long holds
- terminal shutdown

Current local validation:

```text
13 tests passed
```

Run:

```powershell
python -m pytest -q
```

---

# 📁 Project Structure

```text
gesture-vlc-controller/
│
├── main.py
├── config.py
├── config.json
├── requirements.txt
├── .env.example
├── .gitignore
│
├── controllers/
│   └── vlc_controller.py
│
├── gestures/
│   ├── classifier.py
│   ├── temporal.py
│   └── state_machine.py
│
├── vision/
│   ├── camera.py
│   ├── features.py
│   ├── hand_tracker.py
│   └── landmarks.py
│
├── ui/
│   └── dashboard.py
│
├── utils/
│   └── logger.py
│
├── scripts/
│   └── download_model.py
│
├── tests/
│   ├── test_classifier.py
│   ├── test_features.py
│   ├── test_state_machine.py
│   ├── test_temporal.py
│   └── ...
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ENGINEERING.md
│   └── PORTFOLIO.md
│
├── assets/
│   └── gesture-vlc-controller-demo.gif
│
└── models/
    └── hand_landmarker.task
```

> The MediaPipe model is downloaded locally. Do not commit large generated/model artifacts unless you intentionally choose to version them.

---

# ⚙️ Installation

## Requirements

- Python 3.11+ recommended
- working webcam
- VLC Media Player
- MediaPipe hand-landmarker model
- Windows, Linux, or macOS

## 1. Clone

```powershell
git clone https://github.com/YOUR_USERNAME/gesture-vlc-controller.git
cd gesture-vlc-controller
```

## 2. Create virtual environment

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
```

## 3. Install dependencies

```powershell
pip install -r requirements.txt
```

## 4. Download the MediaPipe model

Use the project's model helper:

```powershell
python scripts\download_model.py
```

## 5. Configure VLC

Configure VLC's local HTTP interface and set the local password.

The application is designed to communicate with:

```text
127.0.0.1:4000
```

The published configuration contains only a placeholder password.

## 6. Run

```powershell
python main.py
```

Exit from the application using:

```text
Q
```

or:

```text
Esc
```

Terminal interruption with:

```text
Ctrl+C
```

is also handled cleanly.

---

# 🎥 Demo

> **Place the final demonstration GIF/video here before publishing the repository.**

Recommended file:

```text
assets/gesture-vlc-controller-demo.gif
```

Then add:

```markdown
![Gesture VLC Controller Demo](assets/gesture-vlc-controller-demo.gif)
```

### Recommended demo sequence

```text
01  Application starts
02  ☝ One finger       → Play
03  ✌ Two fingers      → Pause
04  🤟 Three fingers   → Stop
05  ☝ Hold 4 seconds   → Volume Up
06  ✌ Hold 4 seconds   → Volume Down
07  🖐 Hold 5 seconds   → Long Forward
08  Four fingers       → Long Backward
09  Ctrl+C             → Clean Shutdown
```

For maximum portfolio value, keep the demonstration around **20–30 seconds** and make the action labels visible.

---

# 📊 Engineering Decisions

| Decision | Why |
|---|---|
| MediaPipe Hand Landmarker | Provides a strong hand-landmark representation |
| Normalized geometry | Reduces sensitivity to raw image scale |
| Deterministic classifier | Easy to inspect and calibrate |
| Temporal stabilization | Suppresses transient gesture noise |
| Hysteresis / cooldown | Reduces repeated or accidental triggers |
| State machine | Converts continuous observations into discrete events |
| Hold semantics | Adds functionality without many new poses |
| Single-shot long jumps | Prevents repeated large seeks |
| Repeatable volume controls | Provides natural continuous adjustment |
| VLC HTTP/Lua | Clean media-control integration boundary |
| VLC-native long jumps | Preserves VLC's configured playback behavior |
| Environment-based credentials | Avoids exposing secrets |
| Centralized cleanup | Reliable runtime shutdown |
| Automated tests | Makes behavior reproducible |

---

# 🧩 Failure-Analysis Model

One of the strongest engineering properties of this architecture is that different failures map to different layers.

```text
Camera problem
    ↓
Camera Layer

Landmark problem
    ↓
Vision Layer

Wrong gesture
    ↓
Feature / Classifier Layer

Gesture flicker
    ↓
Temporal Layer

Repeated command
    ↓
State Machine

VLC unavailable
    ↓
Controller Layer

Ctrl+C / shutdown
    ↓
Application Lifecycle
```

This makes debugging systematic instead of trial-and-error.

---

# 🧠 Lessons Learned

This project reinforced several practical real-time systems principles:

### 1. Recognition is not control

A gesture classifier can be accurate while the control system is still unreliable.

### 2. Time matters

Real-world interaction requires temporal reasoning, not just spatial recognition.

### 3. Calibration matters

Real webcam measurements can differ significantly from idealized pose assumptions.

### 4. Ambiguity requires discriminative features

Four fingers and open palm required a deliberately selected feature rather than simply counting extended fingers.

### 5. State machines belong at the control boundary

They turn continuous sensor observations into deterministic actions.

### 6. Modularity improves debugging

Separating vision, classification, temporal logic, and VLC control reduces the cost of diagnosing failures.

---

# 🚀 Future Extensions

The current architecture can be extended without redesigning the entire pipeline.

Potential directions include:

- automated user-specific calibration
- configurable gesture profiles
- multi-hand interaction
- runtime confidence/latency telemetry
- pluggable media-control backends
- headless service mode
- ROS 2 event bridge
- formal performance benchmarking
- user-specific adaptive thresholds

These are intentionally future directions; the current project remains focused on a reliable VLC controller.

---

# 💼 Portfolio Positioning

This project should be presented as more than a "gesture project."

It demonstrates experience with:

```text
Computer Vision
       +
Feature Engineering
       +
Temporal Signal Processing
       +
Deterministic State Machines
       +
Protocol / API Integration
       +
Runtime Failure Handling
       +
Automated Testing
```

A concise professional description:

> **Designed and implemented a real-time webcam-based human–computer interaction system that transforms MediaPipe hand landmarks into stabilized, stateful media-control events and drives VLC through an authenticated HTTP/Lua interface.**

### Resume-ready bullets

- Designed a real-time webcam-only HCI system using 21-point MediaPipe hand landmarks and normalized geometric feature extraction.
- Engineered temporal stabilization, confidence filtering, hysteresis, cooldowns, and deterministic state-machine control to convert noisy vision observations into reliable media events.
- Implemented dual-layer interactions with immediate Play/Pause/Stop controls and long-hold Volume Up/Down and VLC-native long-jump actions.
- Solved four-finger vs open-palm ambiguity through real-camera calibration and targeted thumb-geometry discrimination.
- Integrated VLC through a local authenticated HTTP/Lua controller with reconnect handling, command logging, and graceful shutdown.
- Validated gesture, timing, state-machine, and command behavior with automated tests.

---

# 🎤 Interview Summary

### The 30-second explanation

> I built a webcam-only real-time gesture interface for VLC using MediaPipe and OpenCV. MediaPipe estimates 21 hand landmarks, which I convert into normalized geometric features for explainable gesture classification. Instead of directly issuing commands from individual frames, I added temporal stabilization and a deterministic state machine that handles gesture entry, hold duration, cooldowns, and repeat behavior. The final actions are sent to VLC through its local HTTP/Lua interface. I also calibrated the classifier using real webcam observations, handled the four-finger/open-palm ambiguity using thumb geometry, added failure handling and clean shutdown, and validated the system with automated tests.

### Questions an interviewer may ask

**Why not use an end-to-end neural network?**

Because the gesture vocabulary is small and deterministic. MediaPipe already provides the learned perception layer, while explicit downstream logic makes the control decisions easier to inspect, calibrate, test, and debug.

**Why use temporal stabilization?**

Because a single frame is an unreliable control signal. The system needs stable observations before an action becomes actionable.

**Why use a state machine?**

Because an image describes what is visible, while the state machine decides what that observation means over time: enter, remain, hold, repeat, or release.

**How did you distinguish four fingers from open palm?**

Both poses have four extended primary fingers, so I used calibrated thumb geometry as the discriminative feature.

**Why use VLC HTTP rather than keyboard simulation?**

It creates a clean application boundary and avoids OS-level keyboard automation. VLC remains responsible for playback behavior.

**Why are volume holds repeatable but long jumps single-shot?**

Volume adjustment is naturally continuous. A long media jump is better treated as a discrete action to prevent repeated large jumps during one sustained hold.

---

# ⭐ Recommended Repository Presentation

Keep the repository clean and intentional.

### Publish

```text
main.py
config.py
config.json
controllers/
gestures/
vision/
ui/
utils/
scripts/
tests/
docs/
README.md
requirements.txt
.gitignore
.env.example
assets/
```

### Do not publish

```text
venv/
.venv/
__pycache__/
.env
*.log
temporary files
old backups
duplicate "final" scripts
experimental classifiers
personal screenshots
real credentials
large generated artifacts
```

The public repository should represent the **final engineered system**, not the entire development history.

---

# 📌 Suggested GitHub Repository Metadata

### Repository name

```text
gesture-vlc-controller
```

### Description

```text
Real-time webcam gesture controller for VLC using OpenCV, MediaPipe Hand Landmarker, normalized hand geometry, temporal stabilization, and deterministic state-machine control.
```

### Recommended topics

```text
python
opencv
mediapipe
computer-vision
gesture-recognition
human-computer-interaction
vlc
real-time-systems
state-machine
automation
robotics
```

---

# 👤 Author

**Venkateswarlu Reddy**

Robotics • Computer Vision • Embedded Systems • IoT • Automation

GitHub: [@VenkateswarluReddy24](https://github.com/VenkateswarluReddy24)

---

# 📄 License

MIT License
