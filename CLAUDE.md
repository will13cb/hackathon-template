# CLAUDE.md

> Fill in every `TODO` at the start of the hackathon (takes 10 minutes). Everything else is the standing setup.

## Project
- **Hackathon:** TODO (name, track, deadline with timezone)
- **Problem:** TODO (one sentence, one user)
- **The "wow" moment:** TODO (the single thing the demo must show working)
- **Sponsor services we showcase:** TODO (e.g. Gemini on Vertex AI + Cloud Run, or Bedrock + Lambda)
- **Judging criteria:** TODO (paste them; optimize for these)

## Stack
- `api/`: Python 3.12 + FastAPI. `api/app/llm.py` is the only place model calls happen (`LLM_PROVIDER` = `mock` | `vertex` | `bedrock`).
- `web/`: static HTML/JS with no build step, served by the API at `/`. Upgrade to Vite/React only if it's worth the time.
- `deploy/`: shell scripts for Cloud Run (GCP) and Lambda + Function URL (AWS). The same Docker image runs on both (Lambda Web Adapter).
- `tests/`: pytest smoke tests. They run offline with `LLM_PROVIDER=mock`.

## Commands
| Task | Command |
|---|---|
| Install | `make setup` |
| Run locally | `make dev` → http://localhost:8080 |
| Tests | `make test` |
| Format + lint | `make fmt` |
| Run container locally | `make docker-run` |
| Deploy | `make deploy-gcp` / `make deploy-aws` (or `/deploy gcp`) |
| Logs | `make logs-gcp` / `make logs-aws` |
| Check tools + auth | `make doctor` |

## Cloud config
Values live in `.env` (gitignored; `.env.example` lists the keys). Do not hard-code project IDs, account IDs, or keys anywhere in the repo.
- GCP: project `$GCP_PROJECT`, region `$GCP_REGION`, Vertex location `$VERTEX_LOCATION`, model `$GEMINI_MODEL`
- AWS: profile `$AWS_PROFILE`, region `$AWS_REGION`, model `$BEDROCK_MODEL_ID`
- Service name: `$SERVICE_NAME` (keep the `hack-` prefix because the IAM policy is scoped to it)

Tools available to you: MCP servers in `.mcp.json` (`aws`, `aws-knowledge`, `cloud-run`, `gcloud`), plus the `aws` and `gcloud` CLIs through Bash. To debug a deployed service, read the logs yourself (`make logs-*` or MCP). Don't ask the user to paste stack traces.

## API contract
Change this section first and get agreement before changing an endpoint. Every worktree builds against it.

```
GET  /health          → 200 {"status": "ok", "provider": str, "model": str}
POST /api/generate    ← {"prompt": str (1..8000), "system": str | null}
                      → 200 {"text": str, "provider": str, "model": str}
                      → 422 validation error | 502 {"detail": str} if the model call fails
TODO: add project endpoints here
```

## Rules
1. **Never delete cloud resources** and never run teardown scripts. Hooks block this. Ask the user and they will run it.
2. **Never commit secrets.** No `.env`, keys, or service-account JSON in git. A hook checks every commit.
3. **Plan before building infra.** Don't add new cloud services without asking. Stick to the stack above.
4. **Small loops:** one feature → `make test` → deploy → check logs. Deploy early and often, not only at the end.
5. **Keep the sponsor's product central and visible** (in the UI, logs, and README).
6. **Stay in your lane in worktrees:** frontend edits `web/`, backend edits `api/` + `tests/`, infra edits `deploy/` + `Dockerfile`. Only `main` edits `requirements*.txt`, `Makefile`, and this file.
7. Keep tests fast (<10s). A Stop hook runs them after every turn.

## Status / decisions log
- TODO: append one line per significant decision (why, not what).
