# Firestore Migration Guide

**Status**: ✅ COMPLETED - December 2025  
**Note**: This document describes the completed migration. For current setup, see main README.

## Overview
Successfully migrated from GCS-only storage to a Firestore + GCS hybrid architecture.

## Architecture

### Before (GCS-only)
- **Workflows**: Stored as JSON files in GCS
- **Assets**: Base64-encoded data embedded in workflow nodes
- **Problem**: No efficient querying by user_id, index contention, pagination limitations

### After (Firestore + GCS)
- **Workflows**: Metadata in Firestore, queryable by user_id, is_public, created_at
- **Assets**: Metadata in Firestore, binary files in GCS with public URLs
- **References**: Workflows store `assetRef`, `imageRef`, `videoRef` instead of base64 data
- **URL Resolution**: Backend resolves asset IDs to URLs when loading workflows

## Firestore Schema

### Collection: `workflows`
```
/workflows/{workflow_id}
  - id: string
  - name: string
  - description: string
  - user_id: string (indexed)
  - user_email: string
  - is_public: boolean (indexed)
  - created_at: datetime (indexed)
  - updated_at: datetime
  - nodes: array (contains assetRef/imageRef/videoRef)
  - edges: array
  - version: string
```

### Collection: `assets`
```
/assets/{asset_id}
  - id: string
  - user_id: string (indexed)
  - asset_type: "image" | "video" (indexed)
  - blob_path: string (GCS path)
  - mime_type: string
  - created_at: datetime (indexed)
  - prompt: string (optional)
  - source: "upload" | "generated"
  - workflow_id: string (optional)
```

## Changes Made

### New Files
1. **`app/firestore.py`** - Firestore client singleton and collection constants
2. **`app/services/workflow_firestore.py`** - Workflow service with Firestore backend (~320 lines)
   - CRUD operations: create, list, get, update, delete, clone
   - `_resolve_asset_urls()` - Resolves asset references to URLs on workflow load
   - Access control: owner or public workflows
3. **`app/services/library_firestore.py`** - Asset library with Firestore metadata (~240 lines)
   - Save/list/get/delete asset operations
   - GCS upload/download for binary files
   - `resolve_asset_urls()` - Batch URL resolution

### Updated Files
1. **`app/routers/workflow.py`** - Now uses `WorkflowServiceFirestore`
2. **`app/routers/library.py`** - Now uses `LibraryServiceFirestore`
3. **`app/services/generation.py`** - Auto-saves images/videos to library using Firestore service

### Preserved Files
- `app/services/workflow.py` - Original GCS-based service (backward compatibility)
- `app/services/library.py` - Original GCS-based service (backward compatibility)

## Testing Locally

### Prerequisites
1. Ensure you have access to the Firestore database in project `remarkablenotion`
2. Service account credentials should already be configured via `GOOGLE_APPLICATION_CREDENTIALS`

### Option 1: Test Against Dev Firestore
```bash
# Start the server
cd /Users/ldebortolialves/backend/simple_veo_backend
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 2: Use Firestore Emulator (Recommended for Development)
```bash
# Install Firestore emulator if not already installed
gcloud components install cloud-firestore-emulator

# Start the emulator (in a separate terminal)
gcloud beta emulators firestore start --host-port=localhost:8080

# Set environment variable to use emulator
export FIRESTORE_EMULATOR_HOST=localhost:8080

# Start your server
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Test Workflow
1. **Create a workflow** with asset references:
   ```bash
   curl -X POST http://localhost:8000/workflows/save \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Test Workflow",
       "description": "Testing Firestore migration",
       "is_public": false,
       "nodes": [
         {
           "id": "node1",
           "type": "image",
           "data": {
             "imageRef": "asset-id-here",
             "prompt": "A beautiful sunset"
           }
         }
       ],
       "edges": []
     }'
   ```

2. **List workflows**:
   ```bash
   curl -X GET "http://localhost:8000/workflows?scope=my" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. **Get workflow** (URLs should be resolved):
   ```bash
   curl -X GET "http://localhost:8000/workflows/{workflow_id}" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

4. **Generate image** (auto-saves to library):
   ```bash
   curl -X POST http://localhost:8000/generate/image \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "A beautiful mountain landscape"
     }'
   ```

5. **List library assets**:
   ```bash
   curl -X GET http://localhost:8000/library \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

## Key Features

### Automatic URL Resolution
When loading a workflow, the service automatically:
1. Scans all nodes for `assetRef`, `imageRef`, `videoRef` fields
2. Looks up each asset in Firestore
3. Resolves the blob_path to a public GCS URL
4. Handles missing assets gracefully (logs warning, skips resolution)

### Auto-Save to Library
The generation service automatically saves:
- Generated images → Library (asset_type="image", source="generated")
- Generated videos → Library (asset_type="video", source="generated")
- Prompt and workflow_id are stored with each asset

### Public URLs
Assets use public GCS URLs for now:
```
https://storage.googleapis.com/genmedia-assets-remarkablenotion/users/{user_id}/{asset_type}s/{asset_id}.{ext}
```

**Note**: Signed URLs are planned for future implementation (high priority).

## Migration Notes

### Existing GCS Workflows
- Old workflows stored in GCS are considered test data
- They are **not** automatically migrated
- New workflows will use Firestore going forward

### Access Control
- Workflows: Owner can read/update/delete, public workflows readable by all
- Assets: Owner only (for now)

### Pagination
- List workflows: Firestore supports proper pagination (via cursor)
- List assets: Supports limit parameter, can add pagination later

## Next Steps

1. ✅ Core migration complete
2. ⏳ Test locally with Firestore emulator or dev project
3. ⏳ Write comprehensive tests for Firestore services
4. 🔜 Deploy to Cloud Run (update environment variables if needed)
5. 🔜 Update frontend to work with asset references
6. 🔜 Implement signed URLs for asset security

## Troubleshooting

### Firebase Already Initialized Error
- This is expected and handled gracefully in `init_firebase()`
- The Firestore client reuses the existing Firebase app

### Permission Denied
- Ensure your service account has Firestore read/write permissions
- For emulator: No auth needed, works locally

### Asset Not Found Warning
- If a workflow references an asset that doesn't exist, it will log a warning
- The workflow will still load, but the asset reference won't be resolved to a URL

## Questions?
- Old workflows in GCS: Ignored (test data)
- Asset URL strategy: Public URLs (signed URLs coming later)
- Backend resolves URLs: Yes, on workflow load
- Frontend changes: Will be addressed after backend is stable
