#!/bin/bash
set -e

echo "🟢  $(date '+%F %T') – script started"

logfile="/app/script.log"

# Run the Python script and capture logs
stdbuf -oL -eL python3 /app/app/main.py 2>&1 | tee "$logfile"

echo "✅  $(date '+%F %T') – script finished"