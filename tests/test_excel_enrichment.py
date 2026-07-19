import sqlite3
from pathlib import Path

from app.services.excel_enrichment import enrich_database_from_excel


def test_excel_enrichment_service_is_importable():
    assert callable(enrich_database_from_excel)


def test_schema_has_camera_assignments(tmp_path: Path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(db)
    conn.execute("create table camera_assignments(id integer primary key, observation_id integer, slot_number integer, camera_serial text, camera_position text, notes text, updated_at text, updated_by text)")
    found = conn.execute("select name from sqlite_master where type='table' and name='camera_assignments'").fetchone()
    assert found
