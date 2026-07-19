#!/usr/bin/env bash
set -Eeuo pipefail
PATCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${1:-$HOME/Documents/GitHub/BSI_SMT}"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "ERROR: Git repository not found at $REPO_DIR" >&2
  exit 1
fi

BACKUP="$REPO_DIR/data/backups/source-v3.1.1-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
for item in app database docs tests README.md VERSION CHANGELOG.md requirements.txt Dockerfile docker-compose.yml; do
  [[ -e "$REPO_DIR/$item" ]] && cp -a "$REPO_DIR/$item" "$BACKUP/"
done

rsync -a \
  --exclude='.git' \
  --exclude='data/*.db' \
  --exclude='data/uploads' \
  --exclude='data/archive' \
  --exclude='data/backups' \
  "$PATCH_DIR/" "$REPO_DIR/"

chmod +x "$REPO_DIR"/*.sh "$REPO_DIR"/update "$REPO_DIR"/scripts/*.sh "$REPO_DIR"/installer/*.sh

echo
printf 'BSI SMT v3.1.1 copied to: %s\n' "$REPO_DIR"
printf 'Source backup created at: %s\n' "$BACKUP"
echo "Publish with:"
echo "  cd '$REPO_DIR'"
echo "  ./push_dashboard_to_github.sh"
