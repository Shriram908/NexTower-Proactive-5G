"""Metrics calculated from persisted CSV-compatible observations and event records."""

import math
from collections import defaultdict
from statistics import mean


def flag(value) -> bool:
    return value is True or value == 1 or value == "1" or value == "True"


def calculate(rows: list[dict], events: list[dict], dt_s: float, pingpong_window_s: float) -> dict:
    if not rows:
        raise ValueError("metrics require at least one observation")
    by_vehicle = defaultdict(list)
    for row in rows:
        by_vehicle[row["vehicle_id"]].append(row)
    episodes = []
    for vehicle_rows in by_vehicle.values():
        length = 0
        for row in sorted(vehicle_rows, key=lambda r: float(r["time_s"])):
            if flag(row["outage"]):
                length += 1
            elif length:
                episodes.append(length * dt_s)
                length = 0
        if length:
            episodes.append(length * dt_s)
    completed = [e for e in events if e["status"] == "success"]
    history = {}
    pingpongs = 0
    for e in completed:
        previous = history.get(e["vehicle_id"])
        if (
            previous
            and previous["from_tower"] == e["to_tower"]
            and previous["to_tower"] == e["from_tower"]
            and float(e["time_s"]) - float(previous["time_s"]) <= pingpong_window_s
        ):
            pingpongs += 1
        history[e["vehicle_id"]] = e
    good = [
        float(r["serving_quality_dbm"])
        for r in rows
        if not flag(r["outage"])
        and r["state"] == "ATTACHED"
        and r["serving_quality_dbm"] not in (None, "")
    ]
    outage_steps = sum(flag(r["outage"]) for r in rows)
    return {
        "duration_s": max(float(r["time_s"]) for r in rows) + dt_s,
        "observed_steps": len(rows),
        "vehicle_count": len(by_vehicle),
        "observed_vehicle_seconds": len(rows) * dt_s,
        "outage_fraction": outage_steps / len(rows),
        "coverage_fraction": 1 - outage_steps / len(rows),
        "outage_seconds": outage_steps * dt_s,
        "outage_episode_lengths_s": episodes,
        "worst_outage_episode_s": max(episodes, default=0.0),
        "mean_outage_episode_s": mean(episodes) if episodes else 0.0,
        "handover_count": len(completed),
        "attempted_count": sum(e["status"] == "attempted" for e in events),
        "failed_count": sum(e["status"] == "failed" for e in events),
        "rejected_count": sum(e["status"] == "rejected" for e in events),
        "incomplete_count": sum(e["status"] == "incomplete" for e in events),
        "attachment_count": sum(e["status"] == "attached" for e in events),
        "pingpong_count": pingpongs,
        "mean_quality_proxy_dbm": mean(good) if good else None,
        "quality_sample_count": len(good),
        "total_switch_interruption_s": sum(r["state"] == "SWITCHING" for r in rows) * dt_s,
    }


def paired_summary(deltas: list[float]) -> dict:
    """Deterministic paired bootstrap (10,000 resamples), no normality assumption."""
    import random

    if not deltas or any(not math.isfinite(x) for x in deltas):
        raise ValueError("paired differences must be finite and nonempty")
    rng = random.Random(2026)
    samples = sorted(mean(rng.choices(deltas, k=len(deltas))) for _ in range(10000))
    avg = mean(deltas)
    return {
        "n": len(deltas),
        "mean_delta": avg,
        "std_delta": math.sqrt(sum((x - avg) ** 2 for x in deltas) / (len(deltas) - 1))
        if len(deltas) > 1
        else 0.0,
        "ci95_low": samples[249],
        "ci95_high": samples[9749],
        "method": "paired percentile bootstrap, 10000 draws, RNG seed 2026",
    }
