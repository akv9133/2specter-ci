#!/usr/bin/env python3
"""Mail the failing job's step outcomes and its private log to the alert inbox.

Runs as the last step with `if: failure()`. The public log only ever shows exit
codes; the detail lives in $RUNNER_TEMP/out.log (written by quiet.sh) and goes
out here by mail. Exits 1 when the mail cannot be sent, so the job stays red
and a lost alert is at least visible in the run list.

Env: RESEND_API_KEY, ALERT_EMAIL, EMAIL_FROM, STEPS_JSON (toJSON(steps)), and
the GITHUB_* values every runner sets.
"""
from __future__ import annotations

import html
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

TAIL = 120


def body() -> tuple[str, str]:
    esc = html.escape
    repo = os.environ.get("GITHUB_REPOSITORY", "?")
    wf = os.environ.get("GITHUB_WORKFLOW", "?")
    run = os.environ.get("GITHUB_RUN_ID", "")
    url = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/actions/runs/{run}"
    wf_file = os.environ.get("GITHUB_WORKFLOW_REF", "").split("@", 1)[0].rsplit("/", 1)[-1]
    try:
        steps = json.loads(os.environ.get("STEPS_JSON") or "{}")
    except json.JSONDecodeError:
        steps = {}
    failed = next((k for k, v in steps.items() if v.get("outcome") == "failure"), None)
    rows = "".join(f"<tr><td>{esc(k)}</td><td>{esc(str(v.get('outcome')))}</td></tr>"
                   for k, v in steps.items())
    if not rows:
        rows = "<tr><td colspan=2>no step with an id reported an outcome</td></tr>"
    log = pathlib.Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "out.log"
    lines = (log.read_text(errors="replace").splitlines()[-TAIL:] if log.exists()
             else ["(no log: the job failed before any check ran)"])
    missing = next((l.split("missing secrets:", 1)[1].split() for l in reversed(lines)
                    if "missing secrets:" in l), [])
    fix = ""
    if missing:
        fix = ("<h3>Missing secrets</h3><p>The job stopped before doing any work. Set these, "
               "then rerun:</p><pre>" + esc("\n".join(f"gh secret set {m} --repo {repo}" for m in missing))
               + "</pre>")
    cmds = [f"gh run rerun {run} --repo {repo} --failed"]
    if wf_file:
        cmds.append(f"gh workflow run {wf_file} --repo {repo}")
    at = f" at {failed}" if failed else ""
    subject = f"[2specter-ci] {wf} failed{at}"
    page = (f"<p><b>{esc(wf)}</b> failed{esc(at)}. <a href=\"{esc(url)}\">Open the run</a></p>"
            f"{fix}"
            f"<h3>Rerun</h3><pre>{esc(chr(10).join(cmds))}</pre>"
            f"<h3>Steps</h3><table cellpadding=4 border=1 style=\"border-collapse:collapse\">"
            f"<tr><th>step</th><th>outcome</th></tr>{rows}</table>"
            f"<h3>Last {len(lines)} log lines</h3><pre>{esc(chr(10).join(lines))}</pre>")
    return subject, page


def main() -> int:
    missing = [k for k in ("RESEND_API_KEY", "ALERT_EMAIL", "EMAIL_FROM") if not os.environ.get(k)]
    if missing:
        print(f"::error::cannot mail the failure: secret(s) {' '.join(missing)} empty; "
              f"set with gh secret set NAME --repo {os.environ.get('GITHUB_REPOSITORY', '<repo>')}")
        return 1
    key, to, sender = (os.environ[k] for k in ("RESEND_API_KEY", "ALERT_EMAIL", "EMAIL_FROM"))
    subject, page = body()
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps({"from": sender, "to": [to], "subject": subject, "html": page}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 # Resend's edge rejects urllib's default User-Agent with a 403.
                 "User-Agent": "2specter-ci-mail/1.0"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"failure mailed (HTTP {r.status})")
            return 0
    except urllib.error.HTTPError as e:
        print(f"::error::Resend refused the failure mail: HTTP {e.code}")
    except OSError as e:
        print(f"::error::could not reach Resend: {type(e).__name__}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
