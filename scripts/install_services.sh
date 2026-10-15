#!/usr/bin/env bash
# Install + enable (and restart) the per-user systemd unit for the deck server:
# decks on :8093, comments/export API on :8094, one process. Also removes the
# former separate slides-export unit. scripts/start.sh then just restarts it.
#
#   scripts/install_services.sh            # install, enable, (re)start, health-check
#   SLIDES_HOST=0.0.0.0 scripts/install_services.sh   # reachable from other machines
#   scripts/install_services.sh --remove   # disable + remove the unit
set -euo pipefail
cd "$(dirname "$0")/.."
UNIT=slides-server.service
DEST="$HOME/.config/systemd/user"

# the export server used to be its own unit
if [ -f "$DEST/slides-export.service" ]; then
    systemctl --user disable --now slides-export.service 2>/dev/null || true
    rm -f "$DEST/slides-export.service"
    echo "removed the former slides-export.service (its API now runs inside $UNIT)"
fi

if [ "${1:-}" = "--remove" ]; then
    systemctl --user disable --now "$UNIT" 2>/dev/null || true
    rm -f "$DEST/$UNIT"; systemctl --user daemon-reload
    echo "removed $UNIT"; exit 0
fi

[ -x .venv/bin/python ] || { echo "ERROR: .venv missing (python3 -m venv .venv && .venv/bin/pip install --require-hashes -r scripts/pptx_export/requirements.lock)" >&2; exit 1; }
[ -x quarto/.dist/quarto/bin/quarto ] || { echo "ERROR: quarto missing (quarto/scripts/setup.sh)" >&2; exit 1; }

# nohup'd instances from start.sh would hold the ports and make the unit fail to bind.
for pidfile in "$PWD/.quarto/slides-server-8093.pid"; do
    if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
        echo "stopping nohup'd server pid $(cat "$pidfile")"
        kill "$(cat "$pidfile")" 2>/dev/null || true; sleep 1
    fi
    rm -f "$pidfile"
done

for v in "$(pwd)" "${SLIDES_HOST:-127.0.0.1}" "${SLIDES_AUTH:-on}"; do
    case "$v" in *[[:space:][:cntrl:]\#\&\\@%\$\"\'\;]*) echo "ERROR: unsupported character in '$v' (space, control chars, # & \\ @ % \$ ; quotes); the unit can't hold it" >&2; exit 1 ;; esac
done
mkdir -p "$DEST"
sed -e "s#@REPO@#$(pwd)#g" -e "s#@BIND@#${SLIDES_HOST:-127.0.0.1}#g" -e "s#@AUTH@#${SLIDES_AUTH:-on}#g" "scripts/systemd/$UNIT" > "$DEST/$UNIT"
systemctl --user daemon-reload
systemctl --user enable "$UNIT"
systemctl --user restart "$UNIT"   # `enable --now` would keep an already running old instance
# Keep the user manager (and this unit) alive when no session is logged in.
loginctl enable-linger "$USER" 2>/dev/null || echo "note: loginctl enable-linger failed — the unit stops at logout without it" >&2

for _ in $(seq 1 20); do
    if curl -fs -m 2 -o /dev/null http://127.0.0.1:8094/healthz && curl -fs -m 2 -o /dev/null http://127.0.0.1:8093/healthz; then
        echo "OK: $UNIT active, :8093 and :8094 healthy"
        auth="${SLIDES_AUTH:-on}"; [ "$(echo "${auth,,}" | xargs)" = off ] || echo "login:  http://localhost:8093/?token=$(cat .quarto/server-token)"
        echo "logs:   journalctl --user -u slides-server -f"
        exit 0
    fi
    sleep 0.4
done
echo "ERROR: not healthy after start; see: journalctl --user -u slides-server -n 30" >&2
exit 1
