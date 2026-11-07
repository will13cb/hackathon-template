---
name: demo-check
description: Pre-demo/pre-submission audit. Walks the live demo path, checks README, architecture diagram, and secrets, and lists everything broken or missing. Use in the final hours, before judging, or when the user asks "are we ready?".
argument-hint: "[live-url]"
---

# Demo check

Live URL: `$ARGUMENTS` (if empty, get it from the latest deploy line in CLAUDE.md, or run `gcloud run services describe` / `aws lambda get-function-url-config`).

**This is read-only. Don't fix anything during the check.** Collect findings, then offer fixes ranked by demo impact.

1. **Live path.** `curl` `/health`, then walk the demo flow described in CLAUDE.md ("The wow moment") against the live URL, using real payloads. Time each call; anything over 5s is a demo risk. Make sure the provider is not `mock`.
2. **Cold start.** If the last request was more than 5 min ago, note the first-request latency and suggest a warm-up `curl` right before presenting.
3. **Logs.** Look for errors in the last 30 minutes (MCP or `make logs-*`).
4. **README** must have: problem, solution, a named list of sponsor services, an architecture diagram, how to run locally, the live URL, and a demo video link. Flag every missing item and every leftover TODO or template text.
5. **docs/architecture.md:** the diagram matches what's actually deployed (services, data flow). Flag drift.
6. **Repo hygiene:** `git status` is clean, `make test` passes, nothing secret is tracked (`git ls-files | grep -Ei '\.env$|\.pem$|credentials|service.?account'`), and `make scan` passes if gitleaks or Docker is available.
7. **Submission rules:** re-read the rules section of CLAUDE.md (public repo? video length? AI-tool disclosure?) and check each one.

Report as a checklist: ✅ ok / ⚠️ risk / ❌ broken, with a one-line fix for each non-green item. Put the top-3 must-fix items first.
