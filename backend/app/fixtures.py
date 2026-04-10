from __future__ import annotations

import json
from pathlib import Path

from .schemas import BorrowerSignalInput

_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "personas.json"


def load_personas() -> dict[str, BorrowerSignalInput]:
    with _FIXTURE_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return {entry["id"]: BorrowerSignalInput(**entry["signals"]) for entry in raw["personas"]}
