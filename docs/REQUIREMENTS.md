# Blueprint traceability and acceptance

Source: owner-supplied *HandoverAI Complete Project Blueprint*, version 1.0, dated
18 November 2026. The blueprint is treated as the project specification. Its sample prompts
are reference material; the owner's explicit request authorizes this build and 30 local commits.

## Mandatory Tier A requirements

| ID | Implementation | Verification |
|---|---|---|
| A1 | `config.py`; versioned YAML, seed, simulation/road/model/policy settings | `test_config.py`; CLI validate |
| A2 | `models.py`, `mobility.py`, `handover.py`; routes and association state | route-turn test; state invariants |
| A3 | three uniquely named positioned towers in each supplied scenario; enabled flag | duplicate IDs, disabled-tower tests |
| A4 | static rectangles, optional activation windows, zero blockers | geometry tests, no-blockage scenario |
| A5 | immutable `PositionSample`; synthetic/export/replay use one schema | canonical trace roundtrip |
| A6 | strict typed configuration, finite SI values, IDs and shape checks | invalid numeric/units/shapes/route tests |
| B1 | closed segment/AABB intersection, endpoints and edges block | T03-T04 parameterized fixtures |
| B2 | log-distance loss, one blocker penalty, keyed Gaussian shadowing | channel equation and deterministic draw tests |
| B3 | configured threshold, delayed switching, outage recorded each tick | T13, T17 and golden regression |
| B4 | planned-route causal forecast; schedules sanitized; no oracle shipped | T14 and predictor interface |
| B5 | `links.csv`, serving quality in `timeseries.csv` | storage contract; CSV/report consistency |
| C1 | nearest, strongest, A3, predictive share `Policy.decide` contract | controlled policy examples; all-policy replay |
| C2 | one frozen `World`, per-vehicle/per-policy controller | T15-T16 repeatability and reversed order |
| C3 | dwell, TTT, delay, attempt/success/fail/reject/incomplete events | controller timing and transaction tests |
| C4 | no towers, stable ties, invalid candidates, permanent departure | T07-T08, T19-T22 |
| D1 | per-run CSV/JSON, summary CSV, F1-F5 PNGs, offline HTML | report end-to-end + checked-in actual reports |
| D2 | installed CLI, module entry point, `--set` overrides | CLI success and actionable failure test |
| D3 | pytest, CI config, exact lock, license, README, ignores | tests, Ruff, package/clean-copy verification |
| D4 | explicit proxy labeling and optional integration status | README, architecture, limitations, figure labels |

## Test matrix

| Blueprint test | Evidence in `tests/` | Status |
|---|---|---|
| T01 | `test_t01_invalid_numeric_and_units`, negative-speed test | covered |
| T02 | `test_t02_duplicate_ids`, `test_t02_unknown_initial_tower` | covered |
| T03, T04 | `test_t03_t04_closed_geometry` | covered |
| T05 | `test_t05_zero_distance` | covered |
| T06 | `test_t06_activation_window` | covered |
| T07 | `test_t07_no_towers_is_total_outage` | covered |
| T08 | deterministic tie and identical-tower tests | covered |
| T09 | controlled strongest quality/tie test | covered |
| T10 | `test_t10_a3_candidate_reset` | covered |
| T11 | elapsed TTT tests at dt 0.25 / 0.5 / 1.0 | covered |
| T12 | `test_t12_dwell_prevents_immediate_return` | covered |
| T13 | `test_t13_delay_and_single_pending`; all-policy invariant test | covered |
| T14 | `test_t14_forecasts_ignore_future_noise_and_schedules` | covered |
| T15 | `test_t15_exact_csv_reproducibility` | covered |
| T16 | `test_t16_policy_order_cannot_change_channel` | covered |
| T17 | zero/one outage, episode boundaries, multivehicle denominators | covered |
| T18 | `test_t18_single_tick_and_empty` | covered |
| T19 | six malformed CSV cases; contiguous-prefix/departure rule | covered; CSV interchange only |
| T20 | unique output dirs, four policy outputs, repeat-write refusal | covered |
| T21 | `test_t21_disconnected_recovers_and_no_usable_stays_disconnected` | covered |
| T22 | failed/deactivated target tests; rejected/terminal cases | covered |
| T23 | report recomputation/tamper detection; metrics calculated from saved CSV | covered |
| T24 | actual ns-3 packet/HO evidence | optional Tier C; not implemented |

## Experiments and figures

| ID | Implementation/output | Scope |
|---|---|---|
| E1 | four policies, matched seeds | implemented |
| E2 | speeds 5/10/15/20 m/s, full route + 5 s | implemented |
| E3 | penalties 0/10/20/30 dB | implemented |
| E4 | horizons 1/3/5/10 s | implemented |
| E5 | forecast displacement std 0/1/3/5 m | implemented |
| E6 | no TTT / no dwell / no switch cost + naive combined ablation | implemented |
| E7 | optional tower/blocker density study | configurable but no packaged density study claimed |
| E8 | actual packet metrics | optional Tier C; not implemented |
| F1 | map with tower/blocker geometry and completed handover markers | implemented |
| F2 | categorical serving-cell timeline | implemented |
| F3 | serving-link proxy vs threshold | implemented |
| F4 | matched-seed outcomes and SD plus paired confidence table | implemented |
| F5 | horizon/TTT heatmap | implemented |
| F6 | ns-3 delivery/latency | optional Tier C; not implemented |

The Python submission completes the mandatory Tier A gate. Optional SUMO/native NR integrations
are explicitly outside its completed scope; no placeholder adapter is presented as working code.
