PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS events(
 id INTEGER PRIMARY KEY AUTOINCREMENT,series TEXT,race_date TEXT,track TEXT,track_type TEXT,
 data_rate REAL,notes TEXT,source_file TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT,UNIQUE(series,race_date,track));
CREATE TABLE IF NOT EXISTS observations(
 id INTEGER PRIMARY KEY AUTOINCREMENT,event_id INTEGER NOT NULL,report_row INTEGER,car_number TEXT,
 team TEXT,vector TEXT,last_lap_vec INTEGER,last_lap_ts INTEGER,diff_laps INTEGER,
 missing_pre REAL,missing_post REAL,diff_pre_post REAL,missing_points_percent REAL,
 data_coverage REAL,rt2_percent REAL,rt2_tracking REAL,rt20_percent REAL,
 rt20_sol_good_percent REAL,diff_percent REAL,avg_l1as REAL,avg_l2as REAL,avg_l5as REAL,
 camera_flag INTEGER DEFAULT 0,camera_360_flag INTEGER DEFAULT 0,notes TEXT,
 original_values_json TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT,updated_by TEXT,
 FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE,
 UNIQUE(event_id,car_number,vector));
CREATE TABLE IF NOT EXISTS camera_assignments(
 id INTEGER PRIMARY KEY AUTOINCREMENT,observation_id INTEGER NOT NULL,slot_number INTEGER NOT NULL,
 camera_serial TEXT,camera_position TEXT,notes TEXT,updated_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_by TEXT,
 FOREIGN KEY(observation_id) REFERENCES observations(id) ON DELETE CASCADE,
 UNIQUE(observation_id,slot_number));
CREATE TABLE IF NOT EXISTS imports(
 id INTEGER PRIMARY KEY AUTOINCREMENT,source_file TEXT,file_hash TEXT UNIQUE,status TEXT,
 rows_read INTEGER DEFAULT 0,rows_inserted INTEGER DEFAULT 0,rows_skipped INTEGER DEFAULT 0,
 message TEXT,imported_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS audit_log(
 id INTEGER PRIMARY KEY AUTOINCREMENT,entity_type TEXT,entity_id INTEGER,field_name TEXT,
 old_value TEXT,new_value TEXT,changed_by TEXT,reason TEXT,action TEXT DEFAULT 'update',
 changed_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE VIEW IF NOT EXISTS v_dashboard AS
SELECT COUNT(*) observations,COUNT(DISTINCT event_id) events,COUNT(DISTINCT camera_serial) cameras,
ROUND(AVG(rt2_tracking),2) avg_rt2,
SUM(CASE WHEN rt2_tracking<95 THEN 1 ELSE 0 END) failures_below_95
FROM observations LEFT JOIN camera_assignments ON camera_assignments.observation_id=observations.id;
