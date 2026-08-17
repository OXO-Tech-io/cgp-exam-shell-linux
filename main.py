import os
import sys

# Force X11 compatibility over Wayland before initializing Qt
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["GDK_BACKEND"] = "x11"

# TEMPORARY DEBUG -- lets us inspect the live exam page (console/network/DOM) from a
# normal browser while it's loaded inside this shell. Remove once the assignment_id
# routing issue is diagnosed. Must be set before QtWebEngine initializes.
if os.environ.get("CGP_SHELL_DEBUG") == "1":
    os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9223"

from PySide6.QtWidgets import QApplication
from browser.browser_window import ExamShellWindow
from browser.launch_uri import find_launch_uri, build_exam_url
from browser import session_log
from config.settings import validate_exam_url
from browser.display_gate_dialog import DisplayGateDialog
from lockdown.display_monitor import connected_screen_count

EXAM_URL = "https://cgp-assessment-frontend-app-297614602590.us-central1.run.app/"

def main():
    app = QApplication(sys.argv)

    # Block launch entirely while multiple displays are connected.
    if connected_screen_count() > 1:
        gate = DisplayGateDialog()
        gate.exec()  # blocks here until only one screen remains

    launch_uri = find_launch_uri(sys.argv[1:])
    target_url = validate_exam_url(build_exam_url(EXAM_URL, launch_uri))
    session_log.log_event(f"argv={sys.argv[1:]!r} launch_uri={launch_uri!r} target_url={target_url!r}")

    window = ExamShellWindow(target_url)
    window.showFullScreen()
    window.focus_monitor.start()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()