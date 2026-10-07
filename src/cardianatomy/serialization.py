"""Strict JSON parsing and atomic artifact replacement."""

import json
import os
from pathlib import Path
import tempfile


def read_json(path):
    def invalid(value):
        raise ValueError(f"Nonstandard JSON number: {value}")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(
        Path(path).read_text(encoding="utf-8"), parse_constant=invalid, object_pairs_hook=unique
    )


def write_text_atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".cardianatomy-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def write_json_atomic(path, value):
    text = json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n"
    write_text_atomic(path, text)
