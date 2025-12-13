from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import base64
import httpx
import google.auth
import google.auth.transport.requests

app = FastAPI(title="HubSpot GenMedia API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ID = os.environ.get("PROJECT_ID", "remarkablenotion")
LOCATION = os.environ.get("LOCATION", "us-central1")

# Models
GEMINI_IMAGE_MODEL = "gemini-3-pro-image-preview"  # Gemini 3 Pro for image generation
GEMINI_TEXT_MODEL = "gemini-3-pro-preview"  # Gemini 3 Pro for text
VEO_MODEL = "veo-3.1-generate-preview"  # Veo 3.1

class ImageRequest(BaseModel):
    prompt: str
    reference_images: Optional[List[str]] = None  # Base64 encoded images
    aspect_ratio: Optional[str] = "1:1"
    resolution: Optional[str] = "1K"  # 1K, 2K, or 4K

class VideoRequest(BaseModel):
    prompt: str
    first_frame: Optional[str] = None  # Base64 encoded image
    last_frame: Optional[str] = None   # Base64 encoded image
    reference_images: Optional[List[str]] = None  # Up to 3 reference images
    aspect_ratio: Optional[str] = "16:9"
    duration_seconds: Optional[int] = 8
    generate_audio: Optional[bool] = True

class TextRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None  # Instructions for the LLM
    context: Optional[str] = None  # Additional context from other nodes
    temperature: Optional[float] = 0.7

class StatusRequest(BaseModel):
    operation_name: str

class ImageResponse(BaseModel):
    images: List[str]  # Base64 encoded images

class TextResponse(BaseModel):
    response: str

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
        "models": {
            "image": "Gemini 3 Pro",
            "video": "Veo 3.1",
            "text": "Gemini 3 Pro"
        }
    }

