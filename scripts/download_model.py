"""Download the official MediaPipe Hand Landmarker full model bundle."""
from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
ROOT = Path(__file__).resolve().parent
DEST = ROOT / "models" / "hand_landmarker.task"


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading official Hand Landmarker model to: {DEST}")
    with urlopen(MODEL_URL, timeout=60) as response:
        data = response.read()
    DEST.write_bytes(data)
    print(f"Downloaded {len(data):,} bytes.")


if __name__ == "__main__":
    main()
