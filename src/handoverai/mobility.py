"""Canonical synthetic samples on the half-open observation interval [0, duration)."""

import math

from .config import Config
from .geometry import distance
from .models import PositionSample, Vehicle


def along_route(path: tuple[tuple[float, float], ...], offset_m: float):
    remaining = max(0.0, offset_m)
    for a, b in zip(path, path[1:]):
        length = distance(a, b)
        if remaining < length:
            ratio = remaining / length
            return (
                (a[0] + ratio * (b[0] - a[0]), a[1] + ratio * (b[1] - a[1])),
                math.atan2(b[1] - a[1], b[0] - a[0]),
                False,
            )
        remaining -= length
    a, b = path[-2:]
    return b, math.atan2(b[1] - a[1], b[0] - a[0]), True


def position_at(vehicle: Vehicle, time_s: float) -> PositionSample:
    xy, heading, stopped = along_route(vehicle.path_xy_m, vehicle.speed_mps * time_s)
    return PositionSample(time_s, vehicle.id, *xy, 0.0 if stopped else vehicle.speed_mps, heading)


def synthetic_trace(cfg: Config) -> tuple[PositionSample, ...]:
    return tuple(
        position_at(v, round(tick * cfg.simulation.dt_s, 10))
        for tick in range(cfg.ticks)
        for v in sorted(cfg.vehicles, key=lambda v: v.id)
    )
