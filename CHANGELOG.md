# Changelog

## 2.2.1

- Fixed update failures when Docker-created data directories are owned by root.
- Added automatic ownership repair before and after container rebuilds.
- Added database and `.env` backups before every update.
- Added the `bsi-update` system command and root-level `./update` wrapper.
- Added login-page health verification before an installation or update reports success.
- Recreates the desktop launcher so it always opens `/login`.

## 2.2.0

- Added multi-PDF batch import with independent success, duplicate, and failure results.
- Added automatic analysis snapshots after import.
- Added event z-scores, Pearson p-values, 95% confidence intervals, transparent evidence scores, and a calculation audit.
- Fixed unauthenticated page routing so browser requests redirect to `/login`.
- Fixed desktop launcher and update script to open `/login`.
- Added a simple Git-based one-command update workflow.


## 2.1.0

- Added RT2 descriptive statistics, selectable failure threshold, correlations, event trends, equipment rankings, event-adjusted rankings, and explainable root-cause analysis.

## 2.0.0

- Rebuilt BSI SMT as a standalone FastAPI application.
- Removed required Grafana dependency.
- Added login, dashboard, imports, event manager, editing, and camera assignments.
- Added PDF/Excel/CSV ingestion and Raspberry Pi appliance installer.

## 2.2.2

- Added automatic, versioned SQLite database migrations.
- Added a pre-migration database backup.
- Added updater schema verification before reporting success.
- Added a defensive migration check before imports and analysis snapshots.
- Added `scripts/migrate.sh` for repairing an existing installation.
- Fixed `no such table: analysis_runs` when upgrading an older database.
