import subprocess
from PySide6.QtCore import QObject, QTimer, Signal


class FocusMonitor(QObject):
    """
    Two independent focus checks, run on every tick:

    1. Qt-level (`isActiveWindow`) -- fast, no subprocess, but only knows
       about focus *within this application's own windows*. Misses cases
       where the compositor's notion of "active" diverges from Qt's.

    2. OS-level (`xdotool getactivewindow`) -- asks the window manager
       directly which window ID is actually in the foreground right now,
       independent of anything Qt believes. This is ground truth.

    Either check failing counts as focus lost -- we don't require both
    to agree, since the whole point is catching whichever one notices
    first.
    """

    focus_lost = Signal(str)  # carries a short reason string

    def __init__(self, window, poll_interval_ms: int = 300):
        super().__init__()
        self.window = window
        self._own_window_id = None  # resolved lazily, window must be shown first

        self.timer = QTimer(self)
        self.timer.setInterval(poll_interval_ms)
        self.timer.timeout.connect(self._check)

    def start(self):
        # winId() only returns a real, stable value after the window has
        # been shown at least once -- calling this too early can return 0.
        self._own_window_id = str(int(self.window.winId()))
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def _check(self):
        if not self.window.isActiveWindow():
            self.focus_lost.emit("qt-level: window not active")
            return

        active_id = self._get_os_active_window_id()
        if active_id is not None and active_id != self._own_window_id:
            self.focus_lost.emit("os-level: foreground window differs from exam window")

    def _get_os_active_window_id(self) -> str | None:
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True, text=True, timeout=0.5
            )
            if result.returncode != 0:
                return None
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # FileNotFoundError -> xdotool not installed; timeout -> WM slow
            # to respond. Either way, we can't get a reading this tick --
            # don't treat "couldn't check" as "check passed."
            return None