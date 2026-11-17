"""Closed-segment/AABB clipping. Endpoints, tangencies and edges count as blocked."""

from math import hypot

from .models import Blocker


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return hypot(b[0] - a[0], b[1] - a[1])


def intersects_rectangle(a: tuple[float, float], b: tuple[float, float],
                         bounds: tuple[float, float, float, float]) -> bool:
    """Slab intersection with a closed rectangle, also valid for a zero-length segment."""
    lo, hi = 0.0, 1.0
    for origin, delta, lower, upper in (
        (a[0], b[0] - a[0], bounds[0], bounds[2]),
        (a[1], b[1] - a[1], bounds[1], bounds[3]),
    ):
        if abs(delta) < 1e-12:
            if origin < lower or origin > upper:
                return False
            continue
        first, last = sorted(((lower - origin) / delta, (upper - origin) / delta))
        lo, hi = max(lo, first), min(hi, last)
        if lo > hi:
            return False
    return True


def is_blocked(a: tuple[float, float], b: tuple[float, float],
               blockers: tuple[Blocker, ...], time_s: float) -> bool:
    return any(x.active(time_s) and intersects_rectangle(a, b, x.bounds_m) for x in blockers)
