#!/usr/bin/env bash
#
# Deck server: decks on :8093, comments/export API on :8094 (one process).
#   Usage: scripts/start.sh [port]      (default port: 8093)
#
# quarto/scripts/serve.py serves the rendered decks at /<category>/<deck>/slides.md,
# re-renders a deck when its source changes (edit-pane saves, agent edits, a Marp
# slides.md converted on the fly), live-updates open pages and answers the
# comments/export API. Preferred: the per-user systemd unit
# (scripts/install_services.sh), which this restarts; otherwise a setsid/nohup child.
#
# Run a second checkout side by side by giving it its own ports:
#   SLIDES_EXPORT_PORT=8194 scripts/start.sh 8193   (stop with the same variables + stop.sh)
#
# The server listens on 127.0.0.1 only. To open the decks from another machine
# (LAN/VPN), bind all interfaces:  SLIDES_HOST=0.0.0.0 scripts/start.sh
# Token login is on: open the printed URL once (it sets a cookie); agents send
# X-Deck-Token: $(cat .quarto/server-token). SLIDES_AUTH=off turns it off (see SECURITY.md).
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${1:-${SLIDES_PORT:-8093}}"
API_PORT="${SLIDES_EXPORT_PORT:-8094}"
# serve.py tells every page it serves (and every HTML export) to use API_PORT
export SLIDES_HOST="${SLIDES_HOST:-127.0.0.1}" SLIDES_EXPORT_PORT="$API_PORT"

[ -x quarto/.dist/quarto/bin/quarto ] || { echo "ERROR: quarto missing — run quarto/scripts/setup.sh" >&2; exit 1; }
[ -x .venv/bin/python ] || { echo "ERROR: .venv missing (python3 -m venv .venv && .venv/bin/pip install --require-hashes -r scripts/pptx_export/requirements.lock)" >&2; exit 1; }
python3 quarto/scripts/gen_client.py
# First start (or wiped renders): one full build instead of one render per deck.
[ -f decks/index.html ] || { echo "Rendering every deck (a few minutes) ..."; quarto/scripts/render_all.sh --quiet; }

RUN="$PWD/.quarto"   # pid + log: this checkout's, not a shared /tmp
mkdir -p "$RUN"; touch "$RUN/slides-server-${PORT}.log"; chmod 600 "$RUN/slides-server-${PORT}.log"
UNIT=slides-server.service PID="$RUN/slides-server-${PORT}.pid" LOG="$RUN/slides-server-${PORT}.log"
# Only use the unit if it serves THIS checkout on the default ports (another clone may own it).
if [ "$PORT" = 8093 ] && [ "$API_PORT" = 8094 ] && systemctl --user is-enabled "$UNIT" >/dev/null 2>&1 \
   && [ "$(systemctl --user show -p WorkingDirectory --value "$UNIT" 2>/dev/null)" = "$(pwd)" ]; then
    systemctl --user restart "$UNIT"
    MANAGED_BY_SYSTEMD=1
else
    [ ! -f "$PID" ] || kill "$(cat "$PID")" 2>/dev/null || true
    # setsid: own session + process group, so whatever reaps THIS shell's group
    # (an agent harness ending a tool call, a closing pane) cannot take the
    # server with it. Append, don't truncate: the previous instance's last words.
    setsid nohup .venv/bin/python -u quarto/scripts/serve.py --host "$SLIDES_HOST" --port "$PORT" --api-port "$API_PORT" \
        >> "$LOG" 2>&1 < /dev/null &
    echo $! > "$PID"
    echo "note: the deck server is a nohup child; make it permanent with scripts/install_services.sh"
fi

# Confirm it bound: a stale process on a port makes the server die instantly with
# EADDRINUSE, and deck comments then silently queue in the browser.
for _ in $(seq 1 20); do
    curl -fs -m 2 -o /dev/null "http://localhost:${API_PORT}/healthz" 2>/dev/null \
        && curl -fs -m 2 -o /dev/null "http://localhost:${PORT}/healthz" 2>/dev/null && {
        login="" auth="${SLIDES_AUTH:-on}"
        [ "$(echo "$auth" | tr '[:upper:]' '[:lower:]' | xargs)" = off ] || [ ! -f .quarto/server-token ] || login="?token=$(cat .quarto/server-token)"
        echo "Decks:  http://localhost:${PORT}/${login}   (each at /<category>/<deck>/slides.md)"
        stop="scripts/stop.sh"
        [ "$PORT" = 8093 ] && [ "$API_PORT" = 8094 ] || stop="SLIDES_EXPORT_PORT=$API_PORT scripts/stop.sh $PORT"
        echo "Stop:   $stop"; exit 0; }
    sleep 0.3
done
echo "ERROR: the deck server did NOT come up on :${PORT}/:${API_PORT}. Last log lines:" >&2
if [ -n "${MANAGED_BY_SYSTEMD:-}" ]; then
    journalctl --user -u "$UNIT" -n 5 --no-pager 2>/dev/null | sed 's/^/       | /' >&2
else
    tail -5 "$LOG" 2>/dev/null | sed 's/^/       | /' >&2
fi
exit 1
