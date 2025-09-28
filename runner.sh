#!/usr/bin/env bash
set -euo pipefail

echo "🟢  $(date '+%F %T') – script started"
logfile="/app/script.log"

# Forward all args to Python (very important: "$@")
stdbuf -oL -eL python3 /app/app/main.py "$@" 2>&1 | tee "$logfile"
status=${PIPESTATUS[0]}

echo "✅  $(date '+%F %T') – script finished"
exit $status
