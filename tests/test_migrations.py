import sqlite3
import tempfile
from pathlib import Path
from database.migrate import migrate


def test_migrate_legacy_v1_database():
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/'test.db'
        with sqlite3.connect(db) as c:
            c.executescript('''
            CREATE TABLE schema_version(version INTEGER PRIMARY KEY, applied_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE events(id INTEGER PRIMARY KEY AUTOINCREMENT,series TEXT,race_date TEXT,track TEXT,track_type TEXT,data_rate REAL,notes TEXT,source_file TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT,UNIQUE(series,race_date,track));
            CREATE TABLE observations(id INTEGER PRIMARY KEY AUTOINCREMENT,event_id INTEGER NOT NULL,report_row INTEGER,car_number TEXT,team TEXT,vector TEXT,last_lap_vec INTEGER,last_lap_ts INTEGER,diff_laps INTEGER,missing_pre REAL,missing_post REAL,diff_pre_post REAL,missing_points_percent REAL,data_coverage REAL,rt2_percent REAL,rt2_tracking REAL,rt20_percent REAL,rt20_sol_good_percent REAL,diff_percent REAL,avg_l1as REAL,avg_l2as REAL,avg_l5as REAL,camera_flag INTEGER DEFAULT 0,camera_360_flag INTEGER DEFAULT 0,notes TEXT,original_values_json TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT,updated_by TEXT,UNIQUE(event_id,car_number,vector));
            CREATE TABLE camera_assignments(id INTEGER PRIMARY KEY AUTOINCREMENT,observation_id INTEGER NOT NULL,slot_number INTEGER NOT NULL,camera_serial TEXT,camera_position TEXT,notes TEXT,updated_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_by TEXT,UNIQUE(observation_id,slot_number));
            CREATE TABLE imports(id INTEGER PRIMARY KEY AUTOINCREMENT,source_file TEXT,file_hash TEXT UNIQUE,status TEXT,rows_read INTEGER DEFAULT 0,rows_inserted INTEGER DEFAULT 0,rows_skipped INTEGER DEFAULT 0,message TEXT,imported_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT,entity_type TEXT,entity_id INTEGER,field_name TEXT,old_value TEXT,new_value TEXT,changed_by TEXT,reason TEXT,action TEXT DEFAULT 'update',changed_at TEXT DEFAULT CURRENT_TIMESTAMP);
            INSERT INTO schema_version(version) VALUES(1);
            INSERT INTO events(series,race_date,track) VALUES('NCS','2026-05-24','Charlotte');
            ''')
        result=migrate(db,make_backup=False)
        with sqlite3.connect(db) as c:
            assert c.execute("select count(*) from events").fetchone()[0]==1
            assert c.execute("select 1 from sqlite_master where type='table' and name='analysis_runs'").fetchone()
            assert c.execute("select max(version) from schema_version").fetchone()[0]==3
        assert result['to_version']==3
