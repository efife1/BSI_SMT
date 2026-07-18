#!/usr/bin/env bash
set -Eeuo pipefail

CREATE_TAG=false
FORCE_PUSH=false

for arg in "$@"; do
  case "$arg" in
    --tag) CREATE_TAG=true ;;
    --force) FORCE_PUSH=true ;;
    -h|--help)
      cat <<'HELP'
BSI SMT release helper

Usage:
  ./release.sh [--tag] [--force]

Options:
  --tag     Create and push an annotated v<VERSION> Git tag.
  --force   Push main using --force-with-lease.
  -h        Show this help.
HELP
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo
echo "=========================================="
echo " BSI SMT GitHub Release"
echo "=========================================="
echo "Project: $PROJECT_DIR"

command -v git >/dev/null 2>&1 || { echo "ERROR: Git is not installed." >&2; exit 1; }

if [[ ! -d .git ]]; then
  echo "ERROR: This folder is not a Git repository." >&2
  echo "Run once:"
  echo "  git init"
  echo "  git branch -M main"
  echo "  git remote add origin https://github.com/efife1/BSI_SMT.git"
  exit 1
fi

[[ -f VERSION ]] || { echo "ERROR: VERSION file was not found." >&2; exit 1; }
VERSION="$(tr -d '[:space:]' < VERSION)"
[[ -n "$VERSION" ]] || { echo "ERROR: VERSION is empty." >&2; exit 1; }
TAG="v${VERSION}"

CURRENT_BRANCH="$(git branch --show-current)"
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  echo "Switching from '$CURRENT_BRANCH' to main..."
  git switch main
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "ERROR: Git remote 'origin' is not configured." >&2
  echo "  git remote add origin https://github.com/efife1/BSI_SMT.git"
  exit 1
fi

REMOTE_URL="$(git remote get-url origin)"
echo "Version: $VERSION"
echo "Remote:  $REMOTE_URL"
echo

required_paths=(app installer scripts Dockerfile docker-compose.yml requirements.txt VERSION)
for required in "${required_paths[@]}"; do
  [[ -e "$required" ]] || { echo "ERROR: Missing required project item: $required" >&2; exit 1; }
done

echo "Checking shell scripts..."
while IFS= read -r -d '' shell_file; do
  bash -n "$shell_file"
done < <(find . -path './.git' -prune -o -type f -name '*.sh' -print0)

if command -v python3 >/dev/null 2>&1; then
  echo "Checking Python syntax..."
  python3 -m compileall -q app
fi

echo "Fetching origin/main..."
git fetch origin main

LOCAL_HEAD="$(git rev-parse HEAD)"
REMOTE_HEAD="$(git rev-parse origin/main)"
if ! git merge-base --is-ancestor "$REMOTE_HEAD" "$LOCAL_HEAD"; then
  if [[ "$FORCE_PUSH" != true ]]; then
    echo "ERROR: origin/main contains commits not present locally." >&2
    echo "Review with: git log --oneline --left-right main...origin/main"
    echo "Use --force only when intentionally replacing origin/main."
    exit 1
  fi
fi

echo "Staging changes..."
git add -A

if git diff --cached --quiet; then
  echo "No uncommitted changes found."
else
  COMMIT_MESSAGE="BSI SMT ${VERSION}"
  echo "Creating commit: $COMMIT_MESSAGE"
  git commit -m "$COMMIT_MESSAGE"
fi

echo "Pushing main..."
if [[ "$FORCE_PUSH" == true ]]; then
  git push --force-with-lease origin main
else
  git push origin main
fi

if [[ "$CREATE_TAG" == true ]]; then
  if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "Tag $TAG already exists locally."
  else
    echo "Creating annotated tag $TAG..."
    git tag -a "$TAG" -m "BSI SMT ${VERSION}"
  fi
  echo "Pushing tag $TAG..."
  git push origin "$TAG"
fi

echo
echo "=========================================="
echo " Release complete"
echo "=========================================="
echo "Version: $VERSION"
echo "Branch:  main"
[[ "$CREATE_TAG" == true ]] && echo "Tag:     $TAG"
echo
echo "Update the Raspberry Pi with:"
echo "  bsi-update"
