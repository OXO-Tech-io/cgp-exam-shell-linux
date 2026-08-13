import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

if getattr(sys, "frozen", False):
    # PyInstaller extracts --add-data "config/exam_config.json:config" here; __file__
    # inside a frozen build doesn't map to a real path on disk the way it does in dev.
    _CONFIG_PATH = Path(sys._MEIPASS) / "config" / "exam_config.json"
else:
    _CONFIG_PATH = Path(__file__).resolve().parent / "exam_config.json"


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_config = _load_config()

# Override with CGP_BACKEND_BASE_URL for staging/QA without touching the installed config file.
BASE_URL = os.environ.get("CGP_BACKEND_BASE_URL", _config.get("base_url", "")).rstrip("/")

# Hardcoded allowlist -- same role as ConfigValidator.cs on the Windows shell: even if
# exam_config.json is tampered with, or a cgpshell:// launch URI carries an unexpected
# query string, the shell will refuse to load anything outside these hosts, so the SSO
# token handoff can't be redirected to an attacker-controlled page.
ALLOWED_EXAM_HOSTS = {
    "cgp-assessment-frontend-app-297614602590.us-central1.run.app",
}


def validate_exam_url(url: str) -> str:
    """Raises ValueError if url isn't https and on an allowlisted host; else returns it."""
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise ValueError(f"exam URL must use https: {url!r}")
    if parts.hostname not in ALLOWED_EXAM_HOSTS:
        raise ValueError(f"exam URL host not allowlisted: {parts.hostname!r}")
    return url
