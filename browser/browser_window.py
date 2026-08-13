"""
Main exam browser window.

QWebEngineView is Chromium-based (same engine family as WebView2 on
Windows), so cookie/profile behavior stays close to what you already
solved there. Fullscreen + close/minimize suppression happens here;
deeper OS-level lockdown (hotkeys, focus monitoring) lives in the
lockdown/ package and is wired in here.
"""

import threading

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QDialog,
    QLabel, QTextEdit, QMessageBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QUrl, Qt, Signal

from lockdown.hotkey_blocker import HotkeyBlocker
from lockdown.focus_monitor import FocusMonitor
from browser.violation_overlay import ViolationOverlay
from browser import session_log
from browser.bridge import WebBridge, make_bridge_script, BRIDGE_JS_OBJECT_NAME
from browser.token_bootstrap import make_token_bootstrap_script
from browser.session_manager import SessionManager, SessionError, HOTKEY_EVENT_TYPES


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

    session_error = Signal(str)

    def __init__(self, exam_url: str):
        super().__init__()

        self.violation_count = 0
        self._allow_close = False

        session_log.banner("Shell started")

        self.session = SessionManager()
        self.session_error.connect(self._show_session_error)

        # ---- Profile: off-the-record, no persistent cookies -------------
        self.profile = QWebEngineProfile()
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
        )
        self.profile.scripts().insert(make_token_bootstrap_script())
        self.profile.scripts().insert(make_bridge_script())

        # ---- WebChannel bridge (JS -> Python messages) ------------------
        self.channel = QWebChannel()
        self.bridge = WebBridge()
        self.channel.registerObject(BRIDGE_JS_OBJECT_NAME, self.bridge)
        self.bridge.assessment_started.connect(self._on_assessment_started)

        # ---- Webview + page: created FIRST, before anything touches
        # webview.settings() or the page's signals ------------------------
        self.webview = QWebEngineView(self)
        page = QWebEnginePage(self.profile, self.webview)
        page.setWebChannel(self.channel)
        page.featurePermissionRequested.connect(self._handle_permission_request)
        self.webview.setPage(page)

        # Allow audio/video to autoplay without a prior user gesture --
        # the assessment's question audio needs this, since it plays
        # immediately on page load, before any click has happened.
        settings = self.webview.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False
        )

        self.webview.load(QUrl(exam_url))

        # ---- Exit button --------------------------------------------------
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

        # ---- Violation overlay + lockdown layers ---------------------------
        self.overlay = ViolationOverlay(self, on_countdown_done=self._reseize_focus)

        self.hotkey_blocker = HotkeyBlocker()
        self.hotkey_blocker.violation.connect(
            lambda combo: self.register_violation(f"Blocked key combo: {combo}")
        )
        self.hotkey_blocker.violation.connect(
            lambda combo: self.session.queue_security_event(
                HOTKEY_EVENT_TYPES.get(combo, "HOTKEY_BLOCKED"),
                f"Blocked key combo: {combo}",
            )
        )
        self.hotkey_blocker.start()

        self.focus_monitor = FocusMonitor(self)
        self.focus_monitor.focus_lost.connect(self.register_violation)
        self.focus_monitor.focus_lost.connect(
            lambda reason: self.session.queue_security_event("FOCUS_LOST", reason)
        )
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
        self._send_audit_log_async(
            "EXAM_CANCELLED", f"Exam terminated after {self.MAX_VIOLATIONS} violations."
        )
        self.hotkey_blocker.stop()
        self.focus_monitor.stop()
        self._allow_close = True
        QMessageBox.critical(
            self, "Exam Terminated",
            f"Your exam session has been ended after {self.MAX_VIOLATIONS} violations."
        )
        self.close()

    def handle_exit_request(self):
        # Stop watching for focus loss before the dialog opens -- otherwise
        # the dialog itself becoming the active window gets flagged as a
        # focus-loss violation.
        self.focus_monitor.stop()

        dialog = ExitReasonDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            print(f"[EXIT REASON] {dialog.reason}")
            self._send_audit_log_async("EXAM_CANCELLED", dialog.reason)
            self.hotkey_blocker.stop()
            self._allow_close = True
            self.close()
        else:
            self.focus_monitor.start()

    def _on_assessment_started(self, payload: dict):
        if self.session.session_token is not None:
            return  # duplicate assessment_started message; session already established

        exam_id = payload.get("examId")
        student_id = payload.get("studentId")
        session_token = payload.get("sessionToken")

        def _start():
            try:
                self.session.start_session(exam_id, student_id, session_token)
            except SessionError as exc:
                self.session_error.emit(str(exc))
                return

            self.session.queue_security_event(
                "ASSESSMENT_STARTED", "Exam started from Webview message"
            )
            try:
                result = self.session.send_audit_log(
                    "EXAM_STARTED", "Student started the examination."
                )
                print(f"[AUDIT-LOG] EXAM_STARTED -> {result}")
                if result.get("accepted"):
                    session_log.log("API SUCCESS")
            except SessionError as exc:
                print(f"[AUDIT-LOG SEND FAILED] action=EXAM_STARTED: {exc}")

        threading.Thread(target=_start, daemon=True).start()

    def _send_audit_log_async(self, action: str, description: str):
        if self.session.session_token is None:
            return  # no session was ever established; nothing to report

        def _send():
            try:
                result = self.session.send_audit_log(action, description)
                print(f"[AUDIT-LOG] {action} -> {result}")
            except SessionError as exc:
                print(f"[AUDIT-LOG SEND FAILED] action={action}: {exc}")

        threading.Thread(target=_send, daemon=True).start()

    def _show_session_error(self, message: str):
        QMessageBox.critical(self, "Backend Session Error", message)

    def _handle_permission_request(self, origin, feature):
        if feature in (
            QWebEnginePage.Feature.MediaAudioCapture,
            QWebEnginePage.Feature.MediaVideoCapture,
            QWebEnginePage.Feature.MediaAudioVideoCapture,
        ):
            self.webview.page().setFeaturePermission(
                origin, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
            )

    def closeEvent(self, event):
        if self._allow_close:
            event.accept()
        else:
            event.ignore()