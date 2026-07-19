# BSI SMT v3.1.0

BSI SMT is a Raspberry Pi-hosted RF performance analysis application for tracking RT2 performance by series, race, vector, car, camera serial, and camera position.

## v3.1.0 highlights

- PDF batch import for NCS, NCTS, and NOAPS race reports
- Excel enrichment import from `.xlsx` and `.xlsm` workbooks
- Safe matching by series, race date, track, car number, and vector
- Missing observation fields filled without erasing existing values
- Camera serial and camera position assignments added to each race observation
- Conflicting spreadsheet values preserved for review rather than overwriting the database
- Sortable Equipment Analysis columns
- Improved four-camera assignment editor for every race
- Series-wide recurring-offender and combination analysis
- Automatic database migrations, backups, updater verification, and rollback protection

## Application architecture

- FastAPI web application
- SQLite database
- Docker Compose deployment
- Raspberry Pi 5 host
- GitHub-based update workflow

Default URL:

```text
http://bsismtdash.local:8000/login
```

## Supported series

- NCS
- NCTS
- NOAPS

Every imported observation remains associated with its individual series. Series are not mixed during recurring-offender analysis.

## PDF imports

Open **Import Center**, select one or more PDF race reports, and select **Import selected files**.

The PDF filename must identify the series with `NCS`, `NCTS`, or `NOAPS`. PDF imports create race events and RT2/vector observations.

## Excel enrichment imports

The Import Center also accepts `.xlsx` and `.xlsm` workbooks. A workbook can contain sheets named:

- `NCS`
- `NCTS`
- `NOAPS`

The importer first matches spreadsheet rows against existing PDF observations using:

```text
Series + Race Date + Track + Car Number + Vector
```

When a matching event or observation is missing, the importer can create it from the spreadsheet. It can also fill these missing fields:

- Team
- Track type
- Last-lap vector
- Last-lap timing and scoring
- Lap difference
- Missing points before and after ERDP
- Missing-points percentage
- Data coverage
- RT2 percentage
- RT2 tracking
- RT20 values
- Difference percentage
- Average L1AS, L2AS, and L5AS
- Camera and 360-camera flags
- Notes
- Camera serial number
- Camera position

### Safe enrichment rules

- Blank spreadsheet cells never erase database values.
- Missing database values are filled automatically.
- Matching values are skipped.
- Conflicting values are retained in the database and counted in the reconciliation result.
- Camera rows are assigned to camera slots 1 through 4 in spreadsheet order.
- Rows marked `No Cameras` are not added as assignments.
- Reuploading the exact same file is blocked by its SHA-256 file hash.
- All applied changes are entered in the audit log with the reason `Excel enrichment import`.

PDFs should normally be imported first because they remain the primary RT2 source. However, v3.1 can create missing spreadsheet events and observations when the match keys are complete.

## Equipment Analysis sorting

On **Equipment Analysis**, select a group such as vector, car number, camera serial, or camera position. Click a column header to cycle through:

1. Ascending order
2. Descending order
3. Original analysis order

Numeric columns use numeric sorting.

## Camera assignments by race

Open **Events**, select a race, and enter up to four cameras for each observation. Each assignment stores:

- Camera serial number
- Camera position
- Camera notes

Assignments remain historically tied to that race, car, and vector. They are used by camera and combination trend analysis.

## Root-cause analysis

BSI SMT ranks recurring associations with low RT2 values. It evaluates factors including:

- Vector
- Car number
- Camera serial
- Camera position
- Camera + vector
- Camera + car
- Vector + car
- Camera + vector + car

The application presents evidence and trends. It does not claim that statistical association alone proves physical causation.

## Install on Raspberry Pi

Clone the repository:

```bash
git clone https://github.com/efife1/BSI_SMT.git ~/BSI_SMT
cd ~/BSI_SMT
chmod +x update scripts/*.sh installer/*.sh
./installer/install.sh
```

The installer creates the Docker application, initializes the database, and installs the `bsi-update` command.

## Updating the Raspberry Pi

```bash
bsi-update
```

The updater:

1. Backs up the database and environment settings.
2. Fetches the newest GitHub source.
3. Runs pending database migrations.
4. Rebuilds Docker.
5. Starts the application.
6. Verifies the login page and database schema.
7. Restores the previous release if verification fails.

## Publishing from the Mac

The expected local repository is:

```text
/Users/ep/Documents/GitHub/BSI_SMT
```

Publish the current version with:

```bash
cd ~/Documents/GitHub/BSI_SMT
chmod +x push_to_github.sh
./push_to_github.sh
```

The script validates the GitHub remote, checks Python and shell syntax, commits changes, pushes `main`, and creates the matching version tag.

## Database and backups

Default database:

```text
data/bsi_smt_v2.db
```

Manual backup:

```bash
cd ~/BSI_SMT
./scripts/backup.sh
```

Manual migration:

```bash
cd ~/BSI_SMT
./scripts/migrate.sh
```

Do not commit the live SQLite database, uploaded PDFs, archives, backups, or `.env` to GitHub.

## Troubleshooting

### Login redirects or Unauthorized

Open the login page directly:

```text
http://bsismtdash.local:8000/login
```

### Spreadsheet rows do not match

Confirm that the PDF observations already exist and that the workbook contains compatible values for series, date, track, car number, and vector. The importer tolerates a leading `#` and uniquely resolvable leading-zero differences in car numbers.

### View application status

```bash
cd ~/BSI_SMT
./scripts/status.sh
```

### View Docker logs

```bash
cd ~/BSI_SMT
sudo docker compose logs --tail=200 app
```

## Release workflow

```text
Mac repository
    ↓
push_to_github.sh
    ↓
GitHub main branch and version tag
    ↓
Raspberry Pi
    ↓
bsi-update
```

## License

See `LICENSE` and `THIRD_PARTY_NOTICES.md`.
