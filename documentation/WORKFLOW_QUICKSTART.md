# Workflow API - Quick Reference

## 🚀 Quick Start

### 1. Setup Storage (One-time)
```bash
./scripts/setup_workflow_storage.sh
```

### 2. Deploy
```bash
./scripts/deploy.sh
```

### 3. Test
```bash
# Get a Firebase token first
python scripts/get_test_token.py

# Run all tests
./scripts/test_workflow_api.sh <your-token>
```

---

## 📡 API Endpoints

Base URL: `https://veo-api-82187245577.us-central1.run.app`

All endpoints require: `Authorization: Bearer <firebase-token>`

### Create Workflow
```bash
POST /workflows/save
```
**Body:**
```json
{
  "name": "My Workflow",
  "description": "Optional description",
  "is_public": false,
  "nodes": [...],
  "edges": [...]
}
```
**Response:** `{ "id": "wf_1734300000_abc" }`

---

### List Workflows
```bash
GET /workflows?scope=my      # Your workflows
GET /workflows?scope=public  # Public workflows
```
**Response:**
```json
{
  "workflows": [
    {
      "id": "wf_...",
      "name": "...",
      "nodes": [...],
      "edges": [...],
      ...
    }
  ]
}
```

---

### Get Workflow
```bash
GET /workflows/{workflow_id}
```
**Response:** Full workflow object

---

### Update Workflow
```bash
PUT /workflows/{workflow_id}
```
**Body:** Same as create
**Response:** `{ "message": "Workflow updated successfully" }`

---

### Delete Workflow
```bash
DELETE /workflows/{workflow_id}
```
**Response:** `{ "message": "Workflow deleted successfully" }`

---

### Clone Workflow
```bash
POST /workflows/{workflow_id}/clone
```
**Response:** `{ "id": "wf_new_..." }`

---

## 🔒 Access Control

| Action | Owner | Public | Private (Other User) |
|--------|-------|--------|----------------------|
| View   | ✅    | ✅     | ❌                   |
| Update | ✅    | ❌     | ❌                   |
| Delete | ✅    | ❌     | ❌                   |
| Clone  | ✅    | ✅     | ❌                   |

---

## ✅ Validation Rules

- **Name:** Required, max 100 characters
- **Nodes:** Min 1, max 100
- **Description:** Optional
- **Public:** Boolean, default `false`

---

## 📁 File Structure

```
app/
├── schemas.py              # Workflow models added
├── config.py              # workflows_bucket setting added
├── main.py                # workflow router mounted
├── routers/
│   └── workflow.py        # 🆕 All workflow endpoints
└── services/
    └── workflow.py        # 🆕 Business logic & GCS integration

scripts/
├── setup_workflow_storage.sh  # 🆕 GCS setup
└── test_workflow_api.sh       # 🆕 API testing

tests/unit/
└── test_workflow_service.py   # 🆕 Unit tests

WORKFLOW_API.md                # 🆕 Full documentation
```

---

## 🐛 Troubleshooting

### Check logs
```bash
gcloud run logs read --service=veo-api --limit=50
```

### Verify bucket
```bash
gsutil ls -r gs://veo-workflows-remarkablenotion/
```

### Test endpoints
```bash
curl https://veo-api-.../workflows?scope=my \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📚 More Info

- Full docs: [WORKFLOW_API.md](WORKFLOW_API.md)
- API docs: https://veo-api-.../docs
- Tests: `pytest tests/unit/test_workflow_service.py`
