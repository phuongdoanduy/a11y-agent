#!/usr/bin/env bash
# Starts the a11y-agent sidecar validator (port 8001) and the ADK API server (port 8000).
# Ctrl-C terminates both processes cleanly.
set -e
cd "$(dirname "$0")"

if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "ERROR: port 8001 is already in use. Stop the existing process first."
  exit 1
fi

uvicorn app.path_validator:app --port 8001 &
VALIDATOR_PID=$!
echo "Validator started on :8001 (pid $VALIDATOR_PID)"

adk api_server app --port 8000 &
ADK_PID=$!
echo "ADK API server started on :8000 (pid $ADK_PID)"

trap 'echo "Stopping..."; kill "$VALIDATOR_PID" "$ADK_PID" 2>/dev/null; wait' INT TERM

wait "$ADK_PID"
kill "$VALIDATOR_PID" 2>/dev/null
