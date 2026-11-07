#!/usr/bin/env bash
# HUMAN-ONLY (the guard hook blocks Claude from running this). Deletes what gcp-cloudrun.sh created.
# The simplest full cleanup is deleting the whole hackathon project: gcloud projects delete $GCP_PROJECT
set -euo pipefail
: "${GCP_PROJECT:?Set GCP_PROJECT in .env}"
GCP_REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-hack-app}"

read -r -p "Delete Cloud Run service '$SERVICE_NAME' and source-deploy images in $GCP_PROJECT? [y/N] " ok
[[ "$ok" =~ ^[Yy]$ ]] || { echo "aborted"; exit 1; }

gcloud run services delete "$SERVICE_NAME" --project "$GCP_PROJECT" --region "$GCP_REGION" --quiet || true
# `gcloud run deploy --source` stores images in this Artifact Registry repo:
gcloud artifacts repositories delete cloud-run-source-deploy \
  --project "$GCP_PROJECT" --location "$GCP_REGION" --quiet || true
echo "✅ GCP teardown done. Check billing: https://console.cloud.google.com/billing"
