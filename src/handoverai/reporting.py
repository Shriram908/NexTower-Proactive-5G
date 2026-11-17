"""Reports derive their numbers and figures from saved traces, never invented series."""

import json
import os
import shutil
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "handoverai-matplotlib"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from .config import load_config
from .metrics import calculate
from .storage import read_csv, write_csv, write_json

COLORS = {"nearest": "#7585ff", "strongest": "#f5b84c", "a3": "#ed709b", "predictive": "#20bfa2"}


def collect(runs: Path) -> list[dict]:
    manifests = sorted(runs.rglob("manifest.json"))
    if not manifests:
        raise ValueError(f"no run manifests found under {runs}")
    results = []
    seen = set()
    for path in manifests:
        manifest = json.loads(path.read_text())
        rid = manifest["run_id"]
        if rid in seen:
            continue
        seen.add(rid)
        directory = path.parent
        cfg = load_config(directory / "config.yaml")
        if cfg.digest != manifest["config_hash"]:
            raise ValueError(f"config hash mismatch: {directory}")
        rows, events = read_csv(directory / "timeseries.csv"), read_csv(directory / "handovers.csv")
        metrics = calculate(rows, events, cfg.simulation.dt_s, cfg.handover.pingpong_window_s)
        if metrics != json.loads((directory / "metrics.json").read_text()):
            raise ValueError(f"stored metrics do not match traces: {directory}")
        results.append(
            {
                "manifest": manifest,
                "config": cfg.to_dict(),
                "metrics": metrics,
                "timeseries": rows,
                "events": events,
                "source": directory,
            }
        )
    return results


def _save(fig, output: Path, name: str):
    fig.tight_layout()
    fig.savefig(output / name, dpi=150, facecolor="white")
    plt.close(fig)


