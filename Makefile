# Every target loads .env (if present) so scripts and Claude see the same config.
SHELL := /bin/bash
ENV   := set -a; [ -f .env ] && . ./.env; set +a;
PY    := .venv/bin/python

.DEFAULT_GOAL := help
.PHONY: help setup use-aws use-gcp pin-mcp dev test fmt lint docker-run claude doctor deploy-gcp deploy-aws aws-bootstrap \
	    logs-gcp logs-aws worktrees scan teardown-gcp teardown-aws

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## Create .venv, install deps, create .env from template
	@if command -v uv >/dev/null; then uv venv -q .venv && uv pip install -q -p .venv -r requirements-dev.txt; \
	 else python3 -m venv .venv && $(PY) -m pip install -q --upgrade pip && $(PY) -m pip install -q -r requirements-dev.txt; fi
	@[ -f .env ] || { cp .env.example .env; echo "created .env, fill it in"; }
	@echo "setup done"

use-aws: ## Kickoff: keep AWS, delete the GCP scaffolding
	@python3 scripts/use_cloud.py aws

use-gcp: ## Kickoff: keep GCP, delete the AWS scaffolding
	@python3 scripts/use_cloud.py gcp

pin-mcp: ## Pin MCP server versions in .mcp.json (run the week before, commit)
	@python3 scripts/pin_mcp.py

dev: ## Run locally with reload on :8080
	@$(ENV) $(PY) -m uvicorn api.app.main:app --reload --port 8080

test: ## Run smoke tests (offline, mock provider)
	@LLM_PROVIDER=mock $(PY) -m pytest

fmt: ## Format + autofix lint
	@.venv/bin/ruff format . && .venv/bin/ruff check --fix .

lint: ## Lint without fixing
	@.venv/bin/ruff format --check . && .venv/bin/ruff check .

docker-run: ## Build and run the container locally (mock provider)
	@$(ENV) docker build -t "$${SERVICE_NAME:-hack-app}:local" . && docker run --rm -p 8080:8080 -e LLM_PROVIDER=mock "$${SERVICE_NAME:-hack-app}:local"

claude: ## Launch Claude Code with .env loaded (so .mcp.json can expand values)
	@$(ENV) claude

doctor: ## Check tools, auth, and config
	@$(ENV) bash scripts/doctor.sh

deploy-gcp: ## Deploy to Cloud Run
	@$(ENV) bash deploy/gcp-cloudrun.sh

deploy-aws: ## Deploy to Lambda + Function URL
	@$(ENV) bash deploy/aws-lambda.sh

aws-bootstrap: ## (HUMAN, admin profile) one-time: create the Lambda execution role
	@$(ENV) bash deploy/aws-bootstrap.sh

logs-gcp: ## Recent Cloud Run logs
	@$(ENV) gcloud run services logs read "$$SERVICE_NAME" --project "$$GCP_PROJECT" --region "$$GCP_REGION" --limit 50

logs-aws: ## Recent Lambda logs (last 15 min)
	@$(ENV) aws logs tail "/aws/lambda/$$SERVICE_NAME" --since 15m --region "$$AWS_REGION"

worktrees: ## Create parallel worktrees: make worktrees [NAMES="frontend backend infra"]
	@bash scripts/worktrees.sh $(NAMES)

scan: ## Scan full git history for secrets (gitleaks, or via Docker)
	@bash scripts/scan-secrets.sh

teardown-gcp: ## (HUMAN) delete the Cloud Run service + source images
	@$(ENV) bash deploy/teardown-gcp.sh

teardown-aws: ## (HUMAN) delete Lambda, URL, ECR repo, role, logs
	@$(ENV) bash deploy/teardown-aws.sh
