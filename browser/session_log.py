import os
import threading
from datetime import datetime, timezone
from pathlib import Path

# Never write next to the installed app -- under a packaged install that's a
# root-owned path (e.g. /opt/cgp-exam-shell), so a normal user process can't create
# files there. XDG_STATE_HOME (~/.local/state by default) is always user-writable.
_STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "cgp-exam-shell"
_STATE_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = _STATE_DIR / "sessionLog.txt"

_lock = threading.Lock()


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def log(message: str):
    """Bare marker line, no timestamp prefix -- RAW:, PARSED:, CALLING API..., API SUCCESS."""
    _write(message)


def banner(text: str):
    """A visually distinct separator line, e.g. to mark the start of a new shell run."""
    _write(f"===== {text} @ {_timestamp()} =====")


def log_event(message: str):
    """Timestamp-prefixed line -- POST .../SIGN ... entries."""
    _write(f"[{_timestamp()}] {message}")


def _write(line: str):
    with _lock:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
