"""Main webcam gesture controller.

The main loop deliberately contains no gesture geometry or VLC HTTP details.
It wires together:
    camera -> MediaPipe -> classifier -> temporal -> state machine -> VLC
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import cv2

from config import CONFIG, PROJECT_ROOT, AppConfig, CameraConfig, GestureConfig, MediaPipeConfig, VLCConfig, UIConfig
from controllers.vlc_controller import VLCController
from gestures.classifier import Gesture
from gestures.state_machine import GestureStateMachine
from gestures.swipe import SwipeDetector
from gestures.temporal import TemporalStabilizer
from ui.dashboard import Dashboard
from utils.logger import configure_logging
from vision.camera import Camera
from vision.hand_tracker import HandTracker


def _load_config() -> AppConfig:
    path = PROJECT_ROOT / "config.json"
    if not path.exists():
        return CONFIG

    raw = json.loads(path.read_text(encoding="utf-8"))

    camera = CameraConfig(
        **{**CONFIG.camera.__dict__, **raw.get("camera", {})}
    )

    mp_raw = dict(raw.get("mediapipe", {}))
    model_path = Path(mp_raw.get("model_path", "models/hand_landmarker.task"))
    if not model_path.is_absolute():
        model_path = PROJECT_ROOT / model_path
    mp_raw["model_path"] = model_path

    media = MediaPipeConfig(
        **{**CONFIG.mediapipe.__dict__, **mp_raw}
    )

    gestures = GestureConfig(
        **{**CONFIG.gestures.__dict__, **raw.get("gestures", {})}
    )

    vlc_raw = dict(raw.get("vlc", {}))
    executable = Path(
        vlc_raw.get(
            "executable",
            str(CONFIG.vlc.executable),
        )
    )
    if not executable.is_absolute():
        executable = PROJECT_ROOT / executable
    vlc_raw["executable"] = executable

    vlc = VLCConfig(
        **{**CONFIG.vlc.__dict__, **vlc_raw}
    )

    ui = UIConfig(
        **{**CONFIG.ui.__dict__, **raw.get("ui", {})}
    )

    return AppConfig(
        camera=camera,
        mediapipe=media,
        gestures=gestures,
        vlc=vlc,
        ui=ui,
        log_file=PROJECT_ROOT / raw.get(
            "log_file",
            "logs/app.log",
        ),
    )


def _dispatch_vlc(vlc: VLCController, action: str, logger: logging.Logger) -> bool:
    methods = {
        "play": vlc.play,
        "pause": vlc.pause,
        "stop": vlc.stop,
        "next": vlc.next_track,
        "previous": vlc.previous_track,
        "volume_up": vlc.volume_up,
        "volume_down": vlc.volume_down,
        "long_forward": vlc.long_forward,
        "long_backward": vlc.long_backward,
        # Backward-compatible aliases.
        "seek_forward": vlc.seek_forward,
        "seek_backward": vlc.seek_backward,
    }

    handler = methods.get(action)
    if handler is None:
        logger.error("Unsupported action: %s", action)
        return False

    logger.info("VLC COMMAND REQUEST: %s", action.upper())

    try:
        ok = bool(handler())
    except Exception:
        logger.exception("VLC command raised an exception: %s", action)
        return False

    logger.info(
        "VLC COMMAND %s: %s",
        "SUCCESS" if ok else "FAILED",
        action.upper(),
    )
    return ok


def main() -> int:
    config = _load_config()
    logger = configure_logging(config.log_file)

    logger.info("Starting Gesture VLC Controller")
    logger.info(
        "VLC endpoint: http://%s:%s",
        config.vlc.host,
        config.vlc.port,
    )

    camera = None
    tracker = None
    vlc = None
    dashboard = Dashboard(
        config.ui.window_name,
        config.ui.debug_mode,
    )

    try:
        vlc = VLCController(
            host=config.vlc.host,
            port=config.vlc.port,
            password=config.vlc.password,
            timeout=config.vlc.timeout,
            reconnect_interval=config.vlc.reconnect_interval,
            executable=config.vlc.executable,
            auto_start=config.vlc.auto_start,
            startup_timeout=config.vlc.startup_timeout,
        )

        if vlc.connect(force=True):
            logger.info("VLC CONNECTED at %s", vlc.base_url)
        else:
            logger.warning("VLC not connected at startup")

        camera = Camera(config.camera)
        logger.info("Camera initialized: index=%s", config.camera.index)

        tracker = HandTracker(config.mediapipe)
        logger.info("MediaPipe Hand Landmarker initialized")

        from gestures.classifier import GestureClassifier

        classifier = GestureClassifier(
            extended_threshold=config.gestures.finger_extended_threshold,
            folded_threshold=config.gestures.finger_folded_threshold,
            thumb_extended_threshold=config.gestures.thumb_extended_threshold,
            thumb_folded_threshold=config.gestures.thumb_folded_threshold,
        )

        temporal = TemporalStabilizer(
            config.gestures.stability_frames,
            config.gestures.min_gesture_confidence,
            config.gestures.state_hysteresis_frames,
        )

        swipe = SwipeDetector(
            min_distance=config.gestures.swipe_min_distance,
            min_velocity=config.gestures.swipe_min_velocity,
            window_ms=config.gestures.swipe_window_ms,
            vertical_tolerance=config.gestures.swipe_vertical_tolerance,
            cooldown=config.gestures.swipe_cooldown,
            max_points=config.gestures.trajectory_max_points,
            min_open_palm_confidence=config.gestures.swipe_min_open_palm_confidence,
        )

        cooldowns = {
            "play": config.gestures.static_action_cooldown,
            "pause": config.gestures.static_action_cooldown,
            "stop": config.gestures.stop_cooldown,
            "next": config.gestures.swipe_cooldown,
            "previous": config.gestures.swipe_cooldown,
            "volume_up": config.gestures.long_hold_action_cooldown,
            "volume_down": config.gestures.long_hold_action_cooldown,
            "long_forward": config.gestures.long_hold_action_cooldown,
            "long_backward": config.gestures.long_hold_action_cooldown,
        }

        state_machine = GestureStateMachine(
            cooldowns,
            swipe,
            hold_repeat_interval=config.gestures.long_hold_repeat_interval,
            long_hold_enabled=config.gestures.long_hold_enabled,
        )

        dashboard.create()
        logger.info("Application READY")

        previous_time = time.monotonic()
        fps = 0.0

        while True:
            frame_start = time.monotonic()
            frame = camera.read()
            observations = tracker.process(frame)

            hand = None

            if observations:
                hand = max(
                    observations,
                    key=lambda item: item.handedness_score,
                )

            if hand is not None:
                result = classifier.classify(hand.landmarks)

                confirmed = temporal.update(
                    result.gesture,
                    result.confidence,
                    frame_start,
                )

                event = state_machine.update(
                    gesture=confirmed.gesture,
                    confidence=confirmed.confidence,
                    palm_center=hand.palm_center,
                    now=frame_start,
                    gesture_entered=confirmed.entered,
                )
            else:
                confirmed = temporal.update(
                    Gesture.NONE,
                    0.0,
                    frame_start,
                )

                state_machine.update(
                    gesture=Gesture.NONE,
                    confidence=0.0,
                    palm_center=None,
                    now=frame_start,
                    gesture_entered=False,
                )

                event = None

            if event is not None:
                logger.info(
                    "GESTURE EVENT: %s -> %s | hold=%.2fs",
                    event.source_gesture.value,
                    event.action.upper(),
                    event.hold_seconds,
                )

                _dispatch_vlc(
                    vlc,
                    event.action,
                    logger,
                )

            else:
                vlc.connect(force=False)

            now = time.monotonic()
            dt = max(now - previous_time, 1e-6)
            instantaneous_fps = 1.0 / dt
            fps = (
                instantaneous_fps
                if fps == 0.0
                else fps * 0.9
                + instantaneous_fps * 0.1
            )
            previous_time = now

            display = (
                cv2.flip(frame, 1)
                if config.camera.mirrored_display
                else frame.copy()
            )

            dashboard_frame = dashboard.render(
                display,
                hand_detected=hand is not None,
                handedness=hand.handedness if hand else "—",
                gesture=confirmed.gesture,
                confidence=confirmed.confidence,
                vlc_connected=vlc.connected,
                fps=fps,
                inference_ms=(now - frame_start) * 1000.0,
                state=state_machine.state.value,
                debug_values={
                    "Hold": (
                        f"{event.hold_seconds:.1f}s"
                        if event is not None
                        else "-"
                    )
                },
            )

            cv2.imshow(
                config.ui.window_name,
                dashboard_frame,
            )

            key = cv2.waitKey(1) & 0xFF

            if key in (ord("q"), ord("Q"), 27):
                logger.info("Shutdown requested by user")
                break

        return 0

    except KeyboardInterrupt:
        # Ctrl+C can arrive while MediaPipe is inside its native
        # detect_for_video() call. Treat it as a normal user shutdown rather
        # than an application error, then let the finally block release the
        # camera, MediaPipe resources, VLC HTTP session, and UI cleanly.
        logger.info("Shutdown requested by Ctrl+C")
        print("\nShutdown requested by Ctrl+C. Exiting cleanly...")
        return 0

    except Exception as exc:
        logger.exception("Fatal application error: %s", exc)
        print(f"ERROR: {exc}")
        return 1

    finally:
        if tracker is not None:
            try:
                tracker.close()
            except Exception:
                pass

        if camera is not None:
            try:
                camera.release()
            except Exception:
                pass

        if vlc is not None:
            try:
                vlc.close()
            except Exception:
                pass

        try:
            dashboard.close()
        except Exception:
            pass

        cv2.destroyAllWindows()
        logger.info("Application stopped")


if __name__ == "__main__":
    raise SystemExit(main())