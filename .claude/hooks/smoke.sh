#!/usr/bin/env bash
# Stop hook: when Claude finishes a turn, run the fast smoke tests.
# On failure, exit 2 so Claude sees the output and keeps working.
# Skips when nothing changed, when no venv exists yet, or on a hook-triggered re-stop (prevents loops).
set -uo pipefail

input="$(cat)"
active="$(printf '%s' "$input" | python3 -c 'import json,sys; print(str(json.load(sys.stdin).get("stop_hook_active", False)).lower())' 2>/dev/null)"
[ "$active" = "true" ] && exit 0

root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$root" || exit 0

# Only run if code changed (tracked edits or new files) in api/, tests/, or web/.
if git rev-parse --git-dir >/dev/null 2>&1; then
  changed="$(git status --porcelain -- api tests web requirements.txt 2>/dev/null)"
  [ -z "$changed" ] && exit 0
fi

common="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"
main_root="${common%/.git}"
py=""
for c in "$root/.venv/bin/python" "$main_root/.venv/bin/python"; do
  [ -x "$c" ] && { py="$c"; break; }
done
[ -z "$py" ] && exit 0   # run `make setup` to enable

to=(); command -v timeout >/dev/null && to=(timeout 75)   # macOS has no `timeout` by default
out="$(LLM_PROVIDER=mock "${to[@]}" "$py" -m pytest -q -x --no-header -p no:cacheprovider tests 2>&1)"
status=$?
if [ $status -ne 0 ]; then
  {
    echo "Smoke tests FAILED (Stop hook). Fix before finishing:"
    echo "$out" | tail -n 40
  } >&2
  exit 2
fi
exit 0
