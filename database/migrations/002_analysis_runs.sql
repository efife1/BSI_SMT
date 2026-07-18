CREATE TABLE IF NOT EXISTS analysis_runs(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 event_id INTEGER,
 formula_version TEXT NOT NULL,
 source TEXT,
 results_json TEXT NOT NULL,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_event_id ON analysis_runs(event_id);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_created_at ON analysis_runs(created_at);
