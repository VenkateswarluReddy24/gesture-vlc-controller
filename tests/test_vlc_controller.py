from controllers.vlc_controller import VLCController


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.auth = None
        self.calls = []
        self.state = "stopped"

    def get(self, url, params=None, timeout=None):
        command = (params or {}).get("command")
        self.calls.append(command)
        if command in {"pl_forceresume", "pl_play"}:
            self.state = "playing"
        elif command == "pl_forcepause":
            self.state = "paused"
        elif command == "pl_stop":
            self.state = "stopped"
        return FakeResponse({
            "state": self.state,
            "position": 0.0,
            "time": 0,
            "length": 60,
        })

    def close(self):
        return None


def test_vlc_commands_map_to_supported_http_commands():
    controller = VLCController(
        host="127.0.0.1",
        port=4000,
        password="vlc123",
        timeout=1,
        reconnect_interval=2,
    )
    fake = FakeSession()
    controller.session = fake

    assert controller.play() is True
    assert controller.pause() is True
    assert controller.stop() is True
    assert controller.next_track() is True
    assert controller.previous_track() is True

    assert "pl_play" in fake.calls
    assert "pl_forcepause" in fake.calls
    assert "pl_stop" in fake.calls
    assert "pl_next" in fake.calls
    assert "pl_previous" in fake.calls
