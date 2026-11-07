#!/usr/bin/env bash
# HUMAN-ONLY (the guard hook blocks Claude from running this). Uses your admin profile.
set -euo pipefail
export AWS_PROFILE="${AWS_ADMIN_PROFILE:-default}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
SERVICE_NAME="${SERVICE_NAME:-hack-app}"
ROLE_NAME="${SERVICE_NAME}-lambda-role"

read -r -p "Delete Lambda '$SERVICE_NAME', its URL, ECR repo, role and logs in $AWS_REGION (profile $AWS_PROFILE)? [y/N] " ok
[[ "$ok" =~ ^[Yy]$ ]] || { echo "aborted"; exit 1; }

aws lambda delete-function-url-config --function-name "$SERVICE_NAME" 2>/dev/null || true
aws lambda delete-function --function-name "$SERVICE_NAME" 2>/dev/null || true
aws ecr delete-repository --repository-name "$SERVICE_NAME" --force >/dev/null 2>&1 || true
aws logs delete-log-group --log-group-name "/aws/lambda/$SERVICE_NAME" 2>/dev/null || true
aws iam delete-role-policy --role-name "$ROLE_NAME" --policy-name bedrock-invoke 2>/dev/null || true
aws iam detach-role-policy --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || true
aws iam delete-role --role-name "$ROLE_NAME" 2>/dev/null || true
echo "✅ AWS teardown done. Also check: NAT gateways, GPU/EC2 instances, SageMaker endpoints, OpenSearch domains."
echo "   Billing: https://console.aws.amazon.com/billing/home#/bills"
