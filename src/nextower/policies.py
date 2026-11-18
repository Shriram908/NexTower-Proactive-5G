"""Common decision interface; controllers alone execute state transitions."""

from dataclasses import dataclass
from typing import Protocol

from .config import Handover
from .geometry import distance
from .models import Decision, HandoverState, LinkSample, PositionSample, Tower


@dataclass(frozen=True)
class Context:
    sample: PositionSample
    towers: tuple[Tower, ...]
    links: tuple[LinkSample, ...]
    # These are causal estimates, never replayed future measurements.
    forecasts: tuple[tuple[str, tuple[LinkSample, ...]], ...] = ()


class Policy(Protocol):
    def decide(self, context: Context, state: HandoverState) -> Decision: ...


def timer_ready(state: HandoverState, candidate: str | None, now: float, ttt_s: float) -> bool:
    if candidate is None:
        state.candidate, state.candidate_since_s = None, None
        return False
    if state.candidate != candidate:
        state.candidate, state.candidate_since_s = candidate, now
    return now - state.candidate_since_s + 1e-9 >= ttt_s


class Nearest:
    def decide(self, context: Context, state: HandoverState) -> Decision:
        towers = [t for t in context.towers if t.enabled]
        target = (
            min(towers, key=lambda t: (distance(context.sample.xy, t.xy_m), t.id)).id
            if towers
            else None
        )
        return Decision(target, "nearest geometric tower")


class Strongest:
    def decide(self, context: Context, state: HandoverState) -> Decision:
        target = (
            min(context.links, key=lambda x: (-x.rx_proxy_dbm, x.tower_id)).tower_id
            if context.links
            else None
        )
        return Decision(target, "strongest current proxy")


class A3:
    def __init__(self, settings: Handover):
        self.settings = settings

    def decide(self, context: Context, state: HandoverState) -> Decision:
        links = {x.tower_id: x for x in context.links}
        best = Strongest().decide(context, state).target
        serving = links.get(state.serving)
        advantage = (
            links[best].rx_proxy_dbm - serving.rx_proxy_dbm
            if best is not None and serving is not None
            else float("inf")
        )
        candidate = (
            best
            if best != state.serving and best is not None and advantage > self.settings.a3_margin_db
            else None
        )
        ready = timer_ready(state, candidate, context.sample.time_s, self.settings.ttt_s)
        return Decision(candidate if ready else None, "A3-style margin sustained for TTT")
