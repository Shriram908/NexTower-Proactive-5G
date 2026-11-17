# Measured release findings

These are outputs of the actual Python runner, not example numbers. The underlying radio
model is a synthetic proxy. No measurements from a modem, public mobile network, field trial
or ns-3 packet simulation are represented.

## Canonical blueprint corridor, seed 42, zero shadowing

180 observations at dt=0.5 seconds; 90-second observation window; one vehicle. The full report
is `reports/demo/index.html`; its `data/<run-id>/` files contain original traces/configs/manifests.

| Policy | Outage fraction | Outage seconds | Completed handovers |
|---|---:|---:|---:|
| nearest | 0.038889 | 3.5 | 2 |
| strongest | 0.033333 | 3.0 | 3 |
| a3 | 0.044444 | 4.0 | 3 |
| predictive | 0.011111 | 1.0 | 1 |

Predictive makes one switch instead of three and has 2 fewer interrupted seconds than strongest
in this deterministic example. This is a sanity demonstration, not independent statistical
evidence. The same output must repeat for the same inputs on the tested runtime.

## E1, matched seeds 42-71, 2 dB shadowing

Command: the full benchmark in `EXPERIMENTS.md`, with no additional parameter tuning.
`reports/research/results.csv`, `aggregate.csv`, `paired.csv`, `configs.json` and its manifest
provide the complete record. Each policy sees identical actual radio draws within each seed.

| Policy | Mean outage | Sample SD of outage | Mean completed HO | Mean ping-pong |
|---|---:|---:|---:|---:|
| nearest | 3.3333% | 0.6190 pp | 1.7333 | 0 |
| strongest | 4.7037% | 1.2697 pp | 3.5333 | 1.3333 |
| a3 | 3.5185% | 0.8794 pp | 1.9667 | 0 |
| predictive | 3.2593% | 2.0773 pp | 0.6333 | 0 |

The mean paired predictive-minus-strongest outage difference is **-0.01444444**, or **-1.4444
percentage points**. The paired percentile-bootstrap 95% interval is **[-2.3889, -0.4815]
percentage points**, using 10,000 paired resamples and bootstrap seed 2026. Relative to the
strongest mean outage of 0.04703704, the observed mean reduction is **30.71%**.

The larger predictive sample SD matters: fewer average handovers do not guarantee a smaller
outage in every seed. Some runs lose all usable links and recover through the shared initial
access rule, so attachment count and successful HO count are distinct. Inspect events when
comparing apparently low switch counts. These intervals are conditional on the synthetic
channel and scenario and are exploratory, without multiple-comparison adjustment.

## Sensitivity and negative outcomes

The full suite evaluates 33 variants × 30 seeds × 4 policies = **3,960 recorded rows**.
Repeated identical configs/policies are cached, leaving **3,000 unique simulations**. It
covers E1-E6 plus the F5 horizon/TTT grid. All exact input snapshots are indexed by SHA256.

* At **10 dB blockage loss**, predictive-minus-strongest mean outage is **+0.3704 percentage
  points**, with 95% interval **[-0.2593, +0.9630] pp**. The mean favors the reactive baseline
  here; the interval spans zero.
* With **5 m forecast displacement std**, the effect shrinks to **-0.3889 pp** with interval
  **[-1.3519, +0.5926] pp**. This does not establish an advantage under that error model.
* At **20 m/s**, the effect is **-0.1053 pp** with interval **[-1.5088, +1.2632] pp**. Speed
  changes observation duration to preserve the full traveled route, as documented.
* With **1 s horizon and 2 s TTT**, mean predictive outage is worse by **+0.1667 pp**, with
  interval **[-0.9444, +1.2963] pp**. Longer TTT can delay action beyond a short forecast.

These results demonstrate why the horizon, error assumptions and stability gates must be
reported with performance. They are included without removing unfavorable variants.

## Ablation findings, predictive policy

| Variant | Mean outage | Mean completed HO | Mean ping-pong |
|---|---:|---:|---:|
| default E1 | 3.2593% | 0.6333 | 0 |
| no TTT | 3.4074% | 0.8667 | 0 |
| no dwell | 3.2593% | 0.6333 | 0 |
| no switch cost | 3.7593% | 2.3000 | 0 |
| naive combined look-ahead | 3.9815% | 2.6000 | 0 |

Removing switching cost increases handovers in this corridor; removing dwell alone changes
nothing. Every tested predictive ablation has zero ping-pong. Therefore H2 is supported here
for reducing **handover count**, but its specific **ping-pong reduction** is not demonstrated
by this ablation. Strongest has nonzero ping-pong in E1, but comparing it to predictive also
changes more than the stability gates and cannot isolate their causal contribution.

## Other packaged scenarios, seed 42

No-blockage: nearest, strongest and A3 each have 2.2222% outage and 2 completed handovers;
predictive has 1.1111% and 1 handover. With this permissive toy threshold it can remain with a
distant cell. This must not be interpreted as realistic multi-cell capacity optimization.

Temporary blocker with 2 dB shadow noise: nearest/A3 outage is 5.00%, strongest 7.2222%,
predictive 6.1111%. Predictive is worse than nearest/A3 in this seed. Active blockers persist
in its forecast and unseen appearances cannot be anticipated. No method is claimed best
across all supplied settings.

## Hypothesis assessment

* H1: supported for the designated static corridor under these proxy parameters, including
  the matched-seed noisy comparison; external/real-network validity remains untested.
* H2: switching-count reduction is observed; the requested predictive-ablation ping-pong
  reduction remains unproven because its measured counts are all zero.
* H3: supported qualitatively by the varied measured effects across speed, severity, horizon,
  forecast error and stability settings, with null/negative variants explicitly recorded.

No Tier C packet results, real Mbps, SINR, measured RSRP or standardized NR performance are
reported. See `KNOWN_LIMITATIONS.md` for the missing physical/network mechanisms.
