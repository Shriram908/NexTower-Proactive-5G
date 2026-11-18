"""Replay one immutable world through independent policy/controller instances."""

from dataclasses import asdict, dataclass

from .channel import observe
from .config import POLICIES, Config
from .handover import Controller
from .mobility import synthetic_trace
from .models import LinkSample, PositionSample, State
from .policies import A3, Context, Nearest, Strongest
from .predictor import forecast, known_geometry
from .proactive import PredictivePolicy


@dataclass(frozen=True)
class World:
    samples: tuple[PositionSample, ...]
    links: tuple[tuple[LinkSample, ...], ...]


@dataclass
class Result:
    policy: str
    timeseries: list[dict]
    links: list[dict]
    events: list[dict]


def prepare_world(cfg: Config, samples: tuple[PositionSample, ...] | None = None) -> World:
    if samples is None and cfg.simulation.mobility_backend != "synthetic":
        from .traces import load_trace

        samples = load_trace(cfg.simulation.trace_file, cfg)
    samples = samples if samples is not None else synthetic_trace(cfg)
    if not samples:
        raise ValueError("mobility source produced no observations")
    towers = sorted((t for t in cfg.towers if t.enabled), key=lambda t: t.id)
    return World(
        samples,
        tuple(
            tuple(observe(p, t, cfg.blockers, cfg.channel, cfg.seed) for t in towers)
            for p in samples
        ),
    )


def simulate(cfg: Config, policy_name: str, world: World | None = None) -> Result:
    if policy_name not in POLICIES:
        raise ValueError(f"unknown policy {policy_name!r}")
    world = world or prepare_world(cfg)
    policy = {
        "nearest": Nearest(),
        "strongest": Strongest(),
        "a3": A3(cfg.handover),
        "predictive": PredictivePolicy(cfg.predictive, cfg.handover),
    }[policy_name]
    vehicles = {v.id: v for v in cfg.vehicles}
    controllers = {
        v.id: Controller(cfg.handover, v.id, policy_name, v.initial_tower_id) for v in cfg.vehicles
    }
    rows, link_rows = [], []
    last_seen = {}
    for sample, observations in zip(world.samples, world.links, strict=True):
        c = controllers[sample.vehicle_id]
        links = {x.tower_id: x for x in observations}
        c.settle(sample.time_s, links)
        if c.state.state == State.ATTACHED:
            estimates = (
                forecast(
                    sample,
                    vehicles[sample.vehicle_id],
                    cfg.towers,
                    known_geometry(cfg.blockers, sample.time_s),
                    cfg.channel,
                    cfg.predictive,
                    cfg.simulation.dt_s,
                    cfg.seed,
                )
                if policy_name == "predictive"
                else {}
            )
            context = Context(sample, cfg.towers, observations, tuple(sorted(estimates.items())))
            c.request(sample.time_s, policy.decide(context, c.state), links)
        serving = links.get(c.state.serving)
        outage = c.state.state != State.ATTACHED or serving is None or not serving.usable
        rows.append(
            {
                **asdict(sample),
                "policy": policy_name,
                "serving_tower_id": c.state.serving,
                "pending_tower_id": c.state.pending,
                "serving_quality_dbm": serving.rx_proxy_dbm if serving else None,
                "outage": outage,
                "state": c.state.state.value,
            }
        )
        link_rows.extend({**asdict(x), "policy": policy_name} for x in observations)
        last_seen[sample.vehicle_id] = sample.time_s
    for vid, controller in controllers.items():
        if vid in last_seen:
            end = last_seen[vid] + cfg.simulation.dt_s
            if end < cfg.simulation.duration_s - 1e-9:
                controller.disappear(end)
            else:
                controller.finish(cfg.simulation.duration_s)
    events = [asdict(e) for c in controllers.values() for e in c.events]
    events.sort(key=lambda e: (e["time_s"], e["vehicle_id"]))
    return Result(policy_name, rows, link_rows, events)
