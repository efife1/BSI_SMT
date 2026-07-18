CREATE INDEX IF NOT EXISTS idx_events_series ON events(series);
CREATE INDEX IF NOT EXISTS idx_events_series_date ON events(series,race_date);
CREATE INDEX IF NOT EXISTS idx_observations_vector ON observations(vector);
CREATE INDEX IF NOT EXISTS idx_observations_car ON observations(car_number);
CREATE INDEX IF NOT EXISTS idx_observations_rt2 ON observations(rt2_tracking);
CREATE INDEX IF NOT EXISTS idx_camera_assignments_serial ON camera_assignments(camera_serial);
CREATE TABLE IF NOT EXISTS analysis_settings(
 id INTEGER PRIMARY KEY CHECK(id=1),
 rt2_failure_threshold REAL NOT NULL DEFAULT 95.0,
 minimum_samples INTEGER NOT NULL DEFAULT 3,
 updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO analysis_settings(id) VALUES(1);
CREATE TABLE IF NOT EXISTS release_history(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 version TEXT NOT NULL,
 installed_at TEXT DEFAULT CURRENT_TIMESTAMP,
 status TEXT NOT NULL DEFAULT 'installed',
 notes TEXT
);
