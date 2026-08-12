import os
import sys

# Force X11 compatibility over Wayland before initializing Qt
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["GDK_BACKEND"] = "x11"

from PySide6.QtWidgets import QApplication
from browser.browser_window import ExamShellWindow

EXAM_URL = "https://cgp-assessment-frontend-app-297614602590.us-central1.run.app/"

def main():
    app = QApplication(sys.argv)
    window = ExamShellWindow(EXAM_URL)
    window.showFullScreen()
    window.focus_monitor.start()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()