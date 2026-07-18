#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CALLING_USER="${SUDO_USER:-$USER}"
STAMP="$(date +%Y%m%d_%H%M%S)"
sudo mkdir -p "$ROOT/data/backups"
sudo chown -R "$CALLING_USER:$CALLING_USER" "$ROOT/data"
FOUND=0
for DB in "$ROOT/data"/*.db "$ROOT/data"/*.sqlite "$ROOT/data"/*.sqlite3; do
  [[ -f "$DB" ]] || continue
  cp -a "$DB" "$ROOT/data/backups/$(basename "$DB").$STAMP.bak"
  FOUND=1
done
[[ "$FOUND" -eq 1 ]] && echo "Database backup complete." || echo "No database found yet."
