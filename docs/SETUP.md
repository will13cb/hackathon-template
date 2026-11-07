# One-time setup (do this the week before)

Anything that breaks here won't break at 2 a.m. Finish by running `make doctor` until it's all green, then deploy hello-world to both clouds.

## 0. Local tools

| Tool | Why | Install |
|---|---|---|
| uv / uvx | Launches the AWS MCP server | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| AWS CLI v2 | Deploy + logs; Claude uses it via Bash | https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html |
| gcloud | Deploy + logs + ADC | https://cloud.google.com/sdk/docs/install |
| Docker | Builds the Lambda image | already installed? `docker info` |
| Node 18+ | Launches the Cloud Run + gcloud MCP servers (npx) | already installed? `node -v` |
| gitleaks (optional) | Secret scanning (`make scan` falls back to Docker) | https://github.com/gitleaks/gitleaks |

## 1. Google Cloud

```bash
gcloud auth login
gcloud auth application-default login          # ADC: used by Vertex locally and by the MCP servers
gcloud projects create hack-<event>-<random>   # fresh project per event = easy cleanup
gcloud billing projects link <PROJECT> --billing-account <ACCOUNT_ID>
gcloud config set project <PROJECT>
```

- Put the project ID in `.env` as `GCP_PROJECT`.
- **Billing alert:** Console → Billing → Budgets & alerts → set a budget (e.g. $25) with email at 50/90/100%.
- **Credits:** redeem the organizers' coupon on the billing account before the event.
- The first `make deploy-gcp` enables the APIs it needs (Run, Cloud Build, Artifact Registry, Vertex AI).
- If a source deploy fails with a Cloud Build permission error, grant the build service account the builder role:
  `gcloud projects add-iam-policy-binding <PROJECT> --member serviceAccount:<PROJECT_NUMBER>-compute@developer.gserviceaccount.com --role roles/run.builder`
- **Model:** check Vertex AI → Model Garden for the newest Gemini Flash model ID and set `GEMINI_MODEL`.

Least privilege on GCP: the dedicated project *is* the boundary. Don't use a project that holds anything you care about.

## 2. AWS

Use two profiles:
- **Admin** (`AWS_ADMIN_PROFILE`): you only. Used for bootstrap and teardown.
- **`hackathon`** (`AWS_PROFILE`): what Claude and the MCP server use. It's limited to `deploy/iam/claude-dev-policy.json`.

```bash
# As admin: create a user or IAM Identity Center permission set for Claude, attach the policy:
aws iam create-user --user-name hack-claude --profile <admin>
aws iam put-user-policy --user-name hack-claude --policy-name claude-dev \
  --policy-document file://deploy/iam/claude-dev-policy.json --profile <admin>
aws iam create-access-key --user-name hack-claude --profile <admin>   # → aws configure --profile hackathon
# (IAM Identity Center/SSO is better if your account has it: aws configure sso --profile hackathon)

make aws-bootstrap      # creates hack-app-lambda-role (Lambda logs + Bedrock invoke)
```

That policy can create, update, and inspect `hack-*` Lambda functions and ECR repos, invoke Bedrock, and read logs. It **can't delete anything** or create IAM roles. Together with the guard hook, that gives you two layers of protection.

With the AWS MCP Server, **IAM is your security boundary**: the server runs whatever Claude asks for, and IAM decides what succeeds.

- **Billing alert:** Billing → Budgets → create a cost budget with email alerts.
- **Credits:** Billing → Credits → redeem the code.
- **Bedrock model:** the default `us.amazon.nova-lite-v1:0` works with no extra setup. To use Claude on Bedrock, list inference profiles (command in `.env.example`) and set `BEDROCK_MODEL_ID`. Some models need a one-time use-case form in the Bedrock console.

## 3. Claude Code

```bash
make claude     # loads .env, then launches claude, so .mcp.json expands ${AWS_PROFILE}, ${GCP_PROJECT}, …
/mcp            # inside Claude: check that aws, aws-knowledge, cloud-run and gcloud are connected
```

- The first launch asks you to approve the project's MCP servers. Approve them.
- `aws` = the managed **AWS MCP Server** (GA May 2026) through `mcp-proxy-for-aws`, which signs requests with your profile's credentials. If the package name has changed, check https://github.com/aws/mcp-proxy-for-aws (some docs use `mcp-proxy-for-aws-cli`). To make it read-only, add `"--read-only"` to its args.
- `aws-knowledge` = current AWS docs. It's a remote server, so no credentials are needed.
- `cloud-run` / `gcloud` = Google's MCP servers. They use your gcloud login and ADC. `gcloud-mcp` is in preview.
- `FASTMCP_LOG_LEVEL=WARNING` keeps server INFO logs out of Claude's responses.

## 4. Dry run (required)

```bash
make deploy-gcp && make deploy-aws
```

Open both URLs, type a prompt, and confirm the badge shows `vertex` / `bedrock`. Then run `make teardown-gcp` and `make teardown-aws` to confirm teardown also works.
