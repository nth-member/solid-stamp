#!/usr/bin/env bash
# SOLID STAMP's run on GitHub (.github/workflows/solid.yml), every 15 minutes, whether or not the author's
# computer is on:
#
#   1  the last days of REVOTT STAMPS' published archive and of JOMO SFO-WAM's GitHub readings
#      (sparse checkouts under .work/, filled in here)
#   2  stage/recent.py   the archive brought up to the latest reading
#   3  stage/run.py      the table (built here), alerts scheduled, digests sent, finals kept, the record
#   4  commit docs/log, the run's files in docs/data, and state/ -- one rolling commit per Nsukka day -- and
#      push. If a push from elsewhere landed first, this run's files are laid onto it and pushed again: only
#      this run writes them, and a lost state would send a digest twice.
#
# The topic comes from the repository secret NTFY_TOPIC; without it nothing is sent.
set -u
cd "$(dirname "$0")/.." || exit 1
W=.work
python3 - > "$W/want" <<'EOF'
import datetime as dt
now = dt.datetime.now(dt.timezone.utc)
print(" ".join("/docs/data/days/%s.json" % (now + dt.timedelta(hours=1) - dt.timedelta(days=k)).date() for k in range(8)))
print(" ".join("/feeds/history/%s.jsonl.gz" % (now - dt.timedelta(days=k)).date() for k in range(5)))
EOF
git -C "$W/revott-stamps" sparse-checkout add $(sed -n 1p "$W/want") || { echo "FAIL the archive's days"; exit 1; }
git -C "$W/jomo-sfo-wam" sparse-checkout add $(sed -n 2p "$W/want") || { echo "FAIL the feed readings"; exit 1; }
printf '{"revott_stamps": "%s", "jomo": "%s", "engine": ""}\n' "$PWD/$W/revott-stamps" "$PWD/$W/jomo-sfo-wam" > .paths.json
if [ -n "${NTFY_TOPIC:-}" ]; then
  printf '{"server": "%s", "topic": "%s"}\n' "${NTFY_SERVER:-https://ntfy.sh}" "$NTFY_TOPIC" > .ntfy.json
  chmod 600 .ntfy.json
fi

python3 -B stage/recent.py "$W/stamps-data" || { echo "FAIL recent: nothing sent"; exit 1; }
export SOLID_STAMPS_DATA="$PWD/$W/stamps-data"
python3 -B stage/run.py || { echo "FAIL run"; exit 1; }

OURS=(docs/log docs/data/upcoming.json docs/data/status.json docs/data/settings.json docs/data/feeds.json state)
SAVE="$W/save"; rm -rf "$SAVE"; mkdir -p "$SAVE"
for p in "${OURS[@]}"; do [ -e "$p" ] && mkdir -p "$SAVE/$(dirname "$p")" && cp -r "$p" "$SAVE/$p"; done
SUBJECT="Digests through $(TZ=Africa/Lagos date +%F)"
for try in 1 2 3 4; do
  git fetch -q origin main || { sleep 5; continue; }
  git reset -q --hard origin/main
  for p in "${OURS[@]}"; do [ -e "$SAVE/$p" ] && rm -rf "$p" && cp -r "$SAVE/$p" "$p"; done
  git add -A -- "${OURS[@]}"
  if git diff --cached --quiet; then echo "solid: unchanged"; exit 0; fi
  if [ "$(git log -1 --format=%s)" = "$SUBJECT" ] && \
     [ -z "$(git diff-tree --no-commit-id --name-only -r HEAD | grep -v -E '^(docs/(log|data)|state)/')" ]; then
    git commit -q --amend --date=now -m "$SUBJECT" && \
      git push -q --force-with-lease=main:"$(git rev-parse origin/main)" origin HEAD:main && { echo "solid: the day's commit replaced, pushed"; exit 0; }
  else
    git commit -q -m "$SUBJECT" && git push -q origin HEAD:main && { echo "solid: committed, pushed"; exit 0; }
  fi
  echo "solid: a push landed first; laying this run's files onto it (try $try)"
  sleep $((try * 5))
done
echo "FAIL solid: push"
exit 1
