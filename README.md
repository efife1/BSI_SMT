# BSI SMT v2.2

<p align="center"><img src="app/static/bsi-smt-dashboard-icon.png" width="280"></p>

A standalone Raspberry Pi web application for SMT tracking reports.

## Included

- PDF, Excel, and CSV importing
- NCS, NCTS, and NOAPS PDF extraction
- Dashboard
- Event manager
- Editable imported records
- Four camera assignments per car
- Audit-log database foundation
- SQLite storage
- Login
- Desktop launcher
- Backup and update scripts
- No Grafana dependency

## Install

After pushing this release to `efife1/BSI_SMT`:

```bash
cd ~
rm -rf ~/BSI_SMT
curl -fsSL https://raw.githubusercontent.com/efife1/BSI_SMT/main/installer/bootstrap.sh | bash
```

Open:

```text
http://bsismtdash.local:8000
```

## License

Original project code is MIT licensed. Dependencies retain their upstream licenses.

## RT2 analytics and root cause

Use `/analytics`, `/equipment`, and `/root-cause` after importing reports. The root-cause page separates strong evidence, possible contributors, and insufficient data.

## Updating an existing GitHub installation

After replacing your GitHub repository with this complete release, run:

```bash
cd ~/BSI_SMT
chmod +x scripts/update.sh
./scripts/update.sh
```

The updater backs up the database, pulls `main`, rebuilds the container, restarts the application, and repairs the desktop launcher so it opens `/login`.

## Batch PDF import

Open `/import`, select multiple PDFs, leave automatic analysis enabled, and click **Import selected PDFs**. Each file is committed independently.

## Calculation verification

The Root Cause page includes a calculation audit with event mean, event standard deviation, z-score substitution, Pearson correlation, p-value, 95% confidence interval, raw inputs, and the complete weighted evidence-score arithmetic.

## Easy updates

After v2.2.1 is installed, update from anywhere with:

```bash
bsi-update
```

You may also update from the repository with:

```bash
cd ~/BSI_SMT
./update
```

The updater repairs data-directory ownership, backs up the SQLite database and `.env`, pulls the current `main` branch, rebuilds Docker, recreates the `/login` launcher, and verifies that the login page responds.

## Database migrations

The application now upgrades existing databases automatically. The updater backs up the database, runs all pending migrations, verifies required tables, and only then starts the application.

To repair an installation manually:

```bash
cd ~/BSI_SMT
./scripts/migrate.sh
```
