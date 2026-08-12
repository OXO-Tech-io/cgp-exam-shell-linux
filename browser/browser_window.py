import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QDialog,
    QLabel, QTextEdit, QMessageBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PySide6.QtCore import QUrl, Qt
from lockdown.key_grabber import KeyGrabber

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
    def __init__(self, exam_url: str):
        super().__init__()

        self.violation_count = 0
        
        # 1. Turn on GNOME workspace and system lockdowns
        self.set_gnome_lockdown(True)
        
        # 2. Start capturing global system hotkeys via X11
        self.key_grabber = KeyGrabber()
        self.key_grabber.violation.connect(self.handle_violation)
        self.key_grabber.start()

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
                background-color: #d32f2f;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
                outline: none;
            }
            QPushButton:hover { background-color: #b71c1c; }
            QPushButton:focus { border: none; outline: none; }
            QPushButton:pressed { background-color: #a31515; border: none; }
        """)
        self.exit_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.exit_btn.clicked.connect(self.handle_exit_request)
        self.exit_btn.move(12, 12)
        self.exit_btn.raise_()
        
        self._allow_close = False

    def set_gnome_lockdown(self, disable: bool):
        """Disables or restores Ubuntu desktop gestures and workspace switching."""
        # When browser asks to 'disable' system options, we change bindings to empty strings
        left_bind = "['']" if disable else "['<Super>Page_Up', '<Control><Alt>Left', '<Super><Shift>Page_Up']"
        right_bind = "['']" if disable else "['<Super>Page_Up', '<Control><Alt>Right', '<Super><Shift>Page_Down']"
        lockdown_value = "true" if disable else "false"
        
        try:
            # Clear or restore workspace movement keys
            subprocess.run(["gsettings", "set", "org.gnome.desktop.wm.keybindings", "switch-to-workspace-left", left_bind], check=False)
            subprocess.run(["gsettings", "set", "org.gnome.desktop.wm.keybindings", "switch-to-workspace-right", right_bind], check=False)
            
            # Disable command line access (Alt+F2 runner and terminal access restrictions)
            subprocess.run(["gsettings", "set", "org.gnome.desktop.lockdown", "disable-command-line", lockdown_value], check=False)
            subprocess.run(["gsettings", "set", "org.gnome.desktop.lockdown", "disable-printing", lockdown_value], check=False)
        except Exception as e:
            print(f"Failed to modify gsettings parameters: {e}")

    def resizeEvent(self, event):
        self.webview.setGeometry(0, 0, self.width(), self.height())
        self.exit_btn.move(12, 12)
        self.exit_btn.raise_()
        super().resizeEvent(event)

    def handle_exit_request(self):
        dialog = ExitReasonDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            print(f"[EXIT REASON] {dialog.reason}")
            
            # Undo restrictions before exiting
            self.key_grabber.stop()
            self.set_gnome_lockdown(False)
            
            self._allow_close = True
            self.close()

    def handle_violation(self, combo: str):
        self.violation_count += 1
        print(f"[VIOLATION #{self.violation_count}] Blocked combo attempted: {combo}")
        QMessageBox.warning(
            self,
            "Exam Violation Detected",
            f"Attempted restricted action: {combo}\n\n"
            f"This has been logged as violation #{self.violation_count}.\n"
            f"Repeated violations may end your exam session."
        )

    def closeEvent(self, event):
        if self._allow_close:
            event.accept()
        else:
            event.ignore()
