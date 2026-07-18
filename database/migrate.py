from __future__ import annotations

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = PROJECT_ROOT / "data" / "bsi_smt_v2.db"
MIGRATIONS_DIR = Path(__file__).with_name("migrations")


def _backup_database(db_path: Path) -> Path | None:
    if not db_path.exists() or db_path.stat().st_size == 0:
        return None
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"{db_path.name}.pre-migration-{datetime.now():%Y%m%d_%H%M%S}.bak"
    shutil.copy2(db_path, backup)
    return backup


def _ensure_version_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_version(
               version INTEGER PRIMARY KEY,
               applied_at TEXT DEFAULT CURRENT_TIMESTAMP
           )"""
    )


def current_version(conn: sqlite3.Connection) -> int:
    _ensure_version_table(conn)
    row = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()
    return int(row[0] or 0)


def available_migrations() -> list[tuple[int, Path]]:
    result: list[tuple[int, Path]] = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        prefix = path.stem.split("_", 1)[0]
        if prefix.isdigit():
            result.append((int(prefix), path))
    return result


def migrate(db_path: Path | str | None = None, *, make_backup: bool = True) -> dict:
    db = Path(db_path or os.getenv("BSI_SMT_DB", DEFAULT_DB))
    db.parent.mkdir(parents=True, exist_ok=True)
    backup = _backup_database(db) if make_backup else None
    applied: list[int] = []

    with sqlite3.connect(db) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        _ensure_version_table(conn)
        start = current_version(conn)
        for version, path in available_migrations():
            if version <= current_version(conn):
                continue
            sql = path.read_text(encoding="utf-8")
            try:
                conn.executescript("BEGIN IMMEDIATE;\n" + sql + f"\nINSERT OR IGNORE INTO schema_version(version) VALUES({version});\nCOMMIT;")
            except Exception:
                try:
                    conn.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise
            applied.append(version)

        # Defensive validation: these tables are required by the current application.
        required = {"events", "observations", "imports", "analysis_runs"}
        found = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = sorted(required - found)
        if missing:
            raise RuntimeError(f"Database migration incomplete; missing tables: {', '.join(missing)}")
        end = current_version(conn)

    return {
        "database": str(db),
        "from_version": start,
        "to_version": end,
        "applied": applied,
        "backup": str(backup) if backup else None,
    }


if __name__ == "__main__":
    result = migrate()
    print(f"Database: {result['database']}")
    print(f"Schema: {result['from_version']} -> {result['to_version']}")
    print(f"Applied: {result['applied'] or 'none'}")
    if result["backup"]:
        print(f"Backup: {result['backup']}")
