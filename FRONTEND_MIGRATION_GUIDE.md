# Frontend Migration Guide: Aligning with Firestore Backend

**Audience**: AI Coding Assistants  
**Purpose**: Step-by-step guide to migrate frontend code to work with the new Firestore-based backend  
**Backend Version**: Firestore + GCS migration (December 2025)  
**Production API**: https://veo-api-otfo2ctxma-uc.a.run.app

---

## 🎯 Migration Overview

### What Changed in the Backend

The backend migrated from file-based storage to **Firestore + Google Cloud Storage (GCS)**:

| **Component** | **Old Architecture** | **New Architecture** |
|---------------|---------------------|---------------------|
| **Asset Storage** | Local files | GCS bucket (`genmediastudio-assets`) |
| **Asset Metadata** | In-memory/JSON | Firestore collection (`assets`) |
| **Workflows** | Local files | Firestore collection (`workflows`) |
| **URLs** | Direct blob paths exposed | Signed URLs resolved server-side |
| **Authentication** | Custom auth | Firebase Auth (unchanged) |

### Breaking Changes

1. **Asset responses no longer include `blob_path`** - use `url` field instead
2. **Workflow nodes use asset references** - asset IDs resolve to URLs server-side
3. **Thumbnail handling changed** - workflows store `thumbnail_ref` (asset ID), not direct URLs
4. **List endpoints simplified** - workflows list no longer includes full nodes/edges (performance)

---

## 📋 Step-by-Step Migration Guide

### **Step 1: Update Asset/Library Data Models**

#### Old Frontend Model (Before)
```typescript
interface Asset {
  id: string;
  blob_path: string;  // ❌ No longer exists
  asset_type: string;
  prompt?: string;
  created_at: string;
  mime_type: string;
  seed?: number;  // ❌ Not stored in Firestore
  settings?: Record<string, any>;  // ❌ Not stored in Firestore
}
```

#### New Frontend Model (After)
```typescript
interface Asset {
  id: string;
  url: string;  // ✅ Use this instead of blob_path
  asset_type: string;  // "image" | "video"
  prompt?: string;
  created_at: string;  // ISO 8601 string
  mime_type: string;  // e.g., "image/png", "video/mp4"
  user_id?: string;  // Owner's Firebase UID
}
```

#### Migration Actions
- [ ] Replace all references to `asset.blob_path` with `asset.url`
- [ ] Remove usage of `seed` and `settings` fields (not returned by API)
- [ ] Update TypeScript interfaces/types
- [ ] Search codebase for `blob_path` and replace with `url`

**Example Code Change**:
```typescript
// Before
const imageUrl = asset.blob_path;

// After  
const imageUrl = asset.url;
```

---

### **Step 2: Update Workflow Data Models**

#### Old Workflow Model (Before)
```typescript
interface Workflow {
  id: string;
  name: string;
  description?: string;
  is_public: boolean;
  thumbnail?: string;  // ❌ Direct URL
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  // ... timestamps
}
```

#### New Workflow Model (After)
```typescript
interface Workflow {
  id: string;
  name: string;
  description: string;
  is_public: boolean;
  thumbnail_ref?: string;  // ✅ Asset ID reference (not URL)
  thumbnail?: string;  // ✅ Resolved URL (only in GET /workflows/{id})
  created_at: string;  // ISO 8601
  updated_at: string;  // ISO 8601
  user_id: string;
  user_email: string;
  node_count: number;
  edge_count: number;
  nodes: WorkflowNode[];  // ⚠️ Only in GET /workflows/{id}, not in list
  edges: WorkflowEdge[];  // ⚠️ Only in GET /workflows/{id}, not in list
}
```

#### Migration Actions
- [ ] Add `thumbnail_ref`, `user_id`, `user_email`, `node_count`, `edge_count` fields
- [ ] Update list view to not expect `nodes`/`edges` in response
- [ ] Handle thumbnail resolution (see Step 4)
- [ ] Update timestamp parsing to handle ISO 8601 strings

