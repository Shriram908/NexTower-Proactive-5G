"""Inspectable CSV/JSON artifacts plus transactional, normalized SQLite persistence."""

import csv
import hashlib
import importlib.metadata
import json
import platform
import sqlite3
import subprocess
import uuid
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import __version__
from .config import Config
from .engine import Result
from .metrics import calculate
from .models import HandoverEvent, LinkSample

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
 run_id TEXT PRIMARY KEY, scenario TEXT NOT NULL, policy TEXT NOT NULL, seed INTEGER NOT NULL,
 config_hash TEXT NOT NULL, manifest_json TEXT NOT NULL, metrics_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS observations (
 run_id TEXT REFERENCES runs(run_id) ON DELETE CASCADE,
 time_s REAL NOT NULL, vehicle_id TEXT NOT NULL, x_m REAL, y_m REAL,
 serving_tower_id TEXT, serving_quality_dbm REAL, outage INTEGER NOT NULL, state TEXT NOT NULL,
 PRIMARY KEY(run_id, time_s, vehicle_id));
CREATE TABLE IF NOT EXISTS links (
 run_id TEXT REFERENCES runs(run_id) ON DELETE CASCADE, time_s REAL NOT NULL,
 vehicle_id TEXT NOT NULL, tower_id TEXT NOT NULL, rx_proxy_dbm REAL NOT NULL,
 blocked INTEGER NOT NULL, usable INTEGER NOT NULL,
 PRIMARY KEY(run_id, time_s, vehicle_id, tower_id));
CREATE TABLE IF NOT EXISTS events (
 run_id TEXT REFERENCES runs(run_id) ON DELETE CASCADE, event_index INTEGER NOT NULL,
 time_s REAL NOT NULL, vehicle_id TEXT NOT NULL, from_tower TEXT, to_tower TEXT,
 status TEXT NOT NULL, reason TEXT NOT NULL, completed_s REAL,
 PRIMARY KEY(run_id, event_index));
CREATE INDEX IF NOT EXISTS runs_scenario_policy ON runs(scenario, policy, seed);
PRAGMA user_version=1;
"""


def write_csv(path: Path, rows: list[dict], columns: list[str] | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def revision() -> dict:
    package = Path(__file__).resolve().parent
    source = hashlib.sha256()
    for path in sorted(p for p in package.iterdir() if p.suffix in (".py", ".html")):
        source.update(path.name.encode() + b"\0" + path.read_bytes() + b"\0")
    metadata = {"source_sha256": source.hexdigest()}
    try:
        root = Path(__file__).resolve().parents[2]
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.DEVNULL, text=True
        ).strip()
        dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=root, stderr=subprocess.DEVNULL, text=True
            ).strip()
        )
        source_dirty = bool(
            subprocess.check_output(
                [
                    "git",
                    "status",
                    "--porcelain",
                    "--",
                    "src",
                    "pyproject.toml",
                    "requirements.lock",
                ],
                cwd=root,
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        )
        return {
            **metadata,
            "code_commit": commit,
            "working_tree_dirty": dirty,
            "source_tree_dirty": source_dirty,
        }
    except (subprocess.SubprocessError, OSError):
        return {
            **metadata,
            "code_commit": None,
            "working_tree_dirty": None,
            "source_tree_dirty": None,
        }


def batch_directory(cfg: Config, output: str | Path | None = None) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = Path(output or cfg.output_dir) / cfg.scenario_id / f"{stamp}-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def persist_database(db_path: Path, manifest: dict, metrics: dict, result: Result):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        if db.execute("PRAGMA user_version").fetchone()[0] not in (0, 1):
            raise ValueError("unsupported database schema version")
        db.executescript(SCHEMA)
        rid = manifest["run_id"]
        db.execute(
            "INSERT INTO runs VALUES (?,?,?,?,?,?,?)",
            (
                rid,
                manifest["scenario_id"],
                result.policy,
                manifest["seed"],
                manifest["config_hash"],
                json.dumps(manifest),
                json.dumps(metrics),
            ),
        )
        db.executemany(
            "INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?)",
            [
                (
                    rid,
                    r["time_s"],
                    r["vehicle_id"],
                    r["x_m"],
                    r["y_m"],
                    r["serving_tower_id"],
                    r["serving_quality_dbm"],
                    int(r["outage"]),
                    r["state"],
                )
                for r in result.timeseries
            ],
        )
        db.executemany(
            "INSERT INTO links VALUES (?,?,?,?,?,?,?)",
            [
                (
                    rid,
                    r["time_s"],
                    r["vehicle_id"],
                    r["tower_id"],
                    r["rx_proxy_dbm"],
                    int(r["blocked"]),
                    int(r["usable"]),
                )
                for r in result.links
            ],
        )
        db.executemany(
            "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)",
            [
                (
                    rid,
                    i,
                    e["time_s"],
                    e["vehicle_id"],
                    e["from_tower"],
                    e["to_tower"],
                    e["status"],
                    e["reason"],
                    e["completed_s"],
                )
                for i, e in enumerate(result.events)
            ],
        )


def write_run(cfg: Config, result: Result, batch: Path, db_path: Path | None = None) -> Path:
    provenance = revision()
    directory = batch / result.policy
    directory.mkdir(exist_ok=False)
    write_csv(directory / "timeseries.csv", result.timeseries)
    write_csv(
        directory / "links.csv", result.links, [f.name for f in fields(LinkSample)] + ["policy"]
    )
    write_csv(directory / "handovers.csv", result.events, [f.name for f in fields(HandoverEvent)])
    # Re-read exactly the serialized data used by reporting, avoiding two metric pipelines.
    metrics = calculate(
        read_csv(directory / "timeseries.csv"),
        read_csv(directory / "handovers.csv"),
        cfg.simulation.dt_s,
        cfg.handover.pingpong_window_s,
    )
    manifest = {
        "schema_version": 1,
        "run_id": uuid.uuid4().hex,
        "scenario_id": cfg.scenario_id,
        "seed": cfg.seed,
        "policy": result.policy,
        "config_hash": cfg.digest,
        "backend": f"{cfg.simulation.mobility_backend}/proxy",
        "simulation_backend": "python",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        **provenance,
        "versions": {
            "python": platform.python_version(),
            "handoverai": __version__,
            "PyYAML": importlib.metadata.version("PyYAML"),
            "matplotlib": importlib.metadata.version("matplotlib"),
            "numpy": importlib.metadata.version("numpy"),
            "sqlite": sqlite3.sqlite_version,
        },
        "platform": platform.platform(),
    }
    write_json(directory / "metrics.json", metrics)
    write_json(directory / "manifest.json", manifest)
    (directory / "config.yaml").write_text(yaml.safe_dump(cfg.to_dict(), sort_keys=False))
    if db_path is not None:
        persist_database(db_path, manifest, metrics, result)
    return directory


def list_runs(db_path: str | Path) -> list[dict]:
    path = Path(db_path)
    if not path.is_file():
        raise ValueError(f"database does not exist: {path}; run simulate first")
    with sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        return [
            dict(r)
            for r in db.execute(
                "SELECT run_id, scenario, policy, seed, config_hash FROM runs ORDER BY rowid DESC"
            )
        ]
