"""
Centralized QSS theme for CGPExamShell dialogs and controls.
Keeping this in one place means every dialog/button shares a consistent
look instead of each widget hand-rolling its own inline stylesheet.
"""

DIALOG_STYLE = """
QDialog {
    background-color: #1e2a2b;
    border-radius: 10px;
}

QLabel#dialogTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: 700;
}

QLabel#dialogSubtitle {
    color: #9fb3b4;
    font-size: 13px;
}

QTextEdit {
    background-color: #0f1717;
    color: #ffffff;
    border: 1px solid #2f4344;
    border-radius: 8px;
    padding: 10px;
    font-size: 14px;
}

QTextEdit:focus {
    border: 1px solid #2a9d8f;
}

QPushButton#primaryBtn {
    background-color: #2a9d8f;
    color: white;
    font-weight: 600;
    font-size: 14px;
    padding: 10px 20px;
    border-radius: 8px;
    border: none;
}
QPushButton#primaryBtn:hover { background-color: #238b7e; }
QPushButton#primaryBtn:pressed { background-color: #1c6f64; }

QPushButton#secondaryBtn {
    background-color: transparent;
    color: #9fb3b4;
    font-size: 13px;
    padding: 10px 16px;
    border-radius: 8px;
    border: 1px solid #2f4344;
}
QPushButton#secondaryBtn:hover {
    background-color: #24393a;
    color: #ffffff;
}
"""

EXIT_BUTTON_STYLE = """
QPushButton {
    background-color: #d32f2f;
    color: white;
    font-weight: 600;
    font-size: 13px;
    padding: 9px 18px;
    border-radius: 8px;
    border: none;
    outline: none;
}
QPushButton:hover { background-color: #b71c1c; }
QPushButton:focus { border: none; outline: none; }
QPushButton:pressed { background-color: #a31515; }
"""

CRITICAL_DIALOG_STYLE = """
QDialog {
    background-color: #2a1414;
    border-radius: 10px;
}
QLabel#criticalTitle {
    color: #ff6b6b;
    font-size: 18px;
    font-weight: 700;
}
QLabel#criticalBody {
    color: #f0d9d9;
    font-size: 14px;
}
QPushButton#ackBtn {
    background-color: #d32f2f;
    color: white;
    font-weight: 600;
    font-size: 14px;
    padding: 10px 24px;
    border-radius: 8px;
    border: none;
}
QPushButton#ackBtn:hover { background-color: #b71c1c; }
"""
VIOLATION_OVERLAY_STYLE = """
QWidget#violationBackdrop {
    background-color: rgba(0, 0, 0, 160);
}

QWidget#violationCard {
    background-color: #2a1414;
    border: 1px solid #d32f2f;
    border-radius: 14px;
}

QLabel#violationIcon {
    font-size: 36px;
}

QLabel#violationTitle {
    color: #ff6b6b;
    font-size: 20px;
    font-weight: 700;
}

QLabel#violationCount {
    color: #ffffff;
    background-color: #d32f2f;
    font-size: 12px;
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 10px;
}

QLabel#violationMessage {
    color: #f0d9d9;
    font-size: 14px;
}

QLabel#violationCountdownLabel {
    color: #9fb3b4;
    font-size: 12px;
}

QProgressBar#violationProgress {
    background-color: #1a0e0e;
    border: none;
    border-radius: 4px;
    height: 8px;
}
QProgressBar#violationProgress::chunk {
    background-color: #d32f2f;
    border-radius: 4px;
}
"""