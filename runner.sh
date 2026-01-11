#!/usr/bin/env bash
set -u -o pipefail

echo "🟢  $(date '+%F %T') – script started"

# optional: coin extracted from args (best effort) for log file naming
coin="unknown"
for ((i=1; i<=$#; i++)); do
  if [[ "${!i}" == "--symbol" ]] && (( i+1 <= $# )); then
    j=$((i+1))
    coin="${!j}"
    break
  fi
done

ts="$(date '+%Y%m%d_%H%M%S')"
logfile="/app/script_${coin}_${ts}.log"
echo "📄 logfile=$logfile"

# Do NOT let `set -e` kill us before we can record PIPESTATUS
set +e
stdbuf -oL -eL python3 /app/app/main.py "$@" 2>&1 | tee -a "$logfile"
status=${PIPESTATUS[0]}
set -e

echo "✅  $(date '+%F %T') – script finished (exit=$status)"
exit "$status"