**Example Code Change**:
```typescript
// Before - List endpoint returned full workflows
const workflows: Workflow[] = await api.getWorkflows();
workflows.forEach(wf => console.log(wf.nodes));  // ❌ Won't work

// After - List returns metadata only
const workflows: WorkflowListItem[] = await api.getWorkflows();
// To get full workflow with nodes/edges:
const fullWorkflow = await api.getWorkflow(workflowId);
console.log(fullWorkflow.nodes);  // ✅ Works
```

---

### **Step 3: Update Asset References in Workflow Nodes**

#### How Asset References Work

Workflow nodes store **asset IDs** as references. The backend resolves these to **signed URLs** when you GET a workflow.

#### Node Data Structure (Before)
```typescript
interface WorkflowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: {
    prompt?: string;
    imageUrl?: string;  // ❌ Direct URL
    videoUrl?: string;  // ❌ Direct URL
    // ... other fields
  };
}
```

#### Node Data Structure (After)
```typescript
interface WorkflowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: {
    prompt?: string;
    
    // Asset references (IDs) - stored in Firestore
    imageRef?: string;  // Asset ID
    videoRef?: string;  // Asset ID
    firstFrameRef?: string;  // Asset ID
    lastFrameRef?: string;  // Asset ID
    
    // Resolved URLs - added by backend when fetching
    imageUrl?: string;  // Resolved from imageRef
    videoUrl?: string;  // Resolved from videoRef
    firstFrameUrl?: string;  // Resolved from firstFrameRef
    lastFrameUrl?: string;  // Resolved from lastFrameRef
    
    // Existence flags - tells you if asset still exists
    imageRefExists?: boolean;
    videoRefExists?: boolean;
    firstFrameRefExists?: boolean;
    lastFrameRefExists?: boolean;
    
    // Outputs work the same way
    outputs?: {
      imageRef?: string;
      imageUrl?: string;  // Resolved
      imageRefExists?: boolean;
      videoRef?: string;
      videoUrl?: string;  // Resolved
      videoRefExists?: boolean;
    };
  };
}
```

#### Migration Actions

##### When Saving a Workflow (Create/Update)
- [ ] Store asset IDs in `*Ref` fields (e.g., `imageRef`, `videoRef`)
- [ ] Do NOT send `*Url` fields to backend (they are computed server-side)
- [ ] Remove any `*RefExists` flags before saving (backend ignores them)

**Example Code**:
```typescript
// When user selects an asset from library
async function addAssetToNode(nodeId: string, asset: Asset) {
  const node = workflow.nodes.find(n => n.id === nodeId);
  
  // ✅ Correct: Store asset ID as reference
  node.data.imageRef = asset.id;
  
  // ❌ Wrong: Don't store URL directly
  // node.data.imageUrl = asset.url;
  
  await saveWorkflow(workflow);
}
```

##### When Loading a Workflow (GET)
- [ ] Read URLs from `*Url` fields for display
- [ ] Check `*RefExists` flags to show "Asset deleted" warnings
- [ ] Keep `*Ref` fields in state (needed when saving later)

**Example Code**:
```typescript
// When displaying a node's image
function NodeDisplay({ node }: { node: WorkflowNode }) {
  const imageUrl = node.data.imageUrl;
  const imageExists = node.data.imageRefExists;
  
  if (!imageExists) {
    return <div>⚠️ Referenced asset was deleted</div>;
  }
  
  return imageUrl ? <img src={imageUrl} /> : <div>No image</div>;
}
```

---

### **Step 4: Handle Workflow Thumbnails**

#### Thumbnail Resolution

- Workflows store `thumbnail_ref` (an asset ID)
- When you GET a specific workflow, backend adds `thumbnail` (resolved URL)
- List endpoints return `thumbnail_ref` only (you must resolve separately if needed)

#### Migration Actions

##### Option A: Don't Show Thumbnails in List View (Simplest)
```typescript
// Just ignore thumbnail_ref in list view
function WorkflowCard({ workflow }: { workflow: WorkflowListItem }) {
  return (
    <div>
      <h3>{workflow.name}</h3>
      {/* No thumbnail in list view */}
    </div>
  );
}
```

