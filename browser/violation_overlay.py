"""
Full-screen violation warning overlay.

This is a SEPARATE top-level window, not a child widget of the exam
window. That's deliberate: Qt.WindowStaysOnTopHint lets this float
above whatever the student switched to (another app, a terminal, the
desktop) -- a child widget could only ever render inside its own
parent's window, invisible if focus moved elsewhere.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication

from browser.theme import VIOLATION_OVERLAY_STYLE

COUNTDOWN_SECONDS = 2
TICK_MS = 50


class ViolationOverlay(QWidget):
    def __init__(self, parent, on_countdown_done):
        # No parent passed to super().__init__() -- this must be a real
        # top-level window, not embedded inside ExamShellWindow.
        super().__init__()
        self._exam_window = parent
        self.on_countdown_done = on_countdown_done

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # keeps it out of the taskbar/alt-tab list
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("violationBackdrop")
        self.setStyleSheet(VIOLATION_OVERLAY_STYLE)

        self._total_ticks = int((COUNTDOWN_SECONDS * 1000) / TICK_MS)
        self._ticks_left = self._total_ticks

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch()

        card_row = QHBoxLayout()
        card_row.addStretch()

        self.card = QWidget()
        self.card.setObjectName("violationCard")
        self.card.setFixedWidth(420)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(12)

        header_row = QHBoxLayout()
        icon = QLabel("⚠")
        icon.setObjectName("violationIcon")
        header_row.addWidget(icon)
        header_row.addStretch()
        self.count_label = QLabel("")
        self.count_label.setObjectName("violationCount")
        header_row.addWidget(self.count_label)
        card_layout.addLayout(header_row)

        title = QLabel("Exam Violation Detected")
        title.setObjectName("violationTitle")
        card_layout.addWidget(title)

        self.message_label = QLabel("")
        self.message_label.setObjectName("violationMessage")
        self.message_label.setWordWrap(True)
        card_layout.addWidget(self.message_label)

        self.progress = QProgressBar()
        self.progress.setObjectName("violationProgress")
        self.progress.setTextVisible(False)
        self.progress.setRange(0, self._total_ticks)
        card_layout.addWidget(self.progress)

        self.countdown_label = QLabel("")
        self.countdown_label.setObjectName("violationCountdownLabel")
        card_layout.addWidget(self.countdown_label)

        card_row.addWidget(self.card)
        card_row.addStretch()
        outer.addLayout(card_row)
        outer.addStretch()

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)

        self.hide()

    def show_violation(self, message: str, violation_count: int):
        self._ticks_left = self._total_ticks
        self.message_label.setText(message)
        self.count_label.setText(f"VIOLATION #{violation_count}")
        self.progress.setValue(self._total_ticks)
        self._update_countdown_text()

        # Cover the full screen the exam window lives on -- not just the
        # exam window's own geometry, since focus may currently be
        # somewhere else entirely.
        screen = self._exam_window.screen() or QGuiApplication.primaryScreen()
        self.setGeometry(screen.geometry())

        self.show()
        self.raise_()
        self.activateWindow()  # bring this specific window forward, on top of whatever has focus
        self._timer.start()

    def _tick(self):
        self._ticks_left -= 1
        self.progress.setValue(max(self._ticks_left, 0))
        self._update_countdown_text()

        if self._ticks_left <= 0:
            self._timer.stop()
            self.hide()
            self.on_countdown_done()

    def _update_countdown_text(self):
        seconds_left = max(self._ticks_left, 0) * TICK_MS / 1000
        self.countdown_label.setText(f"Returning to exam in {seconds_left:.1f}s…")