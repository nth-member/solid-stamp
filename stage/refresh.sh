#!/usr/bin/env bash
# SOLID STAMP's run; with --push, publish its record.
#
#   stage/refresh.sh [--push]
#
#   1  build/engine.py --if-changed   the engine's maps, read again only when an engine source changed
#   2  stage/run.py                   (rebuilding the table first if REVOTT's keys or the maps changed)
#                                     alerts scheduled, digests sent, finals kept, the record written
#   3  commit docs/log and docs/data only, as one rolling commit per Nsukka day
#   4  with --push and a remote, push (forced with lease when the day's commit was replaced)
set -u
cd "$(dirname "$0")/.." || exit 1
PUSH=0; [ "${1:-}" = "--push" ] && PUSH=1
exec 9>.git/solid-refresh.lock
flock -n 9 || { echo "solid: another run is going"; exit 0; }

python3 -B build/engine.py --if-changed || echo "FAIL engine"
python3 -B stage/run.py || { echo "FAIL run: nothing committed"; exit 1; }

PATHS=(docs/log docs/data)
git add -A -- "${PATHS[@]}"
if git diff --cached --quiet -- "${PATHS[@]}"; then echo "solid: unchanged"; exit 0; fi
SUBJECT="Digests through $(TZ=Africa/Lagos date +%F)"
rolling=0
if [ "$(git log -1 --format=%s 2>/dev/null)" = "$SUBJECT" ] && \
   [ -z "$(git diff-tree --no-commit-id --name-only -r HEAD | grep -v -E '^docs/(log|data)/')" ]; then
  rolling=1
fi
if [ $rolling = 1 ]; then
  git commit -q --amend --date=now -m "$SUBJECT" -- "${PATHS[@]}" && echo "solid: the day's commit replaced"
else
  git commit -q -m "$SUBJECT" -- "${PATHS[@]}" && echo "solid: committed"
fi
OTHER=$(git status --porcelain | grep -v -E ' docs/(log|data)/')
[ -n "$OTHER" ] && printf 'solid: other uncommitted changes, left alone:\n%s\n' "$OTHER"

if [ $PUSH = 1 ] && git remote get-url origin >/dev/null 2>&1; then
  if [ $rolling = 1 ]; then git push -q --force-with-lease origin HEAD:main; else git push -q origin HEAD:main; fi \
    && echo "solid: pushed" || { echo "FAIL solid: push"; exit 1; }
fi
