#!/usr/bin/env bash
set -euo pipefail

for attempt in 1 2 3; do
  if git push origin HEAD:main; then
    exit 0
  fi
  if [ "$attempt" -eq 3 ]; then
    echo 'Publication failed after three push attempts.' >&2
    exit 1
  fi
  git fetch origin main
  if ! git rebase origin/main; then
    git rebase --abort
    echo 'Publication stopped: refresh conflicts with changes on main.' >&2
    exit 1
  fi
done
