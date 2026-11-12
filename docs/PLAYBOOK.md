# Hackathon Playbook

Step-by-step from "template on GitHub" to "public repo submitted", plus a short tour of the repo. Teammates: start at [step 2](#2-joining-as-a-partner).

## How this repo works (2-minute tour)

| Piece | What it does | You touch it when… |
|---|---|---|
| `CLAUDE.md` | Brief Claude reads every session: problem, rules, **API contract** | Hour 0 (fill in the TODOs), and whenever the contract changes |
| `.env` | Your project ID, region, AWS profile, model IDs. Gitignored, so each person has their own | Setup |
| `make claude` | Starts Claude Code with `.env` loaded, so the MCP servers know your project and profile | Every session |
| `.mcp.json` | Connects Claude to AWS (MCP Server + docs) and Google Cloud (Cloud Run + gcloud) | Never (shared) |
| `.claude/hooks/` | Run automatically. They **block** cloud deletes, force-push, and secret commits, format edited files, and run tests when Claude finishes a turn | Never |
| `/deploy` `/sync` `/demo-check` | Skills you type in Claude: deploy + verify, merge branches, pre-judging audit | During the event |
| `api/app/llm.py` | The only place model calls happen. `LLM_PROVIDER` = `mock` (offline) / `vertex` (Gemini) / `bedrock` | Changing models |
| `api/` `web/` `tests/` | Backend (FastAPI), frontend (static HTML/JS), smoke tests | Building |
| `deploy/` | `make deploy-gcp` → Cloud Run, `make deploy-aws` → Lambda. Teardown scripts are human-only | Deploying / cleaning up |
| `make help` | Lists every command | Any time |

**Guardrails:** Claude can't delete cloud resources, force-push, or commit secrets. The hook blocks it, and on AWS the IAM policy also refuses deletes. Commands like teardown are blocked for Claude only, so run them yourself in a normal terminal.

---

## 0. Before the event (once)

1. Put the template on GitHub as a **template repo** (public is fine because it holds no features or secrets):
   ```bash
   gh repo create hackathon-template --public --source . --push
   gh repo edit --template
   ```
2. Do the dry run in [SETUP.md](SETUP.md):
   - install `uv`, the AWS CLI and `gcloud`
   - fill in `.env`, then run `make doctor` until nothing is red
   - deploy once to each cloud, then tear down
3. `make pin-mcp`, check that `/mcp` in Claude Code shows the servers connected, and commit `.mcp.json`. No `@latest` surprises on event morning.

## 1. When you arrive

1. Create the event repo from the template, **private**:
   ```bash
   gh repo create my-event-project --private --template <you>/hackathon-template --clone
   cd my-event-project && make setup
   ```
2. Create a **fresh GCP project** (or a clean AWS account), redeem the organizers' credits, and set a **billing alert**.
3. Once you know the sponsor cloud: `make use-aws` or `make use-gcp`. It deletes the other cloud's scripts, MCP servers, SDK and `.env` keys, so `make doctor` only checks what you use. Commit.
4. Fill in `.env`, then run `make doctor`.
5. Deploy hello-world right away (`make deploy-gcp` or `make deploy-aws`) to prove deploys work on the venue network.

## 2. Joining as a partner

**Owner**, for each partner:
```bash
gh repo edit --add-collaborator <github-username>     # a private repo needs an invite; a link isn't enough
# GCP access:
gcloud projects add-iam-policy-binding <PROJECT> --member user:<their-email> --role roles/editor
# AWS access: create a separate user per person with deploy/iam/claude-dev-policy.json (see SETUP.md).
#             Never share your own keys.
```
Send the `.env` values (project ID, region) by DM. IDs are fine to share, but **don't paste API keys** into team chat.

**Partner:**
```bash
gh repo clone <owner>/my-event-project && cd my-event-project
make setup                                   # creates your own .env; fill in the shared values
gcloud auth login && gcloud auth application-default login     # Google track
aws configure --profile hackathon                              # AWS track
make doctor                                  # everything green? you're ready
```

## 3. When you know the problem (hour 0–1)

1. Fill in the TODOs in `CLAUDE.md`: problem, **wow moment**, sponsor services, judging criteria.
2. **Write the API contract** (endpoints + JSON shapes) in `CLAUDE.md`. This is what lets everyone build in parallel.
3. Run `make claude`, switch to **plan mode** (`shift+tab`), and ask for an architecture plan. Agree on it, then lock it.
4. Push it to `main` **before anyone branches**:
   ```bash
   git add -A && git commit -m "brief + API contract" && git push
   ```
5. Pick lanes. Each lane only edits its own folders:

   | Lane | Owns |
   |---|---|
   | frontend | `web/` |
   | backend | `api/`, `tests/` |
   | infra | `deploy/`, `Dockerfile` |
   | `main` only | `CLAUDE.md`, `requirements*.txt`, `Makefile` |

## 4. While developing

**Team, one branch per person:**
```bash
git switch -c feat/<lane>
make claude
```
Loop: **one feature → `make test` → `/deploy` → check logs.** Deploy early and often.

Merge every 1–2 hours:
```bash
git push -u origin feat/<lane>
gh pr create --fill && gh pr merge --merge
git switch main && git pull && git switch feat/<lane> && git merge main
```
One person (usually infra) runs `/deploy` from `main`, so the live URL is always the merged version.

**Solo, parallel Claude sessions:** run `make worktrees`, then `make claude` in each `../<repo>-frontend`, `-backend` and `-infra` folder. Run `/sync` every 1–2 hours.

**Debugging:** tell Claude "check the logs". It reads them itself (MCP or `make logs-gcp` / `make logs-aws`). Don't paste stack traces.

## 5. Last 3 hours: feature freeze

- [ ] `/demo-check`: fix the top 3 items it reports
- [ ] Replace the README with the **Submission README** outline in [DEMO.md](DEMO.md)
- [ ] Update the diagram in [architecture.md](architecture.md)
- [ ] Record a **backup video** of the demo
- [ ] Rehearse the 2–3 min pitch **twice** with a timer
- [ ] `curl <url>/health` right before presenting to avoid a cold start

## 6. Submit and go public

```bash
make scan       # scans the WHOLE git history for secrets, not just current files
```
If it finds anything, **rotate the key** in the AWS or GCP console. Deleting the file isn't enough, because the key stays in old commits. Then:
```bash
gh repo edit --visibility public --accept-visibility-change-consequences
```
- [ ] README has the live URL, video link, sponsor services, and how to run it
- [ ] LICENSE present (MIT)
- [ ] AI-tool disclosure, if the rules require it
- [ ] Submit the repo link

## 7. After the event

- [ ] `make teardown-gcp` / `make teardown-aws` (you run these, not Claude), or delete the whole GCP project
- [ ] Check both billing consoles the next day
- [ ] Pin the project on your GitHub profile and link it from your site
