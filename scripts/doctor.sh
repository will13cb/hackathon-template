#!/usr/bin/env bash
# Check that tools, auth and config are ready. Run the week before the event, and again at hour 0.
set -uo pipefail
cd "$(dirname "$0")/.."
ok()   { printf "  \033[32m✓\033[0m %s\n" "$*"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$*"; }
bad()  { printf "  \033[31m✗\033[0m %s\n" "$*"; }

echo "Tools"
for t in git python3 docker node npx claude make; do
  command -v "$t" >/dev/null && ok "$t" || bad "$t missing"
done
command -v uvx >/dev/null && ok "uv/uvx (needed for the AWS MCP server)" \
  || bad "uv missing: curl -LsSf https://astral.sh/uv/install.sh | sh"
command -v aws >/dev/null && ok "aws cli $(aws --version 2>&1 | cut -d' ' -f1)" || warn "aws cli missing (AWS track only)"
command -v gcloud >/dev/null && ok "gcloud" || warn "gcloud missing (Google track only)"
command -v gitleaks >/dev/null && ok "gitleaks" || warn "gitleaks missing (make scan falls back to Docker)"
[ -x .venv/bin/python ] && ok ".venv" || bad ".venv missing: make setup"
docker info >/dev/null 2>&1 && ok "docker daemon running" || warn "docker daemon not running (needed for deploy-aws)"

echo "Config (.env)"
[ -f .env ] && ok ".env present" || bad ".env missing: cp .env.example .env"
[[ "${SERVICE_NAME:-hack-app}" == hack-* ]] && ok "SERVICE_NAME=${SERVICE_NAME:-hack-app}" \
  || warn "SERVICE_NAME doesn't start with hack-, so the IAM policy won't match"

echo "AWS"
if command -v aws >/dev/null; then
  if id="$(AWS_PROFILE="${AWS_PROFILE:-hackathon}" aws sts get-caller-identity --query Arn --output text 2>/dev/null)"; then
    ok "profile ${AWS_PROFILE:-hackathon} → $id"
    AWS_PROFILE="${AWS_PROFILE:-hackathon}" aws iam get-role --role-name "${SERVICE_NAME:-hack-app}-lambda-role" >/dev/null 2>&1 \
      && ok "lambda role exists" || warn "lambda role missing: make aws-bootstrap (admin profile)"
  else
    bad "profile ${AWS_PROFILE:-hackathon} not authenticated (aws configure / aws sso login --profile ${AWS_PROFILE:-hackathon})"
  fi
fi

echo "Google Cloud"
if command -v gcloud >/dev/null; then
  acct="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null)"
  [ -n "$acct" ] && ok "gcloud account $acct" || bad "not logged in: gcloud auth login"
  gcloud auth application-default print-access-token >/dev/null 2>&1 && ok "ADC (for Vertex locally + MCP)" \
    || bad "no ADC: gcloud auth application-default login"
  [ -n "${GCP_PROJECT:-}" ] && ok "GCP_PROJECT=$GCP_PROJECT" || warn "GCP_PROJECT not set in .env"
fi

echo "Tests"
if [ -x .venv/bin/python ]; then
  LLM_PROVIDER=mock .venv/bin/python -m pytest -q --no-header -p no:cacheprovider >/dev/null 2>&1 \
    && ok "smoke tests pass" || bad "smoke tests fail: make test"
fi
