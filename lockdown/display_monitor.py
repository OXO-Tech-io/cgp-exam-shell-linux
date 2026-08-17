"""
Multi-monitor detection.

Two responsibilities:
  1. Pre-start gate -- blocks the exam from launching at all while more
     than one screen is connected.
  2. Live monitoring -- if a screen is added *during* the exam (a second
     monitor plugged in mid-session), this is treated as a critical
     violation, not a countdown-and-warn case. Multiple displays are a
     bigger integrity risk than a stray keypress, so this ends the
     session immediately rather than counting toward the 3-strike limit.

Qt's QGuiApplication.screens() reflects real connected displays,
independent of X11 vs Wayland -- this works on both, unlike the
keyboard-grab approaches.
"""

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication


def connected_screen_count() -> int:
    return len(QGuiApplication.screens())


class DisplayMonitor(QObject):
    """Watches for a screen being added/removed after startup."""

    screen_count_changed = Signal(int)  # emits new total screen count

    def __init__(self):
        super().__init__()
        self._app = QGuiApplication.instance()

    def start(self):
        self._app.screenAdded.connect(self._on_screen_changed)
        self._app.screenRemoved.connect(self._on_screen_changed)

    def stop(self):
        try:
            self._app.screenAdded.disconnect(self._on_screen_changed)
            self._app.screenRemoved.disconnect(self._on_screen_changed)
        except (TypeError, RuntimeError):
            pass  # already disconnected

    def _on_screen_changed(self, _screen=None):
        self.screen_count_changed.emit(connected_screen_count())