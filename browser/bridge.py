import json

from PySide6.QtCore import QFile, QIODevice, QObject, Signal, Slot
from PySide6.QtWebEngineCore import QWebEngineScript

from browser import session_log

BRIDGE_JS_OBJECT_NAME = "cgpShellBridge"


class WebBridge(QObject):
    """Receives messages the assessment page sends via window.chrome.webview.postMessage,
    the same WebView2-style API the frontend already uses on the Windows shell."""

    assessment_started = Signal(dict)
    message_received = Signal(dict)

    @Slot(str)
    def postMessage(self, raw: str):
        session_log.log(f"RAW: {raw}")

        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            print(f"[BRIDGE] dropped malformed message: {raw!r}")
            return

        event = payload.get("event")
        session_log.log(f"PARSED: {event}")

        self.message_received.emit(payload)
        if event == "assessment_started":
            session_log.log("CALLING API...")
            self.assessment_started.emit(payload)


def _load_qwebchannel_js() -> str:
    f = QFile(":/qtwebchannel/qwebchannel.js")
    if not f.open(QIODevice.OpenModeFlag.ReadOnly):
        raise RuntimeError("qwebchannel.js resource not found -- is QtWebChannel imported?")
    try:
        return bytes(f.readAll()).decode("utf-8")
    finally:
        f.close()


def make_bridge_script(channel_object_name: str = BRIDGE_JS_OBJECT_NAME) -> QWebEngineScript:
    """Builds the QWebEngineScript that shims window.chrome.webview.postMessage on top of
    QWebChannel, so the unmodified assessment frontend can talk to this shell as if it
    were running under WebView2."""

    setup_js = f"""
    (function() {{
        document.addEventListener('DOMContentLoaded', function() {{
            new QWebChannel(qt.webChannelTransport, function(channel) {{
                var bridge = channel.objects.{channel_object_name};
                window.chrome = window.chrome || {{}};
                window.chrome.webview = window.chrome.webview || {{}};
                window.chrome.webview.postMessage = function(msg) {{
                    bridge.postMessage(typeof msg === 'string' ? msg : JSON.stringify(msg));
                }};
            }});
        }});
    }})();
    """

    script = QWebEngineScript()
    script.setName("cgp_webchannel_bridge")
    script.setSourceCode(_load_qwebchannel_js() + setup_js)
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    script.setRunsOnSubFrames(False)
    return script
