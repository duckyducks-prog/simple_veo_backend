# Workflow Storage API - Implementation Guide

## 🎉 Implementation Complete!

The Workflow Storage API has been successfully implemented with all required endpoints.

## 📋 What Was Implemented

### 1. **Data Models** ([app/schemas.py](app/schemas.py))
- `WorkflowNode` - Represents a node in the workflow graph
- `WorkflowEdge` - Represents connections between nodes
- `SaveWorkflowRequest` - Request model for creating workflows
- `UpdateWorkflowRequest` - Request model for updating workflows
- `WorkflowResponse` - Complete workflow response with metadata
- `WorkflowListResponse` - List of workflows
- `WorkflowIdResponse` - Response with workflow ID
- `WorkflowMessageResponse` - Generic success message

### 2. **Service Layer** ([app/services/workflow.py](app/services/workflow.py))
Complete `WorkflowService` class with:
- GCS bucket integration
- Index management for fast queries
- Full CRUD operations
- Access control validation
- Input validation (name length, node limits, etc.)

### 3. **API Endpoints** ([app/routers/workflow.py](app/routers/workflow.py))
All 7 required endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/workflows/save` | Create a new workflow |
| `GET` | `/workflows?scope=my` | List user's workflows |
| `GET` | `/workflows?scope=public` | List public workflows |
| `GET` | `/workflows/{workflow_id}` | Get specific workflow |
| `PUT` | `/workflows/{workflow_id}` | Update workflow |
| `DELETE` | `/workflows/{workflow_id}` | Delete workflow |
| `POST` | `/workflows/{workflow_id}/clone` | Clone workflow |

### 4. **Configuration** ([app/config.py](app/config.py))
- Added `workflows_bucket` setting (defaults to `veo-workflows-remarkablenotion`)

### 5. **Router Integration** ([app/main.py](app/main.py))
- Workflow router mounted at `/workflows` prefix

## 🚀 Deployment Steps

### Step 1: Set Up GCS Bucket

Run the provided setup script:

```bash
cd scripts
chmod +x setup_workflow_storage.sh
./setup_workflow_storage.sh
```

This script will:
- Create the GCS bucket `veo-workflows-remarkablenotion`
- Enable versioning
- Configure CORS
- Grant service account permissions
- Create initial directory structure
- Set lifecycle policies

**Manual Setup (Alternative):**

```bash
# 1. Create bucket
gsutil mb -l us-central1 gs://veo-workflows-remarkablenotion

# 2. Enable versioning
gsutil versioning set on gs://veo-workflows-remarkablenotion

# 3. Grant service account access
gsutil iam ch \
  serviceAccount:veo-api-service-account@remarkablenotion.iam.gserviceaccount.com:objectAdmin \
  gs://veo-workflows-remarkablenotion

# 4. Create initial index
echo '{}' | gsutil cp - gs://veo-workflows-remarkablenotion/workflows/metadata/index.json
```

### Step 2: Update Environment Variables (Optional)

If you want to use a different bucket name, add to your `.env` file:

```bash
WORKFLOWS_BUCKET=your-custom-bucket-name
```

### Step 3: Deploy to Cloud Run

```bash
# From the project root
./scripts/deploy.sh
```

Or manually:

```bash
gcloud run deploy veo-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Step 4: Test the Endpoints

Get a test token:
```bash
python scripts/get_test_token.py
export TOKEN="<your-token>"
```

**Test save workflow:**
```bash
curl -X POST https://veo-api-82187245577.us-central1.run.app/workflows/save \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Workflow",
    "description": "My first workflow",
    "is_public": false,
    "nodes": [
      {
        "id": "node-1",
        "type": "imageInput",
        "position": {"x": 100, "y": 100},
        "data": {"label": "Image Input"}
      }
    ],
    "edges": []
  }'
```

Expected response:
```json
{
  "id": "wf_1734300000_abc123"
}
```

**Test list workflows:**
```bash
curl "https://veo-api-82187245577.us-central1.run.app/workflows?scope=my" \
  -H "Authorization: Bearer $TOKEN"
```

**Test get workflow:**
```bash
curl "https://veo-api-82187245577.us-central1.run.app/workflows/wf_1734300000_abc123" \
  -H "Authorization: Bearer $TOKEN"
```

**Test list public workflows:**
```bash
curl "https://veo-api-82187245577.us-central1.run.app/workflows?scope=public" \
  -H "Authorization: Bearer $TOKEN"
```

**Test update workflow:**
```bash
curl -X PUT "https://veo-api-82187245577.us-central1.run.app/workflows/wf_1734300000_abc123" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Workflow",
    "description": "Updated description",
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
  }'
```

**Test clone workflow:**
```bash
curl -X POST "https://veo-api-82187245577.us-central1.run.app/workflows/wf_1734300000_abc123/clone" \
  -H "Authorization: Bearer $TOKEN"
```

