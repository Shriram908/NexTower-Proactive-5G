"""A toy log-distance power proxy, explicitly not a calibrated 5G PHY."""

import hashlib
import math
import random

from .config import Channel
from .geometry import distance, is_blocked
from .models import Blocker, LinkSample, PositionSample, Tower


def keyed_normal(seed: int, *keys: object) -> float:
    """Independent deterministic Gaussian draw, unaffected by traversal/policy order."""
    digest = hashlib.sha256(repr((seed, *keys)).encode()).digest()
    return random.Random(int.from_bytes(digest[:16], "big")).gauss(0, 1)


def observe(
    sample: PositionSample,
    tower: Tower,
    blockers: tuple[Blocker, ...],
    channel: Channel,
    seed: int,
    *,
    forecast: bool = False,
) -> LinkSample:
    d = max(distance(sample.xy, tower.xy_m), channel.d0_m)
    blocked = is_blocked(sample.xy, tower.xy_m, blockers, sample.time_s)
    loss = channel.pl0_db + 10 * channel.pathloss_exponent * math.log10(d / channel.d0_m)
    shadow = (
        0.0
        if forecast
        else channel.shadowing_std_db
        * keyed_normal(seed, "radio", sample.vehicle_id, tower.id, round(sample.time_s, 10))
    )
    quality = (
        tower.tx_power_dbm
        + channel.tx_gain_dbi
        + channel.rx_gain_dbi
        - loss
        - (channel.blocker_penalty_db if blocked else 0)
        + shadow
    )
    return LinkSample(
        sample.time_s,
        sample.vehicle_id,
        tower.id,
        d,
        blocked,
        quality,
        tower.enabled and quality >= channel.min_rx_dbm,
    )
