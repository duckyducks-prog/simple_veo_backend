from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import base64
import httpx
import google.auth
import google.auth.transport.requests
from google.cloud import storage
from datetime import datetime
import uuid
import json
import firebase_admin
from firebase_admin import auth as firebase_auth

app = FastAPI(title="GenMedia API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ID = os.environ.get("PROJECT_ID", "remarkablenotion")
LOCATION = os.environ.get("LOCATION", "us-central1")
GCS_BUCKET = os.environ.get("GCS_BUCKET", "genmedia-assets-remarkablenotion")
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "genmediastudio")

# Allowed users whitelist (can also be set via ALLOWED_EMAILS env var, comma-separated)
ALLOWED_EMAILS = os.environ.get("ALLOWED_EMAILS", "ldebortolialves@hubspot.com").split(",")

# Initialize Firebase Admin SDK
try:
    firebase_admin.initialize_app()
except ValueError:
    pass  # Already initialized

# Models
GEMINI_IMAGE_MODEL = "gemini-3-pro-image-preview"  # Gemini 3 Pro Image (Nano Banana Pro)
GEMINI_TEXT_MODEL = "gemini-3-pro-preview"  # Gemini 3 Pro for text
VEO_MODEL = "veo-3.1-generate-preview"  # Veo 3.1
UPSCALE_MODEL = "imagen-4.0-upscale-preview"  # Imagen 4.0 Upscale

# GCS client
gcs_client = storage.Client()


class ImageRequest(BaseModel):
    prompt: str
    reference_images: Optional[List[str]] = None
    aspect_ratio: Optional[str] = "1:1"
    resolution: Optional[str] = "1K"
    user_id: Optional[str] = None  # Firebase user ID
    user_email: Optional[str] = None  # For whitelist check


class VideoRequest(BaseModel):
    prompt: str
    first_frame: Optional[str] = None
    last_frame: Optional[str] = None
    reference_images: Optional[List[str]] = None
    aspect_ratio: Optional[str] = "16:9"
    duration_seconds: Optional[int] = 8
    generate_audio: Optional[bool] = True
    user_id: Optional[str] = None  # Firebase user ID
    user_email: Optional[str] = None  # For whitelist check


class TextRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    context: Optional[str] = None
    temperature: Optional[float] = 0.7


class StatusRequest(BaseModel):
    operation_name: str
    user_id: Optional[str] = None  # Firebase user ID
    prompt: Optional[str] = None  # For saving video with prompt


class UpscaleRequest(BaseModel):
    image: str  # Base64 encoded image
    upscale_factor: Optional[str] = "x2"  # x2, x3, or x4
    output_mime_type: Optional[str] = "image/png"  # image/png or image/jpeg


class ImageResponse(BaseModel):
    images: List[str]


class TextResponse(BaseModel):
    response: str


class UpscaleResponse(BaseModel):
    image: str  # Base64 encoded upscaled image
    mime_type: str


class SaveAssetRequest(BaseModel):
    data: str  # Base64 encoded image or video
    asset_type: str  # "image" or "video"
    prompt: Optional[str] = None
    mime_type: Optional[str] = None  # e.g., "image/png", "video/mp4"
    user_id: Optional[str] = None  # Firebase user ID


class AssetResponse(BaseModel):
    id: str
    url: str
    asset_type: str
    prompt: Optional[str]
    created_at: str
    mime_type: str
    user_id: Optional[str] = None


def get_auth_headers():
    """Get authentication headers for Google Cloud APIs"""
    credentials, project = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    return {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json"
    }


@app.get("/")
def health():
    return {
        "status": "ok",
        "project": PROJECT_ID,
        "location": LOCATION,
        "models": {
            "image": "Gemini 3 Pro Image (Nano Banana Pro)",
            "video": "Veo 3.1",
            "text": "Gemini 3 Pro",
            "upscale": "Imagen 4.0 Upscale"
        }
    }


def strip_base64_prefix(data: str) -> str:
    """Remove data URL prefix if present (e.g., 'data:image/png;base64,')"""
    if data and ',' in data and data.startswith('data:'):
        return data.split(',', 1)[1]
    return data


def check_user_allowed(user_email: Optional[str]) -> bool:
    """Check if user email is in the whitelist"""
    if not user_email:
        return False
    return user_email.lower().strip() in [e.lower().strip() for e in ALLOWED_EMAILS]


