#!/usr/bin/env bash
# Install a desktop-menu entry for the Graphify Workspace Cockpit (Linux).
#
# Creates a .desktop launcher in your application menu that points at
# launcher/launch-cockpit.sh, so you can start the cockpit with a click instead
# of from a terminal. Safe and reversible: it writes a single file under your
# per-user applications directory. Re-run it any time (for example after moving
# the repo to a new path).
#
# Remove it with:
#   rm "${XDG_DATA_HOME:-$HOME/.local/share}/applications/graphify-cockpit.desktop"
#
# PLANNED: a true double-click app with native installers (Tauri/Electron) is
# intended once real-world usability on another machine is confirmed. Until then
# this entry + launch-cockpit.sh are the supported Linux click-to-launch path.
set -euo pipefail

LAUNCHER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCH_SCRIPT="$LAUNCHER_DIR/launch-cockpit.sh"
ICON_PATH="$LAUNCHER_DIR/icon.png"

APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$APPS_DIR/graphify-cockpit.desktop"

if [ ! -f "$LAUNCH_SCRIPT" ]; then
  echo "error: launcher not found: $LAUNCH_SCRIPT" >&2
  exit 1
fi
# The .desktop Exec needs the launcher to be executable.
chmod +x "$LAUNCH_SCRIPT" 2>/dev/null || true

mkdir -p "$APPS_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Graphify Cockpit
Comment=Workspace decision surface — Ask, Map, Decisions, Recommendations, Work Queue, AI Assistant
Exec="$LAUNCH_SCRIPT"
Icon=$ICON_PATH
Terminal=false
Categories=Development;Utility;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE" 2>/dev/null || true

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPS_DIR" 2>/dev/null || true
fi

echo "Installed desktop entry:"
echo "  $DESKTOP_FILE"
echo
echo "Look for \"Graphify Workspace Cockpit\" in your application menu."
echo "First launch sets up dependencies, so it may take a minute before the browser opens."
echo
echo "To remove it:  rm \"$DESKTOP_FILE\""
