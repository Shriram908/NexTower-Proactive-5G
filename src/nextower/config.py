"""Strict versioned YAML configuration; all numbers use explicit SI units."""

import copy
import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

import yaml

from .models import Blocker, Tower, Vehicle

POLICIES = ("nearest", "strongest", "a3", "predictive")


@dataclass(frozen=True)
class Simulation:
    duration_s: float
    dt_s: float
    mobility_backend: str = "synthetic"
    channel_backend: str = "proxy"
    trace_file: str | None = None


@dataclass(frozen=True)
class Road:
    x_min_m: float
    x_max_m: float
    y_min_m: float
    y_max_m: float


@dataclass(frozen=True)
class Channel:
    pl0_db: float = 60.0
    d0_m: float = 1.0
    pathloss_exponent: float = 2.2
    blocker_penalty_db: float = 22.0
    min_rx_dbm: float = -90.0
    shadowing_std_db: float = 0.0
    tx_gain_dbi: float = 0.0
    rx_gain_dbi: float = 0.0


@dataclass(frozen=True)
class Handover:
    switch_delay_s: float = 1.0
    min_dwell_s: float = 2.0
    a3_margin_db: float = 3.0
    ttt_s: float = 1.0
    pingpong_window_s: float = 10.0


@dataclass(frozen=True)
class Predictive:
    horizon_s: float = 5.0
    weight_quality: float = 0.35
    weight_outage: float = 0.55
    weight_switch: float = 0.10
    score_margin: float = 0.04
    q_min_dbm: float = -120.0
    q_max_dbm: float = -40.0
    location_noise_m: float = 0.0


@dataclass(frozen=True)
class Config:
    schema_version: int
    scenario_id: str
    seed: int
    simulation: Simulation
    road: Road
    vehicles: tuple[Vehicle, ...]
    towers: tuple[Tower, ...]
    blockers: tuple[Blocker, ...]
    channel: Channel
    handover: Handover
    predictive: Predictive
    policies: tuple[str, ...] = POLICIES
    output_dir: str = "runs"

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()

    @property
    def ticks(self) -> int:
        return round(self.simulation.duration_s / self.simulation.dt_s)


def _record(cls, value: Any, label: str):
    if not isinstance(value, dict):
        raise ValueError(f"{label}: expected a mapping")
    unknown = set(value) - {f.name for f in fields(cls)}
    if unknown:
        raise ValueError(f"{label}: unknown fields {sorted(unknown)}; check units and spelling")
    try:
        return cls(**value)
    except TypeError as exc:
        raise ValueError(f"{label}: {exc}") from exc


def _finite(value: Any, name: str, minimum: float | None = None, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name}: expected a finite number in the named unit")
    if positive and value <= 0 or minimum is not None and value < minimum:
        raise ValueError(f"{name}: must be {'> 0' if positive else f'>= {minimum}'}")


def _xy(value: Any, name: str) -> tuple[float, float]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError(f"{name}: expected [x_m, y_m]")
    for n in value:
        _finite(n, name)
    return tuple(value)


def from_dict(data: dict) -> Config:
    """Reject unknown keys, invalid geometry, nonfinite values and unsafe output ids."""
    if not isinstance(data, dict):
        raise ValueError("configuration must be a YAML mapping")
    d = copy.deepcopy(data)
    try:
        for key, cls in (
            ("simulation", Simulation),
            ("road", Road),
            ("channel", Channel),
            ("handover", Handover),
            ("predictive", Predictive),
        ):
            d[key] = _record(cls, d.get(key, {}), key)
        for key, cls in (("vehicles", Vehicle), ("towers", Tower), ("blockers", Blocker)):
            rows = d.get(key, [])
            if not isinstance(rows, (list, tuple)):
                raise ValueError(f"{key}: expected a list")
            parsed = []
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError(f"{key}: each item must be a mapping")
                row = dict(row)
                if cls is Tower:
                    row["xy_m"] = _xy(row.get("xy_m"), "tower.xy_m")
                if cls is Vehicle:
                    row["start_xy_m"] = _xy(row.get("start_xy_m"), "vehicle.start_xy_m")
                    path = row.get("path_xy_m")
                    if not isinstance(path, (list, tuple)) or len(path) < 2:
                        raise ValueError("vehicle.path_xy_m: at least two waypoints required")
                    row["path_xy_m"] = tuple(_xy(p, "vehicle.path_xy_m") for p in path)
                if cls is Blocker:
                    b = row.get("bounds_m")
                    if not isinstance(b, (tuple, list)) or len(b) != 4:
                        raise ValueError("blocker.bounds_m: expected [xmin, ymin, xmax, ymax]")
                    for n in b:
                        _finite(n, "blocker.bounds_m")
                    if b[0] >= b[2] or b[1] >= b[3]:
                        raise ValueError("blocker.bounds_m: require xmin<xmax and ymin<ymax")
                    row["bounds_m"] = tuple(b)
                parsed.append(_record(cls, row, key))
            d[key] = tuple(parsed)
        d["policies"] = tuple(d.get("policies", POLICIES))
        cfg = _record(Config, d, "config")
        _validate(cfg)
        return cfg
    except (TypeError, KeyError) as exc:
        raise ValueError(f"invalid configuration: {exc}") from exc


