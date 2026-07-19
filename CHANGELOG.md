# Changelog

## 3.1.1

- Added top-five camera serial, vector, and car-number panels to the main dashboard.
- Added series, low-RT2 threshold, and minimum-sample dashboard controls.
- Rankings use the existing transparent recurring-offender evidence score.
- Added direct links from each dashboard factor to its Evidence Explorer history.
- Added dashboard-ranking tests and a GitHub publishing script.

## 3.1.0

- Added Excel XLSX/XLSM enrichment import.
- Added safe matching by series, date, track, car, and vector.
- Added camera serial and position import into race assignments.
- Added reconciliation summaries and conflict preservation.
- Added sortable Equipment Analysis columns.
- Improved the per-race four-camera assignment editor.
- Added `push_to_github.sh` for the Mac GitHub workflow.
- Replaced the README with complete installation and operating documentation.

## 3.0.0

- Added filename-based NCS, NCTS, and NOAPS classification.
- Added strict separation of analytics by series.
- Added recurring offender analysis for vectors, cars, camera serials, pairwise combinations, and three-way vector/car/camera combinations.
- Added event-adjusted comparisons, recurring failure-race counts, evidence scores, and calculation display.
- Added Evidence Explorer race history for every offender and combination.
- Added automatic schema migration 003 with analysis indexes and release tracking.
- Added rollback-safe `bsi-update` with backups, health checks, login-launcher repair, and automatic rollback.

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
