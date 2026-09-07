"""Gesture state machine for VLC-native long-hold controls."""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from gestures.classifier import Gesture


@dataclass(frozen=True)
class ActionEvent:
    action: str
    source_gesture: Gesture
    confidence: float
    hold_seconds: float = 0.0


class GestureStateMachine:
    """Convert stable gestures into edge-triggered and long-hold events.

    Immediate controls:
        ONE_FINGER   -> PLAY
        TWO_FINGER   -> PAUSE
        THREE_FINGER -> STOP

    Long holds:
        ONE_FINGER  >= 4s -> VLC Volume Up (repeat while held)
        TWO_FINGER  >= 4s -> VLC Volume Down (repeat while held)
        OPEN_PALM   >= 5s -> VLC Long Forward Jump (ONCE per hold)
        FOUR_FINGER >= 5s -> VLC Long Backward Jump (ONCE per hold)

    The jump actions intentionally do not repeat every second. VLC's long
    jump is commonly configured to a large interval (e.g. 300 s), so repeating
    it while a hand remains held would be unpleasant and unsafe for control.
    """

    STATIC_ACTIONS = {
        Gesture.ONE_FINGER: "play",
        Gesture.TWO_FINGER: "pause",
        Gesture.THREE_FINGER: "stop",
    }

    LONG_HOLD_ACTIONS = {
        Gesture.ONE_FINGER: ("volume_up", 4.0, True),
        Gesture.TWO_FINGER: ("volume_down", 4.0, True),
        Gesture.OPEN_PALM: ("long_forward", 5.0, False),
        Gesture.FOUR_FINGER: ("long_backward", 5.0, False),
    }

    def __init__(
        self,
        cooldowns: dict[str, float] | None = None,
        swipe_detector=None,
        *,
        hold_repeat_interval: float = 1.0,
        long_hold_enabled: bool = True,
    ) -> None:
        self.cooldowns = dict(cooldowns or {})
        self.swipe_detector = swipe_detector
        self.hold_repeat_interval = max(0.1, float(hold_repeat_interval))
        self.long_hold_enabled = bool(long_hold_enabled)

        self.state = Gesture.NONE
        self.last_action_time: dict[str, float] = {}
        self._active_gesture = Gesture.NONE
        self._hold_started_at: float | None = None
        self._long_hold_started = False
        self._last_long_hold_event = -1e9

    def update(
        self,
        gesture: Gesture,
        confidence: float,
        palm_center: tuple[float, float] | None = None,
        now: float | None = None,
        gesture_entered: bool = False,
    ) -> ActionEvent | None:
        timestamp = monotonic() if now is None else float(now)

        if gesture is not self._active_gesture:
            self._active_gesture = gesture
            self._hold_started_at = timestamp if gesture is not Gesture.NONE else None
            self._long_hold_started = False
            self._last_long_hold_event = -1e9

        if gesture is Gesture.NONE:
            self.reset()
            return None

        hold_seconds = (
            0.0
            if self._hold_started_at is None
            else max(0.0, timestamp - self._hold_started_at)
        )

        # Edge-triggered playback commands.
        if gesture_entered and gesture in self.STATIC_ACTIONS:
            action = self.STATIC_ACTIONS[gesture]
            if self._allowed(action, timestamp):
                event = ActionEvent(action, gesture, float(confidence), 0.0)
                self._record(event, timestamp)
                self.state = gesture
                return event

        if self.long_hold_enabled:
            spec = self.LONG_HOLD_ACTIONS.get(gesture)
            if spec is not None:
                action, threshold, repeat = spec
                if hold_seconds >= threshold:
                    first_fire = not self._long_hold_started
                    can_repeat = (
                        repeat
                        and timestamp - self._last_long_hold_event >= self.hold_repeat_interval
                    )

                    if first_fire or can_repeat:
                        if self._allowed(action, timestamp):
                            event = ActionEvent(
                                action=action,
                                source_gesture=gesture,
                                confidence=float(confidence),
                                hold_seconds=hold_seconds,
                            )
                            self._record(event, timestamp)
                            self._long_hold_started = True
                            self._last_long_hold_event = timestamp
                            self.state = gesture
                            return event

        self.state = gesture
        return None

    def _allowed(self, action: str, now: float) -> bool:
        last = self.last_action_time.get(action, -1e9)
        return now - last >= self.cooldowns.get(action, 0.0)

    def _record(self, event: ActionEvent, now: float) -> None:
        self.last_action_time[event.action] = now

    def reset(self) -> None:
        self.state = Gesture.NONE
        self._active_gesture = Gesture.NONE
        self._hold_started_at = None
        self._long_hold_started = False
        self._last_long_hold_event = -1e9

        if self.swipe_detector is not None:
            try:
                self.swipe_detector.reset()
            except Exception:
                pass