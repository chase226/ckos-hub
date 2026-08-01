#!/usr/bin/env bash
#
# CKOS Hub — rebuild Mission Control, encrypt it, push to GitHub Pages.
#
#   ./deploy.sh            rebuild from live CKOS state, then deploy
#   ./deploy.sh --quiet    same, no output unless something fails (for launchd)
#
# Safe to re-run. After the first time it is just a rebuild and a push.

set -euo pipefail

REPO_NAME="ckos-hub"
GH="$(command -v gh || echo "${HOME}/.local/bin/gh")"

cd "$(dirname "$0")"

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1
say () { [ "$QUIET" -eq 1 ] || echo "$@"; }

if [ ! -x "$GH" ]; then
  echo "GitHub CLI not found." >&2
  exit 1
fi

if ! "$GH" auth status >/dev/null 2>&1; then
  echo "Not signed in to GitHub. Run: gh auth login" >&2
  exit 1
fi

# ------------------------------------------------------------ rebuild --
# Always regenerate from live CKOS state so the deployed page is never stale.
say "Rebuilding Mission Control..."
python3 build.py >/dev/null

for blob in data/hub.enc.json data/library.enc.json; do
  if [ ! -s "$blob" ]; then
    echo "build.py produced no ciphertext for $blob. Refusing to deploy." >&2
    exit 1
  fi
done

# Guard: never let a plaintext render reach the repo.
if git ls-files --error-unmatch mission-control.html >/dev/null 2>&1; then
  echo "REFUSING: a plaintext mission-control.html is tracked by git." >&2
  exit 1
fi
if [ -f .passcode ] && git ls-files --error-unmatch .passcode >/dev/null 2>&1; then
  echo "REFUSING: .passcode is tracked by git." >&2
  exit 1
fi

# ----------------------------------------------------------------- git --
if [ ! -d .git ]; then
  say "Initializing repo..."
  git init -q
  git branch -M main
fi

git add -A
if git diff --cached --quiet; then
  say "Nothing changed. Already current."
  exit 0
fi

git -c user.name="CKOS" -c user.email="chase@thekincergroup.com" \
    commit -q -m "Refresh Mission Control $(date +%Y-%m-%d\ %H:%M)"

if ! git remote get-url origin >/dev/null 2>&1; then
  say "Creating GitHub repo..."
  "$GH" repo create "$REPO_NAME" --public --source=. --remote=origin >/dev/null
fi

git push -q -u origin main

# --------------------------------------------------------------- pages --
OWNER="$("$GH" api user --jq .login)"
if ! "$GH" api "repos/$OWNER/$REPO_NAME/pages" >/dev/null 2>&1; then
  say "Turning on GitHub Pages..."
  "$GH" api -X POST "repos/$OWNER/$REPO_NAME/pages" \
    -f "source[branch]=main" -f "source[path]=/" >/dev/null
fi

say ""
say "Live: https://${OWNER}.github.io/${REPO_NAME}/"
say "First deploy takes a minute or two to go green."
