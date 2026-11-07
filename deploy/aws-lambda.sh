#!/usr/bin/env bash
# Deploy the container to AWS Lambda behind a public Function URL. Idempotent: re-run to redeploy.
# Needs: Docker running, AWS_PROFILE with deploy/iam/claude-dev-policy.json, and `make aws-bootstrap` done once.
# Usage: make deploy-aws     (reads .env)
set -euo pipefail
cd "$(dirname "$0")/.."

export AWS_PROFILE="${AWS_PROFILE:-hackathon}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
SERVICE_NAME="${SERVICE_NAME:-hack-app}"
BEDROCK_MODEL_ID="${BEDROCK_MODEL_ID:-us.amazon.nova-lite-v1:0}"
ROLE_NAME="${SERVICE_NAME}-lambda-role"

ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
REGISTRY="${ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"
TAG="$(git rev-parse --short HEAD 2>/dev/null || date +%s)$(git diff --quiet 2>/dev/null || echo -dirty-$(date +%H%M%S))"
IMAGE="${REGISTRY}/${SERVICE_NAME}:${TAG}"
ROLE_ARN="$(aws iam get-role --role-name "$ROLE_NAME" --query Role.Arn --output text 2>/dev/null)" || {
  echo "✖ Role $ROLE_NAME not found. A human must run: make aws-bootstrap"; exit 1; }

echo "▶ ECR repo…"
aws ecr describe-repositories --repository-names "$SERVICE_NAME" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "$SERVICE_NAME" \
       --image-scanning-configuration scanOnPush=true --tags Key=purpose,Value=hackathon >/dev/null
aws ecr get-login-password | docker login --username AWS --password-stdin "$REGISTRY" >/dev/null

echo "▶ Building $IMAGE (linux/amd64)…"
docker build --platform linux/amd64 --provenance=false -t "$IMAGE" .
docker push "$IMAGE" >/dev/null

ENV_VARS="Variables={LLM_PROVIDER=bedrock,BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID},AWS_LWA_READINESS_CHECK_PATH=/health}"

if aws lambda get-function --function-name "$SERVICE_NAME" >/dev/null 2>&1; then
  echo "▶ Updating function…"
  aws lambda update-function-code --function-name "$SERVICE_NAME" --image-uri "$IMAGE" >/dev/null
  aws lambda wait function-updated-v2 --function-name "$SERVICE_NAME"
  aws lambda update-function-configuration --function-name "$SERVICE_NAME" \
    --environment "$ENV_VARS" --timeout 60 --memory-size 1024 >/dev/null
  aws lambda wait function-updated-v2 --function-name "$SERVICE_NAME"
else
  echo "▶ Creating function…"
  aws lambda create-function --function-name "$SERVICE_NAME" \
    --package-type Image --code "ImageUri=$IMAGE" --role "$ROLE_ARN" \
    --architectures x86_64 --timeout 60 --memory-size 1024 \
    --environment "$ENV_VARS" --tags purpose=hackathon >/dev/null
  aws lambda wait function-active-v2 --function-name "$SERVICE_NAME"
fi

if ! URL="$(aws lambda get-function-url-config --function-name "$SERVICE_NAME" --query FunctionUrl --output text 2>/dev/null)"; then
  echo "▶ Creating public Function URL…"
  URL="$(aws lambda create-function-url-config --function-name "$SERVICE_NAME" \
          --auth-type NONE --query FunctionUrl --output text)"
  # Public URLs need BOTH permissions (required for URLs created since Oct 2025).
  aws lambda add-permission --function-name "$SERVICE_NAME" \
    --statement-id FunctionURLAllowPublicAccess --action lambda:InvokeFunctionUrl \
    --principal "*" --function-url-auth-type NONE >/dev/null
  aws lambda add-permission --function-name "$SERVICE_NAME" \
    --statement-id FunctionURLAllowInvokeAction --action lambda:InvokeFunction \
    --principal "*" --invoked-via-function-url >/dev/null 2>&1 \
  || { echo "  (older AWS CLI: run 'pip install -U awscli' or upgrade v2 if the URL returns 403)"; }
fi
URL="${URL%/}"

echo "▶ Health check…"
curl -fsS --retry 5 --retry-delay 3 --retry-all-errors "$URL/health" && echo
echo "LIVE: $URL"
