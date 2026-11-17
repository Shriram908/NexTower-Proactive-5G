"""Paired-seed E1-E6 and horizon/TTT sensitivity, with replayable config snapshots."""

import copy
import importlib.metadata
import math
import platform
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev

from .config import Config, from_dict
from .engine import prepare_world, simulate
from .geometry import distance
from .metrics import calculate, paired_summary
from .storage import revision, write_csv, write_json


def variants(cfg: Config, suite: str) -> list[tuple[str, str, dict]]:
    base = cfg.to_dict()
    result = [("E1", "baseline", copy.deepcopy(base))]

    def add(experiment, name, section, field, value):
        data = copy.deepcopy(base)
        data[section][field] = value
        result.append((experiment, name, data))

    for horizon in (1.0, 3.0, 5.0, 10.0):
        if horizon >= cfg.simulation.dt_s and math.isclose(
            horizon / cfg.simulation.dt_s, round(horizon / cfg.simulation.dt_s), abs_tol=1e-8
        ):
            add("E4", f"horizon_{horizon:g}s", "predictive", "horizon_s", horizon)
    if suite == "quick":
        return result
    for speed in (5.0, 10.0, 15.0, 20.0):
        data = copy.deepcopy(base)
        for vehicle in data["vehicles"]:
            vehicle["speed_mps"] = speed
        travel = max(
            sum(distance(a, b) for a, b in zip(v.path_xy_m, v.path_xy_m[1:])) / speed
            for v in cfg.vehicles
        )
        data["simulation"]["duration_s"] = (
            math.ceil((travel + 5) / cfg.simulation.dt_s) * cfg.simulation.dt_s
        )
        result.append(("E2", f"speed_{speed:g}mps", data))
    for severity in (0.0, 10.0, 20.0, 30.0):
        add("E3", f"penalty_{severity:g}dB", "channel", "blocker_penalty_db", severity)
    for error in (0.0, 1.0, 3.0, 5.0):
        add("E5", f"location_noise_{error:g}m", "predictive", "location_noise_m", error)
    for field, section in (
        ("ttt_s", "handover"),
        ("min_dwell_s", "handover"),
        ("weight_switch", "predictive"),
    ):
        add("E6", f"without_{field}", section, field, 0.0)
    naive = copy.deepcopy(base)
    naive["handover"].update(ttt_s=0.0, min_dwell_s=0.0)
    naive["predictive"].update(weight_switch=0.0, score_margin=0.0)
    result.append(("E6", "naive_lookahead", naive))
    for horizon in (1.0, 3.0, 5.0, 10.0):
        if horizon < cfg.simulation.dt_s or not math.isclose(
            horizon / cfg.simulation.dt_s, round(horizon / cfg.simulation.dt_s), abs_tol=1e-8
        ):
            continue
        for ttt in (0.0, 1.0, 2.0):
            data = copy.deepcopy(base)
            data["predictive"]["horizon_s"], data["handover"]["ttt_s"] = horizon, ttt
            result.append(("F5", f"h{horizon:g}_ttt{ttt:g}", data))
    return result


