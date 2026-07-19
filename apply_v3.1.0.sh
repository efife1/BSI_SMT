#!/usr/bin/env bash
set -Eeuo pipefail
PATCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${1:-$HOME/Documents/GitHub/BSI_SMT}"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "ERROR: Git repository not found at $REPO_DIR" >&2
  exit 1
fi

BACKUP="$REPO_DIR/data/backups/source-v3.1.0-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
for item in app database README.md VERSION CHANGELOG.md requirements.txt; do
  [[ -e "$REPO_DIR/$item" ]] && cp -a "$REPO_DIR/$item" "$BACKUP/"
done

rsync -a --exclude='.git' --exclude='data/*.db' --exclude='data/uploads' --exclude='data/archive' --exclude='data/backups' "$PATCH_DIR/" "$REPO_DIR/"
chmod +x "$REPO_DIR"/*.sh "$REPO_DIR"/update "$REPO_DIR"/scripts/*.sh "$REPO_DIR"/installer/*.sh

echo "BSI SMT v3.1.0 files copied to: $REPO_DIR"
echo "Source backup: $BACKUP"
echo "Publish with: cd '$REPO_DIR' && ./push_to_github.sh"
