#!/usr/bin/env bash
#
# Stop the deck server (:8093 decks, :8094 comments/export API).
#   Usage: scripts/stop.sh [port]
# Use the same port / SLIDES_EXPORT_PORT as scripts/start.sh when stopping a
# side-by-side instance.
cd "$(dirname "$0")/.."
PORT="${1:-${SLIDES_PORT:-8093}}"

# Only stop the unit if it serves THIS checkout (another clone may own it).
if [ "$PORT" = 8093 ] && systemctl --user is-active slides-server.service >/dev/null 2>&1 \
   && [ "$(systemctl --user show -p WorkingDirectory --value slides-server.service 2>/dev/null)" = "$(pwd)" ]; then
    systemctl --user stop slides-server.service
    echo "slides-server.service stopped"
fi
pidfile="$PWD/.quarto/slides-server-${PORT}.pid"
if [ -f "$pidfile" ]; then
    kill "$(cat "$pidfile")" 2>/dev/null || true
    rm -f "$pidfile"
    echo "nohup'd server stopped"
fi
