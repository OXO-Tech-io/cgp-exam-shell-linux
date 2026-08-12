from pynput import keyboard
from PySide6.QtCore import QObject, Signal


class HotkeyBlocker(QObject):
    """Detects exam-violation key combos and reports them via a Qt signal."""

    violation = Signal(str)  # emits the combo string that was pressed

    BLOCKED_COMBOS = [
        "<ctrl>+<alt>+t",
        "<ctrl>+<alt>+<f2>",
        "<alt>+<tab>",
        "<ctrl>+<alt>+<delete>",
        "<cmd>",
        "<print_screen>",
    ]

    def __init__(self):
        super().__init__()
        self._listener = None

    def _make_callback(self, combo: str):
        def _cb():
            self.violation.emit(combo)
        return _cb

    def start(self):
        mapping = {combo: self._make_callback(combo) for combo in self.BLOCKED_COMBOS}
        self._listener = keyboard.GlobalHotKeys(mapping)
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()