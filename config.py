"""Typed configuration for the Gesture VLC Controller."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class CameraConfig:
    index: int = 0
    width: int = 640
    height: int = 480
    fps: int = 30
    mirrored_display: bool = True


@dataclass(frozen=True)
class MediaPipeConfig:
    model_path: Path = PROJECT_ROOT / "models" / "hand_landmarker.task"
    num_hands: int = 2
    min_hand_detection_confidence: float = 0.65
    min_hand_presence_confidence: float = 0.65
    min_tracking_confidence: float = 0.65


@dataclass(frozen=True)
class GestureConfig:
    # Static gesture stabilization
    stability_frames: int = 4
    min_gesture_confidence: float = 0.75
    state_hysteresis_frames: int = 2
    hand_reacquire_frames: int = 3

    # Hand-size filtering
    min_hand_scale: float = 0.06
    max_hand_scale: float = 0.65

    # Static action protection
    static_action_cooldown: float = 0.80
    stop_cooldown: float = 1.00

    # Swipe configuration
    swipe_cooldown: float = 1.00
    swipe_min_distance: float = 0.18
    swipe_min_velocity: float = 0.65
    swipe_window_ms: int = 550
    swipe_vertical_tolerance: float = 0.16
    swipe_min_open_palm_confidence: float = 0.78
    trajectory_max_points: int = 20
    gesture_lost_reset_ms: int = 220

    # Finger calibration from the user's real webcam.
    # Extended >= 0.72
    # Folded   <= 0.65
    finger_extended_threshold: float = 0.72
    finger_folded_threshold: float = 0.65

    # Thumb threshold used by the calibrated classifier.
    thumb_extended_threshold: float = 0.63
    thumb_folded_threshold: float = 0.45

    # Long-hold controls
    #
    # ONE_FINGER   held 4 s -> volume up
    # TWO_FINGER   held 4 s -> volume down
    # OPEN_PALM    held 5 s -> seek forward
    # FOUR_FINGER  held 5 s -> seek backward
    long_hold_enabled: bool = True
    long_hold_repeat_interval: float = 1.00
    long_hold_action_cooldown: float = 0.80
    volume_step: int = 5
    seek_seconds: int = 10


@dataclass(frozen=True)
class VLCConfig:
    executable: Path = Path(
        r"C:\Program Files\VideoLAN\VLC\vlc.exe"
    )
    host: str = "HOSTING ADDRESS"
    port: int = "PORT NUMBER"
    password: str = "PASSWORD"
    timeout: float = 1.2
    reconnect_interval: float = 2.0
    auto_start: bool = True
    startup_timeout: float = 8.0


@dataclass(frozen=True)
class UIConfig:
    window_name: str = "Gesture VLC Controller"
    debug_mode: bool = True
    show_landmarks_when_debug: bool = True
    camera_panel_width: int = 640
    camera_panel_height: int = 480


@dataclass(frozen=True)
class AppConfig:
    camera: CameraConfig = field(default_factory=CameraConfig)
    mediapipe: MediaPipeConfig = field(
        default_factory=MediaPipeConfig
    )
    gestures: GestureConfig = field(
        default_factory=GestureConfig
    )
    vlc: VLCConfig = field(default_factory=VLCConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    log_file: Path = PROJECT_ROOT / "logs" / "app.log"


CONFIG = AppConfig()
