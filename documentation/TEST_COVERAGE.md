# E2E Test Coverage Summary

## Overview
**Total E2E Tests: 63** (increased from 41 baseline)

The e2e test suite comprehensively tests all API endpoints with real cloud services (Firestore, GCS, Firebase Auth).

## Test Execution

### Automated (Recommended)
```bash
# Test against local server (auto-starts and stops server)
LOCAL_MODE=true ./scripts/run_e2e_tests.sh

# Test against production
./scripts/run_e2e_tests.sh
```

### Manual
```bash
# Generate token and run tests
export FIREBASE_TEST_TOKEN=$(uv run python scripts/get_test_token.py)
export API_URL="http://localhost:8000"
uv run pytest tests/e2e/ --run-e2e -v
```

## Test Coverage by Endpoint

### ✅ Health (`test_health.py`)
- Basic health check endpoint

### ✅ Image Generation (`test_image_generation.py`)
- Generate simple image
- Unauthorized request (401)
- Missing prompt validation (422)
- Seed parameter acceptance
- Different aspect ratios (1:1, 16:9, 9:16)

### ✅ Video Generation (`test_video_generation.py`)
- Generate video with polling (full workflow)
- Unauthorized request (401)
- Seed parameter variations (zero, large, null, without seed)

### ✅ Video Reference Images (`test_video_reference_images.py`) **NEW!**
Tests the recently fixed reference images feature:
- Generate video with first_frame
- Generate video with reference_images (style)
- Multiple reference images
- Combined first_frame + reference_images
- Validation errors for invalid references
- Workflow integration with reference images

### ✅ Text & Upscale (`test_text_and_upscale.py`) **NEW!**
- Text generation
- Text generation validation (unauthorized, missing prompt, empty prompt, long prompt)
- Image upscaling
- Upscale validation (unauthorized, missing image, invalid base64)
- Workflow with text generation node
- Workflow with upscale pipeline

### ✅ Library/Assets (`test_library.py`)
- List library with Firestore queries
- Save & retrieve asset (Firestore + GCS)
- Delete asset (cleanup both Firestore and GCS)
- Upload image/video
- Asset URL resolution from blob_path
- Ownership and access control
- Filter by asset type

### ✅ Workflows (`test_workflow.py`)
**Basic Operations:**
- Create workflow
- List my/public workflows (Firestore indexed queries)
- CRUD lifecycle (Create, Read, Update, Delete)
- Clone workflow with access control
- Workflow access control (private/public)
- Public workflow visibility

**Asset Integration:**
- Workflows with asset references
- Asset URL resolution in workflow nodes
- Multiple assets in single workflow

**Seed Data:**
- Workflow with seed in generation node
- Multiple seeded nodes
- Seed + asset references combined
- Clone preserves seed data
- Update preserves seed data

**Library Integration:**
- Generated images auto-save to library
- Workflow with multiple asset types

### ✅ Complete Workflows (`test_complete_workflows.py`) **NEW!**
End-to-end execution scenarios:

**Full Pipelines:**
- Complete image-to-video workflow (generate → save → workflow → execute)
- Multi-step workflow with filtering (image → filter → upscale → video)
- Branching workflow (1 input → 3 parallel outputs)

**Real User Scenarios:**
- Clone workflow and modify (common pattern)
- Library filtering with workflow assets
- Workflow execution with resolved URLs

## Coverage by Feature

### 🎨 Generation Features
- ✅ Image generation (Gemini)
- ✅ Video generation (Veo 3.1)
- ✅ Text generation (Gemini)
- ✅ Video with first_frame
- ✅ Video with reference_images (style)
- ✅ Upscaling
- ✅ Seed parameter support

### 📚 Library Features
- ✅ Save assets (upload)
- ✅ List assets with filtering
- ✅ Get asset by ID
- ✅ Delete asset
- ✅ URL resolution from GCS
- ✅ Ownership validation

### 🔄 Workflow Features
- ✅ Create workflow
- ✅ List workflows (my/public)
- ✅ Get workflow by ID
- ✅ Update workflow
- ✅ Delete workflow
- ✅ Clone workflow
- ✅ Asset reference resolution
- ✅ Seed data preservation
- ✅ Access control (private/public)

### 🔗 Integration Features
- ✅ Image → Video pipeline
- ✅ Generated assets auto-save to library
- ✅ Workflow asset URL resolution
- ✅ Multi-node workflows with edges
- ✅ Branching workflows
- ✅ Reference images in workflows

## Test Organization

```
tests/e2e/
├── conftest.py                           # Fixtures (auth, cleanup, seed data)
├── test_health.py                        # 1 test
├── test_image_generation.py              # 6 tests
├── test_video_generation.py              # 7 tests
├── test_video_reference_images.py        # 7 tests (NEW!)
├── test_text_and_upscale.py             # 12 tests (NEW!)
├── test_library.py                       # 11 tests
├── test_workflow.py                      # 16 tests
└── test_complete_workflows.py           # 7 tests (NEW!)
```

## What's Not Tested (Future Improvements)

1. **Error Recovery**
   - What happens when a workflow node fails mid-execution?
   - Network failures and retries
   - Partial workflow completion

2. **Performance/Load**
   - Large workflow execution
   - Concurrent workflow runs
   - Rate limiting behavior

3. **Edge Cases**
   - Very large assets (> 10MB)
   - Extremely long prompts
   - Maximum workflow complexity (100 nodes)

4. **Audio Features**
   - Video generation with audio
   - Audio-only generation (if supported)

## Running Specific Test Categories

```bash
# Reference images tests only
LOCAL_MODE=true ./scripts/run_e2e_tests.sh -k "reference"

# Complete workflow execution tests
LOCAL_MODE=true ./scripts/run_e2e_tests.sh tests/e2e/test_complete_workflows.py

# All generation tests (image + video + text)
LOCAL_MODE=true ./scripts/run_e2e_tests.sh -k "generation"

# Seed data tests across all files
LOCAL_MODE=true ./scripts/run_e2e_tests.sh -k "seed"

# Quick smoke test (health + basic operations)
LOCAL_MODE=true ./scripts/run_e2e_tests.sh tests/e2e/test_health.py tests/e2e/test_library.py
```

## Notes

- **Cost**: E2E tests use real Google APIs and incur costs (especially video generation)
- **Time**: Video generation tests can take 2-5 minutes per test
- **Cleanup**: Tests automatically cleanup created assets (best effort)
- **Auth**: Requires valid Firebase token (auto-generated by script)
- **Local Mode**: Automatically starts/stops local server for testing
