import csv
import json
from dataclasses import replace

import pytest

from handoverai.cli import main
from handoverai.engine import prepare_world, simulate
from handoverai.experiments import benchmark, variants
from handoverai.metrics import calculate
from handoverai.mobility import position_at, synthetic_trace
from handoverai.models import Vehicle
from handoverai.storage import batch_directory, write_run
from handoverai.traces import COLUMNS, export_trace, load_trace


def test_t15_exact_csv_reproducibility(cfg, tmp_path):
    a, b = batch_directory(cfg, tmp_path), batch_directory(cfg, tmp_path)
    for name in cfg.policies:
        p = write_run(cfg, simulate(cfg, name), a)
        q = write_run(cfg, simulate(cfg, name), b)
        for filename in ("timeseries.csv", "links.csv", "handovers.csv", "metrics.json"):
            assert (p / filename).read_bytes() == (q / filename).read_bytes()


def test_t16_policy_order_cannot_change_channel(cfg):
    cfg = replace(cfg, channel=replace(cfg.channel, shadowing_std_db=3))
    world = prepare_world(cfg)
    forward = {name: simulate(cfg, name, world) for name in cfg.policies}
    backward = {name: simulate(cfg, name, world) for name in reversed(cfg.policies)}
    assert forward == backward

    def radio(rows):
        return [{k: v for k, v in r.items() if k != "policy"} for r in rows]

    assert all(
        radio(forward[name].links) == radio(forward["nearest"].links) for name in cfg.policies
    )
    assert world == prepare_world(cfg)


def test_trace_roundtrip_replay_and_permanent_departure(cfg, tmp_path):
    path = tmp_path / "trace.csv"
    export_trace(cfg, path)
    samples = load_trace(path, cfg)
    assert samples == synthetic_trace(cfg)
    replay = replace(
        cfg, simulation=replace(cfg.simulation, mobility_backend="trace", trace_file=str(path))
    )
    assert simulate(replay, "predictive") == simulate(cfg, "predictive")
    shortened = samples[:10]
    r = simulate(cfg, "a3", prepare_world(cfg, shortened))
    assert len(r.timeseries) == 10
    with pytest.raises(FileExistsError):
        export_trace(cfg, path)


@pytest.mark.parametrize(
    "mutation", ["missing", "out_of_order", "unknown", "nan", "off_grid", "gap"]
)
def test_t19_bad_traces(cfg, tmp_path, mutation):
    path = tmp_path / "trace.csv"
    rows = [
        dict(zip(COLUMNS, [0, "car_01", 0, 0, 10, 0])),
        dict(zip(COLUMNS, [0.5, "car_01", 5, 0, 10, 0])),
    ]
    if mutation == "missing":
        rows = []
    elif mutation == "out_of_order":
        rows.reverse()
    elif mutation == "unknown":
        rows[0]["vehicle_id"] = "other"
    elif mutation == "nan":
        rows[0]["x_m"] = "NaN"
    elif mutation == "off_grid":
        rows[1]["time_s"] = 0.3
    elif mutation == "gap":
        rows[1]["time_s"] = 1
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="trace"):
        load_trace(path, cfg)


def test_route_turn_endpoint_stop():
    v = Vehicle("v", (0, 0), 2, ((0, 0), (10, 0), (10, 10)))
    assert position_at(v, 7.5).xy == (10, 5)
    assert position_at(v, 10).speed_mps == 0
    assert position_at(v, 20).xy == (10, 10)


def test_t23_report_reads_saved_traces_and_detects_tampering(cfg, tmp_path):
    from handoverai.reporting import build_report

    cfg = replace(cfg, simulation=replace(cfg.simulation, duration_s=3))
    batch = batch_directory(cfg, tmp_path / "runs")
    for name in cfg.policies:
        write_run(cfg, simulate(cfg, name), batch)
    report = build_report(batch, tmp_path / "report")
    assert report.is_file()
    assert len(list((report.parent / "figures").glob("*.png"))) == 4
    assert "__REPORT_DATA__" not in report.read_text()
    result = json.loads((report.parent / "data.json").read_text())[0]
    assert result["metrics"] == calculate(result["timeseries"], result["events"], 0.5, 10)
    metrics = batch / "a3" / "metrics.json"
    metrics.write_text("{}")
    with pytest.raises(ValueError, match="do not match"):
        build_report(batch, tmp_path / "other")


def test_cli_validate_simulate_db_and_error(cfg, tmp_path, capsys):
    from conftest import ROOT

    config = str(ROOT / "configs/blocked_corridor.yaml")
    assert main(["validate", "--config", config]) == 0
    assert "VALID" in capsys.readouterr().out
    assert (
        main(
            [
                "simulate",
                "--config",
                config,
                "--output",
                str(tmp_path),
                "--set",
                "simulation.duration_s=1",
            ]
        )
        == 0
    )
    assert main(["db", "--database", str(tmp_path / "results.sqlite3")]) == 0
    with pytest.raises(SystemExit) as e:
        main(["validate", "--config", config, "--set", "simulation.dt_s=0"])
    assert e.value.code == 2


def test_experiment_matrix_and_quick_end_to_end(cfg, tmp_path):
    assert {e for e, _, _ in variants(cfg, "full")} == {"E1", "E2", "E3", "E4", "E5", "E6", "F5"}
    cfg = replace(cfg, simulation=replace(cfg.simulation, duration_s=1))
    output = benchmark(cfg, 2, "quick", tmp_path / "benchmark")
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["evaluated_rows"] == 5 * 2 * 4
    assert (output / "paired.csv").is_file()
    assert (output / "figures/paired_outcomes.png").is_file()


def test_golden_blueprint_baseline(cfg):
    # Fixed blueprint fixture: protects state timing and outage-accounting semantics.
    result = simulate(cfg, "strongest")
    metrics = calculate(result.timeseries, result.events, 0.5, 10)
    assert metrics["observed_steps"] == 180
    assert metrics["handover_count"] == 3
    assert metrics["outage_seconds"] == 3
