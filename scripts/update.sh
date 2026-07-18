#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CALLING_USER="${SUDO_USER:-$USER}"
USER_HOME="$(getent passwd "$CALLING_USER" | cut -d: -f6)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

info(){ printf '\n[BSI SMT] %s\n' "$*"; }
fail(){ printf '\n[BSI SMT] ERROR: %s\n' "$*" >&2; exit 1; }

command -v sudo >/dev/null 2>&1 || fail "sudo is required."
command -v git >/dev/null 2>&1 || fail "git is required."
command -v docker >/dev/null 2>&1 || fail "Docker is required."
[[ -d "$ROOT/.git" ]] || fail "This directory is not a Git clone: $ROOT"
[[ -f "$ROOT/.env" ]] || fail "Missing $ROOT/.env. Run installer/install.sh first."

cd "$ROOT"
info "Preparing writable data and backup directories"
sudo mkdir -p "$ROOT/data/backups" "$ROOT/data/archive" "$ROOT/data/imports"
sudo chown -R "$CALLING_USER:$CALLING_USER" "$ROOT/data"
sudo chmod -R u+rwX "$ROOT/data"

info "Backing up the current database"
DB_FOUND=0
for DB in "$ROOT/data"/*.db "$ROOT/data"/*.sqlite "$ROOT/data"/*.sqlite3; do
  [[ -f "$DB" ]] || continue
  cp -a "$DB" "$ROOT/data/backups/$(basename "$DB").$TIMESTAMP.bak"
  DB_FOUND=1
done
[[ "$DB_FOUND" -eq 1 ]] || echo "No SQLite database found yet; continuing."
cp -a "$ROOT/.env" "$ROOT/data/backups/env.$TIMESTAMP.bak"

info "Saving local configuration"
ENV_TMP="$(mktemp)"
cp "$ROOT/.env" "$ENV_TMP"
trap 'rm -f "$ENV_TMP"' EXIT

info "Downloading the latest release from GitHub"
git fetch origin main
git reset --hard origin/main
cp "$ENV_TMP" "$ROOT/.env"
chmod +x installer/*.sh scripts/*.sh update 2>/dev/null || true

info "Stopping the current application"
sudo docker compose down

info "Running database migrations in a temporary container"
sudo docker compose build --no-cache
sudo docker compose run --rm app python -m database.migrate

info "Starting the updated application"
sudo docker compose up -d


info "Verifying database schema"
sudo docker compose exec -T app python - <<'PY'
import sqlite3
from pathlib import Path
db=Path("data/bsi_smt_v2.db")
with sqlite3.connect(db) as c:
    tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
required={"events","observations","imports","analysis_runs"}
missing=required-tables
if missing:
    raise SystemExit("Missing database tables: "+", ".join(sorted(missing)))
print("Database schema verified; analysis_runs is present.")
PY

info "Repairing data ownership after Docker startup"
sudo chown -R "$CALLING_USER:$CALLING_USER" "$ROOT/data"
sudo chmod -R u+rwX "$ROOT/data"

HOSTNAME_NAME="$(grep -E '^HOSTNAME_NAME=' "$ROOT/.env" | cut -d= -f2- || true)"
HOSTNAME_NAME="${HOSTNAME_NAME:-BSISMTDASH}"
LOGIN_URL="http://${HOSTNAME_NAME,,}.local:8000/login"

info "Recreating desktop and application launchers"
mkdir -p "$USER_HOME/Desktop" "$USER_HOME/.local/share/applications"
for FILE in "$USER_HOME/Desktop/BSI-SMT.desktop" "$USER_HOME/.local/share/applications/BSI-SMT.desktop"; do
  cat > "$FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=BSI SMT
Comment=Open BSI SMT login
Exec=xdg-open $LOGIN_URL
Icon=$ROOT/app/static/bsi-smt-dashboard-icon.png
Terminal=false
Categories=Engineering;Utility;
DESKTOP
  chmod +x "$FILE"
done
sudo chown "$CALLING_USER:$CALLING_USER" \
  "$USER_HOME/Desktop/BSI-SMT.desktop" \
  "$USER_HOME/.local/share/applications/BSI-SMT.desktop"

info "Installing the bsi-update command"
sudo tee /usr/local/bin/bsi-update >/dev/null <<COMMAND
#!/usr/bin/env bash
exec "$ROOT/scripts/update.sh" "\$@"
COMMAND
sudo chmod +x /usr/local/bin/bsi-update

info "Waiting for the login page"
READY=0
for _ in $(seq 1 30); do
  CODE="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/login || true)"
  if [[ "$CODE" == "200" || "$CODE" == "303" ]]; then READY=1; break; fi
  sleep 2
done

if [[ "$READY" -ne 1 ]]; then
  sudo docker compose ps
  sudo docker compose logs --tail=80
  fail "The container started, but the login page did not become ready."
fi

info "Update complete"
echo "Open: $LOGIN_URL"
echo "Future updates: bsi-update"
