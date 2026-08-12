import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QDialog,
    QLabel, QTextEdit, QMessageBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PySide6.QtCore import QUrl, Qt

from lockdown.hotkey_blocker import HotkeyBlocker
from lockdown.focus_monitor import FocusMonitor
from browser.violation_overlay import ViolationOverlay


class ExitReasonDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("End Exam Session")
        self.setModal(True)
        self.reason = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Please state your reason for ending the exam:"))

        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)

        confirm_btn = QPushButton("Confirm Exit")
        confirm_btn.clicked.connect(self._confirm)
        layout.addWidget(confirm_btn)

    def _confirm(self):
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Required", "You must provide a reason before exiting.")
            return
        self.reason = text
        self.accept()


class ExamShellWindow(QWidget):
    MAX_VIOLATIONS = 3

    def __init__(self, exam_url: str):
        super().__init__()

        self.violation_count = 0
        self._allow_close = False

        self.profile = QWebEngineProfile()
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
        )

        self.webview = QWebEngineView(self)
        page = QWebEnginePage(self.profile, self.webview)
        self.webview.setPage(page)
        self.webview.load(QUrl(exam_url))

        self.exit_btn = QPushButton("Exit Exam", self)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f; color: white; font-weight: bold;
                padding: 8px 16px; border-radius: 4px; border: none; outline: none;
            }
            QPushButton:hover { background-color: #b71c1c; }
            QPushButton:focus { border: none; outline: none; }
            QPushButton:pressed { background-color: #a31515; border: none; }
        """)
        self.exit_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.exit_btn.clicked.connect(self.handle_exit_request)
        self.exit_btn.move(12, 12)
        self.exit_btn.raise_()

        self.overlay = ViolationOverlay(self, on_countdown_done=self._reseize_focus)

        self.hotkey_blocker = HotkeyBlocker()
        self.hotkey_blocker.violation.connect(
            lambda combo: self.register_violation(f"Blocked key combo: {combo}")
        )
        self.hotkey_blocker.start()

        self.focus_monitor = FocusMonitor(self)
        self.focus_monitor.focus_lost.connect(self.register_violation)
        self.focus_monitor.start()

    def resizeEvent(self, event):
        self.webview.setGeometry(0, 0, self.width(), self.height())
        self.exit_btn.move(12, 12)
        self.exit_btn.raise_()
        super().resizeEvent(event)

    def register_violation(self, message: str):
        self.violation_count += 1
        print(f"[VIOLATION #{self.violation_count}] {message}")

        if self.violation_count >= self.MAX_VIOLATIONS:
            self._force_exit_due_to_violations()
            return

        self.overlay.show_violation(message, self.violation_count)

    def _reseize_focus(self):
        self.showFullScreen()
        self.activateWindow()
        self.raise_()

    def _force_exit_due_to_violations(self):
        print(f"[EXAM TERMINATED] Reached {self.MAX_VIOLATIONS} violations.")
        self.hotkey_blocker.stop()
        self.focus_monitor.stop()
        self._allow_close = True
        QMessageBox.critical(
            self, "Exam Terminated",
            f"Your exam session has been ended after {self.MAX_VIOLATIONS} violations."
        )
        self.close()

    def handle_exit_request(self):
        dialog = ExitReasonDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            print(f"[EXIT REASON] {dialog.reason}")
            self.hotkey_blocker.stop()
            self.focus_monitor.stop()
            self._allow_close = True
            self.close()

    def closeEvent(self, event):
        if self._allow_close:
            event.accept()
        else:
            event.ignore()