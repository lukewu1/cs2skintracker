#!/bin/bash
# Wrapper launchd invokes on a schedule: makes sure the SSH tunnel to the
# EC2 Postgres is up, then runs scrape.py, skipping this trigger entirely
# if a previous run is still in progress.
set -uo pipefail

BACKEND_DIR="/Users/lukewu/CU_Classes/CS2SkinTracker/CS2SkinTrackerApp/backend"
VENV_PYTHON="/Users/lukewu/CU_Classes/CS2SkinTracker/venv/bin/python3"
LOCKFILE="/tmp/cs2skintracker-scrape.lock"
# Hardcoded, not $HOME/... : launchd agents don't get HOME set in their
# environment, so a $HOME-relative path silently resolved to nothing and
# every scheduled reconnect failed with "Permission denied (publickey)".
# Kept in ~/.ssh, not ~/Downloads: macOS privacy protection blocks launchd
# jobs from reading Downloads ("Load key ...: Operation not permitted").
SSH_KEY="/Users/lukewu/.ssh/cs2-key.pem"
TUNNEL_HOST="ubuntu@54.225.36.231"
TUNNEL_LOCAL_PORT=5433
TUNNEL_REMOTE_PORT=5432

cd "$BACKEND_DIR" || exit 1

if [ -f "$LOCKFILE" ] && kill -0 "$(cat "$LOCKFILE" 2>/dev/null)" 2>/dev/null; then
    echo "$(date): previous run still active (pid $(cat "$LOCKFILE")), skipping"
    exit 0
fi
echo $$ > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

if ! lsof -nP -iTCP:"$TUNNEL_LOCAL_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "$(date): tunnel down, reconnecting"
    ssh -f -N -L "$TUNNEL_LOCAL_PORT:localhost:$TUNNEL_REMOTE_PORT" \
        -i "$SSH_KEY" -o IdentitiesOnly=yes \
        -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
        "$TUNNEL_HOST"

    if ! lsof -nP -iTCP:"$TUNNEL_LOCAL_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
        echo "$(date): tunnel reconnect failed, skipping this run"
        exit 1
    fi
fi

echo "$(date): starting scrape"
"$VENV_PYTHON" scrape.py skins.txt
echo "$(date): scrape finished"
