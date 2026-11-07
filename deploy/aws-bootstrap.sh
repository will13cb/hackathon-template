#!/usr/bin/env bash
# ONE-TIME, run by a HUMAN with an admin profile (AWS_ADMIN_PROFILE).
# Creates the Lambda execution role so Claude's least-privilege profile never needs iam:CreateRole.
# Usage: make aws-bootstrap
set -euo pipefail
cd "$(dirname "$0")/.."

export AWS_PROFILE="${AWS_ADMIN_PROFILE:-default}"
AWS_REGION="${AWS_REGION:-us-east-1}"
SERVICE_NAME="${SERVICE_NAME:-hack-app}"
ROLE_NAME="${SERVICE_NAME}-lambda-role"

echo "▶ Using admin profile '$AWS_PROFILE' → account $(aws sts get-caller-identity --query Account --output text)"

if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  echo "  role $ROLE_NAME already exists"
else
  aws iam create-role --role-name "$ROLE_NAME" \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
    }' \
    --tags Key=purpose,Value=hackathon >/dev/null
  echo "  created role $ROLE_NAME"
fi

aws iam attach-role-policy --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name bedrock-invoke \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      "Resource": "*"
    }]
  }'

echo "✅ Role ready: $ROLE_NAME"
echo "Next: attach deploy/iam/claude-dev-policy.json to the '${AWS_PROFILE_CLAUDE:-hackathon}' user/role (see docs/SETUP.md)."
