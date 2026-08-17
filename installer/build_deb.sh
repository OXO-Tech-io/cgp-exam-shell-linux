#!/bin/bash
# Builds a fully self-contained .deb: PyInstaller freezes main.py + PySide6 + every
# dependency into a onedir bundle at BUILD time, and that's what gets shipped. The
# candidate's machine never runs uv, pip, or any Python packaging step -- `apt
# install`/`dpkg -i` is the only action required, matching how the Windows/macOS
# CGPExamShell already ships as a pre-built binary.
#
# Also registers the cgpshell:// URI scheme (via cgp-exam-shell.desktop's MimeType),
# the Linux equivalent of the Windows installer's protocol registration, so the
# cgpshell://start?access_token=...&id_token=...&refresh_token=... link
# ExamEntryPage.js's handleBeginAssessment() opens is handed to this shell.
#
# Run this on a dev/build machine with `uv` installed -- it installs PyInstaller into
# the project's own dev venv (see [dependency-groups] in pyproject.toml) and uses it
# to freeze the app. None of that build tooling ends up in the .deb.
set -euo pipefail

PKG_NAME="cgp-exam-shell"
ARCH="amd64"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -m1 '^version' "$ROOT/pyproject.toml" | sed -E 's/.*"(.*)".*/\1/')"
BUILD_DIR="$ROOT/installer/.build/${PKG_NAME}_${VERSION}_${ARCH}"
PYI_DIST="$ROOT/installer/.build/dist"
PYI_WORK="$ROOT/installer/.build/pyi-work"

rm -rf "$BUILD_DIR" "$PYI_DIST" "$PYI_WORK"

# 1. Freeze the app. --onedir (not --onefile) so QtWebEngine's helper process and
#    resources sit on disk as real files instead of being re-extracted to /tmp on
#    every launch.
(cd "$ROOT" && uv run pyinstaller \
    --name "$PKG_NAME" \
    --onedir \
    --noconfirm \
    --distpath "$PYI_DIST" \
    --workpath "$PYI_WORK" \
    --add-data "config/exam_config.json:config" \
    main.py)

# 2. Stage the .deb payload
mkdir -p "$BUILD_DIR/DEBIAN" \
         "$BUILD_DIR/opt/$PKG_NAME" \
         "$BUILD_DIR/usr/bin" \
         "$BUILD_DIR/usr/share/applications"

cp -r "$PYI_DIST/$PKG_NAME/." "$BUILD_DIR/opt/$PKG_NAME/"
ln -sf "/opt/$PKG_NAME/$PKG_NAME" "$BUILD_DIR/usr/bin/$PKG_NAME"

install -m 644 "$ROOT/installer/cgp-exam-shell.desktop" \
    "$BUILD_DIR/usr/share/applications/cgp-exam-shell.desktop"

cat > "$BUILD_DIR/DEBIAN/control" <<EOF
Package: $PKG_NAME
Version: $VERSION
Section: education
Priority: optional
Architecture: $ARCH
Maintainer: CGP <support@cgp-assessment.example>
Description: CGP exam lockdown shell (Linux)
 Fullscreen exam browser shell used to run CGP assessments under lockdown.
 Registers the cgpshell:// URI scheme so the assessment frontend can hand off an
 authenticated session into the shell without a second login.
 Self-contained -- no separate Python/uv install needed on the target machine.
EOF

# update-desktop-database / xdg-mime need a per-user context to fully take effect --
# running them here best-effort covers the common case, but on some desktops the
# candidate's first cgpshell:// click may still prompt to pick an app once.
cat > "$BUILD_DIR/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
xdg-mime default cgp-exam-shell.desktop x-scheme-handler/cgpshell >/dev/null 2>&1 || true
EOF
chmod 755 "$BUILD_DIR/DEBIAN/postinst"

DEB_PATH="$ROOT/installer/${PKG_NAME}_${VERSION}_${ARCH}.deb"
dpkg-deb --build --root-owner-group "$BUILD_DIR" "$DEB_PATH"
echo "Built $DEB_PATH"
