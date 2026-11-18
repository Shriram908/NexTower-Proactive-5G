# NexTower · Proactive 5G Tower Selection

**A reproducible simulator for studying when a moving connected vehicle should change its serving tower.**

**Current update:** The project is now named **NexTower**. The folder, Python package, CLI and documentation have been renamed together. These updates are intentionally uncommitted; the existing 30-commit Git history is preserved. The fresh ZIP includes the current working files and that history.

Owner and maintainer: **Shriram Masalekar** · Python 3.11+ · MIT license · Version 1.0.0

NexTower compares four tower-selection policies in the **same recorded world**. It predicts
short-term route geometry, estimates upcoming link obstruction, and trades connectivity against
handover cost. This repository completes the **self-contained Python Tier A** in the supplied
project blueprint, with additional CSV mobility replay, SQLite storage, sensitivity experiments,
and an offline interactive research console.

> All radio values are **synthetic power proxies**. This is a research/portfolio simulator, not
> an operational 5G modem, a standards-compliant NR implementation, or real vehicle control.
> SUMO/TraCI and ns-3/5G-LENA execution are optional extensions and are **not implemented** here.

![Recorded policy comparison](reports/demo/figures/comparison.png)

## 1. What this project does

A car can have a strong current connection just before a building blocks its line to a tower.
Selecting only the strongest signal reacts after that change. Switching too often also causes
interruptions and unstable A → B → A behavior. NexTower makes these competing effects visible.

1. Load a versioned YAML road, route, towers, blockers and model settings.
2. Generate vehicle positions, or replay canonical CSV positions.
3. Compute distance, geometric line of sight and a seeded received-power proxy for every link.
4. Replay exactly these observations through nearest, strongest-current, A3-style and predictive policies.
5. Execute each policy's decisions through independent dwell/delay/failure state machines.
6. Save traces, handover events, metrics, configuration hashes and runtime metadata.
7. Store the run in SQLite and create scientific PNG figures plus an offline HTML dashboard.
8. Run matched-seed studies and ablations to see where proactive selection helps or hurts.

The research question is whether causal geometry-aware prediction reduces outage without
excessive switching. Results can support or refute the hypotheses; they are never hard-coded.

## 2. Run on a Mac — exact commands

