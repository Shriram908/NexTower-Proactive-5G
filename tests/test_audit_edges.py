from dataclasses import replace

import pytest

from nextower.config import from_dict, load_config
from nextower.engine import simulate
from nextower.mobility import synthetic_trace
from nextower.storage import revision


@pytest.mark.parametrize("value", [True, 1.0, "1"])
def test_schema_version_is_an_integer(data, value):
    data["schema_version"] = value
    with pytest.raises(ValueError, match="schema_version"):
        from_dict(data)


def test_duration_cannot_round_to_empty_run(data):
    data["simulation"].update(duration_s=1e-10, dt_s=1)
    with pytest.raises(ValueError, match="duration"):
        from_dict(data)


@pytest.mark.parametrize("value", [False, 0, 123, ""])
def test_initial_tower_requires_valid_id_or_none(data, value):
    data["vehicles"][0]["initial_tower_id"] = value
    with pytest.raises(ValueError, match="initial_tower_id"):
        from_dict(data)


def test_bad_record_errors_are_actionable(data):
    data["towers"] = [None]
    with pytest.raises(ValueError, match="mapping"):
        from_dict(data)


@pytest.mark.parametrize("value", [True, 7, []])
def test_trace_path_type_is_validated(data, value):
    data["simulation"]["trace_file"] = value
    with pytest.raises(ValueError, match="trace_file"):
        from_dict(data)


def test_inactive_vehicles_do_not_generate_observations(cfg, data):
    inactive = replace(cfg.vehicles[0], id="parked", active=False)
    mixed = replace(cfg, vehicles=(cfg.vehicles[0], inactive))
    assert synthetic_trace(mixed) == synthetic_trace(cfg)
    assert simulate(mixed, "strongest").timeseries == simulate(cfg, "strongest").timeseries
    data["vehicles"][0]["active"] = False
    with pytest.raises(ValueError, match="active"):
        from_dict(data)
    data["vehicles"][0]["active"] = "yes"
    with pytest.raises(ValueError, match="active"):
        from_dict(data)


def test_invalid_override_yaml_is_actionable():
    from conftest import ROOT

    with pytest.raises(ValueError, match="invalid YAML override"):
        load_config(ROOT / "configs/blocked_corridor.yaml", ["seed=["])


def test_source_provenance_is_stable():
    a, b = revision(), revision()
    assert a["source_sha256"] == b["source_sha256"]
    assert len(a["source_sha256"]) == 64
    assert a["code_commit"] is not None


def test_no_towers_report_remains_readable(cfg, tmp_path):
    from nextower.reporting import build_report
    from nextower.storage import batch_directory, write_run

    cfg = replace(cfg, towers=(), simulation=replace(cfg.simulation, duration_s=1))
    batch = batch_directory(cfg, tmp_path / "runs")
    write_run(cfg, simulate(cfg, "predictive"), batch)
    assert build_report(batch, tmp_path / "report").is_file()


def test_benchmark_manifest_is_not_misread_as_a_simulation(tmp_path):
    from nextower.reporting import collect

    (tmp_path / "manifest.json").write_text('{"kind":"experiment_suite"}')
    with pytest.raises(ValueError, match="no simulation runs"):
        collect(tmp_path)


def test_benchmark_rejects_zero_seeds(cfg, tmp_path):
    from nextower.experiments import benchmark

    with pytest.raises(ValueError, match="seeds"):
        benchmark(cfg, 0, "quick", tmp_path / "benchmark")
