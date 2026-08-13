"""Seeds Keycloak SSO tokens into the WebView before the assessment frontend loads --
the Linux/QtWebEngine equivalent of the script FullScreenExamForm.cs injects into
WebView2 via AddScriptToExecuteOnDocumentCreatedAsync on the Windows shell.

access_token/id_token/refresh_token arrive as query params (forwarded from the
cgpshell:// launch URI by browser.launch_uri.build_exam_url). This script moves them
into sessionStorage under the cgp_bootstrap_* keys AuthContext.js already checks on
mount, then scrubs them from the URL so they don't linger in WebView navigation
history or leak via a Referer header. It also sets window.__CGP_SHELL__ = true, which
cgpShell.js's isInsideShell() expects.
"""

from PySide6.QtWebEngineCore import QWebEngineScript

_BOOTSTRAP_KEYS_JS = """{
    "access_token": "cgp_bootstrap_token",
    "id_token": "cgp_bootstrap_id_token",
    "refresh_token": "cgp_bootstrap_refresh_token"
}"""

_SETUP_JS = f"""
(function() {{
    window.__CGP_SHELL__ = true;

    var params = new URLSearchParams(window.location.search);
    var keys = {_BOOTSTRAP_KEYS_JS};
    var moved = false;

    for (var param in keys) {{
        var value = params.get(param);
        if (value) {{
            sessionStorage.setItem(keys[param], value);
            params.delete(param);
            moved = true;
        }}
    }}

    if (moved) {{
        var query = params.toString();
        var newUrl = window.location.pathname + (query ? "?" + query : "") + window.location.hash;
        window.history.replaceState({{}}, document.title, newUrl);
    }}
}})();
"""


def make_token_bootstrap_script() -> QWebEngineScript:
    script = QWebEngineScript()
    script.setName("cgp_token_bootstrap")
    script.setSourceCode(_SETUP_JS)
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    script.setRunsOnSubFrames(False)
    return script
