# Veo API (GenMedia Backend)

Simple FastAPI backend for generating text, images, and videos using Google Vertex AI (Gemini & Veo).

**Quick Start (local)**

- Install dependencies:

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install --user "uvicorn[standard]"
```

- Ensure Google credentials are available (ADC) — either:
  - `gcloud auth application-default login` or
  - set `GOOGLE_APPLICATION_CREDENTIALS` to a service account JSON file.

- Set env vars (optional; defaults shown):
  - `PROJECT_ID` (default: remarkablenotion)
  - `LOCATION` (default: us-central1)

- Run locally:

```bash
# preferred (module):
python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
# or if uvicorn on PATH:
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

**Deploy to Cloud Run**

Example used in this project:

```bash
gcloud run deploy veo-api --source . --region us-central1 --allow-unauthenticated \
  --set-env-vars PROJECT_ID=remarkablenotion,LOCATION=us-central1 \
  --timeout=300 --memory=1Gi
```

Service URL will be printed after deployment.

---

## Endpoints

Base URL: http://localhost:8080 (or Cloud Run service URL)

- GET `/` — health check and model info

- POST `/generate/text` — generate text
  - Request JSON: { "prompt": "...", "system_prompt": "...", "context": "...", "temperature": 0.7 }
  - Response: { "response": "..." }

- POST `/generate/image` — generate or edit images
  - Request JSON: {
      "prompt": "...",
      "reference_images": ["<base64 image data>"],
      "aspect_ratio": "1:1",
      "resolution": "1K"
    }
  - Response: { "images": ["<base64 image>"] }
  - Notes: this backend uses `GEMINI_IMAGE_MODEL` for image generation.

- POST `/generate/video` — start Veo video generation (long-running)
  - Request JSON: {
      "prompt": "...",
      "first_frame": "<base64 image>",
      "last_frame": "<base64 image>",
      "reference_images": ["<base64>"],
      "aspect_ratio": "16:9",
      "duration_seconds": 8,
      "generate_audio": true
    }
  - Response: { "status": "processing", "operation_name": "..." }
  - Poll operation status with `/video/status`.

- GET `/video/status/{operation_name}` or POST `/video/status` — check status
  - POST body for POST variant: { "operation_name": "..." }
  - When complete, response includes `video_base64` or `storage_uri`.

- POST `/video/extend` — extend an existing video
  - Query params / body: `video_base64` (string), `prompt` (string), `duration_seconds` (int)
  - Response: { "status": "processing", "operation_name": "..." }

---

## Example curl (text)

```bash
curl -s -X POST http://localhost:8080/generate/text \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Write a short product description for a smart mug","temperature":0.7}'
```

## Example curl (image)

```bash
curl -s -X POST http://localhost:8080/generate/image \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A photorealistic cup of coffee on a wooden table, soft morning light"}'
```

For image editing using reference images, include base64-encoded PNG strings in `reference_images`.

## Authentication & Permissions

The backend calls Vertex AI and uses application default credentials. Ensure the service account has permissions to call Vertex AI (e.g., `roles/aiplatform.user`) and to read/write Cloud Storage if using `storageUri` outputs.

## Notes

- Models are configured at the top of `main.py`:
  - `GEMINI_IMAGE_MODEL` for images
  - `GEMINI_TEXT_MODEL` for text
  - `VEO_MODEL` for video

- Adjust request timeouts and memory limits as needed when deploying.

---

If you want, I can:
- add example Postman collection
- add a small smoke-test script that hits `/generate/image` and `/generate/text`
