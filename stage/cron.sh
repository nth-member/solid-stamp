#!/usr/bin/env bash
# The cron entry, every 15 minutes, four minutes after REVOTT STAMPS' own (5-59/15):
#   9-59/15 * * * * $HOME/solid-stamp/stage/cron.sh
# It waits for REVOTT STAMPS' refresh to finish (its lock), so the digests read a whole archive.
# Logs to ~/.cache/solid-stamp/run.log, kept to its last 2000 lines.
LOG="$HOME/.cache/solid-stamp/run.log"
mkdir -p "$(dirname "$LOG")"
{
  echo "== $(TZ=Africa/Lagos date '+%Y-%m-%d %H:%M') Nsukka"
  flock -w 900 "$HOME/revott-stamps/.git/stamps-refresh.lock" "$(dirname "$0")/refresh.sh" --push
} >> "$LOG" 2>&1
tail -n 2000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
