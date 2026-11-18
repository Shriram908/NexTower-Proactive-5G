from pathlib import Path

import pytest

from nextower.config import load_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cfg():
    return load_config(ROOT / "configs/blocked_corridor.yaml")


@pytest.fixture
def data(cfg):
    return cfg.to_dict()
