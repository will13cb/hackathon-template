#!/usr/bin/env bash
# Deploy to Google Cloud Run from source (Cloud Build uses the Dockerfile). Idempotent: re-run to redeploy.
# Usage: make deploy-gcp     (reads .env)
set -euo pipefail
cd "$(dirname "$0")/.."

: "${GCP_PROJECT:?Set GCP_PROJECT in .env}"
GCP_REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-hack-app}"
VERTEX_LOCATION="${VERTEX_LOCATION:-global}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-2.5-flash}"
G=(--project "$GCP_PROJECT" --quiet)

echo "▶ Enabling APIs (no-op if already enabled)…"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com aiplatform.googleapis.com "${G[@]}"

# Cloud Run uses the default compute service account. Make sure it can call Vertex AI.
PROJECT_NUMBER="$(gcloud projects describe "$GCP_PROJECT" --format='value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
  --member "serviceAccount:${RUNTIME_SA}" --role roles/aiplatform.user \
  --condition=None "${G[@]}" >/dev/null

echo "▶ Deploying $SERVICE_NAME to Cloud Run ($GCP_REGION)…"
gcloud run deploy "$SERVICE_NAME" "${G[@]}" \
  --source . \
  --region "$GCP_REGION" \
  --allow-unauthenticated \
  --memory 1Gi --cpu 1 --timeout 300 \
  --min-instances 0 --max-instances 3 \
  --set-env-vars "LLM_PROVIDER=vertex,GOOGLE_CLOUD_PROJECT=${GCP_PROJECT},GOOGLE_CLOUD_LOCATION=${VERTEX_LOCATION},GEMINI_MODEL=${GEMINI_MODEL}" \
  --labels "app=${SERVICE_NAME},purpose=hackathon"

URL="$(gcloud run services describe "$SERVICE_NAME" "${G[@]}" --region "$GCP_REGION" --format='value(status.url)')"

echo "▶ Health check…"
curl -fsS --retry 5 --retry-delay 3 --retry-all-errors "$URL/health" && echo
echo "LIVE: $URL"
