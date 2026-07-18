#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CALLING_USER="${SUDO_USER:-$USER}"
USER_HOME="$(getent passwd "$CALLING_USER" | cut -d: -f6)"
TS="$(date +%Y%m%d_%H%M%S)"
info(){ printf '\n[BSI SMT] %s\n' "$*"; }
fail(){ printf '\n[BSI SMT] ERROR: %s\n' "$*" >&2; exit 1; }
cd "$ROOT"
command -v sudo >/dev/null || fail "sudo is required"
command -v git >/dev/null || fail "git is required"
command -v docker >/dev/null || fail "Docker is required"
[[ -d .git ]] || fail "This installation is not a Git clone"
[[ -f .env ]] || fail "Missing .env; run installer/install.sh"
OLD_COMMIT="$(git rev-parse HEAD)"
ENV_TMP="$(mktemp)"; cp .env "$ENV_TMP"
trap 'rm -f "$ENV_TMP"' EXIT
sudo mkdir -p data/backups data/archive data/uploads
sudo chown -R "$CALLING_USER:$CALLING_USER" data
chmod -R u+rwX data
info "Backing up configuration and databases"
cp -a .env "data/backups/env.$TS.bak"
for DB in data/*.db data/*.sqlite data/*.sqlite3; do
  [[ -f "$DB" ]] && cp -a "$DB" "data/backups/$(basename "$DB").$TS.bak"
done
info "Checking GitHub for the latest main branch"
git fetch origin main
NEW_COMMIT="$(git rev-parse origin/main)"
info "Updating $OLD_COMMIT -> $NEW_COMMIT"
git reset --hard "$NEW_COMMIT"
cp "$ENV_TMP" .env
chmod +x update scripts/*.sh installer/*.sh
rollback(){
  info "Update verification failed; rolling back to $OLD_COMMIT"
  sudo docker compose down || true
  git reset --hard "$OLD_COMMIT"
  cp "$ENV_TMP" .env
  sudo docker compose build --no-cache
  sudo docker compose up -d
  fail "Update rolled back. Existing data was preserved."
}
trap rollback ERR
info "Stopping current application"
sudo docker compose down
info "Building release"
sudo docker compose build --no-cache
info "Running automatic database migrations"
sudo docker compose run --rm app python -m database.migrate
info "Starting updated application"
sudo docker compose up -d
info "Waiting for login page"
READY=0
for _ in $(seq 1 45); do
  CODE="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/login || true)"
  [[ "$CODE" == "200" || "$CODE" == "303" ]] && READY=1 && break
  sleep 2
done
[[ "$READY" -eq 1 ]] || false
info "Running v3 health checks"
sudo docker compose exec -T app python - <<'PY'
import sqlite3
from pathlib import Path
with sqlite3.connect(Path('data/bsi_smt_v2.db')) as c:
    tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
    required={'events','observations','imports','analysis_runs','analysis_settings','release_history'}
    missing=required-tables
    if missing: raise SystemExit('Missing tables: '+', '.join(sorted(missing)))
print('Database and v3 schema verified.')
PY
trap - ERR
sudo chown -R "$CALLING_USER:$CALLING_USER" data
HOSTNAME_NAME="$(grep -E '^HOSTNAME_NAME=' .env | cut -d= -f2- || true)"; HOSTNAME_NAME="${HOSTNAME_NAME:-BSISMTDASH}"
LOGIN_URL="http://${HOSTNAME_NAME,,}.local:8000/login"
mkdir -p "$USER_HOME/Desktop" "$USER_HOME/.local/share/applications"
for FILE in "$USER_HOME/Desktop/BSI-SMT.desktop" "$USER_HOME/.local/share/applications/BSI-SMT.desktop"; do
cat > "$FILE" <<EOF
[Desktop Entry]
Type=Application
Name=BSI SMT
Comment=Open BSI SMT v3
Exec=xdg-open $LOGIN_URL
Icon=$ROOT/app/static/bsi-smt-dashboard-icon.png
Terminal=false
Categories=Engineering;Utility;
EOF
chmod +x "$FILE"
done
sudo chown "$CALLING_USER:$CALLING_USER" "$USER_HOME/Desktop/BSI-SMT.desktop" "$USER_HOME/.local/share/applications/BSI-SMT.desktop"
sudo tee /usr/local/bin/bsi-update >/dev/null <<EOF
#!/usr/bin/env bash
exec "$ROOT/scripts/update.sh" "\$@"
EOF
sudo chmod +x /usr/local/bin/bsi-update
info "BSI SMT v3 update complete"
echo "Open: $LOGIN_URL"
echo "Future updates: bsi-update"
