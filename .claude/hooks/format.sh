#!/usr/bin/env bash
# PostToolUse (Edit|Write|MultiEdit): format the file Claude just touched.
# Never blocks: formatting failures are silent so they can't stall a session.
set -uo pipefail

input="$(cat)"
file="$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); print((d.get("tool_input") or {}).get("file_path",""))' 2>/dev/null)"
[ -n "$file" ] && [ -f "$file" ] || exit 0

root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
common="$(cd "$root" && git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"
main_root="${common%/.git}"

find_bin() { # prefer this worktree's venv, then the main checkout's venv, then PATH
  for c in "$root/.venv/bin/$1" "$main_root/.venv/bin/$1" "$root/node_modules/.bin/$1"; do
    [ -x "$c" ] && { echo "$c"; return; }
  done
  command -v "$1" 2>/dev/null
}

case "$file" in
  *.py)
    ruff="$(find_bin ruff)"
    if [ -n "$ruff" ]; then
      "$ruff" format --quiet "$file" >/dev/null 2>&1
      "$ruff" check --fix --quiet "$file" >/dev/null 2>&1
    fi
    ;;
  *.js|*.jsx|*.ts|*.tsx|*.css|*.html|*.json|*.md|*.yml|*.yaml)
    prettier="$(find_bin prettier)"
    [ -n "$prettier" ] && "$prettier" --write --log-level silent "$file" >/dev/null 2>&1
    ;;
esac
exit 0
