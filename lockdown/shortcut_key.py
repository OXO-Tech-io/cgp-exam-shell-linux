import logging
import os
import threading

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("cgpexamshell.x11_shortcut_blocker")


class X11ShortcutBlocker(QObject):
    violation = Signal(str)

    # extra modifier bits for every NumLock/CapsLock/ScrollLock combination,
    # so a grab fires regardless of lock-key state
    _LOCK_EXTRAS = (0, 2, 16, 18, 32, 34, 48, 50)

    def __init__(self, regrab_interval_sec: float = 2.0) -> None:
        super().__init__()
        self.regrab_interval_sec = regrab_interval_sec
        self.display = None
        self.root = None
        self._running = False
        self._event_thread = None
        self._regrab_thread = None
        self._blocked_codes = set()  # (keycode, full_modifier_value) pairs actually grabbed

    def is_x11_available(self) -> bool:
        if os.environ.get("WAYLAND_DISPLAY"):
            logger.warning(
                "Wayland session detected -- passive XGrabKey cannot intercept "
                "compositor-level shortcuts (Alt+Tab, Super, workspace switch). "
                "Relying on HotkeyBlocker + FocusMonitor for those instead."
            )
            return False
        return True

    def start(self):
        if not self.is_x11_available():
            return  # graceful no-op, not a crash

        from Xlib import X, XK, display

        self._X = X
        self._XK = XK
        self.display = display.Display()
        self.root = self.display.screen().root

        def error_handler(err, request) -> None:
            logger.debug("XGrabKey non-fatal error: %s", err)

        self.display.set_error_handler(error_handler)

        self._grab_all()
        self._running = True

        self._event_thread = threading.Thread(target=self._event_loop, daemon=True)
        self._event_thread.start()

        self._regrab_thread = threading.Thread(target=self._regrab_loop, daemon=True)
        self._regrab_thread.start()

        logger.info("X11 passive shortcut grabs active (%d combos)", len(self._blocked_codes))

    def _blocked_combos(self) -> list[tuple[str, int]]:
        """(keysym name, modifier mask) pairs -- extend this list as new
        bypass vectors are identified. Modifier masks use Xlib's X module
        constants directly rather than hand-rolled ints, so this reads
        clearly against the X11 spec."""
        X = self._X
        return [
            # window / focus switching
            ("Tab", X.Mod1Mask),
            ("Tab", X.Mod1Mask | X.ShiftMask),
            ("Escape", X.Mod1Mask),
            ("F4", X.Mod1Mask),               # Alt+F4 close window
            ("F1", X.Mod1Mask),                # panel menu
            ("F2", X.Mod1Mask),                # run dialog
            ("Escape", X.ControlMask),

            # Super key + common GNOME bindings
            ("Super_L", 0),
            ("Super_R", 0),
            ("a", X.Mod4Mask),
            ("d", X.Mod4Mask),
            ("e", X.Mod4Mask),
            ("l", X.Mod4Mask),
            ("r", X.Mod4Mask),
            ("s", X.Mod4Mask),
            ("Left", X.Mod4Mask),
            ("Right", X.Mod4Mask),
            ("Up", X.Mod4Mask),
            ("Down", X.Mod4Mask),
            ("Page_Up", X.Mod4Mask),
            ("Page_Down", X.Mod4Mask),

            # terminal / TTY / system
            ("t", X.ControlMask | X.Mod1Mask),
            ("Delete", X.ControlMask | X.Mod1Mask),
            ("F1", X.ControlMask | X.Mod1Mask),
            ("F2", X.ControlMask | X.Mod1Mask),
            ("F3", X.ControlMask | X.Mod1Mask),
            ("F4", X.ControlMask | X.Mod1Mask),
            ("F5", X.ControlMask | X.Mod1Mask),
            ("F6", X.ControlMask | X.Mod1Mask),
            ("F7", X.ControlMask | X.Mod1Mask),

            # screenshot
            ("Print", 0),
            ("Print", X.Mod1Mask),
            ("Print", X.ControlMask),
            ("Print", X.ShiftMask),

            # browser / dev-tools bypass attempts inside the webview
            ("t", X.ControlMask | X.ShiftMask),
            ("w", X.ControlMask),
            ("n", X.ControlMask),
            ("l", X.ControlMask),
            ("j", X.ControlMask | X.ShiftMask),
            ("i", X.ControlMask | X.ShiftMask),
            ("F11", 0),
        ]

    def _grab_all(self) -> None:
        self._blocked_codes.clear()
        for key_name, mod in self._blocked_combos():
            keysym = self._XK.string_to_keysym(key_name)
            keycode = self.display.keysym_to_keycode(keysym)
            if keycode == 0:
                logger.debug("No keycode for '%s', skipping", key_name)
                continue
            for extra in self._LOCK_EXTRAS:
                full_mod = mod | extra
                self.root.grab_key(
                    keycode, full_mod, True,
                    self._X.GrabModeAsync, self._X.GrabModeAsync
                )
                self._blocked_codes.add((keycode, full_mod))
        self.display.sync()

    def _release_all(self) -> None:
        for keycode, full_mod in self._blocked_codes:
            try:
                self.root.ungrab_key(keycode, full_mod, self.root)
            except Exception:
                pass
        self.display.sync()

    def _event_loop(self) -> None:
        while self._running:
            try:
                event = self.display.next_event()
            except Exception:
                break
            if event.type == self._X.KeyPress:
                self.violation.emit(f"x11-grabbed-shortcut keycode={event.detail}")

    def _regrab_loop(self) -> None:
        """Grabs can be silently dropped by a WM restart or certain focus
        transitions -- periodically re-asserting them is cheap insurance."""
        import time
        while self._running:
            time.sleep(self.regrab_interval_sec)
            if not self._running:
                break
            try:
                self._grab_all()
            except Exception as e:
                logger.debug("Re-grab pass failed: %s", e)

    def stop(self) -> None:
        self._running = False
        if self.display:
            self._release_all()
            try:
                self.display.sync()
            except Exception:
                pass