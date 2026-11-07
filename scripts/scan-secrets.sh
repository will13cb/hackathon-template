#!/usr/bin/env bash
# Scan the ENTIRE git history for secrets. Run before making the repo public.
# A deleted .env still lives in old commits; if this finds anything, ROTATE the key (don't just delete it).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if command -v gitleaks >/dev/null; then
  gitleaks git --redact -v .
elif command -v docker >/dev/null; then
  docker run --rm -v "$PWD:/repo" ghcr.io/gitleaks/gitleaks:latest git --redact -v /repo
else
  echo "Install gitleaks (https://github.com/gitleaks/gitleaks) or Docker, or enable GitHub secret scanning."
  exit 1
fi
echo "✅ No secrets found in history."
