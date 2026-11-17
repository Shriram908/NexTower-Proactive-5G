"""Terminal commands with actionable errors and no hidden configuration mutation."""

import argparse
import json
import sqlite3
from pathlib import Path

from . import __version__
from .config import POLICIES, load_config
from .engine import prepare_world, simulate
from .storage import batch_directory, list_runs, write_run


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="HandoverAI synthetic handover research toolkit")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("validate", "Validate a versioned YAML scenario"),
        ("simulate", "Replay four policies and persist results"),
        ("export-trace", "Export canonical synthetic mobility"),
    ):
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--config", type=Path, required=True)
        sub.add_argument("--set", action="append", default=[], metavar="SECTION.KEY=VALUE")
        if name == "simulate":
            sub.add_argument("--policy", choices=("all", *POLICIES), default="all")
            sub.add_argument("--output", type=Path)
            sub.add_argument("--database", type=Path)
            sub.add_argument("--no-database", action="store_true")
        if name == "export-trace":
            sub.add_argument("--output", type=Path, required=True)
    report = commands.add_parser("report", help="Build figures and an offline HTML dashboard")
    report.add_argument("--runs", type=Path, required=True)
    report.add_argument("--output", type=Path, default=Path("reports/latest"))
    bench = commands.add_parser("benchmark", help="Run paired E1-E6 experiments and ablations")
    bench.add_argument("--config", type=Path, default=Path("configs/blocked_corridor.yaml"))
    bench.add_argument("--seeds", type=int, default=10)
    bench.add_argument("--suite", choices=("quick", "full"), default="full")
    bench.add_argument("--output", type=Path, default=Path("reports/benchmark"))
    bench.add_argument("--set", action="append", default=[], metavar="SECTION.KEY=VALUE")
    db = commands.add_parser("db", help="List stored runs (read-only)")
    db.add_argument("--database", type=Path, default=Path("runs/results.sqlite3"))
    return root


def main(argv: list[str] | None = None) -> int:
    root = parser()
    args = root.parse_args(argv)
    try:
        if args.command in ("validate", "simulate", "export-trace", "benchmark"):
            cfg = load_config(args.config, args.set)
        if args.command == "validate":
            print(
                f"VALID {cfg.scenario_id}: {cfg.ticks} ticks, {len(cfg.vehicles)} vehicle(s), "
                f"{len(cfg.towers)} towers; SHA256 {cfg.digest}"
            )
        elif args.command == "simulate":
            world = prepare_world(cfg)
            batch = batch_directory(cfg, args.output)
            database = (
                None
                if args.no_database
                else args.database or Path(args.output or cfg.output_dir) / "results.sqlite3"
            )
            names = cfg.policies if args.policy == "all" else [args.policy]
            for name in names:
                path = write_run(cfg, simulate(cfg, name, world), batch, database)
                m = json.loads((path / "metrics.json").read_text())
                print(
                    f"{name:10s} outage={m['outage_fraction']:.4f} "
                    f"handovers={m['handover_count']} -> {path}"
                )
            print(f"RUNS={batch}")
        elif args.command == "report":
            from .reporting import build_report

            print(build_report(args.runs, args.output))
        elif args.command == "benchmark":
            from .experiments import benchmark

            print(benchmark(cfg, args.seeds, args.suite, args.output))
        elif args.command == "export-trace":
            from .traces import export_trace

            export_trace(cfg, args.output)
            print(args.output)
        elif args.command == "db":
            print(json.dumps(list_runs(args.database), indent=2))
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        root.exit(2, f"handoverai: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
