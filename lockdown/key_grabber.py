from Xlib import X, XK, display
from PySide6.QtCore import QObject, Signal
import threading

class KeyGrabber(QObject):
    violation = Signal(str)

    GRABBED_COMBOS = [
        (X.ControlMask | X.Mod1Mask, "t"),        # Ctrl+Alt+T (Terminal)
        (X.Mod1Mask, "Tab"),                        # Alt+Tab (App switching)
        (X.Mod1Mask | X.ShiftMask, "Tab"),          # Alt+Shift+Tab
        (X.Mod4Mask, "Super_L"),                    # Left Super key
        (X.Mod4Mask, "Super_R"),                    # Right Super key
        (X.Mod4Mask, "d"),                          # Super+D (Minimize)
        (X.Mod4Mask, "Home"),                       # Super+Home
        (X.Mod1Mask, "F4"),                         # Alt+F4 (Close)
        (X.ControlMask | X.Mod1Mask, "Delete"),     # Ctrl+Alt+Del
        (X.ControlMask | X.ShiftMask, "Escape"),    # Ctrl+Shift+Esc
    ]

    def __init__(self):
        super().__init__()
        self.display = display.Display()
        self.root = self.display.screen().root
        self._running = False
        self._thread = None

    def start(self):
        def error_handler(err, request):
            print(f"[XGrabKey ERROR] Failed to grab key: {err}")

        self.display.set_error_handler(error_handler)

        for mods, key_name in self.GRABBED_COMBOS:
            keysym = XK.string_to_keysym(key_name)
            keycode = self.display.keysym_to_keycode(keysym)
            self.root.grab_key(
                keycode, mods, True,
                X.GrabModeAsync, X.GrabModeAsync
            )
        self.display.sync()

        self._running = True
        self._thread = threading.Thread(target=self._event_loop, daemon=True)
        self._thread.start()

    def _event_loop(self):
        while self._running:
            event = self.display.next_event()
            if event.type == X.KeyPress:
                self.violation.emit(f"keycode={event.detail}")

    def stop(self):
        self._running = False
        self.root.ungrab_key(X.AnyKey, X.AnyModifier, self.root)
        self.display.sync()