**Test delete workflow:**
```bash
curl -X DELETE "https://veo-api-82187245577.us-central1.run.app/workflows/wf_1734300000_abc123" \
  -H "Authorization: Bearer $TOKEN"
```

## 🔒 Security Features

✅ **Implemented:**
- Firebase token verification on all endpoints
- Ownership checks for update/delete operations
- Access control for viewing workflows (public OR owner)
- Input validation:
  - Workflow name max 100 characters
  - Max 100 nodes per workflow
  - Min 1 node required
  - Name is required

✅ **Recommended (for production):**
- Add rate limiting (e.g., 100 req/min per user)
- Add pagination for list endpoints
- Add workflow size limits (max JSON size)
- Add user quotas (max workflows per user)

## 📊 Storage Architecture

```
gs://veo-workflows-remarkablenotion/
├── workflows/
│   ├── metadata/
│   │   └── index.json              # Fast lookup index
│   └── data/
│       ├── wf_1734300000_abc.json  # Full workflow data
│       ├── wf_1734300001_def.json
│       └── ...
└── thumbnails/                      # (Future feature)
    └── wf_1734300000_abc.png
```

### Index Structure
The index file contains lightweight metadata for fast filtering:

```json
{
  "wf_1734300000_abc": {
    "id": "wf_1734300000_abc",
    "name": "Product Workflow",
    "description": "...",
    "is_public": false,
    "user_id": "firebase_uid",
    "user_email": "user@example.com",
    "created_at": "2024-12-15T18:30:00Z",
    "updated_at": "2024-12-15T18:45:00Z",
    "node_count": 13,
    "edge_count": 12
  }
}
```

### Full Workflow Document
Complete workflow files include nodes and edges:

```json
{
  "id": "wf_1734300000_abc",
  "name": "Product Workflow",
  "description": "...",
  "is_public": false,
  "thumbnail": null,
  "created_at": "2024-12-15T18:30:00Z",
  "updated_at": "2024-12-15T18:45:00Z",
  "user_id": "firebase_uid",
  "user_email": "user@example.com",
  "node_count": 13,
  "edge_count": 12,
  "nodes": [...],
  "edges": [...]
}
```

## 🐛 Troubleshooting

### Issue: "Workflow bucket not found"
**Solution:** Run the setup script or create the bucket manually (see Step 1)

### Issue: "Permission denied" when accessing GCS
**Solution:** Verify service account has `objectAdmin` role on the bucket:
```bash
gsutil iam get gs://veo-workflows-remarkablenotion
```

### Issue: "Invalid token" errors
**Solution:** Generate a new test token:
```bash
python scripts/get_test_token.py
```

### Issue: Frontend still getting 404
**Solution:** 
1. Verify deployment was successful
2. Check Cloud Run logs: `gcloud run logs read --service=veo-api`
3. Test endpoints directly with curl (see Step 4)

### Check bucket contents:
```bash
gsutil ls -r gs://veo-workflows-remarkablenotion/
```

### View workflow index:
```bash
gsutil cat gs://veo-workflows-remarkablenotion/workflows/metadata/index.json | jq
```

### View a specific workflow:
```bash
gsutil cat gs://veo-workflows-remarkablenotion/workflows/data/wf_*.json | jq
```

## 📈 Performance Optimization

Current implementation includes:
- ✅ Lightweight index for fast filtering
- ✅ Separate metadata from full workflow data
- ✅ GCS versioning for data safety

**Future optimizations:**
- Add in-memory caching with 5-minute TTL
- Implement pagination (`?limit=20&offset=0`)
- Add compression for large workflows
- Use GCS signed URLs for thumbnails
- Implement batch operations

## 💰 Cost Estimation

GCS Storage pricing:
- **Storage:** $0.02/GB/month
- **Operations:** $0.05 per 10,000 operations

Example: 1,000 workflows @ 100KB each:
- Storage: ~100MB = $0.002/month
- Operations: ~10,000/month = $0.05/month
- **Total: ~$0.052/month** 💸

Much cheaper than Firestore ($0.18/GB) for document storage!

## 📚 API Documentation

Once deployed, view interactive API docs at:
- **Swagger UI:** https://veo-api-82187245577.us-central1.run.app/docs
- **ReDoc:** https://veo-api-82187245577.us-central1.run.app/redoc

## ✅ Checklist

Before going to production:
- [ ] Run setup script to create GCS bucket
- [ ] Deploy updated backend code
- [ ] Test all 7 endpoints
- [ ] Verify frontend integration
- [ ] Monitor Cloud Run logs
- [ ] Set up monitoring/alerts
- [ ] Consider adding rate limiting
- [ ] Add analytics/usage tracking
- [ ] Document for frontend team

## 🎯 Next Steps

1. **Run the setup script**
2. **Deploy to Cloud Run**
3. **Test with curl**
4. **Update frontend to use new endpoints**
5. **Monitor and optimize**

---

**Questions?** Check the inline documentation in the code or Cloud Run logs for debugging.