@app.post("/generate/text", response_model=TextResponse)
async def generate_text(request: TextRequest):
    """
    Generate text using Gemini 3 Pro
    Supports system prompts, context injection, and temperature control
    Use for prompt enhancement, content generation, or any LLM task
    """
    try:
        endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{GEMINI_TEXT_MODEL}:generateContent"
        
        # Build the full prompt
        full_prompt = ""
        if request.system_prompt:
            full_prompt += f"Instructions: {request.system_prompt}\n\n"
        if request.context:
            full_prompt += f"Context: {request.context}\n\n"
        full_prompt += request.prompt
        
        payload = {
            "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": request.temperature
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers=get_auth_headers(),
                timeout=60.0
            )
        
        if response.status_code == 200:
            result = response.json()
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            return TextResponse(response=text)
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate/image", response_model=ImageResponse)
async def generate_image(request: ImageRequest):
    """
    Generate images using Gemini 3 Pro
    Supports text-to-image and image editing with reference images
    """
    try:
        endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{GEMINI_IMAGE_MODEL}:generateContent"
        
        # Build the content parts
        parts = []
        
        # Add reference images if provided (for editing/style transfer)
        if request.reference_images:
            for ref_image in request.reference_images:
                parts.append({
                    "inlineData": {
                        "mimeType": "image/png",
                        "data": ref_image
                    }
                })
        
        # Add the text prompt
        parts.append({"text": request.prompt})
        
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "responseMimeType": "text/plain"
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
            
            # Extract images from response
            candidates = result.get("candidates", [])
            for candidate in candidates:
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                for part in parts:
                    if "inlineData" in part:
                        images.append(part["inlineData"]["data"])
            
            if images:
                return ImageResponse(images=images)
            else:
                raise HTTPException(status_code=500, detail="No images generated")
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate/video")
async def generate_video(request: VideoRequest):
    """
    Generate video using Veo 3.1
    Supports:
    - Text-to-video
    - Image-to-video (first frame)
    - Frame bridging (first + last frame)
    - Reference images (up to 3)
    - Native audio generation
    """
    try:
        endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{VEO_MODEL}:predictLongRunning"
        
        # Build the instance
        instance = {
            "prompt": request.prompt
        }
        
        # Add first frame (image-to-video)
        if request.first_frame:
            instance["image"] = {
                "bytesBase64Encoded": request.first_frame,
                "mimeType": "image/png"
            }
        
        # Add last frame for frame bridging
        if request.last_frame:
            instance["lastFrame"] = {
                "bytesBase64Encoded": request.last_frame,
                "mimeType": "image/png"
            }
        
        # Add reference images (up to 3 for "Ingredients to Video")
        if request.reference_images:
            instance["referenceImages"] = [
                {
                    "image": {
                        "bytesBase64Encoded": img,
                        "mimeType": "image/png"
                    },
                    "referenceType": "REFERENCE_TYPE_SUBJECT"
                }
                for img in request.reference_images[:3]  # Max 3 images
            ]
        
        payload = {
            "instances": [instance],
            "parameters": {
                "aspectRatio": request.aspect_ratio,
                "sampleCount": 1,
                "durationSeconds": request.duration_seconds,
                "generateAudio": request.generate_audio,
                "resolution": "1080p"  # Veo 3.1 supports 1080p
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

@app.get("/video/status/{operation_name:path}")
async def check_video_status_get(operation_name: str):
    """GET endpoint for video status - for frontend compatibility"""
    request = StatusRequest(operation_name=operation_name)
    return await check_video_status_post(request)

@app.post("/video/status")
async def check_video_status_post(request: StatusRequest):
    """
    Check the status of a video generation operation
    Returns video base64 when complete
    Uses fetchPredictOperation (POST) as required by Veo 3.1
    """
    try:
        operation_name = request.operation_name
        
        # Use fetchPredictOperation endpoint (POST method required for Veo 3.1)
        endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{VEO_MODEL}:fetchPredictOperation"
        
        payload = {
            "operationName": operation_name
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
            
            # Check if done
            if result.get("done"):
                # Check for error
                if "error" in result:
                    return {
                        "status": "error",
                        "error": result["error"].get("message", "Unknown error")
                    }
                
                # Get video from response (Veo 3.1 response structure)
                video_response = result.get("response", {})
                videos = video_response.get("videos", [])
                
                if videos and len(videos) > 0:
                    video = videos[0]
                    
                    # Check for bytesBase64Encoded (Veo 3.1 uses this field name)
                    if "bytesBase64Encoded" in video:
                        return {
                            "status": "complete",
                            "video_base64": video["bytesBase64Encoded"],
                            "mimeType": video.get("mimeType", "video/mp4")
                        }
                    
                    # Fallback: check for videoBytes
                    elif "videoBytes" in video:
                        return {
                            "status": "complete",
                            "video_base64": video["videoBytes"],
                            "mimeType": video.get("mimeType", "video/mp4")
                        }
                    
                    # Check for storageUri (Cloud Storage)
                    elif "storageUri" in video:
                        return {
                            "status": "complete",
                            "storage_uri": video["storageUri"],
                            "metadata": {
                                "width": video.get("width"),
                                "height": video.get("height"),
                                "duration_seconds": video.get("durationSeconds"),
                                "mime_type": video.get("mimeType", "video/mp4")
                            }
                        }
                
                return {
                    "status": "complete",
                    "error": "No video data in response"
                }
            else:
                # Still processing
                metadata = result.get("metadata", {})
                return {
                    "status": "processing",
                    "progress": metadata.get("progress", "Generating video...")
                }
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/video/extend")
async def extend_video(video_base64: str, prompt: str, duration_seconds: int = 8):
    """
    Extend an existing video using Veo 3.1's scene extension
    Takes the last frame and generates a continuation
    """
    try:
        endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{VEO_MODEL}:predictLongRunning"
        
        payload = {
            "instances": [{
                "prompt": prompt,
                "video": {
                    "bytesBase64Encoded": video_base64,
                    "mimeType": "video/mp4"
                }
            }],
            "parameters": {
                "sampleCount": 1,
                "durationSeconds": duration_seconds,
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
                "operation_name": result.get("name", "")
            }
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)