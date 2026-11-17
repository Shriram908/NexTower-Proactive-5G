import json
import sqlite3
from dataclasses import replace

import pytest

from handoverai.config import from_dict
from handoverai.engine import prepare_world, simulate
from handoverai.metrics import calculate, paired_summary
from handoverai.models import Tower
from handoverai.storage import (batch_directory, list_runs, persist_database, read_csv,
                                write_run)


def metrics(result, cfg):
    return calculate(result.timeseries, result.events, cfg.simulation.dt_s,
                      cfg.handover.pingpong_window_s)


def test_t07_no_towers_is_total_outage(cfg):
    cfg = replace(cfg, towers=())
    r = simulate(cfg, "predictive")
    m = metrics(r, cfg)
    assert m["outage_fraction"] == 1 and m["handover_count"] == 0
    assert m["mean_quality_proxy_dbm"] is None
    assert all(row["serving_tower_id"] is None for row in r.timeseries)


def test_t08_identical_towers_never_pingpong(cfg):
    cfg = replace(cfg, towers=(Tower("B", (100, 0)), Tower("A", (100, 0))), blockers=())
    for name in cfg.policies:
        r = simulate(cfg, name)
        assert metrics(r, cfg)["handover_count"] == 0
        assert {row["serving_tower_id"] for row in r.timeseries} == {"A"}


def test_t17_zero_and_one_outage_exact_denominators(cfg):
    cfg = replace(cfg, towers=(Tower("A", (0, 0), 100),), blockers=())
    m = metrics(simulate(cfg, "strongest"), cfg)
    assert m["outage_fraction"] == 0 and m["worst_outage_episode_s"] == 0
    assert m["coverage_fraction"] == 1 and m["quality_sample_count"] == cfg.ticks
    m = metrics(simulate(replace(cfg, towers=()), "strongest"), cfg)
    assert m["outage_seconds"] == cfg.simulation.duration_s
    assert m["outage_episode_lengths_s"] == [cfg.simulation.duration_s]


def test_t18_single_tick_and_empty(cfg):
    cfg = replace(cfg, simulation=replace(cfg.simulation, duration_s=.5))
    assert metrics(simulate(cfg, "a3"), cfg)["observed_steps"] == 1
    with pytest.raises(ValueError, match="at least"):
        calculate([], [], .5, 10)
    with pytest.raises(ValueError, match="no observations"):
        prepare_world(cfg, ())


def test_episode_boundaries_and_pingpong_counted_per_return():
    rows = [{"time_s": i*.5, "vehicle_id": "v", "outage": outage,
             "state": "ATTACHED", "serving_quality_dbm": -80}
            for i, outage in enumerate([True, True, False, True, False, True])]
    events = [{"time_s": t, "vehicle_id": "v", "status": "success",
               "from_tower": a, "to_tower": b} for t, a, b in
              [(0, "A", "B"), (1, "B", "A"), (2, "A", "B"), (20, "B", "A")]]
    m = calculate(rows, events, .5, 10)
    assert m["outage_fraction"] == pytest.approx(4/6)
    assert m["outage_episode_lengths_s"] == [1.0, .5, .5]
    assert m["pingpong_count"] == 2 and m["handover_count"] == 4


def test_multivehicle_denominator_and_episode_separation(cfg):
    second = replace(cfg.vehicles[0], id="car_02")
    cfg = replace(cfg, vehicles=(*cfg.vehicles, second), towers=())
    m = metrics(simulate(cfg, "nearest"), cfg)
    assert m["observed_steps"] == 2 * cfg.ticks
    assert m["observed_vehicle_seconds"] == 180
    assert m["outage_episode_lengths_s"] == [90, 90]


def test_t20_output_contract_and_unique_paths(cfg, tmp_path):
    cfg = replace(cfg, simulation=replace(cfg.simulation, duration_s=5))
    world = prepare_world(cfg)
    batch = batch_directory(cfg, tmp_path)
    assert batch != batch_directory(cfg, tmp_path)
    for name in cfg.policies:
        path = write_run(cfg, simulate(cfg, name, world), batch, tmp_path / "db.sqlite3")
        assert {p.name for p in path.iterdir()} == {
            "timeseries.csv", "links.csv", "handovers.csv", "metrics.json", "manifest.json", "config.yaml"}
        manifest = json.loads((path / "manifest.json").read_text())
        assert manifest["config_hash"] == cfg.digest and manifest["seed"] == cfg.seed
        assert json.loads((path / "metrics.json").read_text()) == calculate(
            read_csv(path / "timeseries.csv"), read_csv(path / "handovers.csv"), .5, 10)
        with pytest.raises(FileExistsError):
            write_run(cfg, simulate(cfg, name, world), batch)
    assert len(list_runs(tmp_path / "db.sqlite3")) == 4
    with sqlite3.connect(tmp_path / "db.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 40
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_database_duplicate_insert_rolls_back(cfg, tmp_path):
    r = simulate(cfg, "strongest")
    path = write_run(cfg, r, batch_directory(cfg, tmp_path), tmp_path / "db.sqlite3")
    manifest = json.loads((path / "manifest.json").read_text())
    with pytest.raises(sqlite3.IntegrityError):
        persist_database(tmp_path / "db.sqlite3", manifest, metrics(r, cfg), r)
    assert len(list_runs(tmp_path / "db.sqlite3")) == 1


def test_paired_bootstrap_constant_effect():
    summary = paired_summary([-.1]*10)
    assert summary["mean_delta"] == pytest.approx(-.1)
    assert summary["ci95_low"] == pytest.approx(-.1)
    assert summary["ci95_high"] == pytest.approx(-.1)
    with pytest.raises(ValueError):
        paired_summary([])


def test_state_invariants_across_all_policies(cfg):
    for name in cfg.policies:
        r = simulate(cfg, name)
        attempts = {}
        for event in r.events:
            if event["status"] == "attempted":
                attempts[event["vehicle_id"]] = event
                assert event["from_tower"] != event["to_tower"]
            if event["status"] == "success":
                attempt = attempts.pop(event["vehicle_id"])
                assert event["time_s"] - attempt["time_s"] >= cfg.handover.switch_delay_s
        assert all(row["state"] == "SWITCHING" or row["pending_tower_id"] is None
                   for row in r.timeseries)


def test_disabling_all_towers_via_yaml_is_supported(data):
    for tower in data["towers"]:
        tower["enabled"] = False
    cfg = from_dict(data)
    assert metrics(simulate(cfg, "nearest"), cfg)["outage_fraction"] == 1
