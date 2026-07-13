#!/usr/bin/env bash
# Rename worker GitHub repos to the locked names, then refresh submodule URLs.
# Requires: valid `gh` auth with admin on private cuts-* repos
#   (repo scope / fine-grained: Administration + Contents on those repos).
# SSH-only access is not enough — GitHub rename is an HTTP API operation.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -F /dev/null -o IdentitiesOnly=yes -o IdentityFile=$HOME/.ssh/id_ed25519 -o IdentityFile=$HOME/.ssh/id_rsa -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$HOME/.ssh/known_hosts}"

if ! gh api user --jq .login >/dev/null; then
  echo "gh auth failed; run: gh auth login -h github.com" >&2
  exit 1
fi

rename_one() {
  local old="$1" new="$2"
  if gh api "repos/woragis/${new}" --jq .full_name >/dev/null 2>&1; then
    echo "already exists: woragis/${new}"
    return 0
  fi
  if ! gh api "repos/woragis/${old}" --jq .full_name >/dev/null 2>&1; then
    echo "missing source (or PAT cannot see private repo): woragis/${old}" >&2
    return 1
  fi
  echo "renaming woragis/${old} -> ${new}"
  gh repo rename "$new" --repo "woragis/${old}" --yes
}

rename_one cuts-worker-general cuts-worker-control
rename_one cuts-worker-treatment cuts-worker-plan
rename_one cuts-worker-render cuts-worker-ffmpeg
rename_one cuts-worker-notification cuts-worker-notify
rename_one render-remotion cuts-worker-visual

python3 - <<PY
from pathlib import Path
root = Path(${ROOT@Q})
text = (root / ".gitmodules").read_text()
repls = {
    "cuts-worker-general.git": "cuts-worker-control.git",
    "cuts-worker-treatment.git": "cuts-worker-plan.git",
    "cuts-worker-render.git": "cuts-worker-ffmpeg.git",
    "cuts-worker-notification.git": "cuts-worker-notify.git",
    "render-remotion.git": "cuts-worker-visual.git",
}
for a, b in repls.items():
    text = text.replace(a, b)
(root / ".gitmodules").write_text(text)
print("updated", root / ".gitmodules")
PY

cd "$ROOT"
git submodule sync --recursive

for pair in \
  "worker-control:cuts-worker-control" \
  "worker-plan:cuts-worker-plan" \
  "worker-ffmpeg:cuts-worker-ffmpeg" \
  "worker-notify:cuts-worker-notify" \
  "worker-visual:cuts-worker-visual"
do
  path="${pair%%:*}"
  repo="${pair##*:}"
  git -C "$ROOT/$path" remote set-url origin "git@github.com:woragis/${repo}.git"
  echo "origin -> $repo ($path)"
done

echo "Done. Commit .gitmodules when ready."
echo "Archive unused repos with: gh repo archive woragis/<repo> --yes"
