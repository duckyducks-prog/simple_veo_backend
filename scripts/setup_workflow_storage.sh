#!/bin/bash

# Workflow Storage Setup Script
# This script sets up the GCS bucket for workflow storage

set -e

echo "🚀 Setting up Workflow Storage..."

# Configuration
PROJECT_ID="genmediastudio"
BUCKET_NAME="genmediastudio-workflows"
LOCATION="us-central1"
SERVICE_ACCOUNT="veo-api-service-account@${PROJECT_ID}.iam.gserviceaccount.com"

# Check if gsutil is installed
if ! command -v gsutil &> /dev/null; then
    echo "❌ Error: gsutil is not installed. Please install Google Cloud SDK."
    exit 1
fi

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "❌ Error: Not authenticated with gcloud. Run 'gcloud auth login' first."
    exit 1
fi

# Set project
echo "📦 Setting project to ${PROJECT_ID}..."
gcloud config set project ${PROJECT_ID}

# Check if bucket exists
if gsutil ls -b gs://${BUCKET_NAME} &> /dev/null; then
    echo "✅ Bucket gs://${BUCKET_NAME} already exists"
else
    echo "📦 Creating bucket gs://${BUCKET_NAME}..."
    gsutil mb -l ${LOCATION} gs://${BUCKET_NAME}
    echo "✅ Bucket created"
fi

# Enable versioning (recommended for data safety)
echo "🔄 Enabling versioning..."
gsutil versioning set on gs://${BUCKET_NAME}
echo "✅ Versioning enabled"

# Set up CORS (if needed for frontend access)
echo "🌐 Setting up CORS..."
cat > /tmp/cors.json <<EOF
[
  {
    "origin": ["*"],
    "method": ["GET", "HEAD"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
EOF
gsutil cors set /tmp/cors.json gs://${BUCKET_NAME}
rm /tmp/cors.json
echo "✅ CORS configured"

# Grant service account access
echo "🔑 Granting service account access..."
gsutil iam ch serviceAccount:${SERVICE_ACCOUNT}:objectAdmin gs://${BUCKET_NAME}
echo "✅ Service account permissions granted"

# Create initial directory structure
echo "📁 Creating directory structure..."
echo '{}' | gsutil cp - gs://${BUCKET_NAME}/workflows/metadata/index.json
echo "✅ Directory structure created"

# Set lifecycle policy (optional - delete old versions after 30 days)
echo "♻️  Setting lifecycle policy..."
cat > /tmp/lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "numNewerVersions": 5,
          "isLive": false
        }
      }
    ]
  }
}
EOF
gsutil lifecycle set /tmp/lifecycle.json gs://${BUCKET_NAME}
rm /tmp/lifecycle.json
echo "✅ Lifecycle policy set"

echo ""
echo "✅ ✅ ✅ Workflow storage setup complete! ✅ ✅ ✅"
echo ""
echo "Bucket: gs://${BUCKET_NAME}"
echo "Location: ${LOCATION}"
echo "Versioning: Enabled"
echo ""
echo "Next steps:"
echo "1. Deploy your updated backend code"
echo "2. Test the workflow endpoints"
echo "3. Check the bucket: gsutil ls -r gs://${BUCKET_NAME}"
echo ""