##### Option B: Resolve Thumbnails for List View (More Complex)
```typescript
// Fetch thumbnails separately if needed
async function loadWorkflowsWithThumbnails() {
  const workflows = await api.listWorkflows('my');
  
  // For each workflow with thumbnail_ref, fetch asset
  const withThumbnails = await Promise.all(
    workflows.map(async (wf) => {
      if (wf.thumbnail_ref) {
        try {
          const asset = await api.getAsset(wf.thumbnail_ref);
          return { ...wf, thumbnail: asset.url };
        } catch {
          return wf;  // Asset deleted or inaccessible
        }
      }
      return wf;
    })
  );
  
  return withThumbnails;
}
```

##### When Viewing a Single Workflow
```typescript
// Backend already resolves thumbnail URL
const workflow = await api.getWorkflow(workflowId);
const thumbnailUrl = workflow.thumbnail;  // Already resolved!
```

---

### **Step 5: Update API Client Methods**

#### Library/Asset Endpoints

**GET `/library` - List Assets**
```typescript
interface LibraryResponse {
  assets: Asset[];
  count: number;
}

async function listAssets(assetType?: string, limit: number = 50): Promise<LibraryResponse> {
  const params = new URLSearchParams();
  if (assetType) params.append('asset_type', assetType);
  params.append('limit', limit.toString());
  
  const response = await fetch(`${API_URL}/library?${params}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.json();
}
```

**POST `/library/save` - Save Asset**
```typescript
interface SaveAssetRequest {
  data: string;  // base64 encoded
  asset_type: string;  // "image" | "video"
  prompt?: string;
  mime_type?: string;
}

