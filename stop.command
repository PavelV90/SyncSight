#!/bin/bash
# Double-click to stop SyncSight. Loaded data is kept for the next start.
cd "$(dirname "$0")" || exit 1
docker compose stop
echo "SyncSight stopped."
