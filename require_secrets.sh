#!/usr/bin/env bash
# Stop before any work if a secret the job needs is empty, and name every one.
# A missing secret otherwise surfaces later as a confusing failure, or not at all.
# Usage: require_secrets.sh NAME...   (the values come from the job's env)
missing=()
for name in "$@"; do
  [ -n "${!name:-}" ] || missing+=("$name")
done
if [ "${#missing[@]}" -gt 0 ]; then
  echo "::error::missing secrets: ${missing[*]}"
  # Also into the private log, so the failure mail can name them and give the fix.
  echo "missing secrets: ${missing[*]}" >> "${RUNNER_TEMP:-/tmp}/out.log"
  [ -n "${GITHUB_OUTPUT:-}" ] && echo "missing=${missing[*]}" >> "$GITHUB_OUTPUT"
  exit 1
fi
echo "all $# required secrets present"
