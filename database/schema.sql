-- Compatibility bootstrap. The application uses database/migrate.py for versioned migrations.
CREATE TABLE IF NOT EXISTS schema_version(
 version INTEGER PRIMARY KEY,
 applied_at TEXT DEFAULT CURRENT_TIMESTAMP
);
