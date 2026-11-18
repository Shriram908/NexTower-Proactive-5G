"""Explicit delayed handover execution, separate from policy recommendations."""

from .config import Handover
from .models import Decision, HandoverEvent, HandoverState, LinkSample, State


def best_usable(links: dict[str, LinkSample]) -> str | None:
    viable = [key for key in links if links[key].usable]
    return min(viable, key=lambda key: (-links[key].rx_proxy_dbm, key)) if viable else None


class Controller:
    def __init__(
        self, settings: Handover, vehicle_id: str, policy: str, initial_tower: str | None = None
    ):
        self.settings, self.vehicle_id, self.policy = settings, vehicle_id, policy
        self.state = HandoverState(
            State.ATTACHED if initial_tower else State.DISCONNECTED,
            serving=initial_tower,
            last_change_s=0.0 if initial_tower else float("-inf"),
        )
        self.events: list[HandoverEvent] = []

    def emit(
        self,
        now: float,
        target: str | None,
        status: str,
        reason: str,
        completed_s: float | None = None,
    ):
        self.events.append(
            HandoverEvent(
                now,
                self.vehicle_id,
                self.policy,
                self.state.serving,
                target,
                status,
                reason,
                completed_s,
            )
        )

    def settle(self, now: float, links: dict[str, LinkSample]):
        s = self.state
        if s.state == State.SWITCHING:
            if now + 1e-9 < s.completes_at:
                return
            if s.pending in links and links[s.pending].usable:
                self.emit(now, s.pending, "success", "target usable at completion", now)
                s.serving = s.pending
                s.last_change_s = now
                s.state = State.ATTACHED
            else:
                self.emit(now, s.pending, "failed", "target unusable at completion", now)
                s.state = (
                    State.ATTACHED
                    if s.serving in links and links[s.serving].usable
                    else State.DISCONNECTED
                )
                if s.state == State.DISCONNECTED:
                    s.serving = None
            s.pending, s.completes_at = None, None
            s.candidate, s.candidate_since_s = None, None
        if s.state == State.ATTACHED and best_usable(links) is None:
            self.emit(now, None, "lost_link", "no usable tower")
            s.state, s.serving = State.DISCONNECTED, None
            s.candidate, s.candidate_since_s = None, None
        if s.state == State.DISCONNECTED:
            target = best_usable(links)
            if target is not None:
                self.emit(now, target, "attached", "initial access or recovery", now)
                s.state, s.serving, s.last_change_s = State.ATTACHED, target, now

    def request(self, now: float, decision: Decision, links: dict[str, LinkSample]):
        s, target = self.state, decision.target
        if target is None or target == s.serving or s.state != State.ATTACHED:
            return
        if now - s.last_change_s + 1e-9 < self.settings.min_dwell_s:
            return
        if target not in links or not links[target].usable:
            self.emit(now, target, "rejected", "candidate unavailable or unusable")
            return
        self.emit(now, target, "attempted", decision.reason)
        s.state, s.pending = State.SWITCHING, target
        s.completes_at = now + self.settings.switch_delay_s
        s.candidate, s.candidate_since_s = None, None
        if self.settings.switch_delay_s == 0:
            self.settle(now, links)

    def finish(self, end_s: float):
        if self.state.state == State.SWITCHING:
            self.emit(end_s, self.state.pending, "incomplete", "observation window ended")

    def disappear(self, now: float):
        """A trace vehicle may leave permanently. Pending changes do not become successes."""
        if self.state.state == State.SWITCHING:
            self.emit(now, self.state.pending, "failed", "vehicle left trace", now)
        self.state = HandoverState()
