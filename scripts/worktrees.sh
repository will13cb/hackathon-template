#!/usr/bin/env bash
# Create one git worktree per workstream so parallel Claude sessions never edit the same files.
# Usage: scripts/worktrees.sh [name ...]      (default: frontend backend infra)
# Result: ../<repo>-<name> on branch feat/<name>. Run `claude` in each folder.
set -euo pipefail
root="$(git rev-parse --show-toplevel)"
repo="$(basename "$root")"
cd "$root"

git rev-parse --verify HEAD >/dev/null 2>&1 || { echo "✖ Make a first commit before creating worktrees."; exit 1; }
[ -n "$(git status --porcelain)" ] && echo "⚠ main has uncommitted changes; worktrees branch from the last commit."

names=("$@"); [ ${#names[@]} -eq 0 ] && names=(frontend backend infra)
declare -A lane=([frontend]="web/" [backend]="api/ + tests/" [infra]="deploy/ + Dockerfile")

for n in "${names[@]}"; do
  path="$(dirname "$root")/${repo}-${n}"
  if [ -d "$path" ]; then echo "• $path exists, skipping"; continue; fi
  if git show-ref --verify --quiet "refs/heads/feat/$n"; then
    git worktree add -q "$path" "feat/$n"
  else
    git worktree add -q "$path" -b "feat/$n"
  fi
  [ -f .env ] && cp .env "$path/.env"   # .env is gitignored, so copy it over
  echo "✓ $path  (feat/$n, owns ${lane[$n]:-see CLAUDE.md})"
done

cat <<EOF

Next, in one terminal per worktree:
  cd ../${repo}-<name> && make claude
The hooks share main's .venv automatically. Run 'make setup' in a worktree only if its deps differ.
Integrate with /sync (or: git -C $root merge feat/<name>). Remove with: git worktree remove ../${repo}-<name>
EOF