async function saveAsset(request: SaveAssetRequest): Promise<Asset> {
  const response = await fetch(`${API_URL}/library/save`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(request)
  });
  return response.json();
}
```

**GET `/library/{asset_id}` - Get Asset**
```typescript
async function getAsset(assetId: string): Promise<Asset> {
  const response = await fetch(`${API_URL}/library/${assetId}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  
  if (!response.ok) {
    if (response.status === 404) throw new Error('Asset not found');
    if (response.status === 403) throw new Error('Access denied');
    throw new Error('Failed to fetch asset');
  }
  
  return response.json();
}
```

**DELETE `/library/{asset_id}` - Delete Asset**
```typescript
async function deleteAsset(assetId: string): Promise<{ status: string }> {
  const response = await fetch(`${API_URL}/library/${assetId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.json();
}
```

#### Workflow Endpoints

**GET `/workflows?scope={my|public}` - List Workflows**
```typescript
interface WorkflowListItem {
  id: string;
  name: string;
  description: string;
  is_public: boolean;
  thumbnail_ref?: string;  // Asset ID
  created_at: string;
  updated_at: string;
  user_id: string;
  user_email: string;
  node_count: number;
  edge_count: number;
  // ⚠️ No nodes or edges in list response!
}

async function listWorkflows(scope: 'my' | 'public'): Promise<WorkflowListItem[]> {
  const response = await fetch(`${API_URL}/workflows?scope=${scope}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  
  const data = await response.json();
  return data.workflows;
}
```

**POST `/workflows` - Create Workflow**
```typescript
interface SaveWorkflowRequest {
  name: string;
  description?: string;
  is_public: boolean;
  nodes: WorkflowNode[];  // Include asset refs, not URLs
  edges: WorkflowEdge[];
}

async function createWorkflow(request: SaveWorkflowRequest): Promise<{ id: string }> {
  // ⚠️ Strip resolved URLs before sending
  const cleanedNodes = request.nodes.map(node => ({
    ...node,
    data: stripResolvedUrls(node.data)
  }));
  
  const response = await fetch(`${API_URL}/workflows`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({
      ...request,
      nodes: cleanedNodes
    })
  });
  
  return response.json();
}

// Helper to remove computed fields before saving
function stripResolvedUrls(data: any): any {
  const cleaned = { ...data };
  
  // Remove all *Url and *Exists fields (server computes these)
  const keysToRemove = Object.keys(cleaned).filter(
    k => k.endsWith('Url') || k.endsWith('Exists')
  );
  keysToRemove.forEach(k => delete cleaned[k]);
  
  // Also clean outputs
  if (cleaned.outputs) {
    cleaned.outputs = stripResolvedUrls(cleaned.outputs);
  }
  
  return cleaned;
}
```

**GET `/workflows/{workflow_id}` - Get Workflow**
```typescript
async function getWorkflow(workflowId: string): Promise<Workflow> {
  const response = await fetch(`${API_URL}/workflows/${workflowId}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  
  if (!response.ok) {
    if (response.status === 404) throw new Error('Workflow not found');
    if (response.status === 403) throw new Error('Access denied');
    throw new Error('Failed to fetch workflow');
  }
  
  // Response includes resolved URLs in nodes
  return response.json();
}
```

**PUT `/workflows/{workflow_id}` - Update Workflow**
```typescript
async function updateWorkflow(
  workflowId: string,
  request: SaveWorkflowRequest
): Promise<{ message: string }> {
  // Strip URLs like in createWorkflow
  const cleanedNodes = request.nodes.map(node => ({
    ...node,
    data: stripResolvedUrls(node.data)
  }));
  
  const response = await fetch(`${API_URL}/workflows/${workflowId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({
      ...request,
      nodes: cleanedNodes
    })
  });
  
  return response.json();
}
```

**DELETE `/workflows/{workflow_id}` - Delete Workflow**
```typescript
async function deleteWorkflow(workflowId: string): Promise<{ message: string }> {
  const response = await fetch(`${API_URL}/workflows/${workflowId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.json();
}
```

**POST `/workflows/{workflow_id}/clone` - Clone Workflow**
```typescript
async function cloneWorkflow(workflowId: string): Promise<{ id: string }> {
  const response = await fetch(`${API_URL}/workflows/${workflowId}/clone`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    }
  });
  return response.json();
}
```

---

### **Step 6: Update Generation Flow (Auto-Save Assets)**

#### How Auto-Save Works

When generating images/videos, the backend **automatically saves results to the library** and returns asset metadata instead of raw base64 data.

**POST `/generation/image` - Generate Image**

**Response** (Changed):
```typescript
// Before
interface ImageResponse {
  images: string[];  // base64 strings
}

// After - Same structure, but now includes metadata
interface ImageResponse {
  images: string[];  // Still base64 for immediate display
  // ⚠️ But user's library now has these images saved automatically!
}
```

**POST `/generation/video/status` - Check Video Status**

**Response** (Changed):
```typescript
interface VideoStatusResponse {
  status: string;  // "pending" | "completed" | "failed"
  video_base64?: string;  // For immediate display when completed
  storage_uri?: string;  // ❌ Deprecated - ignore this
  progress?: number;
  error?: any;
  message?: string;
  // ⚠️ If status is "completed", asset is auto-saved to library
}
```

#### Migration Actions

##### After Image Generation
```typescript
async function generateAndDisplayImage(prompt: string) {
  const response = await fetch(`${API_URL}/generation/image`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ prompt })
  });
  
  const { images } = await response.json();
  
  // Display image immediately
  displayImage(images[0]);
  
  // ✅ Images are already in library! No need to manually save
  // Refresh library to show new assets
  refreshLibrary();
}
```

##### After Video Generation
```typescript
async function pollVideoStatus(operationName: string, prompt: string) {
  const response = await fetch(`${API_URL}/generation/video/status`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ operation_name: operationName, prompt })
  });
  
  const status = await response.json();
  
  if (status.status === 'completed') {
    // Display video from base64
    displayVideo(status.video_base64);
    
    // ✅ Video is already saved to library with prompt metadata
    refreshLibrary();
  }
}
```

---

### **Step 7: Handle Asset Deletion Edge Cases**

#### Deleted Asset References

When a workflow references an asset that has been deleted:
- `*Ref` field still contains the asset ID
- `*Url` field is `null`
- `*RefExists` field is `false`

#### Migration Actions

**Display Warnings for Deleted Assets**:
```typescript
function NodeAssetDisplay({ node }: { node: WorkflowNode }) {
  const { imageRef, imageUrl, imageRefExists } = node.data;
  
  if (imageRef && !imageRefExists) {
    return (
      <div className="asset-deleted-warning">
        ⚠️ Referenced image (ID: {imageRef}) was deleted
        <button onClick={() => clearReference(node.id, 'imageRef')}>
          Clear Reference
        </button>
      </div>
    );
  }
  
  if (imageUrl) {
    return <img src={imageUrl} alt="Node asset" />;
  }
  
  return <div>No image selected</div>;
}
```

**Clear Deleted References**:
```typescript
function clearDeletedReferences(workflow: Workflow): Workflow {
  const cleanedNodes = workflow.nodes.map(node => {
    const data = { ...node.data };
    
    // Remove refs that no longer exist
    Object.keys(data).forEach(key => {
      if (key.endsWith('Ref')) {
        const existsKey = `${key}Exists`;
        if (data[existsKey] === false) {
          delete data[key];  // Remove the ref
        }
      }
    });
    
    return { ...node, data };
  });
  
  return { ...workflow, nodes: cleanedNodes };
}
```

---

### **Step 8: Update Error Handling**

#### Common Error Responses

```typescript
// 404 - Not Found
{
  "detail": "Asset not found"
}

