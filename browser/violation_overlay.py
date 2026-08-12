from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QTimer


class ViolationOverlay(QLabel):
    """
    A floating, always-on-top warning that counts down and then calls
    on_countdown_done -- used to re-seize focus after showing the warning.
    """

    def __init__(self, parent, on_countdown_done):
        super().__init__(parent)
        self.on_countdown_done = on_countdown_done
        self._seconds_left = 2

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            background-color: rgba(211, 47, 47, 235);
            color: white;
            font-size: 22px;
            font-weight: bold;
            border-radius: 8px;
        """)
        self.setWordWrap(True)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    def show_violation(self, message: str, violation_count: int):
        self._seconds_left = 2
        self._message = message
        self._violation_count = violation_count
        self._update_text()

        # Cover most of the parent window, centered
        parent_rect = self.parent().rect()
        self.setGeometry(
            parent_rect.width() // 6, parent_rect.height() // 3,
            parent_rect.width() * 2 // 3, parent_rect.height() // 4
        )
        self.raise_()
        self.show()
        self._timer.start()

    def _update_text(self):
        self.setText(
            f"⚠ EXAM VIOLATION #{self._violation_count}\n\n"
            f"{self._message}\n\n"
            f"Returning to exam in {self._seconds_left}..."
        )

    def _tick(self):
        self._seconds_left -= 1
        if self._seconds_left <= 0:
            self._timer.stop()
            self.hide()
            self.on_countdown_done()
        else:
            self._update_text()