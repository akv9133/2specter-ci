# ci: the public CI repo's tree

Staged here, inert: GitHub only runs workflows from the repository root's
`.github/workflows`, so nothing under `ci/` runs in the private code repo. The
public CI repo gets this tree only through `ci/sync_ci_repo.py`, which refuses
to publish any source name or host, credential, address or token shape.

- Every workflow starts with `.github/actions/prep`: it stops and names every
  missing secret (`require_secrets.sh`), then checks the private code out into
  `code/` with a read-only deploy key.
- Commands run through `quiet.sh`: the public log shows exit codes only, and the
  detail goes by mail on failure (`mail_failure.py`).
- `pending/` holds inherited workflows not yet converted. It is never published.

Repo settings the workflows need: secret `CODE_DEPLOY_KEY`, variable `CODE_REPO`,
and the secrets each workflow's first step names.