def verify_firebase_token(token: Optional[str]) -> dict:
    """
    Verify Firebase ID token and return user info.
    Returns dict with 'uid' and 'email' if valid.
    Raises HTTPException if invalid.
    """
    if not token:
        raise HTTPException(status_code=401, detail="No authorization token provided")
    
    # Remove 'Bearer ' prefix if present
    if token.startswith("Bearer "):
        token = token[7:]
    
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        user_email = decoded_token.get("email", "").lower().strip()
        user_id = decoded_token.get("uid")
        
        # Check whitelist
        if user_email not in [e.lower().strip() for e in ALLOWED_EMAILS]:
            raise HTTPException(status_code=403, detail="Access denied. User not authorized.")
        
        return {"uid": user_id, "email": user_email}
    except firebase_admin.exceptions.FirebaseError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")


@app.post("/generate/image", response_model=ImageResponse)
async def generate_image(request: ImageRequest, authorization: Optional[str] = Header(None)):
    """Generate images using Gemini 3 Pro Image (global endpoint required)"""
    # Verify token and check whitelist
    user_info = verify_firebase_token(authorization)
    user_id = user_info["uid"]
    
    try:
        # Gemini 3 Pro Image requires GLOBAL endpoint
        endpoint = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/global/publishers/google/models/{GEMINI_IMAGE_MODEL}:generateContent"
        
        parts = []
        
        if request.reference_images:
            for ref_image in request.reference_images:
                clean_image = strip_base64_prefix(ref_image)
                parts.append({
                    "inlineData": {
                        "mimeType": "image/png",
                        "data": clean_image
                    }
                })
        
        parts.append({"text": request.prompt})
        
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"]
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers=get_auth_headers(),
                timeout=300.0
            )
        
        if response.status_code == 200:
            result = response.json()
            images = []
            
            candidates = result.get("candidates", [])
            for candidate in candidates:
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                for part in parts:
                    if "inlineData" in part:
                        images.append(part["inlineData"]["data"])
            
            if images:
                # Auto-save each image to library
                for img_data in images:
                    try:
                        asset_id = str(uuid.uuid4())
                        timestamp = datetime.utcnow().isoformat() + "Z"
                        
                        # Use user-specific path with verified user_id
                        blob_path = f"users/{user_id}/images/{asset_id}.png"
                        
                        file_bytes = base64.b64decode(img_data)
                        bucket = gcs_client.bucket(GCS_BUCKET)
                        blob = bucket.blob(blob_path)
                        blob.upload_from_string(file_bytes, content_type="image/png")
                        blob.make_public()
                        
                        metadata = {
                            "id": asset_id,
                            "asset_type": "image",
                            "prompt": request.prompt,
                            "created_at": timestamp,
                            "mime_type": "image/png",
                            "blob_path": blob_path,
                            "user_id": user_id
                        }
                        meta_blob = bucket.blob(f"metadata/{asset_id}.json")
                        meta_blob.upload_from_string(json.dumps(metadata), content_type="application/json")
                    except Exception:
                        pass  # Don't fail generation if save fails
                
                return ImageResponse(images=images)
            else:
                raise HTTPException(status_code=500, detail="No images generated")
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/video")
async def generate_video(request: VideoRequest, authorization: Optional[str] = Header(None)):
    """Generate video using Veo 3.1 (regional endpoint)"""
    # Verify token and check whitelist
    user_info = verify_firebase_token(authorization)
    user_id = user_info["uid"]
    
    try:
        endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{VEO_MODEL}:predictLongRunning"
        
        instance = {
            "prompt": request.prompt
        }
        
        if request.first_frame:
            instance["image"] = {
                "bytesBase64Encoded": strip_base64_prefix(request.first_frame),
                "mimeType": "image/png"
            }
        
        if request.last_frame:
            instance["lastFrame"] = {
                "bytesBase64Encoded": strip_base64_prefix(request.last_frame),
                "mimeType": "image/png"
            }
        
        if request.reference_images:
            instance["referenceImages"] = [
                {
                    "image": {
                        "bytesBase64Encoded": strip_base64_prefix(img),
                        "mimeType": "image/png"
                    },
                    "referenceType": "REFERENCE_TYPE_SUBJECT"
                }
                for img in request.reference_images[:3]
            ]
        
        payload = {
            "instances": [instance],
            "parameters": {
                "aspectRatio": request.aspect_ratio,
                "sampleCount": 1,
                "durationSeconds": request.duration_seconds,
                "generateAudio": request.generate_audio,
                "resolution": "1080p"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers=get_auth_headers(),
                timeout=300.0
            )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "status": "processing",
                "operation_name": result.get("name", ""),
                "message": "Video generation started. Poll /video/status for completion."
            }
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/video/status")
async def check_video_status(request: StatusRequest, authorization: Optional[str] = Header(None)):
    """Check video generation status"""
    # Verify token and check whitelist
    user_info = verify_firebase_token(authorization)
    user_id = user_info["uid"]
    
    try:
        operation_name = request.operation_name
        endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{operation_name}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                endpoint,
                headers=get_auth_headers(),
                timeout=60.0
            )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("done"):
                if "response" in result:
                    videos = result["response"].get("generateVideoResponse", {}).get("generatedSamples", [])
                    if videos:
                        video_data = videos[0].get("video", {})
                        if "bytesBase64Encoded" in video_data:
                            video_base64 = video_data["bytesBase64Encoded"]
                            
                            # Auto-save video to library
                            try:
                                asset_id = str(uuid.uuid4())
                                timestamp = datetime.utcnow().isoformat() + "Z"
                                
                                # Use user-specific path with verified user_id
                                blob_path = f"users/{user_id}/videos/{asset_id}.mp4"
                                
                                file_bytes = base64.b64decode(video_base64)
                                bucket = gcs_client.bucket(GCS_BUCKET)
                                blob = bucket.blob(blob_path)
                                blob.upload_from_string(file_bytes, content_type="video/mp4")
                                blob.make_public()
                                
                                metadata = {
                                    "id": asset_id,
                                    "asset_type": "video",
                                    "prompt": request.prompt,
                                    "created_at": timestamp,
                                    "mime_type": "video/mp4",
                                    "blob_path": blob_path,
                                    "user_id": user_id
                                }
                                meta_blob = bucket.blob(f"metadata/{asset_id}.json")
                                meta_blob.upload_from_string(json.dumps(metadata), content_type="application/json")
                            except Exception:
                                pass  # Don't fail if save fails
                            
                            return {
                                "status": "complete",
                                "video_base64": video_base64
                            }
                        elif "uri" in video_data:
                            return {
                                "status": "complete",
                                "storage_uri": video_data["uri"]
                            }
                    return {"status": "complete", "message": "Video ready but no data returned"}
                elif "error" in result:
                    return {"status": "error", "error": result["error"]}
            else:
                metadata = result.get("metadata", {})
                return {
                    "status": "processing",
                    "progress": metadata.get("progressPercent", 0)
                }
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/text", response_model=TextResponse)
async def generate_text(request: TextRequest):
    """Generate text using Gemini 3 Pro"""
    try:
        endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{GEMINI_TEXT_MODEL}:generateContent"
        
        contents = []
        
        if request.system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System: {request.system_prompt}"}]
            })
        
        user_text = request.prompt
        if request.context:
            user_text = f"Context: {request.context}\n\nRequest: {request.prompt}"
        
        contents.append({
            "role": "user",
            "parts": [{"text": user_text}]
        })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": 8192
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers=get_auth_headers(),
                timeout=120.0
            )
        
        if response.status_code == 200:
            result = response.json()
            candidates = result.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    return TextResponse(response=parts[0].get("text", ""))
            raise HTTPException(status_code=500, detail="No text generated")
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upscale/image", response_model=UpscaleResponse)
async def upscale_image(request: UpscaleRequest):
    """
    Upscale an image using Imagen 4.0 Upscale.
    
    - upscale_factor: "x2", "x3", or "x4"
    - Input resolution × upscale_factor must not exceed 17 megapixels
    """
    try:
        endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{UPSCALE_MODEL}:predict"
        
        payload = {
            "instances": [
                {
                    "prompt": "Upscale the image",
                    "image": {
                        "bytesBase64Encoded": strip_base64_prefix(request.image)
                    }
                }
            ],
            "parameters": {
                "mode": "upscale",
                "upscaleConfig": {
                    "upscaleFactor": request.upscale_factor
                },
                "outputOptions": {
                    "mimeType": request.output_mime_type
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers=get_auth_headers(),
                timeout=300.0
            )
        
        if response.status_code == 200:
            result = response.json()
            predictions = result.get("predictions", [])
            
            if predictions:
                upscaled_image = predictions[0].get("bytesBase64Encoded", "")
                mime_type = predictions[0].get("mimeType", request.output_mime_type)
                
                if upscaled_image:
                    return UpscaleResponse(image=upscaled_image, mime_type=mime_type)
            
            raise HTTPException(status_code=500, detail="No upscaled image returned")
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/video/extend")
async def extend_video(request: dict):
    """Extend an existing video"""
    try:
        video_base64 = request.get("video_base64")
        prompt = request.get("prompt", "Continue this video")
        duration = request.get("duration_seconds", 8)
        
        if not video_base64:
            raise HTTPException(status_code=400, detail="video_base64 is required")
        
        endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{VEO_MODEL}:predictLongRunning"
        
        payload = {
            "instances": [{
                "prompt": prompt,
                "video": {
                    "bytesBase64Encoded": strip_base64_prefix(video_base64),
                    "mimeType": "video/mp4"
                }
            }],
            "parameters": {
                "sampleCount": 1,
                "durationSeconds": duration,
                "generateAudio": True
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers=get_auth_headers(),
                timeout=300.0
            )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "status": "processing",
                "operation_name": result.get("name", ""),
                "message": "Video extension started. Poll /video/status for completion."
            }
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== ASSET LIBRARY ENDPOINTS ==============

@app.post("/library/save", response_model=AssetResponse)
async def save_asset(request: SaveAssetRequest):
    """Save an image or video to the asset library"""
    try:
        # Generate unique ID
        asset_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Determine file extension and mime type
        if request.asset_type == "image":
            ext = "png" if not request.mime_type or "png" in request.mime_type else "jpg"
            mime_type = request.mime_type or "image/png"
        elif request.asset_type == "video":
            ext = "mp4"
            mime_type = request.mime_type or "video/mp4"
        else:
            raise HTTPException(status_code=400, detail="asset_type must be 'image' or 'video'")
        
        # Create blob path (user-specific if user_id provided)
        if request.user_id:
            blob_path = f"users/{request.user_id}/{request.asset_type}s/{asset_id}.{ext}"
        else:
            blob_path = f"{request.asset_type}s/{asset_id}.{ext}"
        
        # Decode base64 and upload
        clean_data = strip_base64_prefix(request.data)
        file_bytes = base64.b64decode(clean_data)
        
        bucket = gcs_client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_path)
        blob.upload_from_string(file_bytes, content_type=mime_type)
        
        # Make blob publicly readable
        blob.make_public()
        
        # Save metadata
        metadata = {
            "id": asset_id,
            "asset_type": request.asset_type,
            "prompt": request.prompt,
            "created_at": timestamp,
            "mime_type": mime_type,
            "blob_path": blob_path,
            "user_id": request.user_id
        }
        
        meta_blob = bucket.blob(f"metadata/{asset_id}.json")
        meta_blob.upload_from_string(json.dumps(metadata), content_type="application/json")
        
        # Use public URL
        url = blob.public_url
        
        return AssetResponse(
            id=asset_id,
            url=url,
            asset_type=request.asset_type,
            prompt=request.prompt,
            created_at=timestamp,
            mime_type=mime_type,
            user_id=request.user_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/library")
async def list_assets(asset_type: Optional[str] = None, limit: int = 50, authorization: Optional[str] = Header(None)):
    """List assets in the library for the authenticated user"""
    # Verify token and check whitelist
    user_info = verify_firebase_token(authorization)
    user_id = user_info["uid"]
    
    try:
        bucket = gcs_client.bucket(GCS_BUCKET)
        blobs = bucket.list_blobs(prefix="metadata/")
        
        assets = []
        for blob in blobs:
            if not blob.name.endswith(".json"):
                continue
                
            metadata = json.loads(blob.download_as_string())
            
            # Filter by verified user_id
            if metadata.get("user_id") != user_id:
                continue
            
            # Filter by asset_type if specified
            if asset_type and metadata.get("asset_type") != asset_type:
                continue
            
            # Get public URL for the actual asset
            asset_blob = bucket.blob(metadata["blob_path"])
            if asset_blob.exists():
                metadata["url"] = asset_blob.public_url
                assets.append(metadata)
            
            if len(assets) >= limit:
                break
        
        # Sort by created_at descending (newest first)
        assets.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {"assets": assets, "count": len(assets)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/library/{asset_id}")
async def get_asset(asset_id: str):
    """Get a specific asset by ID"""
    try:
        bucket = gcs_client.bucket(GCS_BUCKET)
        meta_blob = bucket.blob(f"metadata/{asset_id}.json")
        
        if not meta_blob.exists():
            raise HTTPException(status_code=404, detail="Asset not found")
        
        metadata = json.loads(meta_blob.download_as_string())
        
        # Get public URL
        asset_blob = bucket.blob(metadata["blob_path"])
        metadata["url"] = asset_blob.public_url
        
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/library/{asset_id}")
async def delete_asset(asset_id: str, authorization: Optional[str] = Header(None)):
    """Delete an asset from the library (only owner can delete)"""
    # Verify token and check whitelist
    user_info = verify_firebase_token(authorization)
    user_id = user_info["uid"]
    
    try:
        bucket = gcs_client.bucket(GCS_BUCKET)
        meta_blob = bucket.blob(f"metadata/{asset_id}.json")
        
        if not meta_blob.exists():
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Get metadata to find the asset blob
        metadata = json.loads(meta_blob.download_as_string())
        
        # Check ownership
        if metadata.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied. You can only delete your own assets.")
        
        # Delete the asset file
        asset_blob = bucket.blob(metadata["blob_path"])
        if asset_blob.exists():
            asset_blob.delete()
        
        # Delete the metadata
        meta_blob.delete()
        
        return {"status": "deleted", "id": asset_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))