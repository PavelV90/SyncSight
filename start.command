#!/bin/bash
# Double-click to start SyncSight (needs Docker Desktop), then open it in the browser.
cd "$(dirname "$0")" || exit 1

wait_for() {  # wait_for <description> <command…>: retry for up to 3 minutes
  local what=$1; shift
  for _ in $(seq 1 90); do "$@" >/dev/null 2>&1 && return 0; sleep 2; done
  echo "Timed out waiting for $what." && exit 1
}

if ! docker info >/dev/null 2>&1; then
  echo "Starting Docker Desktop…"
  open -a Docker
  wait_for "Docker" docker info
fi

docker compose up -d --build || exit 1
echo "Waiting for SyncSight…"
wait_for "the API" curl -sf http://localhost:8010/api/health
wait_for "the web app" curl -sf http://localhost:5173

[ -z "$NO_OPEN" ] && open http://localhost:5173
echo "SyncSight runs at http://localhost:5173 (API docs: http://localhost:8010/docs)."
echo "You can close this window. Double-click stop.command to stop it."
