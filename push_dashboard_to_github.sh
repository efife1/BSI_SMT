#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="${1:-$HOME/Documents/GitHub/BSI_SMT}"
VERSION_EXPECTED="3.1.1"

cd "$REPO_DIR" || { echo "Repository not found: $REPO_DIR" >&2; exit 1; }
[[ -d .git ]] || { echo "Not a Git repository: $REPO_DIR" >&2; exit 1; }
[[ -f VERSION ]] || { echo "VERSION file is missing." >&2; exit 1; }

VERSION="$(tr -d '[:space:]' < VERSION)"
[[ "$VERSION" == "$VERSION_EXPECTED" ]] || {
  echo "Expected VERSION $VERSION_EXPECTED but found $VERSION" >&2
  exit 1
}

REMOTE="$(git remote get-url origin 2>/dev/null || true)"
[[ "$REMOTE" == *"efife1/BSI_SMT"* ]] || {
  echo "Unexpected GitHub remote: ${REMOTE:-not configured}" >&2
  exit 1
}

CURRENT_BRANCH="$(git branch --show-current)"
[[ "$CURRENT_BRANCH" == "main" ]] || git switch main

echo "Checking Bash scripts..."
while IFS= read -r -d '' file; do bash -n "$file"; done < <(find . -path './.git' -prune -o -type f -name '*.sh' -print0)

echo "Checking Python syntax..."
python3 -m compileall -q app database tests

echo "Running tests..."
if command -v pytest >/dev/null 2>&1; then
  pytest -q
else
  echo "pytest is not installed; syntax checks passed, but automated tests were skipped."
fi

echo "Fetching origin/main..."
git fetch origin main
if ! git merge-base --is-ancestor origin/main HEAD; then
  echo "origin/main has commits not present locally. Pull/review them before publishing." >&2
  echo "Run: git log --oneline --left-right HEAD...origin/main" >&2
  exit 1
fi

git add -A
if git diff --cached --quiet; then
  echo "No changes to commit."
else
  git commit -m "BSI SMT 3.1.1 dashboard top RT2 factors"
fi

git push origin main
TAG="v$VERSION"
if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Tag $TAG already exists locally."
else
  git tag -a "$TAG" -m "BSI SMT $VERSION"
fi
if git ls-remote --exit-code --tags origin "refs/tags/$TAG" >/dev/null 2>&1; then
  echo "Tag $TAG already exists on GitHub."
else
  git push origin "$TAG"
fi

echo
printf 'Published BSI SMT %s to %s\n' "$VERSION" "$REMOTE"
echo "Update the Raspberry Pi with: bsi-update"
