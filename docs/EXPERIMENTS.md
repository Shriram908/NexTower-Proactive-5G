# Reproduce and interpret the research

## Research question

Does geometry-aware proactive handover reduce outage compared with reactive strongest-current
selection under predictable obstruction, while limiting switching and using only causal inputs?
The hypothesis concerns an abstract model; no real 5G performance claim follows from it.

## Canonical examples

```sh
python -m nextower simulate --config configs/blocked_corridor.yaml --output runs/corridor
python -m nextower simulate --config configs/no_blockage.yaml --output runs/open-road
python -m nextower simulate --config configs/dynamic_blocker.yaml --output runs/temporary
python -m nextower report --runs runs/corridor --output reports/corridor-new
open reports/corridor-new/index.html
```

The supplied blocked-corridor YAML uses the blueprint's illustrative parameterization. The
second rectangle lies below the y=0 route while towers lie above it; it does not necessarily
obstruct any link. It is retained rather than inventing a more favorable original scenario.
`dynamic_blocker.yaml` adds a temporarily parked rectangle and 2 dB shadow noise. Its future
activation and expiration are known to the world but hidden from the predictor.

The `runs` root contains unique batches. Every policy subdirectory includes its actual config,
SHA256, seed, source revision, runtime versions and timestamp. Opening a report's data downloads
provides the exact CSV/JSON used for its figures and metrics.

## Paired study, E1-E6 and F5

```sh
python -m nextower benchmark \
  --config configs/blocked_corridor.yaml \
  --set channel.shadowing_std_db=2.0 \
  --seeds 30 --suite full --output reports/research-reproduced
```

The release study uses seeds 42 through 71, all four policies in each variant, 33 variants,
3,960 policy/variant/seed rows and 3,000 unique simulations (identical cases cached). Defaults
without shadow noise are deterministic; adding 2 dB here makes seed variation meaningful.
For fast exploration use `--suite quick --seeds 3` and a fresh output directory. A quick result
is not the release's full uncertainty study.

Outputs:

* `results.csv`: one row per experiment, variant, policy and seed.
* `configs.json`: exact validated settings indexed by config hash, including each seed.
* `aggregate.csv`: mean and sample standard deviation, with sample size.
* `paired.csv`: predictive-minus-strongest outage differences, paired bootstrap 95% intervals.
* `manifest.json`: versions, revision, suite, row/seed counts and timing metadata.
* `figures/paired_outcomes.png`: individual E1 seeds and mean ± SD, not a confidence interval.
* `figures/horizon_ttt_heatmap.png`: mean outage for each horizon/TTT combination.
* `figures/ablations.png`: completed handovers and ping-pong for E6 variants.

Horizon 1/3/5/10 seconds is included only when divisible by the configured dt. E2 varies time
exposure so the same complete route is traversed at every speed. E5 perturbs forecasts only.
`naive_lookahead` jointly removes TTT, dwell, switching penalty and score margin; it is an
explicit ablation, not an extra default policy. The one-factor ablations remove only one gate.

## Interpretation protocol

Read `RESULTS.md` for the actual release findings and their denominators. Compare policies
within matched seeds and settings. Do not pool distinct scenario variants into a single
unqualified effect. Separate mean outage, switching cost, attachment events and failures.
Inspect full event/timeline data when an apparently lower outage comes from disconnection and
instantaneous recovery rather than completed handovers.

H1 is supported only in a designated scenario if its measured outcome agrees. For H2 compare
switching and ping-pong separately; if every ablation has zero ping-pong, the experiment cannot
demonstrate a ping-pong reduction. H3 requires inspecting variation across the sensitivity
matrix, including cases where the predictive policy loses. Do not convert a conditional toy
model confidence interval into a statement about real networks. Multiple tested variants are
exploratory and no multiplicity-adjusted significance claim is made.

## Replaying a single saved experiment configuration

```sh
python - <<'PY'
import csv, json, yaml
from pathlib import Path
rows = list(csv.DictReader(open('reports/research/results.csv')))
selected = next(r for r in rows if r['experiment']=='E1' and r['policy']=='predictive')
configs = json.loads(Path('reports/research/configs.json').read_text())
Path('/tmp/nextower-replay.yaml').write_text(yaml.safe_dump(configs[selected['config_hash']]))
print(selected)
PY
python -m nextower simulate --config /tmp/nextower-replay.yaml --policy predictive
```

The saved config hash and policy identify the complete input. UUIDs/timestamps differ between
runs; time series, links, handover CSV and metric values are deterministic on the tested runtime.
