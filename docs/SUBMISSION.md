# Submission and GitHub handoff

Project folder: `HandoverAI-Proactive-5G`.
Portable archive: `HandoverAI-Proactive-5G-Submission.zip`.
Owner/maintainer: Shriram Masalekar. Assistance and licenses: `THIRD_PARTY_NOTICES.md`.

## Included

* Original implementation, typed YAML scenarios and 100 automated tests.
* Detailed README with Mac Terminal, VS Code, algorithm and GitHub instructions.
* Architecture, metric definitions, requirements matrix, assumptions and limitations.
* Actual three-scenario offline dashboard with raw run downloads and PNG figures.
* Actual 30-seed E1-E6/F5 study, per-seed outcomes, inputs and paired bootstrap intervals.
* Generated mobility CSV/dataset card and an integrity-checked SQLite example with 12 runs.
* Pinned direct/transitive dependencies, bootstrap/demo scripts, CI and VS Code settings.
* Exactly 30 real incremental Git commits under the configured owner identity, with original
  build timestamps and the complete `.git` history. No empty or backdated commits.

Excluded: virtual environments, local caches, scratch runs, credentials, external proprietary
data, simulator builds and unimplemented integration stubs. The Desktop working folder has
an installed local environment; the portable archive rebuilds it with `scripts/bootstrap.sh`.

## Verify and run after extraction

Extract the ZIP once to a new location. Keep the hidden `.git` directory so the history survives.
The sibling `HandoverAI-Submission-Manifest.json` records the HEAD, commit count and SHA256 for
every submitted tracked file. The external `.zip.sha256` file verifies the entire archive.

```sh
# Run beside the downloaded ZIP and checksum file
shasum -a 256 -c HandoverAI-Proactive-5G-Submission.zip.sha256

cd HandoverAI-Proactive-5G
git rev-list --count HEAD       # 30
git log --oneline               # actual incremental changes
git status --short             # empty
git fsck --full
sh scripts/bootstrap.sh
source .venv/bin/activate
python -m pytest -q             # 100 tests
sh scripts/demo.sh
```

Open the included `reports/demo/index.html` immediately to inspect evidence without installing
Python dependencies. Opening HTML from a ZIP preview can break relative downloads; extract the
entire archive before opening it. Report figures and inline JSON work without a web server.

## Rebuild the submission archive

Run from a clean committed repository. This script uses only the Python standard library and
Git, creates a temporary clean clone, removes the local origin and hooks/logs, validates Git
objects, preserves history and ZIP file modes, and emits a SHA256 sidecar. It never overwrites
an existing archive. The source working directory is not modified.

```sh
python3 scripts/package_submission.py \
  --expected-commits 30 --output ../HandoverAI-Proactive-5G-Submission.zip
```

For later releases with additional commits, omit `--expected-commits 30` or set the new expected
count, and choose a new archive name. Copying files through GitHub's browser does not retain
Git history; use the README's `git remote add` and `git push` commands with your own repository.

## Scope of the submission

Mandatory Tier A is complete. SQLite, CSV replay, multiple vehicles, temporary rectangles and
prediction-error experiments are additional implemented features. Native SUMO/TraCI generation,
ns-3/5G-LENA, packet metrics and real-network control are not implemented or claimed. This is
a reproducible software/research submission under a synthetic model. It is not a field-tested
telecommunications product. The documentation includes favorable, negative and null findings.
