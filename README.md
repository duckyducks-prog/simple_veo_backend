# GenMedia API Backend

A FastAPI backend service for AI-powered media generation using Google's Gemini and Veo models. Generate images, videos, and text content with a RESTful API.

## 🚀 Quick Start (For Non-Technical Users)

### Prerequisites
You need these installed on your computer:
- **Python 3.11+** - [Download here](https://www.python.org/downloads/)
- **uv** - Python package manager. Install with:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Google Cloud SDK** - [Install instructions](https://cloud.google.com/sdk/docs/install)

### Step 1: Get Your Credentials

1. **Firebase Service Account Key**:
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Select your project (`genmediastudio`)
   - Click the gear icon → **Project Settings** → **Service Accounts**
   - Click **Generate New Private Key**
   - Save the file as `serviceAccountKey.json` in this folder

2. **Firebase API Key**:
   - In Firebase Console → **Project Settings** → **General**
   - Scroll to "Web API Key" and copy it

3. **Google Cloud Authentication**:
   ```bash
   gcloud auth application-default login
   ```

### Step 2: Configure Environment

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Firebase API Key:
   ```bash
   FIREBASE_API_KEY=your_actual_api_key_here
   ```

### Step 3: Install Dependencies

```bash
uv sync
```

This installs all required packages. Takes 1-2 minutes.

### Step 4: Run the Server

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

The server will start at: **http://localhost:8080**

You'll see something like:
```
INFO:     Uvicorn running on http://0.0.0.0:8080
INFO:     Application startup complete.
```

### Step 5: Test It Works

Open your browser and go to: **http://localhost:8080/health**

You should see: `{"status":"healthy"}`

---

## 🧪 Running Tests

### Quick E2E Test Suite (Recommended)

The easiest way to run the full end-to-end test suite locally:

```bash
./scripts/run_e2e_tests.sh
```

This script automatically:
- Generates a Firebase test token
- Starts a local server on port 8000
- Runs all 63 e2e tests
- Stops the server when done

**Run specific tests:**
```bash
./scripts/run_e2e_tests.sh tests/e2e/test_video_generation.py
./scripts/run_e2e_tests.sh tests/e2e/test_image_generation.py::TestImageGenerationE2E::test_generate_simple_image
```

**Test against production:**
```bash
export API_URL="https://your-production-url.com"
./scripts/run_e2e_tests.sh
```

### Run All Tests
```bash
uv run pytest
```

### Run Specific Test Types

**Unit tests only** (fast, no external services needed):
```bash
uv run pytest tests/unit -v
```

**Integration tests** (requires Google Cloud auth):
```bash
uv run pytest tests/integration -v
```

**End-to-end tests manually** (if you want to start server yourself):
```bash
# First, start the server in one terminal:
uv run uvicorn app.main:app --reload --port 8000

# Then in another terminal:
export FIREBASE_TEST_TOKEN=$(uv run python scripts/get_test_token.py)
export API_URL="http://localhost:8000"
uv run pytest tests/e2e -v --run-e2e
```

### E2E Test Coverage (63 Tests)

Our comprehensive e2e test suite covers:
- ✅ **Health checks** (1 test)
- ✅ **Image generation** with Gemini (6 tests)
- ✅ **Video generation** with Veo 3.1 (9 tests)
- ✅ **Video reference images** - first frame & style references (7 tests)
- ✅ **Text generation** with Gemini (5 tests)
- ✅ **Image upscaling** with Imagen (7 tests)
- ✅ **Library management** - save, retrieve, delete assets (15 tests)
- ✅ **Workflow execution** - complete multi-step workflows (7 tests)
- ✅ **Workflow CRUD** - create, read, update, delete (6 tests)

### Run with Coverage
```bash
uv run pytest --cov=app --cov-report=html
```
Then open `htmlcov/index.html` in your browser to see coverage details.

---

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

### Available Endpoints

#### Generation
- `POST /generate/image` - Generate images with Gemini 2.5 Flash
  - Supports reference images as visual ingredients
  - Returns base64 encoded images
  - Automatic retry on rate limits
- `POST /generate/video` - Generate videos with Veo 3.1
  - Supports first frame and last frame conditioning
  - Reference images for style/subject transfer
  - **Auto-resolves asset IDs** - pass library asset UUIDs instead of base64 data
  - 4-8 second duration options
  - Optional audio generation
  - Seed support for reproducibility
- `POST /generate/video/status` - Check video generation status
  - Poll for async video completion
  - Returns download URL when ready
  - Automatic library save on completion
- `POST /generate/text` - Generate text with Gemini 2.0 Flash
  - System prompts and context support
  - Configurable temperature
- `POST /generate/upscale` - Upscale images with Imagen 4.0
  - 2x or 4x upscaling
  - Maintains image quality

#### Library
- `POST /library/save` - Save an asset to user's library
  - Uploads to Google Cloud Storage
  - Returns asset ID and public URL
  - Supports images and videos
- `GET /library` - List user's assets with filtering
  - Filter by media type (image/video)
  - Filter by workflow ID
  - Pagination support
- `GET /library/{asset_id}` - Get specific asset metadata
- `DELETE /library/{asset_id}` - Delete asset and GCS file

#### Workflows (Firestore-backed)
- `POST /workflow` - Create a new workflow
- `GET /workflow` - List user's workflows
- `GET /workflow/{workflow_id}` - Get workflow by ID
- `PUT /workflow/{workflow_id}` - Update workflow
- `DELETE /workflow/{workflow_id}` - Delete workflow
- `POST /workflow/{workflow_id}/clone` - Clone existing workflow

#### Health
- `GET /health` - Health check

---

## 🔧 For Technical Contributors

### Project Structure

```
simple_veo_backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration and settings
│   ├── auth.py              # Firebase authentication
│   ├── schemas.py           # Pydantic models for requests/responses
│   ├── firestore.py         # Firestore client initialization
│   ├── logging_config.py    # Centralized logging setup
│   ├── routers/             # API route handlers
│   │   ├── generation.py    # Image/video/text generation endpoints
│   │   ├── library.py       # Asset management endpoints
│   │   ├── workflow.py      # Workflow CRUD endpoints
│   │   └── health.py        # Health check endpoint
│   └── services/            # Business logic
│       ├── generation.py    # AI generation service (Gemini, Veo, Imagen)
│       ├── library_firestore.py  # Asset storage service (GCS + Firestore)
│       └── workflow_firestore.py # Workflow management service
├── scripts/
│   ├── get_test_token.py    # Generate Firebase test tokens
│   ├── run_e2e_tests.sh     # Automated e2e test runner (LOCAL_MODE support)
│   ├── deploy.sh            # Deploy to Google Cloud Run
│   └── test_workflow_api.sh # Manual workflow API testing
├── tests/
│   ├── unit/                # Unit tests (mocked dependencies)
│   ├── integration/         # Integration tests (real GCP APIs)
│   └── e2e/                 # End-to-end tests (63 comprehensive tests)
│       ├── conftest.py      # Shared fixtures and config
│       ├── test_health.py
│       ├── test_image_generation.py
│       ├── test_video_generation.py
│       ├── test_video_reference_images.py
│       ├── test_text_and_upscale.py
│       ├── test_library.py
│       ├── test_workflow.py
│       └── test_complete_workflows.py
├── documentation/           # Additional documentation
│   ├── FIRESTORE_MIGRATION.md
│   ├── WORKFLOW_API.md
│   └── WORKFLOW_QUICKSTART.md
├── pyproject.toml           # Project dependencies and config
├── Dockerfile               # Container definition for deployment
└── README.md                # This file
```

### Architecture Overview

**Stack**:
- **FastAPI** - Modern async web framework
- **Firebase Admin** - User authentication and Firestore database
- **Firestore** - Document database for workflows and asset metadata
- **Google Cloud AI APIs** - Gemini 2.5, Veo 3.1, Imagen 4.0 models
- **Google Cloud Storage** - Asset library storage
- **Pydantic** - Data validation and serialization
- **uv** - Fast Python package management

**Key Features**:
- 🎨 **Multi-modal generation** - Images, videos, and text
- 🎬 **Video reference images** - Use library assets as first frame or style references
- 🔄 **Asset ID auto-resolution** - Pass UUIDs instead of base64 in video requests
- 📚 **Persistent workflows** - Save and share multi-step generation pipelines
- 🗄️ **Firestore integration** - Scalable metadata storage
- 🔄 **Automatic retries** - Rate limit handling with exponential backoff
- 🌐 **Production-ready** - Comprehensive error handling and logging

**Authentication Flow**:
1. Client sends Firebase ID token in `Authorization` header
2. Backend verifies token with Firebase Admin SDK
3. Email whitelist check against `ALLOWED_EMAILS`
4. User ID extracted for asset management

**Asset Management**:
- Generated images/videos automatically saved to GCS
- User-specific paths: `users/{user_id}/images/` or `videos/`
- Metadata stored in Firestore for fast querying
- Public URLs with appropriate caching headers
- Asset filtering by type and workflow ID

**Video Reference Images**:
- Pass library asset IDs directly in video generation requests
- Backend automatically resolves UUIDs to base64 image data
- Supports first frame conditioning and style transfer
- Multiple reference images for complex compositions

**Workflows**:
- DAG-based multi-step generation pipelines
- Node types: image_generation, video_generation, text_generation, upscale
- Edge connections define data flow between nodes
- Persistent storage in Firestore with user isolation
- Clone and modify existing workflows

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `PROJECT_ID` | Google Cloud project ID | ✅ | `genmediastudio` |
| `LOCATION` | GCP region | ✅ | `us-central1` |
| `GCS_BUCKET` | Cloud Storage bucket for assets | ✅ | `genmediastudio-assets` |
| `WORKFLOWS_BUCKET` | Cloud Storage bucket for workflows | ✅ | `genmediastudio-workflows` |
| `FIREBASE_PROJECT_ID` | Firebase project ID | ✅ | `genmediastudio` |
| `FIREBASE_API_KEY` | Firebase web API key | For testing | - |
| `FIREBASE_SERVICE_ACCOUNT_KEY` | Path to service account JSON | ✅ | `serviceAccountKey.json` |

### Configuration

Edit `app/config.py` to modify:
- **Model versions** - Update AI model names (Gemini 2.5, Veo 3.1, Imagen 4.0)
- **Allowed emails** - Add/remove authorized users
- **Default settings** - Project IDs, regions, buckets, etc.

**Current models:**
- Image: `gemini-2.5-flash-image`
- Video: `veo-3.1-generate-preview`
- Text: `gemini-3-flash-preview`
- Upscale: `imagen-4.0-upscale-preview`

### Logging

Comprehensive logging is configured in `app/logging_config.py`. See [README_LOGGING.md](README_LOGGING.md) for details.

Log levels:
- **INFO** - Request tracking, successful operations
- **WARNING** - Auth failures, invalid requests
- **ERROR** - API failures, exceptions
- **DEBUG** - Verbose operation details

### Adding New Endpoints

1. **Define schemas** in `app/schemas.py`:
   ```python
   class MyRequest(BaseModel):
       field: str
   ```

2. **Create service method** in `app/services/`:
   ```python
   async def my_operation(self, param: str) -> MyResponse:
       # Business logic here
   ```

3. **Add router endpoint** in `app/routers/`:
   ```python
   @router.post("/my-endpoint")
   async def my_endpoint(
       request: MyRequest,
       user: dict = Depends(get_current_user),
       service: MyService = Depends(get_service)
   ):
       return await service.my_operation(request.field)
   ```

4. **Write tests** in `tests/`:
   - Unit tests with mocked dependencies
   - Integration tests with real services
   - E2E tests for full flow

### Development Workflow

1. **Create feature branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes and test**:
   ```bash
   uv run pytest tests/unit -v
   ```

3. **Check formatting** (if you have formatters):
   ```bash
   # Add your formatter commands here
   ```

4. **Run integration tests**:
   ```bash
   uv run pytest tests/integration -v
   ```

5. **Commit and push**:
   ```bash
   git add .
   git commit -m "Add: my feature description"
   git push origin feature/my-feature
   ```

---

## 🚢 Deployment

### Quick Deploy with Script

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

This automated script handles the full deployment to Google Cloud Run.

### Manual Deploy to Google Cloud Run

```bash
gcloud run deploy veo-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=genmediastudio,LOCATION=us-central1,GCS_BUCKET=genmediastudio-assets,FIREBASE_PROJECT_ID=genmediastudio \
  --timeout=300 \
  --memory=1Gi
```

The service will be deployed to a URL like:
`https://veo-api-[hash]-uc.a.run.app`

### Docker Build Locally

```bash
docker build -t veo-api .
docker run -p 8080:8080 \
  -e PROJECT_ID=genmediastudio \
  -e GCS_BUCKET=genmediastudio-assets \
  veo-api
```

---

## 🔒 Security

### Sensitive Files (Never Commit!)

These are in `.gitignore`:
- `.env` - Your local environment variables
- `serviceAccountKey.json` - Firebase credentials
- `*.json` files (except config files)

### Authorized Users

Only whitelisted emails can access the API. Edit `app/config.py`:

```python
ALLOWED_EMAILS: ClassVar[list[str]] = [
    "user1@example.com",
    "user2@example.com"
]
```

### Authentication

All endpoints (except `/health`) require Firebase authentication:

```bash
curl -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
  http://localhost:8080/generate/image
```

---

## 🐛 Troubleshooting

### "No module named 'app'"
Make sure you're using `uv run` to execute commands:
```bash
uv run pytest  # ✅ Correct
pytest         # ❌ Wrong (uses system Python)
```

### "ModuleNotFoundError: No module named 'firebase_admin'"
Install dependencies:
```bash
uv sync
```

### "Failed to determine service account"
You need to authenticate with Google Cloud:
```bash
gcloud auth application-default login
```

### "Access denied. User not authorized"
Add your email to `ALLOWED_EMAILS` in `app/config.py`.

### "No authorization token provided"
Include your Firebase token in the Authorization header:
```bash
export TOKEN=$(uv run python scripts/get_test_token.py)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/generate/image
```

### Tests fail with "Connection refused"
Make sure the server is running:
```bash
uv run uvicorn app.main:app --port 8080
```

---

## 📖 Additional Documentation

- **[Firestore Migration](documentation/FIRESTORE_MIGRATION.md)** - Guide to Firestore integration
- **[Workflow API](documentation/WORKFLOW_API.md)** - Workflow endpoints and schemas
- **[Workflow Quickstart](documentation/WORKFLOW_QUICKSTART.md)** - Getting started with workflows
- **[Logging Guide](README_LOGGING.md)** - Comprehensive logging documentation
- **[API Docs](http://localhost:8080/docs)** - Interactive API documentation (when server is running)

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Code Standards
- Follow PEP 8 style guidelines
- Add type hints to function signatures
- Write docstrings for public functions
- Keep functions focused and single-purpose
- Use logging instead of print statements

---

## 📝 License

[Add your license here]

---

## 💬 Support

For questions or issues:
- Check the troubleshooting section above
- Review existing GitHub issues
- Create a new issue with detailed error messages and logs

---

## 🎯 Quick Reference Commands

| Task | Command |
|------|---------|
| Install dependencies | `uv sync` |
| Start server | `uv run uvicorn app.main:app --reload --port 8080` |
| Run all e2e tests | `./scripts/run_e2e_tests.sh` |
| Run specific test | `./scripts/run_e2e_tests.sh tests/e2e/test_video_generation.py` |
| Run all tests | `uv run pytest` |
| Run unit tests | `uv run pytest tests/unit -v` |
| Generate test token | `uv run python scripts/get_test_token.py` |
| View test coverage | `uv run pytest --cov=app --cov-report=html` |
| Deploy to Cloud Run | `./scripts/deploy.sh` |
| Check health | `curl http://localhost:8080/health` |
| View API docs | Open http://localhost:8080/docs |
| Test workflow API | `./scripts/test_workflow_api.sh` |

---