def figures(results: list[dict], output: Path):
    output.mkdir(parents=True, exist_ok=True)
    first = results[0]
    focus = [
        r
        for r in results
        if r["manifest"]["scenario_id"] == first["manifest"]["scenario_id"]
        and r["manifest"]["seed"] == first["manifest"]["seed"]
    ]
    # Most recent copy for each policy if a caller reports a directory of repeated runs.
    focus = list({r["manifest"]["policy"]: r for r in focus}.values())
    cfg = first["config"]
    vid = sorted({r["vehicle_id"] for r in first["timeseries"]})[0]
    caption = f"{first['manifest']['scenario_id']} | seed {first['manifest']['seed']} | {vid}"
    fig, ax = plt.subplots(figsize=(10, 3.6))
    points = [r for r in first["timeseries"] if r["vehicle_id"] == vid]
    ax.plot(
        [float(r["x_m"]) for r in points],
        [float(r["y_m"]) for r in points],
        "--",
        color="#455266",
        label="recorded vehicle route",
    )
    for tower in cfg["towers"]:
        x, y = tower["xy_m"]
        ax.scatter(x, y, marker="^", s=100, color="#253349")
        ax.annotate(tower["id"], (x, y), xytext=(0, 7), textcoords="offset points", ha="center")
    for b in cfg["blockers"]:
        x0, y0, x1, y1 = b["bounds_m"]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color="#9da8b6", alpha=0.5))
    for run in focus:
        policy = run["manifest"]["policy"]
        lookup = {r["time_s"]: r for r in run["timeseries"] if r["vehicle_id"] == vid}
        changes = [
            lookup[e["time_s"]]
            for e in run["events"]
            if e["status"] == "success" and e["vehicle_id"] == vid and e["time_s"] in lookup
        ]
        ax.scatter(
            [float(r["x_m"]) for r in changes],
            [float(r["y_m"]) for r in changes],
            s=45,
            label=f"{policy} completed HO",
            color=COLORS[policy],
        )
    ax.set(xlabel="x (m)", ylabel="y (m)", title=f"Geometry and completed handovers\n{caption}")
    ax.set_ylim(cfg["road"]["y_min_m"] - 15, cfg["road"]["y_max_m"] + 30)
    ax.legend(fontsize=7, loc="lower right", ncol=2)
    _save(fig, output, "map.png")

    fig, ax = plt.subplots(figsize=(10, 4))
    for run in focus:
        policy = run["manifest"]["policy"]
        rows = [r for r in run["timeseries"] if r["vehicle_id"] == vid]
        ax.plot(
            [float(r["time_s"]) for r in rows],
            [
                float(r["serving_quality_dbm"]) if r["serving_quality_dbm"] else float("nan")
                for r in rows
            ],
            label=policy,
            color=COLORS[policy],
            linewidth=1.4,
        )
    ax.axhline(
        cfg["channel"]["min_rx_dbm"], linestyle="--", color="black", label="usability threshold"
    )
    ax.set(
        xlabel="time (s)",
        ylabel="synthetic receive-power proxy (dBm)",
        title=f"Serving-link proxy (includes interruption samples)\n{caption}",
    )
    ax.legend(ncol=3, fontsize=8)
    _save(fig, output, "quality.png")

    fig, ax = plt.subplots(figsize=(10, 3.5))
    tower_ids = [t["id"] for t in cfg["towers"]]
    palette = plt.get_cmap("tab10")
    for i, run in enumerate(focus):
        rows = [r for r in run["timeseries"] if r["vehicle_id"] == vid]
        for row in rows:
            serving = row["serving_tower_id"]
            color = "#d9dee5" if row["state"] != "ATTACHED" else palette(tower_ids.index(serving))
            ax.broken_barh(
                [(float(row["time_s"]), cfg["simulation"]["dt_s"])],
                (i - 0.3, 0.6),
                facecolors=color,
            )
    handles = [Rectangle((0, 0), 1, 1, color=palette(i), label=t) for i, t in enumerate(tower_ids)]
    handles.append(Rectangle((0, 0), 1, 1, color="#d9dee5", label="switching/disconnected"))
    ax.set(
        yticks=list(range(len(focus))),
        yticklabels=[r["manifest"]["policy"] for r in focus],
        xlabel="time (s)",
        title=f"Serving-cell identity (categorical colors)\n{caption}",
    )
    ax.legend(handles=handles, fontsize=7, loc="upper center", ncol=4, bbox_to_anchor=(0.5, -0.18))
    _save(fig, output, "timeline.png")

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.7))
    names = [r["manifest"]["policy"] for r in focus]
    for ax, metric, title in zip(
        axes,
        ("outage_fraction", "handover_count"),
        ("Outage fraction", "Completed handovers"),
        strict=True,
    ):
        ax.bar(names, [r["metrics"][metric] for r in focus], color=[COLORS[p] for p in names])
        ax.set_title(title)
        ax.tick_params(axis="x", labelrotation=15)
    fig.suptitle(caption)
    _save(fig, output, "comparison.png")


def build_report(runs: Path, output: Path) -> Path:
    if output.resolve().is_relative_to(runs.resolve()):
        raise ValueError("report output must be outside the input runs directory")
    results = collect(runs)
    output.mkdir(parents=True, exist_ok=False)
    summary = []
    for result in results:
        manifest = result["manifest"]
        for metric, value in result["metrics"].items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                unit = (
                    "fraction"
                    if metric.endswith("fraction")
                    else "dBm proxy"
                    if metric == "mean_quality_proxy_dbm"
                    else "s"
                    if metric.endswith("_s") or metric.endswith("seconds")
                    else "count"
                )
                summary.append(
                    {
                        "scenario": manifest["scenario_id"],
                        "policy": manifest["policy"],
                        "seed": manifest["seed"],
                        "metric_name": metric,
                        "value": value,
                        "unit": unit,
                        "backend": manifest["backend"],
                        "run_id": manifest["run_id"],
                    }
                )
        destination = output / "data" / manifest["run_id"]
        shutil.copytree(result.pop("source"), destination)
        result["download"] = f"data/{manifest['run_id']}"
    write_csv(output / "summary.csv", summary)
    write_json(output / "data.json", results)
    figures(results, output / "figures")
    template = Path(__file__).with_name("dashboard.html").read_text()
    payload = json.dumps(results, allow_nan=False).replace("<", "\\u003c")
    (output / "index.html").write_text(template.replace("__REPORT_DATA__", payload))
    return output / "index.html"
