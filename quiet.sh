#!/usr/bin/env bash
# Run a command without putting its output in the log: this repo's logs are
# public. Output goes to $RUNNER_TEMP/out.log, which mail_failure.py mails
# privately when the job fails. Only the exit code and a line count print here.
log="${RUNNER_TEMP:-/tmp}/out.log"
echo "== $*" >> "$log"
"$@" >> "$log" 2>&1
rc=$?
echo "exit=$rc ($(wc -l < "$log" | tr -d ' ') log lines so far, detail goes by mail on failure)"
exit "$rc"
