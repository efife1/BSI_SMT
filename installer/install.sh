#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."&&pwd)"
exec 3</dev/tty
read -r -u 3 -p "Hostname [BSISMTDASH]: " H;H="${H:-BSISMTDASH}"
read -r -u 3 -p "Username [admin]: " U;U="${U:-admin}"
while true;do read -r -s -u 3 -p "Password: " P;echo;read -r -s -u 3 -p "Confirm password: " P2;echo;[[ "$P" == "$P2" && -n "$P" ]]&&break;echo "Passwords do not match.";done
sudo apt-get update;sudo apt-get install -y git curl ca-certificates avahi-daemon xdg-utils
command -v docker >/dev/null||curl -fsSL https://get.docker.com|sudo sh
sudo systemctl enable --now docker avahi-daemon
cd "$ROOT";sudo mkdir -p "$ROOT/data/backups" "$ROOT/data/archive" "$ROOT/data/imports";sudo chown -R "$USER:$USER" "$ROOT/data";umask 077;cat >.env <<EOF
APP_USERNAME=$U
APP_PASSWORD=$P
APP_PORT=8000
HOSTNAME_NAME=$H
EOF
sudo hostnamectl set-hostname "$H"
sudo docker compose build --no-cache
sudo docker compose up -d
sudo chown -R "$USER:$USER" "$ROOT/data"
HOME_DIR="$(getent passwd "$USER"|cut -d: -f6)";mkdir -p "$HOME_DIR/Desktop" "$HOME_DIR/.local/share/applications"
for F in "$HOME_DIR/Desktop/BSI-SMT.desktop" "$HOME_DIR/.local/share/applications/BSI-SMT.desktop";do cat >"$F" <<EOF
[Desktop Entry]
Type=Application
Name=BSI SMT
Comment=Open BSI SMT login
Exec=xdg-open http://${H,,}.local:8000/login
Icon=$ROOT/app/static/bsi-smt-dashboard-icon.png
Terminal=false
Categories=Engineering;Utility;
EOF
chmod +x "$F";done
chown -R "$USER":"$USER" "$HOME_DIR/Desktop/BSI-SMT.desktop" "$HOME_DIR/.local/share/applications/BSI-SMT.desktop" 2>/dev/null || true
sudo tee /usr/local/bin/bsi-update >/dev/null <<COMMAND
#!/usr/bin/env bash
exec "$ROOT/scripts/update.sh" "\$@"
COMMAND
sudo chmod +x /usr/local/bin/bsi-update
READY=0
for _ in $(seq 1 30);do CODE="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/login || true)";if [[ "$CODE" == "200" || "$CODE" == "303" ]];then READY=1;break;fi;sleep 2;done
[[ "$READY" -eq 1 ]] || { sudo docker compose logs --tail=80;echo "Application did not become ready." >&2;exit 1; }
echo "Open http://${H,,}.local:8000/login"
echo "Future updates: bsi-update"
