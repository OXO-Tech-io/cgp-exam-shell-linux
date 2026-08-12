import subprocess

class WorkspaceLock:
    """Disables multi-workspace switching for the duration of the exam."""

    def __init__(self):
        self._original_dynamic = None
        self._original_num = None

    def _gsettings_get(self, schema: str, key: str) -> str:
        result = subprocess.run(
            ["gsettings", "get", schema, key],
            capture_output=True, text=True
        )
        return result.stdout.strip()

    def _gsettings_set(self, schema: str, key: str, value: str):
        subprocess.run(["gsettings", "set", schema, key, value])

    def lock(self):
        self._original_dynamic = self._gsettings_get(
            "org.gnome.mutter" , "dynamic-workspaces"
        )
        self._original_num = self._gsettings_get(
            "org.gnome.desktop.wm.preferences", "num-workspaces"
        )

        self._gsettings_set("org.gnome.mutter", "dynamic-workspaces", "false")
        self._gsettings_set("org.gnome.desktop.wm.preferences", "num-workspaces", "1")

    def unlock(self):
        if self._original_dynamic is not None:
            self._gsettings_set("org.gnome.mutter", "dynamic-workspaces", self._original_dynamic)
        if self._original_num is not None:
            self._gsettings_set("org.gnome.desktop.wm.preferences", "num-workspaces", self._original_num)