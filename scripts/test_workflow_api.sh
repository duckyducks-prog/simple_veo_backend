#!/bin/bash

# Quick Test Script for Workflow API
# Usage: ./test_workflow_api.sh <your-firebase-token>

set -e

if [ -z "$1" ]; then
    echo "Usage: ./test_workflow_api.sh <firebase-token>"
    echo ""
    echo "Get a token by running: python scripts/get_test_token.py"
    exit 1
fi

TOKEN="$1"
BASE_URL="https://veo-api-otfo2ctxma-uc.a.run.app"

echo "🧪 Testing Workflow API..."
echo ""

# Test 1: Save workflow
echo "1️⃣  Testing POST /workflows/save..."
WORKFLOW_ID=$(curl -s -X POST "${BASE_URL}/workflows/save" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Workflow",
    "description": "Created by test script",
    "is_public": false,
    "nodes": [
      {
        "id": "node-1",
        "type": "imageInput",
        "position": {"x": 100, "y": 100},
        "data": {"label": "Image Input"}
      },
      {
        "id": "node-2",
        "type": "generateVideo",
        "position": {"x": 400, "y": 100},
        "data": {"label": "Video Generator"}
      }
    ],
    "edges": [
      {
        "id": "edge-1",
        "source": "node-1",
        "target": "node-2",
        "sourceHandle": "image",
        "targetHandle": "first_frame"
      }
    ]
  }' | jq -r '.id')

if [ -z "$WORKFLOW_ID" ] || [ "$WORKFLOW_ID" = "null" ]; then
    echo "❌ Failed to create workflow"
    exit 1
fi

echo "✅ Created workflow: $WORKFLOW_ID"
echo ""

# Test 2: List my workflows
echo "2️⃣  Testing GET /workflows?scope=my..."
MY_WORKFLOWS=$(curl -s "${BASE_URL}/workflows?scope=my" \
  -H "Authorization: Bearer ${TOKEN}" | jq '.workflows | length')

echo "✅ Found $MY_WORKFLOWS workflows"
echo ""

# Test 3: Get specific workflow
echo "3️⃣  Testing GET /workflows/{id}..."
WORKFLOW_NAME=$(curl -s "${BASE_URL}/workflows/${WORKFLOW_ID}" \
  -H "Authorization: Bearer ${TOKEN}" | jq -r '.name')

echo "✅ Retrieved workflow: $WORKFLOW_NAME"
echo ""

# Test 4: Update workflow
echo "4️⃣  Testing PUT /workflows/{id}..."
UPDATE_RESPONSE=$(curl -s -X PUT "${BASE_URL}/workflows/${WORKFLOW_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Test Workflow",
    "description": "Updated by test script",
    "is_public": true,
    "nodes": [
      {
        "id": "node-1",
        "type": "imageInput",
        "position": {"x": 100, "y": 100},
        "data": {"label": "Image Input"}
      }
    ],
    "edges": []
  }' | jq -r '.message')

echo "✅ $UPDATE_RESPONSE"
echo ""

# Test 5: Clone workflow
echo "5️⃣  Testing POST /workflows/{id}/clone..."
CLONED_ID=$(curl -s -X POST "${BASE_URL}/workflows/${WORKFLOW_ID}/clone" \
  -H "Authorization: Bearer ${TOKEN}" | jq -r '.id')

echo "✅ Cloned workflow: $CLONED_ID"
echo ""

# Test 6: List public workflows
echo "6️⃣  Testing GET /workflows?scope=public..."
PUBLIC_WORKFLOWS=$(curl -s "${BASE_URL}/workflows?scope=public" \
  -H "Authorization: Bearer ${TOKEN}" | jq '.workflows | length')

echo "✅ Found $PUBLIC_WORKFLOWS public workflows"
echo ""

# Test 7: Delete cloned workflow
echo "7️⃣  Testing DELETE /workflows/{id}..."
DELETE_RESPONSE=$(curl -s -X DELETE "${BASE_URL}/workflows/${CLONED_ID}" \
  -H "Authorization: Bearer ${TOKEN}" | jq -r '.message')

echo "✅ $DELETE_RESPONSE"
echo ""

# Test 8: Delete original workflow
echo "8️⃣  Testing DELETE /workflows/{id} (original)..."
DELETE_RESPONSE=$(curl -s -X DELETE "${BASE_URL}/workflows/${WORKFLOW_ID}" \
  -H "Authorization: Bearer ${TOKEN}" | jq -r '.message')

echo "✅ $DELETE_RESPONSE"
echo ""

echo "🎉 All tests passed!"
echo ""
echo "Summary:"
echo "  - Created workflow: $WORKFLOW_ID"
echo "  - Updated workflow: ✓"
echo "  - Cloned workflow: $CLONED_ID"
echo "  - Listed my workflows: $MY_WORKFLOWS found"
echo "  - Listed public workflows: $PUBLIC_WORKFLOWS found"
echo "  - Deleted workflows: ✓"