// 403 - Forbidden
{
  "detail": "Access denied"
}

// 400 - Bad Request
{
  "detail": "Workflow name is required"
}

// 500 - Internal Server Error
{
  "detail": "Failed to save asset"
}
```

#### Migration Actions

**Centralized Error Handler**:
```typescript
async function handleApiError(response: Response): Promise<never> {
  const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
  
  switch (response.status) {
    case 404:
      throw new NotFoundError(error.detail);
    case 403:
      throw new ForbiddenError(error.detail);
    case 400:
      throw new ValidationError(error.detail);
    case 401:
      throw new AuthError('Authentication required');
    default:
      throw new ApiError(error.detail || 'Server error');
  }
}

// Use in API calls
async function getAsset(assetId: string): Promise<Asset> {
  const response = await fetch(`${API_URL}/library/${assetId}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  
  if (!response.ok) {
    await handleApiError(response);
  }
  
  return response.json();
}
```

---

### **Step 9: Testing Checklist**

#### Asset/Library Tests
- [ ] List assets returns URLs (not blob_paths)
- [ ] Save asset returns valid URL
- [ ] Asset URL is publicly accessible (fetch succeeds)
- [ ] Delete asset removes from library
- [ ] Filter by asset_type works correctly
- [ ] Can fetch asset by ID

#### Workflow Tests
- [ ] List workflows returns metadata only (no nodes/edges)
- [ ] Get workflow by ID includes resolved asset URLs
- [ ] Create workflow with asset refs saves correctly
- [ ] Update workflow preserves asset refs
- [ ] Deleted asset shows warning (`*RefExists: false`)
- [ ] Clone workflow duplicates refs correctly
- [ ] Delete workflow succeeds

#### Generation Tests
- [ ] Image generation auto-saves to library
- [ ] Video generation auto-saves when complete
- [ ] Library shows new assets after generation
- [ ] Generated assets have correct prompt metadata

#### Edge Cases
- [ ] Loading workflow with deleted assets shows warnings
- [ ] Saving workflow strips resolved URLs
- [ ] 404/403 errors display user-friendly messages
- [ ] Expired signed URLs refresh (if implemented)

---

## 🔍 Common Migration Patterns

### Pattern 1: Asset Selection Flow

**Before (using blob_path)**:
```typescript
// User selects asset, store URL directly
node.data.imageUrl = selectedAsset.blob_path;
```

**After (using asset references)**:
```typescript
// Store asset ID as reference
node.data.imageRef = selectedAsset.id;

// When displaying, use resolved URL from GET response
const displayUrl = node.data.imageUrl;  // Backend resolves this
```

### Pattern 2: Workflow Save/Load Cycle

**Save**:
```typescript
// Remove computed fields before saving
const savePayload = {
  ...workflow,
  nodes: workflow.nodes.map(node => ({
    ...node,
    data: stripResolvedUrls(node.data)  // Removes *Url, *Exists
  }))
};

await api.updateWorkflow(workflowId, savePayload);
```

**Load**:
```typescript
// Backend returns nodes with resolved URLs
const workflow = await api.getWorkflow(workflowId);

// Can display immediately
workflow.nodes.forEach(node => {
  console.log(node.data.imageUrl);  // Resolved by backend
});
```

### Pattern 3: Handling Missing Assets

**Display Logic**:
```typescript
function AssetPreview({ assetRef, assetUrl, assetExists }) {
  if (!assetRef) {
    return <EmptyState />;
  }
  
  if (!assetExists) {
    return <DeletedAssetWarning assetId={assetRef} />;
  }
  
  if (assetUrl) {
    return <img src={assetUrl} />;
  }
  
  return <LoadingSpinner />;
}
```

---

## 📚 Additional Resources

### Backend API Documentation
- Health: `GET /health`
- Library: `GET /library`, `POST /library/save`, `GET /library/{id}`, `DELETE /library/{id}`
- Workflows: `GET /workflows`, `POST /workflows`, `GET /workflows/{id}`, `PUT /workflows/{id}`, `DELETE /workflows/{id}`, `POST /workflows/{id}/clone`
- Generation: `POST /generation/image`, `POST /generation/video`, `POST /generation/video/status`

### Key Backend Files (for reference)
- API Schemas: [`app/schemas.py`](./app/schemas.py)
- Library Service: [`app/services/library_firestore.py`](./app/services/library_firestore.py)
- Workflow Service: [`app/services/workflow_firestore.py`](./app/services/workflow_firestore.py)
- Library Router: [`app/routers/library.py`](./app/routers/library.py)
- Workflow Router: [`app/routers/workflows.py`](./app/routers/workflows.py)

### E2E Tests (reference implementations)
- Library Tests: [`tests/e2e/test_library.py`](./tests/e2e/test_library.py)
- Workflow Tests: [`tests/e2e/test_workflow.py`](./tests/e2e/test_workflow.py)

---

## ✅ Migration Completion Checklist

### Phase 1: Data Models
- [ ] Updated Asset interface (removed `blob_path`, added `url`)
- [ ] Updated Workflow interface (added metadata fields)
- [ ] Updated WorkflowNode data structure (asset refs pattern)
- [ ] Created TypeScript types for all API responses

### Phase 2: API Client
- [ ] Updated all library endpoints
- [ ] Updated all workflow endpoints
- [ ] Implemented `stripResolvedUrls` helper
- [ ] Added proper error handling

### Phase 3: UI Components
- [ ] Updated asset display components to use `url`
- [ ] Updated workflow list (handle missing nodes/edges)
- [ ] Added deleted asset warnings
- [ ] Implemented reference cleanup UI

### Phase 4: Generation Flow
- [ ] Updated post-generation logic (auto-save awareness)
- [ ] Added library refresh after generation
- [ ] Removed manual save buttons (if applicable)

### Phase 5: Testing
- [ ] Tested asset save/retrieve/delete
- [ ] Tested workflow save/load with asset refs
- [ ] Tested deleted asset handling
- [ ] Tested error scenarios (404, 403)
- [ ] End-to-end testing with production API

### Phase 6: Cleanup
- [ ] Removed all `blob_path` references
- [ ] Removed unused fields (`seed`, `settings`)
- [ ] Updated documentation
- [ ] Code review for migration patterns

---

## 🚨 Critical Gotchas

1. **Never send `*Url` fields when saving workflows** - They are computed server-side
2. **List workflows endpoint doesn't include nodes/edges** - Fetch individual workflow for full data
3. **Asset URLs are signed** - They expire after 7 days (consider refreshing logic if needed)
4. **Auto-save happens during generation** - Don't duplicate assets in library
5. **Asset references can become orphaned** - Always check `*RefExists` flags

---

## 🆘 Troubleshooting

### "Asset not found" when loading workflow
**Cause**: Referenced asset was deleted  
**Solution**: Check `*RefExists` flags, show warning, allow user to clear reference

### Workflow save fails with "data too large"
**Cause**: Sending resolved URLs in payload  
**Solution**: Use `stripResolvedUrls()` before saving

### Images not loading in workflow
**Cause**: Using `*Ref` instead of `*Url` for display  
**Solution**: Display using `*Url` fields (resolved by backend)

### List endpoint missing workflow details
**Cause**: List returns metadata only, not full workflow  
**Solution**: Call `GET /workflows/{id}` to fetch full workflow with nodes/edges

---

**Document Version**: 1.0  
**Last Updated**: December 16, 2025  
**Backend Compatibility**: Firestore Migration (v2.0)
