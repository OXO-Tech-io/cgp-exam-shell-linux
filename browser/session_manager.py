import base64
import hashlib
import hmac
import json
import queue
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone

from browser import session_log
from config.settings import BASE_URL

# Confirmed against a real backend exchange (sessionLog.txt reference run):
# hotkey combo -> eventType string the backend already accepts.
HOTKEY_EVENT_TYPES = {
    "<alt>+<tab>": "ALT_TAB_ATTEMPT",
    "<cmd>": "WINDOWS_KEY_BLOCKED",
}
# Not confirmed against the reference log -- same naming convention, verify with backend team.
_UNCONFIRMED_HOTKEY_EVENT_TYPES = {
    "<ctrl>+<alt>+t": "TERMINAL_SHORTCUT_BLOCKED",
    "<ctrl>+<alt>+<f2>": "VT_SWITCH_BLOCKED",
    "<ctrl>+<alt>+<delete>": "CTRL_ALT_DEL_BLOCKED",
    "<print_screen>": "PRINT_SCREEN_BLOCKED",
}
HOTKEY_EVENT_TYPES.update(_UNCONFIRMED_HOTKEY_EVENT_TYPES)

_SHUTDOWN_SENTINEL = object()


class SessionError(Exception):
    """Raised when the backend rejects session creation or a network error occurs."""


class SessionManager:
    """Owns the exam session lifecycle: session establishment, HMAC signing,
    and strictly-ordered delivery of audit-log / security-event calls.

    security-events are handed to a single background worker thread via a queue,
    so seq_no assignment stays monotonic even though violations can be detected
    from multiple threads (pynput's hotkey listener thread, the Qt focus-poll timer).
    """

    def __init__(self, base_url: str = BASE_URL) -> None:
        self._base_url = base_url.rstrip("/")
        self._student_id = None
        self._session_token = None
        self._session_secret = None  # in-memory only -- never persisted, never logged

        self._session_ready = threading.Event()
        self._next_seq_no = 0
        self._queue = queue.Queue()
        self._worker = threading.Thread(target=self._process_queue, daemon=True)
        self._worker.start()

    @property
    def session_token(self) -> str | None:
        return self._session_token

    @property
    def is_active(self) -> bool:
        return self._session_ready.is_set()

    # ---- session lifecycle -------------------------------------------------

    def start_session(self, exam_id, student_id, session_token: str) -> dict:
        self._student_id = student_id
        self._session_token = session_token

        body = {
            "examId": exam_id,
            "studentId": student_id,
            "sessionToken": session_token,
        }
        status, response = self._post_json("/api/v1/shell/sessions", body)

        if status == 404:
            raise SessionError(f"session_not_found: {response}")
        if status == 401:
            raise SessionError(f"session_expired_or_already_active: {response}")
        if status != 200:
            raise SessionError(f"unexpected status {status} from /sessions: {response}")

        self._session_secret = response.get("session_secret")
        self._session_ready.set()
        return response

    # ---- audit logs (no seq_no; signature is over sessionToken alone) -------

    def send_audit_log(self, action: str, description: str) -> dict:
        signature = self._sign(self._session_token)
        body = {
            "sessionToken": self._session_token,
            "action": action,
            "description": description,
            "signature": signature,
        }
        status, response = self._post_json("/api/v1/shell/audit-logs", body)
        return {"status": status, **response}

    # ---- security events (queued, seq_no assigned in strict send order) ----

    def queue_security_event(self, event_type: str, description: str) -> None:
        occurred_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        self._queue.put({
            "eventType": event_type,
            "description": description,
            "occurred_at": occurred_at,
        })

    def shutdown(self) -> None:
        """Signal the worker thread to finish its current item,
        drop out of the lopp, and stop -- call this before the app closes so queued
        security events aren't silently dropped by an abrupt process exit."""
        self._queue.put(_SHUTDOWN_SENTINEL)
        self._worker.join(timeout=5.0)

    def _process_queue(self) -> None:
        while True:
            item = self._queue.get()

            if item is _SHUTDOWN_SENTINEL:
                break
            
            self._session_ready.wait()

            seq_no = self._next_seq_no
            self._next_seq_no += 1
            signature = self._sign(f"{self._session_token}|{seq_no}")
            body = {
                "sessionToken": self._session_token,
                "eventType": item["eventType"],
                "description": item["description"],
                "seq_no": seq_no,
                "occurred_at": item["occurred_at"],
                "signature": signature,
            }
            try:
                status, response = self._post_json("/api/v1/shell/security-events", body)
                if status != 202 or not response.get("accepted"):
                    print(f"[SECURITY-EVENT REJECTED] seq_no={seq_no} status={status} response={response}")
            except Exception as exc:
                print(f"[SECURITY-EVENT SEND FAILED] seq_no={seq_no}: {exc}")

    # ---- signing -------------------------------------------------------------

    def _sign(self, canonical: str) -> str:
        key = self._session_secret.encode("utf-8")
        digest = hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode("ascii")
        session_log.log_event(f'SIGN canonical="{canonical}" signature={signature}')
        return signature

    # ---- transport -------------------------------------------------------------

    def _post_json(self, path: str, body: dict, timeout: float = 10.0) -> tuple[int, dict]:
        url = f"{self._base_url}{path}"
        endpoint = path.lstrip("/")
        session_log.log_event(f"POST {endpoint} request={json.dumps(body)}")

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                status, response = resp.status, (json.loads(raw) if raw else {})
                session_log.log_event(
                    f"POST {endpoint} status={status} response={json.dumps(_redact(response))}"
                )
                return status, response
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8")
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {"raw": raw}
            session_log.log_event(
                f"POST {endpoint} status={e.code} response={json.dumps(_redact(parsed))}"
            )
            return e.code, parsed
        except urllib.error.URLError as e:
            session_log.log_event(f"POST {endpoint} ERROR {e}")
            raise SessionError(f"network error calling {path}: {e}") from e


def _redact(response: dict) -> dict:
    if "session_secret" in response:
        redacted = dict(response)
        redacted["session_secret"] = "***REDACTED***"
        return redacted
    return response
