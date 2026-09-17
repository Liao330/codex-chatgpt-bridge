from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re
import tempfile
from typing import Any

from .errors import ValidationError


RUN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,79}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ccw_home() -> Path:
    return Path(os.environ.get("CCW_HOME", Path.home() / ".ccw")).resolve()


def runs_root() -> Path:
    return ccw_home() / "runs"


def validate_run_id(run_id: str) -> str:
    if not RUN_ID_RE.fullmatch(run_id):
        raise ValidationError("run id must match [a-z0-9][a-z0-9._-]{2,79}")
    return run_id


def run_dir(run_id: str) -> Path:
    return runs_root() / validate_run_id(run_id)


def ensure_run_dir(run_id: str) -> Path:
    path = run_dir(run_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def atomic_write_text(path: Path, text: str, *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        if private:
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def write_json(path: Path, value: Any, *, private: bool = False) -> None:
    atomic_write_text(
        path,
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        private=private,
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def append_event(run_id: str, event: dict[str, Any]) -> None:
    path = ensure_run_dir(run_id) / "events.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
