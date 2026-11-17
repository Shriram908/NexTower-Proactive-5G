"""Immutable observations, and the one mutable state owned by each vehicle/policy."""

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True)
class Tower:
    id: str
    xy_m: tuple[float, float]
    tx_power_dbm: float = 30.0
    enabled: bool = True


@dataclass(frozen=True)
class Blocker:
    id: str
    bounds_m: tuple[float, float, float, float]
    start_s: float = 0.0
    end_s: float | None = None

    def active(self, time_s: float) -> bool:
        """Temporary rectangles occupy [start_s, end_s); edge contact blocks LOS."""
        return time_s >= self.start_s and (self.end_s is None or time_s < self.end_s)


@dataclass(frozen=True)
class Vehicle:
    id: str
    start_xy_m: tuple[float, float]
    speed_mps: float
    path_xy_m: tuple[tuple[float, float], ...]
    initial_tower_id: str | None = None
    active: bool = True


@dataclass(frozen=True)
class PositionSample:
    time_s: float
    vehicle_id: str
    x_m: float
    y_m: float
    speed_mps: float
    heading_rad: float

    @property
    def xy(self) -> tuple[float, float]:
        return self.x_m, self.y_m


@dataclass(frozen=True)
class LinkSample:
    time_s: float
    vehicle_id: str
    tower_id: str
    distance_m: float
    blocked: bool
    rx_proxy_dbm: float
    usable: bool


class State(StrEnum):
    DISCONNECTED = "DISCONNECTED"
    ATTACHED = "ATTACHED"
    SWITCHING = "SWITCHING"


@dataclass
class HandoverState:
    state: State = State.DISCONNECTED
    serving: str | None = None
    pending: str | None = None
    completes_at: float | None = None
    last_change_s: float = float("-inf")
    candidate: str | None = None
    candidate_since_s: float | None = None


@dataclass(frozen=True)
class Decision:
    target: str | None
    reason: str


@dataclass(frozen=True)
class HandoverEvent:
    time_s: float
    vehicle_id: str
    policy: str
    from_tower: str | None
    to_tower: str | None
    status: str
    reason: str
    completed_s: float | None = None