Python 3.11 or newer is required. The release was tested with Python 3.14.7 and 3.12.14 on macOS ARM64.
The initial dependency installation needs internet access; subsequent simulations work offline.
If Python is missing, install a current Python from [python.org](https://www.python.org/downloads/macos/).
No paid API, API key, database server, Node.js or external dataset is required.

### Option A: prepared Desktop folder

Open **Terminal** and run:

```sh
cd ~/Desktop/NexTower-Proactive-5G
sh scripts/bootstrap.sh
source .venv/bin/activate
python -m nextower --version
python -m pytest -q
sh scripts/demo.sh
```

The demo writes a unique run/report directory and opens the dashboard automatically on macOS.
To inspect the included report immediately, no installation is needed:

```sh
cd ~/Desktop/NexTower-Proactive-5G
open reports/demo/index.html
```

If the Desktop environment is already installed, just activate it and run the demo. Virtual
environments cannot safely be moved between folders or machines; rerun bootstrap after moving.

### Option B: fresh clone or extracted submission

```sh
cd /path/to/NexTower-Proactive-5G
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
python -m nextower validate --config configs/blocked_corridor.yaml
python -m nextower simulate --config configs/blocked_corridor.yaml --policy all
python -m nextower report --runs runs/blocked_corridor_v1 --output reports/my-first-report
open reports/my-first-report/index.html
```

`nextower ...` is also installed as a console command. Use `python -m nextower ...` to make
interpreter selection explicit. Every simulation batch gets a unique directory; report and
benchmark outputs intentionally require a **new** destination to avoid silent overwrites.

To select a specific Python installed on your Mac:

```sh
PYTHON_BIN=python3.13 sh scripts/bootstrap.sh
```

### Run and debug in VS Code

1. Open **VS Code → File → Open Folder** and select `NexTower-Proactive-5G`.
2. Install the recommended Python and Python Debugger extensions if prompted.
3. Open **Terminal → New Terminal**, then run the bootstrap/activation commands above.
4. Use **Python: Select Interpreter** from the Command Palette and choose `.venv/bin/python`.
5. Open **Run and Debug**, select **NexTower: simulate all policies**, and press F5.
6. Place breakpoints in `src/nextower/engine.py`, `policies.py` or `proactive.py` to inspect decisions.
7. Use the Testing panel for pytest, or **Terminal → Run Task** for tests, lint or the demo.

If the `code` command is installed, `code .` opens the current folder. The included `.vscode`
files configure the interpreter, test discovery, debug arguments and tasks. Run commands from
this project root so relative scenario/data paths resolve correctly.

## 3. Commands and scenarios

```sh
# Validate without running
python -m nextower validate --config configs/blocked_corridor.yaml

# Compare all policies; SQLite is created automatically
python -m nextower simulate --config configs/blocked_corridor.yaml --output runs/my-demo

# One policy with explicit overrides; no source edits
python -m nextower simulate --config configs/dynamic_blocker.yaml --policy predictive \
  --set seed=7 --set predictive.horizon_s=3.0 --set channel.shadowing_std_db=2.0

# A portable report from persisted traces
python -m nextower report --runs runs/my-demo --output reports/my-demo
open reports/my-demo/index.html

# List database runs (read-only)
python -m nextower db --database runs/my-demo/results.sqlite3

# Export synthetic mobility; output must not already exist
python -m nextower export-trace --config configs/blocked_corridor.yaml \
  --output /tmp/nextower-mobility.csv

# Full research matrix, 30 matched seeds
python -m nextower benchmark --config configs/blocked_corridor.yaml \
  --set channel.shadowing_std_db=2.0 --seeds 30 --suite full \
  --output reports/my-research

# Fast exploratory benchmark
python -m nextower benchmark --seeds 3 --suite quick --output reports/my-quick-study

# All available flags
python -m nextower --help
python -m nextower simulate --help
```

| Scenario | Purpose | Seed/noise defaults |
|---|---|---|
| `blocked_corridor.yaml` | Blueprint's 850 m route, three towers and two rectangles | 42 / no shadow noise |
| `no_blockage.yaml` | Same route/towers without rectangles | 42 / no shadow noise |
| `dynamic_blocker.yaml` | A temporary parked bus appears at 35 s and leaves at 55 s | 42 / 2 dB noise |

All distances are meters, speed is m/s, time seconds and heading radians. There are 180
observations for a 90-second run at dt=0.5: times are `[0, 90)`, without an extra endpoint.
Unknown settings, invalid shapes, duplicate IDs, nonfinite values and incompatible tick grids
fail with actionable errors. Fewer or zero towers are allowed for edge-case studies; the supplied
scenarios each have three. See [configuration validation](src/nextower/config.py).

## 4. How it is built

```mermaid
flowchart LR
  C[YAML configuration] --> M[Synthetic or CSV mobility]
  M --> W[Immutable geometry and channel observations]
  W --> B[Nearest / strongest / A3]
  W --> P[Causal route-aware forecast]
  P --> Q[Predictive scoring]
  B --> E[Independent delayed handover controllers]
  Q --> E
  E --> S[CSV + JSON + SQLite]
  S --> R[Verified metrics / PNG / offline HTML]
```

The core uses small Python modules and frozen data classes. All policies receive identical
position and link observations. Keyed random draws are independent of policy execution order.
A controller, rather than the policy, enforces switching delay and dwell constraints.

| Policy | Decision rule | Stability behavior |
|---|---|---|
| nearest | Choose shortest geometric distance | Common dwell/delay; unusable candidates rejected |
| strongest | Choose maximum current power proxy | Common dwell/delay |
| a3 | Neighbor exceeds serving proxy by a configured margin | Consecutive elapsed TTT, reset on lost advantage |
| predictive | Maximize mean forecast quality minus outage and switching penalties | Current feasibility, score margin, TTT and dwell |

The predictive algorithm projects the **current observed position** onto the planned route,
advances with **current measured speed**, and evaluates future geometry for a configurable
horizon. It receives currently visible rectangles with their future schedules removed. They
persist in the forecast. It never receives actual future noise or mobility observations.

```text
synthetic_rx_dbm = tx_power + gains - pl0 - 10*n*log10(max(distance,d0)/d0)
                   - blockage_penalty + seeded_shadowing

score[j] = weight_quality * normalized(mean(clamped_forecast_quality[j]))
           - weight_outage * forecast_outage_fraction[j]
           - weight_switch * (j != serving)
```

Rectangle edges/corners count as blocked; multiple blockers apply one fixed penalty. Future
shadowing is predicted as zero. No trained neural network is hidden behind the project name:
this is analytical, geometry-aware look-ahead. Read the [full architecture](docs/ARCHITECTURE.md)
for timer boundaries, route projection, recovery and failure semantics.

Initial/recovery attachment uses the same strongest-usable rule for every policy and is counted
separately. A switch can succeed only after its delay and if the target remains usable. During
switching the vehicle is in outage. A failed target keeps the old usable association or becomes
disconnected. Unfinished requests do not become imaginary successful handovers.

## 5. Real results included in this release

These numbers were generated by the actual runner. They describe this **synthetic corridor**,
not field-measured 5G performance. The packaged reports include raw downloadable traces.

| Policy | Default seed 42 outage | Completed handovers | 30-seed mean outage, 2 dB shadowing |
|---|---:|---:|---:|
| nearest | 3.89% | 2 | 3.33% |
| strongest | 3.33% | 3 | 4.70% |
| a3 | 4.44% | 3 | 3.52% |
| predictive | 1.11% | 1 | 3.26% |

For the noisy E1 study, predictive minus strongest mean outage is **−1.44 percentage points**;
its paired bootstrap 95% interval is **[−2.39, −0.48] percentage points**, using 30 paired seeds
42–71. Relative to strongest's mean outage, that is a **30.71% reduction in this experiment**.
There are 33 variants, 3,960 policy/variant/seed rows and 3,000 unique simulated inputs/policies.

Prediction is not universally better. At a 10 dB blockage penalty its mean outage is **0.37
percentage points higher** than strongest, with an interval spanning zero. Removing dwell
alone had no observable effect in this corridor. All tested predictive E6 ablations had zero
ping-pong returns, so they do **not** establish a ping-pong reduction; removing switching cost
increased mean handovers from 0.63 to 2.30. These negative/null outcomes are included.

![Horizon and TTT sensitivity](reports/research/figures/horizon_ttt_heatmap.png)

See [measured findings](docs/RESULTS.md), [research protocol](docs/EXPERIMENTS.md), and the actual
[per-seed results](reports/research/results.csv), [paired intervals](reports/research/paired.csv)
and [configuration snapshots](reports/research/configs.json). The interactive report at
`reports/demo/index.html` opens directly from disk; no web server is needed. On GitHub, download
or clone before opening the HTML report locally.

## 6. Outputs and database

```text
runs/<scenario>/<unique-batch>/<policy>/
  config.yaml          # exact validated input
  manifest.json        # UUID, seed, config SHA256, code revision, runtime versions
  timeseries.csv       # position, serving/pending cell, power proxy, outage, state
  links.csv            # every current tower observation
  handovers.csv        # attachments, losses, attempts, success/fail/reject/incomplete
  metrics.json         # exact denominators and event counts
runs/results.sqlite3   # default normalized local database
reports/<report>/
  index.html           # offline interactive console; select a scenario/policy/seed
  summary.csv          # long-form metrics with units, backend and run IDs
  data.json            # report input data
  data/<run-id>/       # downloadable original run files
  figures/             # map, timeline, proxy quality, comparison
```

Outage fraction counts unusable or interrupted observations divided by observed vehicle-ticks.
Outage seconds are steps × dt. Quality means include only usable attached samples and record
the sample count. Ping-pong is a consecutive completed A → B → A inside the configured window.
For multiple vehicles, outage seconds are vehicle-seconds; episodes are kept separate per car.
All definitions are in [ASSUMPTIONS.md](docs/ASSUMPTIONS.md).

SQLite tables are `runs`, `observations`, `links`, and `events`, linked by UUID with foreign keys.
Writes are transactional; duplicate run IDs fail. The archive includes a generated example at
`data/demo.sqlite3`; large databases and arbitrary runs are ignored by Git. See
[DATABASE.md](docs/DATABASE.md) for schema details and inspection commands.

## 7. Dataset and CSV replay

The included [synthetic mobility dataset](data/corridor_mobility.csv) has 180 canonical
observations. Its [dataset card](data/DATASET_CARD.md) explains origin, license, units,
generation and limitations. No external/private dataset, personal telemetry or model download
is required. It is an evaluation fixture, not training data.

```sh
python -m nextower simulate --config configs/blocked_corridor.yaml \
  --set simulation.mobility_backend=trace \
  --set simulation.trace_file=data/corridor_mobility.csv --output runs/replay
```

External mobility must use exactly
`time_s,vehicle_id,x_m,y_m,speed_mps,heading_rad`, sorted by time then ID, on the configured tick
grid. Each vehicle begins at zero and has a contiguous prefix; permanent departure is allowed.
This interchange can receive independently exported simulator positions, but is not a verified
SUMO/TraCI or online ns-3 co-simulation integration.

## 8. Tests, reproducibility and project layout

```sh
python -m pytest -q
python -m ruff check .
python -m ruff format --check src tests scripts
python -m pip check
python -m build --no-isolation
```

The 100 tests cover T01–T23, including malformed scenarios, geometry tangencies, zero distance, TTT
across tick sizes, delayed/failing switches, causal forecasts, exact replay, reversed policy
order, metrics denominators, trace gaps, database integrity, report tampering and CLI errors.
See [TESTING_REPORT.md](docs/TESTING_REPORT.md) for actual execution evidence, not a remote CI claim.
GitHub Actions is configured for Python 3.11 and 3.14 on Linux.

```text
configs/               three complete scenario YAMLs
src/nextower/         typed config, geometry, mobility, channel, policies, engine,
                       metrics, SQLite/CSV storage, experiments and reporting
src/nextower/dashboard.html   standalone offline report template
tests/                 unit, scenario, regression and end-to-end tests
data/                  synthetic mobility and its dataset card
reports/demo/          actual three-scenario report and raw run evidence
reports/research/      full 30-seed sensitivity/ablation study
scripts/               bootstrap, demo, benchmark and submission packaging
.vscode/               interpreter, tasks and launch configurations
.github/workflows/     automated lint/tests/smoke report
requirements.lock      exact direct/transitive tested dependency pins
docs/                  architecture, assumptions, requirements, experiments,
                       results, database, testing and limitations
```

The [requirements matrix](docs/REQUIREMENTS.md) maps every mandatory blueprint item to code and
verification. Manifests record source revision/config hash; timestamps and run UUIDs change on
repetition, while output traces/metrics remain deterministic on the tested runtime.

## 9. Submission and uploading to your GitHub

The repository retains **30 meaningful commits** under the configured owner identity. The NexTower rename and expanded documentation are uncommitted working-tree changes.
The portable ZIP includes source, documentation, reports, dataset, example database and Git
history. It excludes virtual environments, caches, credentials and large scratch runs. Bootstrap
installs the same pinned dependencies on a new machine. See [SUBMISSION.md](docs/SUBMISSION.md).

Create a new **empty** GitHub repository named `NexTower-Proactive-5G` in your own account.
Then replace `YOUR_GITHUB_USERNAME` below and run from this project folder:

```sh
# Inspect the committed history and the intentionally uncommitted updates

git status  # modified/deleted/new files are expected for this update
git log --oneline
git rev-list --count HEAD

# Add your empty repository; do this only once

git remote add origin https://github.com/YOUR_GITHUB_USERNAME/NexTower-Proactive-5G.git
# A later commit is needed before Git push can include the current rename.
# This update deliberately does not create that commit.
# Once you choose to commit your reviewed changes, publish with:
# git push -u origin main
```

Authenticate using your own GitHub credential manager or SSH configuration. No credentials
belong in the project. If `origin` already exists, inspect it with `git remote -v` and use
`git remote set-url origin ...` if necessary. Uploading through GitHub's browser file picker
uploads files but does not preserve the local 30-commit history; use Git push for that.
Git push publishes committed snapshots only; the current rename stays local until you choose to commit it. Nothing has been published to your account automatically.

Suggested About text: “Reproducible blockage-aware handover simulator for connected vehicles,
with reactive and predictive policies, paired experiments, SQLite and an offline research console.”

## 10. Ownership, limitations and references

This project was implemented for **Shriram Masalekar** with **OpenAI Codex assistance** from the
owner-provided blueprint. Commit dates are actual build dates. No third-party repository or
unseen professor codebase was copied. The project's original implementation is MIT licensed;
dependencies retain their own licenses. See [ownership/third-party notices](THIRD_PARTY_NOTICES.md).

The current model omits real PHY/MAC/RRC, packets, scheduler, interference, beam management,
correlated fading, sensor stacks and live vehicle control. Predictive decisions assume a known
route and a simplified persistence forecast. Results are conditional on these assumptions.
Read [KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) before describing this as network research.

Reference starting points from the supplied blueprint (not claims of implemented integrations):

* [Official SUMO TraCI interface](https://sumo.dlr.de/docs/TraCI/Interfacing_TraCI_from_Python.html)
* [Official SUMO installation guide](https://eclipse.dev/sumo/docs/Installing/index.html)
* [CTTC 5G-LENA documentation](https://cttc-lena.gitlab.io/nr/html/)
* [ETSI TR 138 901 v18.0.0](https://www.etsi.org/deliver/etsi_tr/138900_138999/138901/18.00.00_60/tr_138901v180000p.pdf)
* [ETSI TS 138 331 v15.26.0](https://www.etsi.org/deliver/etsi_ts/138300_138399/138331/15.26.00_60/ts_138331v152600p.pdf)

## Troubleshooting

| Symptom | Fix |
|---|---|
| `python: command not found` | Use `python3` before activating the venv; install Python 3.11+ if needed. |
| `No module named nextower` | Activate `.venv`, run editable installation above, and work from the project root. |
| Wrong VS Code interpreter | Select `.venv/bin/python` and reopen the integrated terminal. |
| Permission/package-manager error | Install inside `.venv`; do not use `sudo pip` or the system Python environment. |
| Report output already exists | Choose a new `--output` directory; existing reports are preserved. |
| Invalid horizon/duration | Use a positive integer multiple of `simulation.dt_s`. |
| Dataset trace rejected | Check exact headers, configured vehicle IDs, finite SI values and sorted contiguous ticks. |
| Missing database | Run `simulate` first or pass the actual path used with `--output`/`--database`. |
| ZIP contains no visible Git files in Finder | `.git` is hidden; `git log` in Terminal confirms the history. |
| Browser report on GitHub shows source | Clone/download the project and open the local HTML file. |

## Code walkthrough

### Start here: the path from a terminal command to a result

For `python -m nextower simulate --config configs/blocked_corridor.yaml --policy all`,
Python executes `src/nextower/__main__.py`. That module calls `cli.main()` and returns its
exit code. `cli.parser()` defines command arguments; `main()` selects the operation.

The simulation call chain is:

```text
__main__.py
  -> cli.main()
     -> config.load_config(path, overrides)
        -> from_dict() -> _validate() -> frozen Config
     -> engine.prepare_world(config)
        -> mobility.synthetic_trace() OR traces.load_trace()
        -> channel.observe() for every enabled tower and position
        -> immutable World(samples, links)
     -> storage.batch_directory() creates a unique batch path
     -> for each requested policy:
        -> engine.simulate(config, policy, SAME world)
           -> one Controller per vehicle
           -> settle pending changes at each observed timestamp
           -> create causal forecasts for the predictive policy
           -> policy.decide(context, state)
           -> Controller.request() validates and executes recommendations
           -> append observed state, outage flag and current links
        -> storage.write_run()
           -> save CSV -> re-read CSV -> metrics.calculate()
           -> write metrics/config/manifest JSON or YAML
           -> persist_database() commits normalized SQLite records
```

`report` is a separate operation. `reporting.collect()` loads the saved files, checks the
configuration hash and recalculates metrics. If stored metrics disagree with the traces, it
stops. `build_report()` copies the run evidence, draws PNGs and embeds the actual data into
`dashboard.html`. Opening the resulting `index.html` therefore needs no server or internet.

### File-by-file explanation

| File | Main entry points | What to understand |
|---|---|---|
| `src/nextower/__main__.py` | `main()` import | Makes `python -m nextower` executable. |
| `cli.py` | `parser`, `main` | Parses flags, applies overrides, coordinates commands and formats errors. |
| `models.py` | `Tower`, `Vehicle`, `Blocker`, `PositionSample`, `LinkSample`, `Decision`, `HandoverState` | Frozen observations are shared safely; controller state is mutable and private. |
| `config.py` | `load_config`, `from_dict`, `_validate`, `Config.digest` | Converts YAML to typed settings, checks SI units/invariants, hashes the exact normalized input. |
| `mobility.py` | `along_route`, `position_at`, `synthetic_trace` | Walks route segments by distance traveled and stops at the endpoint. |
| `traces.py` | `load_trace`, `export_trace` | Imports/exports the canonical CSV schema and rejects gaps, bad ordering and invalid values. |
| `geometry.py` | `intersects_rectangle`, `is_blocked`, `distance` | Determines whether the vehicle-to-tower segment touches an active rectangle. |
| `channel.py` | `observe`, `keyed_normal` | Computes the synthetic power proxy and deterministic, order-independent noise. |
| `predictor.py` | `known_geometry`, `route_offset`, `forecast` | Removes future blocker schedules, projects current position onto the planned route, and predicts link quality. |
| `policies.py` | `Context`, `Nearest.decide`, `Strongest.decide`, `A3.decide`, `timer_ready` | Defines the common decision contract and the three baselines. |
| `proactive.py` | `PredictivePolicy.scores`, `PredictivePolicy.decide` | Scores forecast quality/outage against switch cost, then applies feasibility, margin and TTT gates. |
| `handover.py` | `Controller.settle`, `request`, `finish`, `disappear` | Owns attachment, dwell, switching delay, completion checks, failure, departure and incomplete events. |
| `engine.py` | `prepare_world`, `simulate`, `World`, `Result` | Replays identical observations through isolated policies and records every tick. |
| `metrics.py` | `calculate`, `paired_summary` | Calculates exact outage/event denominators, per-vehicle episodes and paired bootstrap intervals. |
| `storage.py` | `write_run`, `persist_database`, `revision`, `list_runs` | Produces inspectable artifacts and transactional database rows with source/config provenance. |
| `reporting.py` | `collect`, `figures`, `build_report` | Validates stored evidence and creates the offline dashboard and scientific figures. |
| `experiments.py` | `variants`, `benchmark`, `benchmark_figures` | Runs matched-seed E1-E6/F5 studies, caches identical cases, and exports aggregates/intervals. |
| `dashboard.html` | Run selector and SVG rendering functions | Displays the selected saved run, its measured metrics, geometry and event log locally. |

### What happens at one simulation tick

1. Read this vehicle's current immutable position and current link observations.
2. If a switch deadline has arrived, check whether its target is still usable. Complete or fail it.
3. If every tower is unusable, clear attachment. A disconnected car can recover using the
   common strongest-usable initial-access rule.
4. When logically attached, construct the policy context. The predictive context includes
   estimates made from present information, with future blocker times removed.
5. Ask the chosen policy for a target and reason. A recommendation is not a successful handover.
6. The controller enforces a different existing target, current feasibility and minimum dwell.
   Accepted positive-delay requests enter `SWITCHING`; completion is checked on a later tick.
7. Record the final state for this timestamp. Switching, disconnection or an unusable serving
   link count as outage. Also record every enabled tower's current channel observation.
8. At the observation boundary, pending changes become incomplete; departing trace vehicles
   cancel pending changes explicitly. Neither case creates an unobserved success.

### Why the comparison is fair and causal

`prepare_world()` is called once for an all-policy run. Each policy consumes the same `World`,
so different decisions do not consume a random generator in different orders. Gaussian noise
is keyed by seed, vehicle, tower and timestamp. `simulate()` creates a fresh controller for each
vehicle and policy. Deterministic ties prefer ascending tower ID.

Prediction uses current position/speed, the known planned route, fixed tower locations and
currently active blocker footprints. `known_geometry()` strips activation/expiry schedules.
Forecast shadowing is zero; the predictor never receives the actual future noise samples.
Location-error experiments perturb forecast positions while preserving the true recorded world.

### Recommendation versus execution

This separation is central to the project. A policy answers **which tower looks preferable**.
The controller answers **whether a change can start now and whether it later succeeds**.
For example, a forecast may favor another tower while dwell is still locked. The controller
keeps the association; it does not bypass the constraint because prediction looks promising.
When a target becomes blocked during the switching delay, completion fails and the old usable
association is retained or the car becomes disconnected. Tests verify these transitions.

## Task-by-task implementation guide

Follow this order to study, demonstrate or explain the complete project. Each task names the
implemented code, its purpose and a concrete verification point.

| Task | Work and purpose | Code to inspect | Verification/evidence |
|---|---|---|---|
| 1. Define the research question | Compare proactive and reactive selection using outage and switching cost under identical inputs. | `docs/REQUIREMENTS.md`, `docs/ASSUMPTIONS.md` | Every mandatory Tier-A requirement maps to implementation and tests. |
| 2. Prepare the environment | Isolate dependencies and install the package without changing system Python. | `pyproject.toml`, `requirements.lock`, `scripts/bootstrap.sh` | `python -m pip check`; `python -m nextower --version`. |
| 3. Model the domain | Define towers, active vehicles, rectangles, observations, decisions and events with clear invariants. | `models.py` | Frozen observation objects and separate mutable controller state. |
| 4. Validate scenarios | Read YAML, apply typed overrides, reject invalid IDs/units/shapes and establish config hashes. | `config.py`, `configs/*.yaml` | `python -m nextower validate --config configs/blocked_corridor.yaml`; configuration tests. |
| 5. Generate mobility | Advance the vehicle along a planned polyline at configured speed and hold it at the endpoint. | `mobility.py` | Turn/stop tests; `data/corridor_mobility.csv` contains 180 canonical observations. |
| 6. Support trace interchange | Replay independently supplied positions through the same position schema. | `traces.py`, `data/DATASET_CARD.md` | Export/replay roundtrip; bad timestamps, missing ticks and unknown IDs are rejected. |
| 7. Detect obstruction | Test the closed vehicle-to-tower segment against active rectangular footprints. | `geometry.py` | Crossing, corner, edge, endpoint and zero-length geometry fixtures. |
| 8. Calculate current links | Apply distance loss, one blocker penalty and optional keyed Gaussian shadowing. | `channel.py` | Channel-equation and deterministic-noise tests; `links.csv`. |
| 9. Freeze the shared world | Precompute actual observations so policies compare the same positions and radio realizations. | `engine.prepare_world` | Reversed policy order yields identical radio observations and per-policy outcomes. |
| 10. Implement simple baselines | Select by distance or strongest current proxy to establish interpretable comparators. | `Nearest`, `Strongest` in `policies.py` | Controlled maximum-quality and deterministic-tie tests. |
| 11. Execute handovers | Model initial access, delay, dwell, success, target failure, loss and recovery independently of recommendations. | `handover.Controller` | Delay/dwell/failure tests; distinct attempted, success, failed, rejected and incomplete events. |
| 12. Add A3-style stability | Require a sustained neighbor advantage with candidate timer resets. | `A3`, `timer_ready` | TTT is checked at dt 0.25, 0.5 and 1.0 seconds. |
| 13. Forecast causally | Advance from present route progress and speed, using only observed geometry persistence. | `predictor.py` | Changing future noise/schedules cannot leak realized future observations into the forecast. |
| 14. Score proactive candidates | Balance normalized horizon quality, forecast outage and switching cost; require usable targets and stability gates. | `proactive.PredictivePolicy` | Controlled score/feasibility tests; compare predictive with baseline event logs. |
| 15. Evaluate exact outcomes | Count outage vehicle-ticks, usable samples, outage episodes, completed changes and ping-pong returns. | `metrics.calculate` | Zero/one outage, multivehicle exposure and golden regression tests. |
| 16. Persist research evidence | Write CSV/JSON/YAML plus normalized SQLite rows, recording the exact configuration and source. | `storage.py` | CSV roundtrip, repeat-write protection, transaction and foreign-key integrity tests. |
| 17. Build the dashboard | Recalculate saved metrics, draw actual figures, embed the saved data, and provide raw downloads. | `reporting.py`, `dashboard.html` | Report tamper detection; offline run selection; no invented graph data. |
| 18. Run experiments | Vary speed, blocker severity, horizon, forecast error and stability gates using matched seeds. | `experiments.py` | 33 variants, 30 seeds, 3,960 rows; `reports/research/paired.csv` records uncertainty. |
| 19. Verify the complete flow | Exercise validation, policies, state timing, persistence, reports and CLI from installed code. | `tests/`, `.github/workflows/ci.yml` | `python -m pytest -q`; lint/format/build checks. |
| 20. Prepare the handoff | Document operation, limitations, ownership and code; package the current uncommitted snapshot with its existing history. | `README.md`, `docs/SUBMISSION.md`, `scripts/package_submission.py` | ZIP CRC/SHA256/file-hash checks; Git HEAD and 30-commit count remain unchanged. |

### A practical demonstration sequence

```sh
cd ~/Desktop/NexTower-Proactive-5G
source .venv/bin/activate

# Task 4: prove that the scenario is valid
python -m nextower validate --config configs/blocked_corridor.yaml

# Tasks 5-16: run the shared world through all four policies
python -m nextower simulate --config configs/blocked_corridor.yaml --output runs/explain-demo

# Task 17: inspect state, metrics, plots and actual event downloads
python -m nextower report --runs runs/explain-demo --output reports/explain-demo
open reports/explain-demo/index.html

# Task 19: run the automated verification suite
python -m pytest -q

# Task 18: create an exploratory study in a new output directory
python -m nextower benchmark --seeds 3 --suite quick --output reports/explain-study
```

Use new output names when repeating the report/benchmark commands. For an interview, start with
`engine.py`, follow one tick into a policy and `Controller`, then show its actual CSV event and
explain how `metrics.py` counts it. Finish by discussing a negative experiment and the omitted
real-network mechanisms. This demonstrates understanding of both the software and its limits.
