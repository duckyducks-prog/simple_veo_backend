# End-to-End Tests

These tests validate the complete backend functionality with real cloud services (Firestore, GCS, Firebase Auth).

## Quick Setup

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Download serviceAccountKey.json from Firebase Console
#    Project Settings > Service Accounts > Generate New Private Key

# 3. Edit .env and add your FIREBASE_API_KEY
#    Find in: Project Settings > General > Web API Key

# 4. Generate test token
python scripts/get_test_token.py

# 5. Export the token (copy the JWT token from script output)
export FIREBASE_TEST_TOKEN="<paste-jwt-token-here>"

# 6. Run tests against local server
export API_URL="http://localhost:8000"
uv run pytest tests/e2e/ --run-e2e -v

# Or against production (default)
# uv run pytest tests/e2e/ --run-e2e -v
```

## Prerequisites

1. **Firebase Service Account Key**: Download your Firebase service account key
   ```bash
   # Download from Firebase Console:
   # Project Settings > Service Accounts > Generate New Private Key
   # Save as serviceAccountKey.json in project root
   ```

2. **Firebase API Key**: Set your Firebase Web API key
   ```bash
   # Find in Firebase Console:
   # Project Settings > General > Web API Key
   export FIREBASE_API_KEY="your-web-api-key"
   ```

3. **Generate Test Token**: Get a valid Firebase authentication token
   ```bash
   # Ensure serviceAccountKey.json is in project root
   # Ensure FIREBASE_API_KEY is set in environment
   python scripts/get_test_token.py
   
   # Copy the token and export it:
   export FIREBASE_TEST_TOKEN="eyJhbGciOiJSUzI1NiIsImtpZCI..."
   ```

4. **Cloud Access**: Ensure you have access to:
   - Firebase project: `genmediastudio`
   - GCS bucket: `genmediastudio-assets`
   - Firestore collections: `workflows`, `assets`

## Running E2E Tests

E2E tests are skipped by default. Use the `--run-e2e` flag to execute them:

```bash
# Set required environment variables
export FIREBASE_TEST_TOKEN="<your-jwt-token>"

# Run against local server (default port 8000)
export API_URL="http://localhost:8000"
uv run pytest tests/e2e/ --run-e2e -v

# Run against production (Cloud Run)
export API_URL="https://veo-api-otfo2ctxma-uc.a.run.app"
uv run pytest tests/e2e/ --run-e2e -v

# Or use defaults (production URL)
uv run pytest tests/e2e/ --run-e2e -v

# Run specific test file
uv run pytest tests/e2e/test_workflow.py --run-e2e -v

# Run specific test
uv run pytest tests/e2e/test_workflow.py::TestWorkflowE2E::test_workflow_crud_lifecycle --run-e2e -v
```

## Test Coverage

### Workflow Tests (`test_workflow.py`)

**TestWorkflowE2E**:
- `test_create_workflow` - Basic workflow creation
- `test_list_my_workflows` - List user's workflows (Firestore query by user_id)
- `test_list_public_workflows` - List public workflows (Firestore query by is_public)
- `test_workflow_crud_lifecycle` - Complete Create/Read/Update/Delete cycle
- `test_clone_workflow` - Clone workflow with access control
- `test_workflow_with_asset_references` - Asset URL resolution (Firestore → GCS)
- `test_workflow_access_control` - Private workflow auth verification
- `test_public_workflow_visibility` - Public workflows appear in listings

**TestWorkflowLibraryIntegrationE2E**:
- `test_generated_image_auto_saves_to_library` - Generation service auto-saves to Firestore
- `test_workflow_with_multiple_assets` - Batch URL resolution for multiple assets

### Library Tests (`test_library.py`)

**TestLibraryE2E**:
- `test_list_library` - List assets with URL resolution
- `test_save_and_retrieve_asset` - Save metadata to Firestore + binary to GCS
- `test_delete_asset` - Delete from both Firestore and GCS
- `test_filter_by_asset_type` - Firestore query filtering
- `test_asset_ownership` - User isolation via Firestore user_id

**TestLibraryFirestoreIntegration**:
- `test_firestore_metadata_persistence` - Verify all metadata fields stored
- `test_gcs_blob_storage` - Verify binary data stored in GCS, not Firestore

### Other E2E Tests
- `test_health.py` - Health endpoint validation
- `test_image_generation.py` - Image generation workflow
- `test_video_generation.py` - Video generation workflow (if implemented)

## What These Tests Validate

### Firestore Integration
- ✅ Metadata storage in Firestore collections
- ✅ Query capabilities (user_id, is_public, asset_type)
- ✅ User isolation and access control
- ✅ Timestamp and indexing

### GCS Integration
- ✅ Binary file storage in GCS bucket
- ✅ Public URL generation from blob_path
- ✅ File deletion cleanup
- ✅ Content-type handling

### URL Resolution
- ✅ Asset references (imageRef, videoRef, assetRef) → URLs
- ✅ Batch URL resolution for multiple assets
- ✅ Public accessibility of resolved URLs

### API Behavior
- ✅ Authentication and authorization
- ✅ CRUD operations
- ✅ Error handling (404s, 401s)
- ✅ Response format consistency

## Architecture Validation

These tests verify the hybrid Firestore + GCS architecture:

```
User Request → FastAPI Router → Service Layer
                                     ↓
                        ┌────────────┴────────────┐
                        ↓                         ↓
                  Firestore                     GCS
              (metadata storage)         (binary storage)
                  - workflows                - images
                  - assets                   - videos
                  - user_id index            - public URLs
                  - queryable                - blob_path refs
```

## Troubleshooting

**Test fails with "No Firebase token"**:
- Ensure `FIREBASE_TEST_TOKEN` environment variable is set
- Run `python scripts/get_test_token.py` to generate a fresh token
- Ensure `serviceAccountKey.json` exists in project root
- Ensure `FIREBASE_API_KEY` is set in environment
- Token may have expired - regenerate with `get_test_token.py`

**Test fails with 401 Unauthorized**:
- Check that `FIREBASE_TEST_TOKEN` is a valid JWT token (starts with `eyJ...`)
- If token contains error messages, regenerate it properly
- Verify the test user email matches `allowed_emails` in config
- Default test email: `ldebortolialves@hubspot.com`

**Test fails with "404 Not Found" on assets**:
- GCS may have eventual consistency delays
- Firestore indexing may need time (tests include `time.sleep()` where needed)

**Test fails with authentication errors**:
- Verify Firebase project ID is correct (`genmediastudio`)
- Check that user has permissions in Firebase Auth

**Tests are slow**:
- E2E tests make real network calls to cloud services
- Use `-k pattern` to run specific tests during development
- Expected runtime: ~30-60 seconds for full suite

## Cleanup

Tests use the `cleanup_asset` fixture to automatically delete created assets. If tests are interrupted:

```bash
# Manually clean up test data
# Use Firebase Console to delete test workflows/assets
# Or use the API with your test token
```

## CI/CD Integration

For automated testing in CI/CD pipelines:

```yaml
- name: Run E2E Tests
  env:
    FIREBASE_TEST_TOKEN: ${{ secrets.FIREBASE_TEST_TOKEN }}
  run: uv run pytest tests/e2e/ --run-e2e -v --tb=short
```
