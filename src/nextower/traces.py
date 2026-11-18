"""Canonical CSV interchange, suitable for independently exported SUMO mobility."""

import csv
import math
from dataclasses import asdict, fields
from pathlib import Path

from .config import Config
from .mobility import synthetic_trace
from .models import PositionSample

COLUMNS = [f.name for f in fields(PositionSample)]


def load_trace(path: str | Path, cfg: Config) -> tuple[PositionSample, ...]:
    with Path(path).open(newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != COLUMNS:
            raise ValueError(f"trace columns must be exactly {COLUMNS}")
        samples = []
        known = {v.id for v in cfg.vehicles if v.active}
        ticks = {vid: [] for vid in known}
        previous = (-1.0, "")
        for line, row in enumerate(reader, 2):
            try:
                values = {
                    key: row[key] if key == "vehicle_id" else float(row[key]) for key in COLUMNS
                }
                sample = PositionSample(**values)
                key = (sample.time_s, sample.vehicle_id)
                if any(not math.isfinite(v) for v in values.values() if not isinstance(v, str)):
                    raise ValueError("nonfinite coordinate/time")
                if sample.vehicle_id not in known:
                    raise ValueError("unknown vehicle ID")
                if sample.speed_mps < 0 or not 0 <= sample.time_s < cfg.simulation.duration_s:
                    raise ValueError("negative speed or time outside observation interval")
                tick = round(sample.time_s / cfg.simulation.dt_s)
                if not math.isclose(tick * cfg.simulation.dt_s, sample.time_s, abs_tol=1e-8):
                    raise ValueError("timestamp is not on the configured tick grid")
                if key <= previous:
                    raise ValueError("rows must be unique and sorted by time_s, vehicle_id")
                ticks[sample.vehicle_id].append(tick)
                samples.append(sample)
                previous = key
            except (TypeError, ValueError, KeyError) as exc:
                raise ValueError(f"trace line {line}: {exc}") from exc
    for vid, observed in ticks.items():
        if not observed or observed != list(range(observed[-1] + 1)):
            raise ValueError(
                f"trace {vid}: require a contiguous prefix starting at t=0; "
                "permanent departure is allowed, gaps/re-entry are not"
            )
    return tuple(samples)


def export_trace(cfg: Config, path: Path):
    if cfg.simulation.mobility_backend != "synthetic":
        raise ValueError("export-trace requires synthetic mobility")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(asdict(p) for p in synthetic_trace(cfg))
