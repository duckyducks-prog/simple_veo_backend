from fastapi import APIRouter, Depends, HTTPException
from app.schemas import (
    ImageRequest, ImageResponse,
    VideoRequest, StatusRequest, VideoStatusResponse,
    TextRequest, TextResponse,
    UpscaleRequest, UpscaleResponse
)
from app.auth import get_current_user
from app.services.generation import GenerationService
from app.services.library_firestore import LibraryServiceFirestore
from app.logging_config import setup_logger
import base64
import httpx
import re

logger = setup_logger(__name__)
router = APIRouter()

async def resolve_asset_to_base64(asset_id: str, user_id: str) -> str:
    """Resolve an asset ID to base64 image data by fetching from GCS"""
    try:
        # Get asset metadata from Firestore
        library_service = LibraryServiceFirestore()
        asset = await library_service.get_asset_by_id(asset_id)
        
        if not asset or not asset.get("url"):
            raise ValueError(f"Asset {asset_id} not found or has no URL")
        
        # Download the image from GCS URL
        async with httpx.AsyncClient() as client:
            response = await client.get(asset["url"])
            response.raise_for_status()
            image_bytes = response.content
        
        # Convert to base64
        return base64.b64encode(image_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to resolve asset {asset_id}: {e}")
        raise

def is_asset_id(value: str) -> bool:
    """Check if a string looks like an asset ID (UUID format)"""
    # UUID pattern: 8-4-4-4-12 hex characters
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, value, re.IGNORECASE))

def get_generation_service() -> GenerationService:
    return GenerationService()

@router.post("/image", response_model=ImageResponse)
async def generate_image(
    request: ImageRequest,
    user: dict = Depends(get_current_user),
    service: GenerationService = Depends(get_generation_service)
):
    """Generate images using Gemini 3 Pro Image"""
    try:
        ref_count = len(request.reference_images) if request.reference_images else 0
        logger.info(f"Image generation request from user {user['email']}, prompt={request.prompt[:50]}..., reference_images={ref_count}")
        return await service.generate_image(
            prompt=request.prompt,
            user_id=user["uid"],
            reference_images=request.reference_images
        )
    except Exception as e:
        logger.error(f"Image generation failed for user {user['email']}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/video")
async def generate_video(
    request: VideoRequest,
    user: dict = Depends(get_current_user),
    service: GenerationService = Depends(get_generation_service)
):
    """Generate video using Veo 3.1"""
    try:
        logger.info(f"Video generation request from user {user['email']}")
        logger.info(f"Video params: prompt={request.prompt[:50] if request.prompt else 'None'}..., first_frame={'Yes' if request.first_frame else 'No'}, aspect_ratio={request.aspect_ratio}, duration={request.duration_seconds}, seed={request.seed}")
        
        # Resolve asset IDs to base64 image data
        first_frame_data = None
        if request.first_frame:
            if is_asset_id(request.first_frame):
                logger.info(f"Resolving first_frame asset ID: {request.first_frame}")
                first_frame_data = await resolve_asset_to_base64(request.first_frame, user["uid"])
            else:
                first_frame_data = request.first_frame
                frame_preview = first_frame_data[:100] if len(first_frame_data) > 100 else first_frame_data
                logger.info(f"First frame data length: {len(first_frame_data)}, preview: {frame_preview}")
        
        # Resolve reference image asset IDs
        reference_images_data = None
        if request.reference_images:
            reference_images_data = []
            for ref_img in request.reference_images:
                if is_asset_id(ref_img):
                    logger.info(f"Resolving reference_image asset ID: {ref_img}")
                    img_data = await resolve_asset_to_base64(ref_img, user["uid"])
                    reference_images_data.append(img_data)
                else:
                    reference_images_data.append(ref_img)
        
        return await service.generate_video(
            prompt=request.prompt,
            user_id=user["uid"],
            first_frame=first_frame_data,
            last_frame=request.last_frame,
            reference_images=reference_images_data,
            aspect_ratio=request.aspect_ratio,
            duration_seconds=request.duration_seconds,
            generate_audio=request.generate_audio,
            seed=request.seed
        )
    except Exception as e:
        logger.error(f"Video generation failed for user {user['email']}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/text", response_model=TextResponse)
async def generate_text(
    request: TextRequest,
    service: GenerationService = Depends(get_generation_service)
):
    """Generate text using Gemini 3 Pro"""
    try:
        logger.info("Text generation request")
        return await service.generate_text(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            context=request.context,
            temperature=request.temperature
        )
    except Exception as e:
        logger.error(f"Text generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/video/status", response_model=VideoStatusResponse)
async def check_video_status(
    request: StatusRequest,
    user: dict = Depends(get_current_user),
    service: GenerationService = Depends(get_generation_service)
):
    """Check video generation status"""
    try:
        logger.debug(f"Video status check from user {user['email']}: {request.operation_name}")
        return await service.check_video_status(
            operation_name=request.operation_name,
            user_id=user["uid"],
            prompt=request.prompt
        )
    except Exception as e:
        logger.error(f"Video status check failed for user {user['email']}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upscale", response_model=UpscaleResponse)
async def upscale_image(
    request: UpscaleRequest,
    user: dict = Depends(get_current_user),
    service: GenerationService = Depends(get_generation_service)
):
    """Upscale an image using Imagen 4.0"""
    try:
        logger.info(f"Image upscale request from user {user['email']}")
        return await service.upscale_image(
            image=request.image,
            upscale_factor=request.upscale_factor,
            output_mime_type=request.output_mime_type
        )
    except Exception as e:
        logger.error(f"Image upscale failed for user {user['email']}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))