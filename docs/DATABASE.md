# SQLite database guide

Every `simulate` command creates `runs/results.sqlite3` unless `--output`, `--database` or
`--no-database` changes this. With `--output runs/demo`, the default database is
`runs/demo/results.sqlite3`. No database server, credentials, migrations service or Homebrew
package is required: Python includes SQLite. Schema version is stored as `PRAGMA user_version=1`.
`src/handoverai/storage.py:SCHEMA` is the authoritative DDL.

| Table | Key | Purpose |
|---|---|---|
| runs | run_id | scenario, policy, seed, config hash, manifest/metrics JSON |
| observations | run_id, time_s, vehicle_id | position, association, serving proxy, outage, state |
| links | run_id, time_s, vehicle_id, tower_id | per-tower proxy, blocked and usable flags |
| events | run_id, event_index | attachment, loss, attempt, success, failure and incomplete events |

All child tables reference runs with cascading delete. Writes enable foreign-key enforcement;
one transaction stores a run and all its rows. Duplicate IDs fail instead of overwriting data.
Runs are indexed by scenario/policy/seed. Simulations on the same scenario get unique directories
and UUIDs, so repeated experiments coexist.

```sh
python -m handoverai db --database runs/results.sqlite3
sqlite3 runs/results.sqlite3 '.tables'
sqlite3 runs/results.sqlite3 'PRAGMA integrity_check;'
sqlite3 runs/results.sqlite3 'PRAGMA foreign_key_check;'
sqlite3 -header -column runs/results.sqlite3 \
  'SELECT scenario, policy, seed, json_extract(metrics_json, "$.outage_fraction") AS outage FROM runs;'
```

The macOS `sqlite3` command is optional. The package CLI and Python's `sqlite3` module can inspect
the same database if the system command is unavailable. The generated example database at
`data/demo.sqlite3` is included in the submission archive; production-sized run databases and
all `.sqlite3` files are excluded from Git by default. Regenerate the example from the documented
demo commands. A diagram or claimed connection to PostgreSQL is unnecessary for this local tool.
