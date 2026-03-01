# dashboard/engine_control.py
from __future__ import annotations

import datetime as dt
import json
import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

RUNTIME_DIR = Path("runtime/engine")
STATE_PATH = RUNTIME_DIR / "engine_state.json"

# matches your CLI default (runtime/logs/paper_trader.log)
LOG_PATH = Path("runtime/logs/paper_trader.log")


@dataclass(frozen=True)
class EngineState:
    pid: int
    started_at_utc: str
    cmd: list[str]
    cwd: str


def _ensure_runtime() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _read_state() -> Optional[EngineState]:
    if not STATE_PATH.exists():
        return None
    try:
        raw = json.loads(STATE_PATH.read_text())
        return EngineState(
            pid=int(raw["pid"]),
            started_at_utc=str(raw["started_at_utc"]),
            cmd=list(raw["cmd"]),
            cwd=str(raw.get("cwd") or os.getcwd()),
        )
    except Exception:
        return None


def _write_state(state: EngineState) -> None:
    _ensure_runtime()
    STATE_PATH.write_text(
        json.dumps(
            {
                "pid": state.pid,
                "started_at_utc": state.started_at_utc,
                "cmd": state.cmd,
                "cwd": state.cwd,
            },
            indent=2,
        )
    )


def _clear_state() -> None:
    if STATE_PATH.exists():
        STATE_PATH.unlink()


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def get_status() -> dict[str, Any]:
    state = _read_state()
    if not state:
        return {"running": False}

    running = _pid_alive(state.pid)
    if not running:
        _clear_state()
        return {"running": False}

    return {
        "running": True,
        "pid": state.pid,
        "started_at_utc": state.started_at_utc,
        "cmd": state.cmd,
        "cwd": state.cwd,
        "log_path": str(LOG_PATH),
    }


def start_engine(args: list[str]) -> dict[str, Any]:
    """
    args: extra CLI args for paper_trader.py, e.g.
      ["--feed","demo","--ui","rich"]
    """
    status = get_status()
    if status.get("running"):
        return {"ok": False, "message": f"engine already running (pid={status['pid']})"}

    _ensure_runtime()

    cmd = ["python", "paper_trader.py", *args]

    # line-buffered append
    log_f = open(LOG_PATH, "a", buffering=1)

    # start detached in its own process group (mac/linux)
    p = subprocess.Popen(
        cmd,
        stdout=log_f,
        stderr=log_f,
        cwd=os.getcwd(),
        start_new_session=True,
    )

    state = EngineState(
        pid=p.pid,
        started_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        cmd=cmd,
        cwd=os.getcwd(),
    )
    _write_state(state)

    return {"ok": True, "pid": p.pid, "cmd": cmd}


def stop_engine(timeout_s: float = 3.0) -> dict[str, Any]:
    status = get_status()
    if not status.get("running"):
        return {"ok": False, "message": "engine is not running"}

    pid = int(status["pid"])

    # terminate the whole process group
    try:
        os.killpg(pid, signal.SIGTERM)
    except Exception:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception as ex:
            return {"ok": False, "message": f"failed to SIGTERM pid {pid}: {ex}"}

    import time

    end = time.time() + timeout_s
    while time.time() < end:
        if not _pid_alive(pid):
            _clear_state()
            return {"ok": True, "message": "stopped"}

        time.sleep(0.1)

    # hard kill after timeout
    try:
        os.killpg(pid, signal.SIGKILL)
    except Exception:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass

    _clear_state()
    return {"ok": True, "message": "killed (SIGKILL) after timeout"}
