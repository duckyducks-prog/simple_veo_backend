#!/bin/bash
set -e

echo "🚀 Deploying GenMedia API..."

gcloud run deploy veo-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=remarkablenotion,LOCATION=us-central1,GCS_BUCKET=genmedia-assets-remarkablenotion,FIREBASE_PROJECT_ID=genmediastudio \
  --timeout=300 \
  --memory=1Gi

echo "✅ Deployment complete!"
echo "🔗 https://veo-api-82187245577.us-central1.run.app"