from pydantic import BaseModel
from typing import Optional, List

# ============== REQUEST MODELS ==============

class ImageRequest(BaseModel):
    prompt: str
    reference_images: Optional[List[str]] = None
    aspect_ratio: Optional[str] = "1:1"
    resolution: Optional[str] = "1K"

class VideoRequest(BaseModel):
    prompt: str
    first_frame: Optional[str] = None
    last_frame: Optional[str] = None
    reference_images: Optional[List[str]] = None
    aspect_ratio: Optional[str] = "16:9"
    duration_seconds: Optional[int] = 8
    generate_audio: Optional[bool] = True

class TextRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    context: Optional[str] = None
    temperature: Optional[float] = 0.7

class StatusRequest(BaseModel):
    operation_name: str
    prompt: Optional[str] = None

class UpscaleRequest(BaseModel):
    image: str
    upscale_factor: Optional[str] = "x2"
    output_mime_type: Optional[str] = "image/png"

class SaveAssetRequest(BaseModel):
    data: str
    asset_type: str
    prompt: Optional[str] = None
    mime_type: Optional[str] = None

# ============== RESPONSE MODELS ==============

class ImageResponse(BaseModel):
    images: List[str]

class TextResponse(BaseModel):
    response: str

class UpscaleResponse(BaseModel):
    image: str
    mime_type: str

class AssetResponse(BaseModel):
    id: str
    url: str
    asset_type: str
    prompt: Optional[str] = None
    created_at: str
    mime_type: str
    user_id: Optional[str] = None

class VideoStatusResponse(BaseModel):
    status: str
    video_base64: Optional[str] = None
    storage_uri: Optional[str] = None
    progress: Optional[int] = None
    error: Optional[dict] = None
    message: Optional[str] = None

class LibraryResponse(BaseModel):
    assets: List[AssetResponse]
    count: int