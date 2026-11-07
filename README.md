# Hackathon Template: Claude Code × Google Cloud × AWS

A starter for cloud hackathons, prepared before the event. It contains **scaffolding only, with no project features**. The setup is all done ahead of time so the event itself is spent on the demo.

- **One container, two clouds:** a FastAPI app that deploys to **Cloud Run** (Gemini on Vertex AI) or **Lambda + Function URL** (Amazon Bedrock) with one command each.
- **Claude Code wired to both clouds:** `.mcp.json` (AWS MCP Server, AWS Knowledge, Cloud Run, gcloud), hooks for guardrails, and skills for repeatable procedures.
- **Built for parallel work:** git worktrees per lane, an API contract in `CLAUDE.md`, and a `/sync` skill.

> **New here or joining a team? Read [docs/PLAYBOOK.md](docs/PLAYBOOK.md)**: a repo tour plus every step from arriving at the event to submitting.
>
> When you replace this README for a project, use the "Submission README" outline in [docs/DEMO.md](docs/DEMO.md).

## Quick start

```bash
make setup            # .venv + deps + .env from template
make test             # offline smoke tests (mock LLM)
make dev              # http://localhost:8080
make claude           # launch Claude Code with .env loaded, so MCP servers get your project/profile
```

Deploy (after the one-time [setup](docs/SETUP.md)):

```bash
make deploy-gcp       # Cloud Run + Gemini       → prints LIVE: https://…run.app
make deploy-aws       # Lambda + Bedrock          → prints LIVE: https://…lambda-url…on.aws
```

Inside Claude Code: `/deploy gcp`, `/sync`, `/demo-check`.

## What's in here

```
CLAUDE.md                  Project brief + rules + API contract (fill the TODOs at hour 0)
.mcp.json                  MCP servers, shared with teammates; uses ${ENV} expansion, so no IDs in git
.claude/settings.json      Hooks + safe-command allowlist
.claude/hooks/
  guard_bash.py            PreToolUse: blocks cloud deletes, force-push, rm -rf /, and secret commits
  format.sh                PostToolUse: ruff / prettier on every edited file
  smoke.sh                 Stop: runs tests when Claude finishes a turn; failures go back to Claude
.claude/skills/
  deploy/                  /deploy: test → deploy → verify → check logs → report URL
  sync/                    /sync: merge worktrees → test → fan main back out
  demo-check/              /demo-check: read-only pre-judging audit
api/app/main.py            FastAPI: /health, /api/generate, serves web/
api/app/llm.py             The only model-call site: LLM_PROVIDER = mock | vertex | bedrock
web/                       Static HTML/JS, no build step
tests/                     pytest smoke tests (<2s, offline)
Dockerfile                 python:3.12-slim + Lambda Web Adapter (same image on both clouds)
deploy/                    Cloud Run + Lambda deploy scripts, AWS bootstrap, teardown, IAM policy
scripts/                   doctor (preflight), worktrees, scan-secrets
docs/                      SETUP (week before), DEMO (pitch + submission), architecture diagram
```

## Hooks vs skills

| | Hooks (always run) | Skills (Claude decides, or you type `/name`) |
|---|---|---|
| Purpose | Enforce rules | Package multi-step procedures |
| Here | Bash guard, formatter, Stop-time tests | `/deploy`, `/sync`, `/demo-check` |

`CLAUDE.md` says *why* (the rules). Hooks make the rules impossible to break. `/deploy` and `/sync` have side effects, so they only run when **you** type them (`disable-model-invocation`).

**Escape hatch:** the guard only applies to Claude. Run destructive commands yourself in a normal terminal (e.g. `make teardown-aws`).

## Hackathon-day playbook

Summary below. Full commands, partner onboarding, and submission steps are in [docs/PLAYBOOK.md](docs/PLAYBOOK.md).

| When | Do |
|---|---|
| Hour 0–1 | Fill in the `CLAUDE.md` TODOs (problem, wow moment, judging criteria, API contract). Use plan mode (`shift+tab`) to plan, then lock the architecture. `make doctor`. Deploy hello-world once so you know deploys work. |
| Build | Work in loops: one feature → `make test` → `/deploy` → check logs. Deploy early and often. |
| Parallel | `make worktrees`, then run `make claude` in each `../<repo>-frontend`, `-backend`, and `-infra` folder. Run `/sync` every 1–2 h. |
| Debug | Have Claude read the logs itself (MCP or `make logs-*`). Don't paste stack traces. |
| Last 3 h | Freeze features. `/demo-check`, record a backup video, write the README, update the architecture diagram, rehearse twice. |
| After | Before going public: `make scan` and rotate anything ever committed. Then `make teardown-*`. |

## Using this template for a new event

1. GitHub → **Use this template** → new **private** repo (make it public at submission).
2. `make setup`, fill in `.env`, then `make doctor`.
3. Replace `web/` and add endpoints, starting with the API contract in `CLAUDE.md`.

Check the event's rules on AI tools and pre-built code. This repo has no feature code, and its public commit history shows what existed before the event.

## License
MIT. See [LICENSE](LICENSE).