def _validate(c: Config):
    if type(c.schema_version) is not int or c.schema_version != 1:
        raise ValueError("schema_version: only version 1 is supported")
    if not isinstance(c.scenario_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", c.scenario_id):
        raise ValueError("scenario_id: use only letters, digits, underscore and hyphen")
    if isinstance(c.seed, bool) or not isinstance(c.seed, int) or c.seed < 0:
        raise ValueError("seed: expected a nonnegative integer")
    s = c.simulation
    _finite(s.duration_s, "simulation.duration_s", positive=True)
    _finite(s.dt_s, "simulation.dt_s", positive=True)
    if s.duration_s < s.dt_s or not math.isclose(
        s.duration_s / s.dt_s, round(s.duration_s / s.dt_s), rel_tol=0, abs_tol=1e-8
    ):
        raise ValueError("duration_s must be an integer multiple of dt_s")
    if s.mobility_backend not in ("synthetic", "trace") or s.channel_backend != "proxy":
        raise ValueError("backends: mobility=synthetic|trace, channel=proxy only")
    if s.mobility_backend == "trace" and not s.trace_file:
        raise ValueError("simulation.trace_file is required for trace mobility")
    if s.trace_file is not None and (not isinstance(s.trace_file, str) or not s.trace_file):
        raise ValueError("simulation.trace_file must be a nonempty path string")
    for f in fields(c.road):
        _finite(getattr(c.road, f.name), "road." + f.name)
    if c.road.x_min_m >= c.road.x_max_m or c.road.y_min_m >= c.road.y_max_m:
        raise ValueError("road: require increasing x and y bounds")
    for key in ("vehicles", "towers", "blockers"):
        items = getattr(c, key)
        ids = [x.id for x in items]
        if any(not isinstance(x, str) or not x.strip() for x in ids) or len(set(ids)) != len(ids):
            raise ValueError(f"{key}: IDs must be nonempty and unique")
    if not c.vehicles:
        raise ValueError("vehicles: at least one required")
    for t in c.towers:
        _finite(t.tx_power_dbm, "tower.tx_power_dbm")
        if not isinstance(t.enabled, bool):
            raise ValueError("tower.enabled: expected true or false")
    for v in c.vehicles:
        if not isinstance(v.active, bool):
            raise ValueError("vehicle.active: expected true or false")
        _finite(v.speed_mps, "vehicle.speed_mps", minimum=0)
        if v.start_xy_m != v.path_xy_m[0]:
            raise ValueError("vehicle.start_xy_m must equal the first route waypoint")
        if any(a == b for a, b in zip(v.path_xy_m, v.path_xy_m[1:])):
            raise ValueError("vehicle.path_xy_m: consecutive waypoints must differ")
        if v.initial_tower_id is not None and (
            not isinstance(v.initial_tower_id, str)
            or v.initial_tower_id not in {t.id for t in c.towers if t.enabled}
        ):
            raise ValueError("vehicle.initial_tower_id: unknown or disabled tower")
    if not any(v.active for v in c.vehicles):
        raise ValueError("vehicles: at least one active vehicle required")
    for b in c.blockers:
        _finite(b.start_s, "blocker.start_s", minimum=0)
        if b.end_s is not None:
            _finite(b.end_s, "blocker.end_s", positive=True)
            if b.end_s <= b.start_s:
                raise ValueError("blocker.end_s must exceed start_s")
    for f in fields(c.channel):
        _finite(getattr(c.channel, f.name), "channel." + f.name)
    for name in ("d0_m", "pathloss_exponent"):
        _finite(getattr(c.channel, name), "channel." + name, positive=True)
    for name in ("blocker_penalty_db", "shadowing_std_db"):
        _finite(getattr(c.channel, name), "channel." + name, minimum=0)
    for f in fields(c.handover):
        _finite(getattr(c.handover, f.name), "handover." + f.name, minimum=0)
    for f in fields(c.predictive):
        _finite(getattr(c.predictive, f.name), "predictive." + f.name)
    p = c.predictive
    if p.horizon_s < s.dt_s or not math.isclose(
        p.horizon_s / s.dt_s, round(p.horizon_s / s.dt_s), rel_tol=0, abs_tol=1e-8
    ):
        raise ValueError("predictive.horizon_s must be a positive integer multiple of dt_s")
    if p.q_min_dbm >= p.q_max_dbm:
        raise ValueError("predictive quality bounds must increase")
    for name in (
        "weight_quality",
        "weight_outage",
        "weight_switch",
        "score_margin",
        "location_noise_m",
    ):
        _finite(getattr(p, name), "predictive." + name, minimum=0)
    if p.weight_quality + p.weight_outage <= 0:
        raise ValueError("predictive: at least one quality/outage weight must be positive")
    if not c.policies or len(set(c.policies)) != len(c.policies) or set(c.policies) - set(POLICIES):
        raise ValueError(f"policies: choose unique values from {POLICIES}")
    if not isinstance(c.output_dir, str) or not c.output_dir:
        raise ValueError("output_dir must be a nonempty path")


def load_config(path: str | Path, overrides: list[str] | None = None) -> Config:
    try:
        data = yaml.safe_load(Path(path).read_text())
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("configuration must be a YAML mapping")
    for assignment in overrides or []:
        if "=" not in assignment:
            raise ValueError("override syntax: --set section.field=value")
        name, value = assignment.split("=", 1)
        keys = name.split(".")
        target = data
        for key in keys[:-1]:
            if not isinstance(target.get(key), dict):
                raise ValueError(f"unknown override section: {name}")
            target = target[key]
        try:
            target[keys[-1]] = yaml.safe_load(value)
        except yaml.YAMLError as exc:
            raise ValueError(f"invalid YAML override for {name}: {exc}") from exc
    return from_dict(data)
