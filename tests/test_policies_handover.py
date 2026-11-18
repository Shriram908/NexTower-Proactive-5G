from dataclasses import replace

import pytest

from nextower.handover import Controller
from nextower.models import (
    Blocker,
    Decision,
    HandoverState,
    LinkSample,
    PositionSample,
    State,
    Tower,
)
from nextower.policies import A3, Context, Nearest, Strongest
from nextower.predictor import forecast, known_geometry
from nextower.proactive import PredictivePolicy


def link(id, quality, usable=True):
    return LinkSample(0, "v", id, 10, False, quality, usable)


def context(t=0, a=-80, b=-75):
    return Context(
        PositionSample(t, "v", 0, 0, 10, 0),
        (Tower("B", (10, 0)), Tower("A", (-10, 0))),
        (link("B", b), link("A", a)),
    )


def test_t08_t09_strongest_and_ties():
    state = HandoverState(State.ATTACHED, "A")
    assert Strongest().decide(context(), state).target == "B"
    assert Strongest().decide(context(a=-75, b=-75), state).target == "A"
    assert Nearest().decide(context(), state).target == "A"


def test_t10_a3_candidate_reset(cfg):
    policy, state = A3(cfg.handover), HandoverState(State.ATTACHED, "A")
    assert policy.decide(context(0), state).target is None
    assert policy.decide(context(0.5, b=-79), state).target is None
    assert state.candidate is None
    assert policy.decide(context(1), state).target is None
    assert policy.decide(context(1.5), state).target is None
    assert policy.decide(context(2), state).target == "B"


@pytest.mark.parametrize("dt", [0.25, 0.5, 1.0])
def test_t11_ttt_uses_elapsed_seconds(cfg, dt):
    policy, state = A3(replace(cfg.handover, ttt_s=1)), HandoverState(State.ATTACHED, "A")
    for i in range(round(1 / dt)):
        assert policy.decide(context(i * dt), state).target is None
    assert policy.decide(context(1), state).target == "B"


def test_a3_requires_strict_margin(cfg):
    policy = A3(replace(cfg.handover, ttt_s=0))
    assert policy.decide(context(b=-77), HandoverState(State.ATTACHED, "A")).target is None


def test_t12_dwell_prevents_immediate_return(cfg):
    c = Controller(replace(cfg.handover, switch_delay_s=0, min_dwell_s=2), "v", "strongest", "A")
    links = {"A": link("A", -80), "B": link("B", -75)}
    c.request(2, Decision("B", "test"), links)
    assert c.state.serving == "B"
    c.request(2.5, Decision("A", "return"), links)
    assert c.state.serving == "B" and c.state.pending is None
    c.request(4, Decision("A", "return"), links)
    assert c.state.serving == "A"


def test_t13_delay_and_single_pending(cfg):
    c = Controller(replace(cfg.handover, switch_delay_s=1, min_dwell_s=0), "v", "strongest", "A")
    links = {"A": link("A", -80), "B": link("B", -75)}
    c.request(0, Decision("B", "test"), links)
    c.request(0.25, Decision("A", "ignored during switching"), links)
    c.settle(0.5, links)
    assert c.state.state == State.SWITCHING and c.state.serving == "A"
    assert not any(e.status == "success" for e in c.events)
    c.settle(1, links)
    assert c.state.serving == "B" and c.state.pending is None
    assert [e.status for e in c.events] == ["attempted", "success"]


def test_t21_disconnected_recovers_and_no_usable_stays_disconnected(cfg):
    c = Controller(cfg.handover, "v", "a3")
    c.settle(0, {})
    assert c.state.state == State.DISCONNECTED
    c.settle(1, {"A": link("A", -80)})
    assert c.state.serving == "A"
    c.settle(2, {"A": link("A", -120, False)})
    assert c.state.state == State.DISCONNECTED and c.state.serving is None
    c.settle(3, {"B": link("B", -75)})
    assert c.state.serving == "B"


@pytest.mark.parametrize("old_viable", [True, False])
def test_t22_failed_or_deactivated_target(cfg, old_viable):
    c = Controller(replace(cfg.handover, min_dwell_s=0), "v", "a3", "A")
    c.request(0, Decision("B", "test"), {"A": link("A", -80), "B": link("B", -75)})
    c.settle(1, {"A": link("A", -80, old_viable)})
    assert any(e.status == "failed" for e in c.events)
    assert not any(e.status == "success" for e in c.events)
    assert c.state.pending is None
    assert c.state.state == (State.ATTACHED if old_viable else State.DISCONNECTED)


def test_rejected_unknown_candidate_and_incomplete_switch(cfg):
    c = Controller(replace(cfg.handover, min_dwell_s=0), "v", "nearest", "A")
    links = {"A": link("A", -80), "B": link("B", -75)}
    c.request(0, Decision("C", "unavailable"), links)
    assert c.events[-1].status == "rejected"
    c.request(0, Decision("B", "test"), links)
    c.finish(0.5)
    assert c.events[-1].status == "incomplete"


def test_t14_forecasts_ignore_future_noise_and_schedules(cfg):
    sample = PositionSample(10, "car_01", 100, 0, 10, 0)
    base = (sample, cfg.vehicles[0], cfg.towers)
    future = Blocker("future", (110, 1, 120, 20), 11, 13)
    active = Blocker("active", (130, 1, 150, 30), 9, 12)
    geometry = known_geometry((active, future), 10)
    assert geometry == (Blocker("active", active.bounds_m),)
    a = forecast(*base, geometry, cfg.channel, cfg.predictive, 0.5, 42)
    b = forecast(
        *base, geometry, replace(cfg.channel, shadowing_std_db=999), cfg.predictive, 0.5, 999
    )
    assert a == b  # location_noise=0 and forecast shadowing is zero, regardless of seed.
    with pytest.raises(ValueError, match="sanitized"):
        forecast(*base, (future,), cfg.channel, cfg.predictive, 0.5, 42)


def test_predictive_score_and_current_feasibility(cfg):
    settings = replace(cfg.predictive, weight_switch=0, score_margin=0)
    policy = PredictivePolicy(settings, replace(cfg.handover, ttt_s=0))
    ctx = replace(context(), forecasts=(("A", (link("A", -100, False),)), ("B", (link("B", -70),))))
    state = HandoverState(State.ATTACHED, "A")
    assert policy.scores(ctx, state)["B"] == pytest.approx(0.35 * (50 / 80))
    assert policy.decide(ctx, state).target == "B"
    assert (
        policy.decide(replace(ctx, links=(link("A", -80), link("B", -120, False))), state).target
        is None
    )
