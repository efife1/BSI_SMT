#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="${BSI_SMT_REPO:-$HOME/Documents/GitHub/BSI_SMT}"
VERSION_FILE="$REPO_DIR/VERSION"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "ERROR: Git repository not found at: $REPO_DIR" >&2
  echo "Set a different path with:" >&2
  echo "  BSI_SMT_REPO=/path/to/BSI_SMT ./push_to_github.sh" >&2
  exit 1
fi

cd "$REPO_DIR"

REMOTE="$(git remote get-url origin 2>/dev/null || true)"
if [[ "$REMOTE" != *"github.com/efife1/BSI_SMT"* ]]; then
  echo "ERROR: origin does not point to efife1/BSI_SMT." >&2
  echo "Current origin: ${REMOTE:-not configured}" >&2
  exit 1
fi

VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
TAG="v$VERSION"

echo "Repository: $REPO_DIR"
echo "Version:    $VERSION"
echo "Remote:     $REMOTE"

git fetch origin main

if ! git merge-base --is-ancestor origin/main HEAD; then
  echo "ERROR: GitHub contains commits not present in this local copy." >&2
  echo "Review them with: git log --oneline --left-right HEAD...origin/main" >&2
  exit 1
fi

python3 -m compileall -q app database tests
while IFS= read -r -d '' file; do bash -n "$file"; done < <(find . -path './.git' -prune -o -type f -name '*.sh' -print0)

git add -A
if git diff --cached --quiet; then
  echo "No changes to commit. Pushing current main branch."
else
  git commit -m "BSI SMT $VERSION - Excel enrichment import"
fi

git push origin main

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Tag $TAG already exists; it was not changed."
else
  git tag -a "$TAG" -m "BSI SMT $VERSION"
  git push origin "$TAG"
fi

echo "Published BSI SMT $VERSION to GitHub."
echo "Update the Raspberry Pi with: bsi-update"
