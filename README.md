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

**End-to-end tests** (requires running server + Firebase):
```bash
# First, start the server in one terminal:
uv run uvicorn app.main:app --reload --port 8080

# Then in another terminal:
export FIREBASE_TEST_TOKEN=$(uv run python scripts/get_test_token.py)
export API_URL="http://localhost:8080"
uv run pytest tests/e2e -v --run-e2e
```

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
- `POST /generate/image` - Generate images with Gemini
- `POST /generate/video` - Generate videos with Veo 3.1
- `POST /generate/video/status` - Check video generation status
- `POST /generate/text` - Generate text with Gemini
- `POST /generate/upscale` - Upscale images

#### Library
- `POST /library/save` - Save an asset
- `GET /library` - List user's assets
- `GET /library/{asset_id}` - Get specific asset
- `DELETE /library/{asset_id}` - Delete asset

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
│   ├── logging_config.py    # Centralized logging setup
│   ├── routers/             # API route handlers
│   │   ├── generation.py    # Image/video/text generation endpoints
│   │   ├── library.py       # Asset management endpoints
│   │   └── health.py        # Health check endpoint
│   └── services/            # Business logic
│       ├── generation.py    # AI generation service
│       └── library.py       # Asset storage service (GCS)
├── scripts/
│   └── get_test_token.py    # Generate Firebase test tokens
├── tests/
│   ├── unit/                # Unit tests (mocked dependencies)
│   ├── integration/         # Integration tests (real GCP APIs)
│   └── e2e/                 # End-to-end tests (full stack)
├── pyproject.toml           # Project dependencies and config
├── Dockerfile               # Container definition for deployment
└── README.md                # This file
```

### Architecture Overview

**Stack**:
- **FastAPI** - Modern async web framework
- **Firebase Admin** - User authentication
- **Google Cloud AI APIs** - Gemini, Veo, Imagen models
- **Google Cloud Storage** - Asset library storage
- **Pydantic** - Data validation
- **uv** - Fast Python package management

**Authentication Flow**:
1. Client sends Firebase ID token in `Authorization` header
2. Backend verifies token with Firebase Admin SDK
3. Email whitelist check against `ALLOWED_EMAILS`
4. User ID extracted for asset management

**Asset Management**:
- Generated images/videos automatically saved to GCS
- User-specific paths: `users/{user_id}/images/` or `videos/`
- Metadata stored as JSON in `metadata/{asset_id}.json`

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `PROJECT_ID` | Google Cloud project ID | ✅ | `remarkablenotion` |
| `LOCATION` | GCP region | ✅ | `us-central1` |
| `GCS_BUCKET` | Cloud Storage bucket name | ✅ | `genmedia-assets-remarkablenotion` |
| `FIREBASE_PROJECT_ID` | Firebase project ID | ✅ | `genmediastudio` |
| `FIREBASE_API_KEY` | Firebase web API key | For testing | - |
| `FIREBASE_SERVICE_ACCOUNT_KEY` | Path to service account JSON | For testing | `serviceAccountKey.json` |

### Configuration

Edit `app/config.py` to modify:
- **Model versions** - Update AI model names
- **Allowed emails** - Add/remove authorized users
- **Default settings** - Project IDs, regions, etc.

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

### Deploy to Google Cloud Run

```bash
gcloud run deploy veo-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=remarkablenotion,LOCATION=us-central1,GCS_BUCKET=genmedia-assets-remarkablenotion,FIREBASE_PROJECT_ID=genmediastudio \
  --timeout=300 \
  --memory=1Gi
```

The service will be deployed to a URL like:
`https://veo-api-[hash]-uc.a.run.app`

### Docker Build Locally

```bash
docker build -t veo-api .
docker run -p 8080:8080 \
  -e PROJECT_ID=remarkablenotion \
  -e GCS_BUCKET=genmedia-assets-remarkablenotion \
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
| Run all tests | `uv run pytest` |
| Run unit tests | `uv run pytest tests/unit -v` |
| Generate test token | `uv run python scripts/get_test_token.py` |
| View test coverage | `uv run pytest --cov=app --cov-report=html` |
| Deploy to Cloud Run | See Deployment section above |
| Check health | `curl http://localhost:8080/health` |
| View API docs | Open http://localhost:8080/docs |

---

**Built with ❤️ using Google's latest AI models**