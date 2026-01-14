# utils/storage.py
# -*- coding: utf-8 -*-

import json
from pathlib import Path


def load_json(path, default=None):
    path = Path(path)

    if not path.exists():
        return default if default is not None else {}

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