def benchmark(cfg: Config, seeds: int, suite: str, output: Path) -> Path:
    if seeds < 1:
        raise ValueError("--seeds must be >= 1 (use 10+ for uncertainty estimates)")
    if cfg.simulation.mobility_backend != "synthetic":
        raise ValueError(
            "sensitivity experiments require synthetic mobility; use simulate for traces"
        )
    output.mkdir(parents=True, exist_ok=False)
    rows, snapshots, cache = [], {}, {}
    matrix = variants(cfg, suite)
    for experiment, label, settings in matrix:
        for seed in range(cfg.seed, cfg.seed + seeds):
            data = copy.deepcopy(settings)
            data["seed"] = seed
            config = from_dict(data)
            snapshots[config.digest] = config.to_dict()
            world = None
            # Every baseline is included in every variant: genuine paired comparisons.
            for policy in cfg.policies:
                key = (config.digest, policy)
                if key not in cache:
                    world = world or prepare_world(config)
                    result = simulate(config, policy, world)
                    cache[key] = calculate(
                        result.timeseries,
                        result.events,
                        config.simulation.dt_s,
                        config.handover.pingpong_window_s,
                    )
                metrics = cache[key]
                rows.append(
                    {
                        "experiment": experiment,
                        "variant": label,
                        "policy": policy,
                        "seed": seed,
                        "config_hash": config.digest,
                        "scenario": config.scenario_id,
                        "horizon_s": config.predictive.horizon_s,
                        "ttt_s": config.handover.ttt_s,
                        **{
                            k: metrics[k]
                            for k in (
                                "outage_fraction",
                                "handover_count",
                                "pingpong_count",
                                "mean_quality_proxy_dbm",
                                "worst_outage_episode_s",
                                "mean_outage_episode_s",
                                "attempted_count",
                                "failed_count",
                                "observed_steps",
                            )
                        },
                    }
                )
        print(f"{experiment} {label}: {seeds} paired seeds", flush=True)
    write_csv(output / "results.csv", rows)
    write_json(output / "configs.json", snapshots)
    aggregates, paired = [], []
    for experiment, label, _ in matrix:
        subset = [r for r in rows if r["experiment"] == experiment and r["variant"] == label]
        for policy in cfg.policies:
            selected = [r for r in subset if r["policy"] == policy]
            for metric in ("outage_fraction", "handover_count", "pingpong_count"):
                values = [r[metric] for r in selected]
                aggregates.append(
                    {
                        "experiment": experiment,
                        "variant": label,
                        "policy": policy,
                        "metric": metric,
                        "n": len(values),
                        "mean": mean(values),
                        "std": stdev(values) if len(values) > 1 else 0.0,
                    }
                )
        if "predictive" in cfg.policies and "strongest" in cfg.policies:
            indexed = {(r["seed"], r["policy"]): r for r in subset}
            deltas = [
                indexed[s, "predictive"]["outage_fraction"]
                - indexed[s, "strongest"]["outage_fraction"]
                for s in range(cfg.seed, cfg.seed + seeds)
            ]
            paired.append(
                {
                    "experiment": experiment,
                    "variant": label,
                    "comparison": "predictive minus strongest outage fraction",
                    **paired_summary(deltas),
                }
            )
    write_csv(output / "aggregate.csv", aggregates)
    if paired:
        write_csv(output / "paired.csv", paired)
    write_json(
        output / "manifest.json",
        {
            "schema_version": 1,
            "kind": "experiment_suite",
            "suite": suite,
            "seeds": seeds,
            "first_seed": cfg.seed,
            "variant_count": len(matrix),
            "evaluated_rows": len(rows),
            "unique_simulations": len(cache),
            "created_utc": datetime.now(timezone.utc).isoformat(),
            **revision(),
            "versions": {
                "python": platform.python_version(),
                "matplotlib": importlib.metadata.version("matplotlib"),
                "PyYAML": importlib.metadata.version("PyYAML"),
            },
            "note": "Synthetic proxy only. Seeds pair mobility and channel across policies. "
            "E2 duration covers full route plus 5 seconds; prediction error changes forecasts only.",
        },
    )
    benchmark_figures(rows, output / "figures")
    return output


def benchmark_figures(rows: list[dict], output: Path):
    from .reporting import COLORS, _save, plt

    output.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    e1 = [r for r in rows if r["experiment"] == "E1"]
    policies = list(dict.fromkeys(r["policy"] for r in e1))
    for ax, metric in zip(axes, ("outage_fraction", "handover_count"), strict=True):
        for i, policy in enumerate(policies):
            values = [r[metric] for r in e1 if r["policy"] == policy]
            ax.scatter(
                [i + (j - len(values) / 2) * 0.008 for j in range(len(values))],
                values,
                color=COLORS[policy],
                s=15,
                alpha=0.45,
            )
            ax.errorbar(
                i,
                mean(values),
                yerr=stdev(values) if len(values) > 1 else 0,
                color="#253349",
                marker="_",
                capsize=5,
            )
        ax.set(xticks=range(len(policies)), xticklabels=policies, title=metric.replace("_", " "))
    fig.suptitle("Matched seeds: individual outcomes and mean ± sample SD (synthetic proxy)")
    _save(fig, output, "paired_outcomes.png")
    f5 = [r for r in rows if r["experiment"] == "F5" and r["policy"] == "predictive"]
    if f5:
        horizons, ttts = sorted({r["horizon_s"] for r in f5}), sorted({r["ttt_s"] for r in f5})
        values = [
            [
                mean(r["outage_fraction"] for r in f5 if r["horizon_s"] == h and r["ttt_s"] == t)
                for h in horizons
            ]
            for t in ttts
        ]
        fig, ax = plt.subplots(figsize=(7, 4))
        image = ax.imshow(values, cmap="viridis", aspect="auto")
        for y, row in enumerate(values):
            for x, v in enumerate(row):
                ax.text(x, y, f"{v:.3f}", color="white", ha="center", va="center")
        ax.set(
            xticks=range(len(horizons)),
            xticklabels=horizons,
            yticks=range(len(ttts)),
            yticklabels=ttts,
            xlabel="prediction horizon (s)",
            ylabel="TTT (s)",
            title="Predictive outage fraction: horizon / TTT sensitivity",
        )
        fig.colorbar(image, ax=ax, label="mean outage fraction")
        _save(fig, output, "horizon_ttt_heatmap.png")
    e6 = [r for r in rows if r["experiment"] == "E6" and r["policy"] == "predictive"]
    if e6:
        names = list(dict.fromkeys(r["variant"] for r in e6))
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        for ax, metric in zip(axes, ("handover_count", "pingpong_count"), strict=True):
            ax.barh(
                names,
                [mean(r[metric] for r in e6 if r["variant"] == n) for n in names],
                color=COLORS["predictive"],
            )
            ax.set_title(metric.replace("_", " "))
        _save(fig, output, "ablations.png")
