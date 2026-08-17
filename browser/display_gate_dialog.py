"""
Blocks the exam shell from launching while more than one display is
connected. Shown before ExamShellWindow is ever constructed.
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication

from browser.theme import CRITICAL_DIALOG_STYLE
from lockdown.display_monitor import connected_screen_count


class DisplayGateDialog(QDialog):
    """
    Modal dialog shown at startup if multiple screens are detected.
    Polls every second and auto-closes itself the moment only one
    screen remains connected -- the student doesn't need to click
    anything, just physically disconnect the extra monitor.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multiple Displays Detected")
        self.setModal(True)
        self.setFixedWidth(460)
        self.setStyleSheet(CRITICAL_DIALOG_STYLE)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("⚠ Multiple Displays Detected")
        title.setObjectName("criticalTitle")
        layout.addWidget(title)

        self.body = QLabel()
        self.body.setObjectName("criticalBody")
        self.body.setWordWrap(True)
        layout.addWidget(self.body)

        hint = QLabel("This window will close automatically once only one display remains connected.")
        hint.setObjectName("criticalBody")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._update_body_text()

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._check)
        self._timer.start()

    def _update_body_text(self):
        count = connected_screen_count()
        self.body.setText(
            f"CGPExamShell requires a single display. "
            f"You currently have {count} displays connected. "
            f"Please disconnect all but one monitor before continuing."
        )

    def _check(self):
        if connected_screen_count() <= 1:
            self._timer.stop()
            self.accept()
        else:
            self._update_body_text()