import copy

import pytest

from handoverai.config import from_dict, load_config


@pytest.mark.parametrize("section,key,value", [
    ("simulation", "duration_s", 0), ("simulation", "duration_s", -1),
    ("simulation", "dt_s", 0), ("simulation", "dt_s", -0.5),
    ("predictive", "horizon_s", 0), ("predictive", "horizon_s", 0.7),
    ("channel", "d0_m", 0), ("channel", "shadowing_std_db", -1),
    ("channel", "min_rx_dbm", float("nan")), ("handover", "ttt_s", -1),
    ("simulation", "duration_s", True), ("road", "x_max_m", 0),
    ("predictive", "weight_switch", -0.1), ("channel", "tx_power_watts", 3),
])
def test_t01_invalid_numeric_and_units(data, section, key, value):
    data[section][key] = value
    with pytest.raises(ValueError):
        from_dict(data)


@pytest.mark.parametrize("key", ["towers", "vehicles", "blockers"])
def test_t02_duplicate_ids(data, key):
    data[key] = [data[key][0], data[key][0]]
    with pytest.raises(ValueError, match="unique"):
        from_dict(data)


def test_t02_unknown_initial_tower(data):
    data["vehicles"][0]["initial_tower_id"] = "unknown"
    with pytest.raises(ValueError, match="unknown"):
        from_dict(data)


@pytest.mark.parametrize("bounds", [[0, 0, 0, 2], [2, 0, 1, 1], [1, 2, 3], "wrong"])
def test_invalid_shapes(data, bounds):
    data["blockers"][0]["bounds_m"] = bounds
    with pytest.raises(ValueError, match="bounds_m"):
        from_dict(data)


def test_negative_speed_and_invalid_route(data):
    data["vehicles"][0]["speed_mps"] = -1
    with pytest.raises(ValueError, match="speed"):
        from_dict(data)
    data["vehicles"][0]["speed_mps"] = 1
    data["vehicles"][0]["path_xy_m"] = [(1, 0), (10, 0)]
    with pytest.raises(ValueError, match="first route"):
        from_dict(data)


@pytest.mark.parametrize("key,value", [("schema_version", 2), ("scenario_id", "../unsafe"),
    ("seed", -1), ("seed", True), ("policies", ["oracle"]), ("vehicles", [])])
def test_top_level_validation(data, key, value):
    data[key] = value
    with pytest.raises(ValueError):
        from_dict(data)


def test_roundtrip_hash_and_no_mutation(data):
    before = copy.deepcopy(data)
    c = from_dict(data)
    assert c.digest == from_dict(c.to_dict()).digest
    assert data == before


def test_overrides_and_bad_yaml(tmp_path):
    from conftest import ROOT
    c = load_config(ROOT / "configs/blocked_corridor.yaml", ["seed=7", "predictive.horizon_s=3"])
    assert c.seed == 7 and c.predictive.horizon_s == 3
    with pytest.raises(ValueError, match="override"):
        load_config(ROOT / "configs/blocked_corridor.yaml", ["typo.horizon_s=3"])
    bad = tmp_path / "bad.yaml"
    bad.write_text("[not, a, mapping]")
    with pytest.raises(ValueError, match="mapping"):
        load_config(bad)
