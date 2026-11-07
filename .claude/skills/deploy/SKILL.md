---
name: deploy
description: Test, build, and deploy the app to Google Cloud Run or AWS Lambda, verify it from the logs, and report the live URL. Use when the user says /deploy, "ship it", or asks to deploy.
argument-hint: "[gcp|aws|both]"
disable-model-invocation: true
---

# Deploy

Target: `$ARGUMENTS` (if empty, use `gcp` when `GCP_PROJECT` is set in `.env`, else `aws`; `both` = gcp then aws).

Do these steps in order and stop at the first failure. Report what failed and the relevant log lines.

1. **Preflight**
   - `git status --short`: if there are uncommitted changes, list them and ask whether to deploy anyway (deploying uncommitted code is fine mid-hackathon; just say so).
   - `make test`: must pass. If it fails, fix it or stop. Never deploy red.
2. **Deploy**
   - GCP: `make deploy-gcp` (Cloud Build from source → Cloud Run). Takes about 2–4 min.
   - AWS: `make deploy-aws` (docker build → ECR → Lambda + Function URL). Takes about 2–3 min. Needs Docker running.
   - If the script fails on auth or a missing API, explain the one command the user needs to run (e.g. `gcloud auth login`, `aws sso login --profile …`, or `make aws-bootstrap` with their admin profile). Don't try to get around IAM.
3. **Verify live**
   - The script prints `LIVE: <url>`. Run `curl -fsS <url>/health` and one real request: `curl -fsS -X POST <url>/api/generate -H 'content-type: application/json' -d '{"prompt":"Say hi in 5 words"}'`.
   - Confirm `provider` is the real one (`vertex` / `bedrock`), not `mock`.
4. **Check logs** for errors in the last few minutes. Use the `cloud-run` / `gcloud` / `aws` MCP servers or `make logs-gcp` / `make logs-aws`. Call out any ERROR/Traceback lines, even if the request succeeded.
5. **Report** in this format:
   ```
   ✅ Deployed <target> @ <git short sha>
   URL: <url>
   Health: <json>   Sample: <first 80 chars of text>
   Log warnings: <none | summary>
   ```
   Then append one line to the "Status / decisions log" in CLAUDE.md: `- <time> deployed <sha> to <target>: <url>`.
