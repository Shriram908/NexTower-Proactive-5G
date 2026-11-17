"""Geometry-aware horizon scoring with current feasibility and stability gates."""

from statistics import mean

from .config import Handover, Predictive
from .models import Decision, HandoverState
from .policies import Context, timer_ready


class PredictivePolicy:
    def __init__(self, settings: Predictive, handover: Handover):
        self.settings, self.handover = settings, handover

    def scores(self, context: Context, state: HandoverState) -> dict[str, float]:
        p = self.settings
        result = {}
        for tower_id, links in context.forecasts:
            quality = mean(max(p.q_min_dbm, min(p.q_max_dbm, x.rx_proxy_dbm)) for x in links)
            normalized = (quality - p.q_min_dbm) / (p.q_max_dbm - p.q_min_dbm)
            outage = mean(not x.usable for x in links)
            result[tower_id] = (
                p.weight_quality * normalized
                - p.weight_outage * outage
                - p.weight_switch * (tower_id != state.serving)
            )
        return result

    def decide(self, context: Context, state: HandoverState) -> Decision:
        scores = self.scores(context, state)
        links = {x.tower_id: x for x in context.links}
        target = min(scores, key=lambda key: (-scores[key], key)) if scores else None
        eligible = (
            target is not None
            and target != state.serving
            and target in links
            and links[target].usable
            and scores[target]
            > scores.get(state.serving, float("-inf")) + self.settings.score_margin
        )
        candidate = target if eligible else None
        ready = timer_ready(state, candidate, context.sample.time_s, self.handover.ttt_s)
        return Decision(
            candidate if ready else None, "causal horizon score exceeds switching margin"
        )
