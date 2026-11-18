# Execution evidence

Verification date: **18 November 2026, Asia/Kolkata**. No remote CI execution is claimed.
All results below were obtained by executing the project locally.

## Tested environments

| Component | Actual environment/version |
|---|---|
| OS | macOS 15.7.2, ARM64 |
| Primary Python | 3.14.7, isolated project `.venv` |
| Independent Python | 3.12.14, separate venv and clean Git checkout |
| PyYAML / Matplotlib | 6.0.3 / 3.10.8 |
| NumPy / contourpy | 2.3.5 / 1.3.3 |
| pytest / Ruff | 9.0.2 / 0.15.1 |
| Primary SQLite | 3.54.1 via Python stdlib |
| Build / setuptools | 1.4.0 / 82.0.0 |

The complete dependency set is in `requirements.lock`. Python 3.11 is a declared supported
version and configured CI target; it was not installed locally and is not claimed locally
tested. The lock's distributions declare Python 3.11 compatibility.

## Actual checks

| Check | Observed result |
|---|---|
| Primary `python -m pytest -q` | **100 passed**, about 3 seconds |
| Clean-checkout Python 3.12 pytest | **100 passed**, about 6 seconds |
| `python -m ruff check .` | all checks passed |
| `python -m ruff format --check src tests scripts` | all checked files formatted |
| `python -m pip check` | no broken requirements, in both environments |
| Blueprint YAML validation | valid; 180 ticks, one active car, three towers |
| Four-policy smoke simulation | actual trace/event/manifest/metric outputs for every policy |
| Three-scenario release run | 12 policy runs persisted and reported |
| Independent clean checkout | installed from project metadata; validate/simulate/report succeeded |
| `python -m build --no-isolation` | wheel and source distribution built successfully |
| Source distribution contents | scenario YAMLs and `tests/conftest.py` included |
| Wheel contents | `nextower/dashboard.html` included |
| Wheel installation | installed into independent environment; four-policy simulate/report succeeded outside project cwd |
| Full paired research suite | 30 seeds × 33 variants × 4 policies = 3,960 output rows |
| Benchmark caching | 3,000 unique simulations; duplicate input/policy cases reused |
| Audit regression | all 3,960 numerical outcome rows unchanged after validation/provenance hardening |
| SQLite example | 12 runs, 2,160 observations, 6,480 links, 96 event records |
| SQLite integrity / foreign keys | `ok` / zero violations |
| Browser console | 12 run options exercised; zero JavaScript errors |
| Desktop/mobile layout | 1440 px / 390 px; no mobile document overflow after correction |
| Secret-pattern audit | no credential/private-key pattern findings in submitted source/config/docs |

The wheel smoke test matters because it exercises packaged assets rather than relying on an
editable source tree. Clean-checkout testing uses its own interpreter and installation, so an
accidental dependency on the original working directory would be exposed.

## Timing and scientific correctness

Tests cover the blueprint T01-T23 edge cases and a golden default-corridor regression. The
strongest policy records exactly 180 observations, three completed handovers and three outage
seconds in that fixture. Geometry tests include tangencies, endpoints and zero-length segments.
Candidate timers use elapsed seconds at dt 0.25, 0.5 and 1.0; a target cannot succeed before
switch delay. Failed/deactivated candidates, reattachment, no towers and terminal requests are
tested separately. Identical-world replay and reversed policy order preserve channel samples.

The report test rereads CSV and rejects mismatched stored metrics; the release report was
generated through that same verified path. The paired study includes unfavorable outcomes,
and no zero ping-pong ablation is presented as proof of a reduction. Optional T24, real packet
metrics and native network/synchronized simulator integration are explicitly unimplemented.

## Provenance and artifacts

The final simulator source is recorded by SHA256:

```text
72c106b8ead6b3883f0d966194a1586279d540054ea1c1702773e841ce058aaa
```

Release traces/study were regenerated from source revision
`554d6f64c91489e02af83d73b7386f32b63903bb` (the 29th commit). The 30th commit adds final packaging,
documentation and refreshed artifacts without changing simulator source. Manifests record both
the source digest and `source_tree_dirty: false`. `working_tree_dirty` may be true because
regenerated tracked reports were being refreshed; it does not imply unrecorded source changes.

Screenshots: [desktop console](../reports/screenshots/desktop.png) and
[mobile console](../reports/screenshots/mobile.png). The renderer was checked in local headless
Chrome using Playwright available in the build environment; these are QA tools, not runtime
dependencies. Every shown metric comes from the embedded saved report data.

Final archive creation verifies a clean committed tree, the requested 30-commit count, Git
object integrity, ZIP CRC and an external SHA256 checksum. Its sibling submission manifest
records every tracked file digest. After extraction, the README's bootstrap, test and smoke
commands provide the reproducibility check for the recipient. No credentials or environment
binaries are needed in the portable source package.
