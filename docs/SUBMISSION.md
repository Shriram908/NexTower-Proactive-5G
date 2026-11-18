# NexTower submission and GitHub handoff

Project folder: `NexTower-Proactive-5G`.
Fresh archive: `NexTower-Proactive-5G-Submission.zip`.
Owner/maintainer: Shriram Masalekar. Assistance/licenses: `THIRD_PARTY_NOTICES.md`.

## Current snapshot and Git status

The existing **30 commits are preserved**. At the owner's request, the NexTower rename,
Python-package rename, expanded README and refreshed artifacts are **uncommitted**. The
ZIP includes these current working files together with the original `.git` history.
`git status` is therefore expected to show modified/deleted/new files after extraction.
Git HEAD remains the original 30th commit; no rebrand commit is created by packaging.

The Python module and console command are now `nextower`. Activate the rebuilt environment
and use the commands in README. The original owner-supplied blueprint retains its original
HandoverAI title when cited as a source; it is not redistributed in the archive.

## Included

* Current NexTower implementation, YAML scenarios and automated tests.
* Expanded README with project description, algorithms, file-by-file code walkthrough,
  task-by-task implementation guide, Mac Terminal, VS Code and GitHub instructions.
* Actual three-scenario offline dashboard, raw downloads and scientific figures.
* Full 30-seed E1-E6/F5 study with configs, individual outcomes and paired intervals.
* Synthetic mobility CSV/dataset card and integrity-checked example SQLite database.
* Exact dependency pins, installation/demo/package scripts, CI and editor settings.
* Existing Git history plus a manifest that explicitly identifies this as an uncommitted snapshot.

Virtual environments, caches, scratch runs and credentials are excluded. The working Desktop
folder has its own installed environment. Install a new environment after extracting elsewhere.

## Verify and run

```sh
# Beside the fresh ZIP and its checksum
shasum -a 256 -c NexTower-Proactive-5G-Submission.zip.sha256

cd NexTower-Proactive-5G
git rev-list --count HEAD       # still 30
git status --short              # uncommitted rename/update is expected
git fsck --full
sh scripts/bootstrap.sh
source .venv/bin/activate
python -m pytest -q
sh scripts/demo.sh
```

The sibling `NexTower-Submission-Manifest.json` records the committed base, current source
hash, every submitted file digest and `uncommitted_changes_included: true`. It is deliberately
outside the project folder so it does not add another untracked project file. Extract the
entire archive before opening `reports/demo/index.html`; relative downloads need its data files.

## Rebuild without creating a commit

Choose an output filename that does not already exist:

```sh
python3 scripts/package_submission.py --working-tree --expected-commits 30 \
  --output ../NexTower-Proactive-5G-Submission.zip
```

The script creates a temporary clone for history, overlays current tracked/nonignored working
files, removes locally deleted tracked files, strips remote/hooks/logs, validates Git objects,
then writes a checked ZIP and SHA256 sidecar. It does not stage, commit, push or rewrite history.
Existing archives are preserved. Omit `--working-tree` only when packaging a clean committed tree.

GitHub push transfers committed snapshots. The uncommitted NexTower updates will need a future
reviewed commit if you later want them in a GitHub repository; no such commit is made now.
Uploading the ZIP as an artifact or extracting it locally includes the updated working files.

## Scope

Mandatory standalone Python Tier A is implemented. SQLite, CSV replay, multiple vehicles,
temporary blockers and prediction-error experiments are also implemented. SUMO/TraCI export,
ns-3/5G-LENA, genuine packet metrics and live-network control remain unimplemented optional tiers.
All radio outcomes are conditional synthetic-model results, with negative/null cases included.
