#!/bin/bash
set -e

echo "🚀 Deploying GenMedia API..."

# Extract values from config.py using uv environment
PROJECT_ID=$(uv run python -c "from app.config import settings; print(settings.project_id)")
LOCATION=$(uv run python -c "from app.config import settings; print(settings.location)")
GCS_BUCKET=$(uv run python -c "from app.config import settings; print(settings.gcs_bucket)")
WORKFLOWS_BUCKET=$(uv run python -c "from app.config import settings; print(settings.workflows_bucket)")
FIREBASE_PROJECT_ID=$(uv run python -c "from app.config import settings; print(settings.firebase_project_id)")

echo "📋 Deployment config:"
echo "  Project ID: $PROJECT_ID"
echo "  Location: $LOCATION"
echo "  GCS Bucket: $GCS_BUCKET"
echo "  Workflows Bucket: $WORKFLOWS_BUCKET"
echo "  Firebase Project: $FIREBASE_PROJECT_ID"

gcloud run deploy veo-api \
  --source . \
  --project="$PROJECT_ID" \
  --region="$LOCATION" \
  --allow-unauthenticated \
  --set-env-vars "PROJECT_ID=$PROJECT_ID,LOCATION=$LOCATION,GCS_BUCKET=$GCS_BUCKET,WORKFLOWS_BUCKET=$WORKFLOWS_BUCKET,FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID" \
  --timeout=300 \
  --memory=1Gi

# Get the service URL dynamically
SERVICE_URL=$(gcloud run services describe veo-api --region="$LOCATION" --project="$PROJECT_ID" --format='value(status.url)')

echo "✅ Deployment complete!"
echo "🔗 $SERVICE_URL"