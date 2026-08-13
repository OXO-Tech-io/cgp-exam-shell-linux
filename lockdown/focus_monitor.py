import subprocess
from PySide6.QtCore import QObject, QTimer, Signal


class FocusMonitor(QObject):
    focus_lost = Signal(str)

    def __init__(self, window, poll_interval_ms: int = 300):
        super().__init__()
        self.window = window
        self._own_window_id = None
        self._currently_lost = False   # tracks whether we're mid-episode

        self.timer = QTimer(self)
        self.timer.setInterval(poll_interval_ms)
        self.timer.timeout.connect(self._check)

    def start(self):
        self._own_window_id = str(int(self.window.winId()))
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def _check(self):
        is_lost, reason = self._evaluate_focus()

        if is_lost and not self._currently_lost:
            # Just entered a focus-lost episode -- count it once, here.
            self._currently_lost = True
            self.focus_lost.emit(reason)
        elif not is_lost and self._currently_lost:
            # Focus returned -- episode over, ready to count the next one.
            self._currently_lost = False

    def _evaluate_focus(self) -> tuple[bool, str]:
        if not self.window.isActiveWindow():
            return True, "qt-level: window not active"

        active_id = self._get_os_active_window_id()
        if active_id is not None and active_id != self._own_window_id:
            return True, "os-level: foreground window differs from exam window"

        return False, ""

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
            return None