#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
sudo docker compose build
sudo docker compose run --rm app python -m database.migrate
sudo docker compose up -d
sudo docker compose exec -T app python - <<'PY'
import sqlite3
with sqlite3.connect('data/bsi_smt_v2.db') as c:
    print('Schema version:', c.execute('select max(version) from schema_version').fetchone()[0])
    print('analysis_runs:', bool(c.execute("select 1 from sqlite_master where type='table' and name='analysis_runs'").fetchone()))
PY
