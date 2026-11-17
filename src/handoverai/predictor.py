"""Causal route forecasts. No future observations, shadow noise or blocker schedules."""

from dataclasses import replace

from .channel import keyed_normal, observe
from .config import Channel, Predictive
from .geometry import distance
from .mobility import along_route
from .models import Blocker, LinkSample, PositionSample, Tower, Vehicle


def known_geometry(blockers: tuple[Blocker, ...], now_s: float) -> tuple[Blocker, ...]:
    """Currently observed rectangles persist; future activation/expiry is unavailable."""
    return tuple(Blocker(b.id, b.bounds_m) for b in blockers if b.active(now_s))


def route_offset(xy: tuple[float, float], path: tuple[tuple[float, float], ...]) -> float:
    best = (float("inf"), 0.0)
    travelled = 0.0
    for a, b in zip(path, path[1:]):
        length = distance(a, b)
        alpha = max(0.0, min(1.0, ((xy[0] - a[0]) * (b[0] - a[0]) +
                                 (xy[1] - a[1]) * (b[1] - a[1])) / length**2))
        projection = (a[0] + alpha * (b[0] - a[0]), a[1] + alpha * (b[1] - a[1]))
        best = min(best, (distance(xy, projection), travelled + alpha * length))
        travelled += length
    return best[1]


def forecast(sample: PositionSample, vehicle: Vehicle, towers: tuple[Tower, ...],
             geometry: tuple[Blocker, ...], channel: Channel, settings: Predictive,
             dt_s: float, seed: int) -> dict[str, tuple[LinkSample, ...]]:
    """Forecast planned-route progress from the current observation and measured speed."""
    ex, ey = (settings.location_noise_m * keyed_normal(seed, "prediction", sample.vehicle_id,
              sample.time_s, axis) for axis in ("x", "y"))
    start = route_offset(sample.xy, vehicle.path_xy_m)
    future = []
    for k in range(1, round(settings.horizon_s / dt_s) + 1):
        xy, heading, stopped = along_route(vehicle.path_xy_m, start + sample.speed_mps * k * dt_s)
        future.append(PositionSample(sample.time_s + k * dt_s, sample.vehicle_id,
                                      xy[0] + ex, xy[1] + ey,
                                      0.0 if stopped else sample.speed_mps, heading))
    # No temporally scoped Blocker is accepted here: a caller cannot accidentally leak schedules.
    if any(b.start_s != 0 or b.end_s is not None for b in geometry):
        raise ValueError("forecast geometry must be sanitized with known_geometry")
    clean_channel = replace(channel, shadowing_std_db=0.0)
    return {t.id: tuple(observe(p, t, geometry, clean_channel, seed, forecast=True)
                        for p in future) for t in towers if t.enabled}
