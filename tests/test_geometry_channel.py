import math
from dataclasses import replace

import pytest

from handoverai.channel import keyed_normal, observe
from handoverai.geometry import intersects_rectangle, is_blocked
from handoverai.models import Blocker, PositionSample, Tower


@pytest.mark.parametrize("a,b,bounds,expected", [
    ((0, 0), (10, 0), (4, -1, 6, 1), True),
    ((0, 0), (10, 0), (4, 2, 6, 3), False),
    ((0, 0), (10, 0), (4, 0, 6, 1), True),
    ((0, 0), (4, 0), (4, 0, 6, 1), True),
    ((0, 0), (0, 0), (-1, -1, 1, 1), True),
    ((0, 0), (0, 0), (1, 1, 2, 2), False),
    ((10, 0), (0, 0), (4, -1, 6, 1), True),
    ((5, -5), (5, 5), (4, -1, 6, 1), True),
])
def test_t03_t04_closed_geometry(a, b, bounds, expected):
    assert intersects_rectangle(a, b, bounds) is expected


def test_t05_zero_distance(cfg):
    p = PositionSample(0, "v", 0, 0, 0, 0)
    link = observe(p, Tower("A", (0, 0)), (), cfg.channel, 42)
    assert link.distance_m == cfg.channel.d0_m
    assert math.isfinite(link.rx_proxy_dbm)


def test_t06_activation_window():
    blocker = Blocker("bus", (4, -1, 6, 1), 2, 4)
    assert not is_blocked((0, 0), (10, 0), (blocker,), 1.99)
    assert is_blocked((0, 0), (10, 0), (blocker,), 2)
    assert not is_blocked((0, 0), (10, 0), (blocker,), 4)


def test_channel_equation_blockage_and_disabled(cfg):
    p = PositionSample(0, "v", 0, 0, 0, 0)
    tower = Tower("A", (10, 0))
    clear = observe(p, tower, (), cfg.channel, 42)
    blocked = observe(p, tower, (Blocker("b", (4, -1, 6, 1)),), cfg.channel, 42)
    assert clear.rx_proxy_dbm == pytest.approx(30 - 60 - 22)
    assert blocked.rx_proxy_dbm == pytest.approx(clear.rx_proxy_dbm - cfg.channel.blocker_penalty_db)
    assert not observe(p, replace(tower, enabled=False), (), cfg.channel, 42).usable


def test_keyed_randomness_is_repeatable_and_seed_sensitive():
    assert keyed_normal(42, "a") == keyed_normal(42, "a")
    assert keyed_normal(42, "a") != keyed_normal(43, "a")
    assert keyed_normal(42, "a") != keyed_normal(42, "b")
