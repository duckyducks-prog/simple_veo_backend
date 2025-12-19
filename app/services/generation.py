import base64
import httpx
import asyncio
import google.auth
import google.auth.transport.requests
from google import genai
from google.genai import types
from typing import Optional, List
from app.config import settings
from app.schemas import ImageResponse, TextResponse, UpscaleResponse, VideoStatusResponse
from app.services.library_firestore import LibraryServiceFirestore
from app.logging_config import setup_logger

logger = setup_logger(__name__)

# Retry configuration
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 5  # seconds (longer initial delay)
MAX_RETRY_DELAY = 60  # seconds

# Initialize the client
client = genai.Client(
    vertexai=True,
    project=settings.project_id,
    location=settings.location
)

image_client = genai.Client(
    vertexai=True,
    project=settings.project_id,
    location="us-central1"  # Gemini image models
)


class GenerationService:
    def __init__(self, library_service: Optional[LibraryServiceFirestore] = None):
        self.library = library_service or LibraryServiceFirestore()
    
    def _strip_base64_prefix(self, data: str) -> str:
        """Remove data URL prefix if present and ensure valid base64 padding"""
        if not data:
            return data
            
        # Remove data URL prefix if present
        if ',' in data and data.startswith('data:'):
            data = data.split(',', 1)[1]
        
        # Add padding if necessary (base64 strings must be multiple of 4)
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
        
        return data
    
    def _get_auth_headers(self) -> dict:
        """Get authentication headers for REST API calls"""
        credentials, _ = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        return {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json"
        }
    
    async def _retry_with_backoff(self, operation, operation_name: str):
        """Execute an operation with exponential backoff retry on rate limit errors"""
        last_exception = None
        
        for attempt in range(MAX_RETRIES):
            try:
                return await operation()
            except Exception as e:
                error_str = str(e)
                # Check if it's a rate limit error (429)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                    logger.warning(f"{operation_name}: Rate limited (attempt {attempt + 1}/{MAX_RETRIES}). Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    last_exception = e
                else:
                    # Not a rate limit error, raise immediately
                    raise
        
        # All retries exhausted
        logger.error(f"{operation_name}: All {MAX_RETRIES} retries exhausted")
        raise last_exception

    async def generate_image(
        self,
        prompt: str,
        user_id: str,
        reference_images: Optional[List[str]] = None,
        aspect_ratio: str = "1:1",
        resolution: str = "1K"
    ) -> ImageResponse:
        """Generate images using Gemini with retry on rate limits"""
        
<<<<<<< HEAD
        if reference_images:
            for ref_image in reference_images:
                clean_image = self._strip_base64_prefix(ref_image)
                image_bytes = base64.b64decode(clean_image)
                contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/png"))
        
        contents.append(prompt)
        
        response = image_client.models.generate_content(
            model=settings.gemini_image_model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=resolution
                )
=======
        async def _do_generate():
            contents = []
            
            # Add reference images if provided - use as visual ingredients
            if reference_images:
                logger.info(f"Processing {len(reference_images)} reference images as ingredients")
                valid_images = []
                
                for i, ref_image in enumerate(reference_images):
                    try:
                        clean_image = self._strip_base64_prefix(ref_image)
                        image_bytes = base64.b64decode(clean_image)
                        
                        # Validate image size (Gemini requires reasonable sized images)
                        if len(image_bytes) < 100:
                            logger.warning(f"Reference image {i+1} too small ({len(image_bytes)} bytes), skipping")
                            continue
                        
                        # Check for valid PNG/JPEG header
                        is_png = image_bytes[:8] == b'\x89PNG\r\n\x1a\n'
                        is_jpeg = image_bytes[:2] == b'\xff\xd8'
                        
                        if not (is_png or is_jpeg):
                            logger.warning(f"Reference image {i+1} has invalid format (not PNG/JPEG), skipping")
                            continue
                        
                        mime_type = "image/png" if is_png else "image/jpeg"
                        contents.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
                        valid_images.append(i+1)
                        logger.info(f"Added reference image {i+1}: {len(image_bytes)} bytes, format: {mime_type}")
                        
                    except Exception as e:
                        logger.error(f"Failed to process reference image {i+1}: {e}")
                        continue
                
                if valid_images:
                    # Enhanced prompt that treats reference images as ingredients/components
                    ingredient_prompt = (
                        f"IMPORTANT: Use the provided reference image(s) as visual ingredients and components. "
                        f"Extract and incorporate their key visual elements (subjects, objects, colors, textures, style) "
                        f"into the generated image.\n\n"
                        f"Generation request: {prompt}\n\n"
                        f"Create a new image that incorporates visual elements from the reference image(s) "
                        f"while following the generation request above."
                    )
                    contents.append(ingredient_prompt)
                    logger.info(f"Using {len(valid_images)} valid reference images: {valid_images}")
                else:
                    logger.warning("No valid reference images found, generating without references")
                    contents = [prompt]
            else:
                contents.append(prompt)
            
            # Build config with appropriate settings
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"]
>>>>>>> firestore-migration
            )
            
            response = image_client.models.generate_content(
                model=settings.gemini_image_model,
                contents=contents,
                config=config
            )
            
            images = []
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    images.append(base64.b64encode(part.inline_data.data).decode())
            
            if not images:
                raise Exception("No images generated")
            
            logger.info(f"Generated {len(images)} image(s) successfully")
            return images
        
        # Execute with retry
        images = await self._retry_with_backoff(_do_generate, "Image generation")
        
        # Save to library (don't retry this part)
        for img_data in images:
            try:
                await self.library.save_asset(
                    data=img_data,
                    asset_type="image",
                    user_id=user_id,
                    prompt=prompt
                )
            except Exception as e:
                logger.error(f"Failed to save image to library: {type(e).__name__}: {e}")
        
        return ImageResponse(images=images)

    async def generate_video(
        self,
        prompt: str,
        user_id: str,
        first_frame: Optional[str] = None,
        last_frame: Optional[str] = None,
        reference_images: Optional[List[str]] = None,
        aspect_ratio: str = "16:9",
        duration_seconds: int = 8,
        generate_audio: bool = True,
        seed: Optional[int] = None
    ) -> dict:
        """Start video generation using Veo via REST API"""
        endpoint = f"https://{settings.location}-aiplatform.googleapis.com/v1/projects/{settings.project_id}/locations/{settings.location}/publishers/google/models/{settings.veo_model}:predictLongRunning"
        
        instance = {"prompt": prompt}
        
        if first_frame:
            cleaned_frame = self._strip_base64_prefix(first_frame)
            logger.info(f"Adding first frame to request, original length: {len(first_frame)}, cleaned length: {len(cleaned_frame)}")
            instance["image"] = {
                "bytesBase64Encoded": cleaned_frame,
                "mimeType": "image/png"
            }
        else:
            logger.warning("No first frame provided to generate_video")
        
        if last_frame:
            instance["lastFrame"] = {
                "bytesBase64Encoded": self._strip_base64_prefix(last_frame),
                "mimeType": "image/png"
            }
        
        # Reference images for subject consistency (Veo 3.1 feature)
        # Format: uses "image" field (not "referenceImage") and lowercase "style" type
        if reference_images:
            instance["referenceImages"] = [
                {
                    "image": {
                        "bytesBase64Encoded": self._strip_base64_prefix(img),
                        "mimeType": "image/png"
                    },
                    "referenceType": "style"
                }
                for img in reference_images[:3]
            ]
        
        payload = {
            "instances": [instance],
            "parameters": {
                "aspectRatio": aspect_ratio,
                "sampleCount": 1,
                "durationSeconds": duration_seconds,
                "generateAudio": generate_audio,
                "resolution": "1080p"
            }
        }
        
        # Add seed if provided for consistent generation (voice, style, etc.)
        if seed is not None:
            payload["parameters"]["seed"] = seed
            logger.info(f"Using seed {seed} for consistent generation")
        
<<<<<<< HEAD
        if response.status_code == 429:
            raise Exception(f"API error: 429 - Rate limit exceeded. You may have too many concurrent video generations or have reached your daily quota. Please wait a few minutes and try again.")
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text}")
=======
        logger.info(f"Veo API request: endpoint={endpoint}, instance_keys={list(instance.keys())}")
        
        async def _do_video_request():
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(endpoint, json=payload, headers=self._get_auth_headers(), timeout=300.0)
            
            if response.status_code == 429:
                raise Exception(f"429 RESOURCE_EXHAUSTED: {response.text}")
            
            if response.status_code != 200:
                logger.error(f"Veo API error: status={response.status_code}")
                logger.error(f"Veo API response: {response.text[:1000]}")
                raise Exception(f"API error: {response.status_code} - {response.text}")
            
            return response.json()
        
        result = await self._retry_with_backoff(_do_video_request, "Video generation")
>>>>>>> firestore-migration
        
        return {
            "status": "processing",
            "operation_name": result.get("name", ""),
            "message": "Video generation started. Poll /generate/video/status for completion."
        }

    async def check_video_status(
        self,
        operation_name: str,
        user_id: str,
        prompt: Optional[str] = None
    ) -> VideoStatusResponse:
        """Check video generation status using fetchPredictOperation"""
        endpoint = f"https://{settings.location}-aiplatform.googleapis.com/v1/projects/{settings.project_id}/locations/{settings.location}/publishers/google/models/{settings.veo_model}:fetchPredictOperation"
        
        payload = {
            "operationName": operation_name
        }
        
        async def _do_status_check():
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    endpoint, 
                    json=payload, 
                    headers=self._get_auth_headers(), 
                    timeout=60.0
                )
            
            if response.status_code == 429:
                raise Exception(f"429 RESOURCE_EXHAUSTED: {response.text}")
            
            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code} - {response.text}")
            
            return response.json()
        
        result = await self._retry_with_backoff(_do_status_check, "Video status check")
        
        if result.get("done"):
            if "response" in result:
                response_data = result["response"]
                video_base64 = None
                storage_uri = None
                
                # Try different response structures
                # Structure 1: generateVideoResponse.generatedSamples
                videos = response_data.get("generateVideoResponse", {}).get("generatedSamples", [])
                if videos:
                    video_data = videos[0].get("video", {})
                    video_base64 = video_data.get("bytesBase64Encoded")
                    storage_uri = video_data.get("uri")
                
                # Structure 2: videos array (Veo 3.1)
                if not video_base64 and not storage_uri:
                    videos = response_data.get("videos", [])
                    if videos:
                        video_base64 = videos[0].get("bytesBase64Encoded")
                        storage_uri = videos[0].get("uri") or videos[0].get("gcsUri")
                
                if video_base64:
                    try:
                        await self.library.save_asset(
                            data=video_base64,
                            asset_type="video",
                            user_id=user_id,
                            prompt=prompt
                        )
                    except Exception as e:
                        logger.error(f"Failed to save video to library: {type(e).__name__}: {e}")
                    
                    return VideoStatusResponse(status="complete", video_base64=video_base64)
                
                if storage_uri:
                    return VideoStatusResponse(status="complete", storage_uri=storage_uri)
                
                return VideoStatusResponse(
                    status="error",
                    error={"message": "Video generation completed but no video data found"},
                    message=f"Available response keys: {list(response_data.keys())}"
                )
            
            elif "error" in result:
                return VideoStatusResponse(status="error", error=result["error"])
        
        metadata = result.get("metadata", {})
        return VideoStatusResponse(
            status="processing",
            progress=metadata.get("progressPercent", 0)
        )
        
        metadata = result.get("metadata", {})
        return VideoStatusResponse(
            status="processing",
            progress=metadata.get("progressPercent", 0)
        )

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        temperature: float = 0.7
    ) -> TextResponse:
        """Generate text using Gemini"""
        full_prompt = ""
        if system_prompt:
            full_prompt += f"System: {system_prompt}\n\n"
        if context:
            full_prompt += f"Context: {context}\n\n"
        full_prompt += prompt
        
        response = client.models.generate_content(
            model=settings.gemini_text_model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=8192
            )
        )
        
        if response.text:
            return TextResponse(response=response.text)
        
        raise Exception("No text generated")

    async def upscale_image(
        self,
        image: str,
        upscale_factor: str = "x2",
        output_mime_type: str = "image/png"
    ) -> UpscaleResponse:
        """Upscale an image using Imagen"""
        endpoint = f"https://{settings.location}-aiplatform.googleapis.com/v1/projects/{settings.project_id}/locations/{settings.location}/publishers/google/models/{settings.upscale_model}:predict"
        
        payload = {
            "instances": [{
                "prompt": "Upscale the image",
                "image": {"bytesBase64Encoded": self._strip_base64_prefix(image)}
            }],
            "parameters": {
                "mode": "upscale",
                "upscaleConfig": {"upscaleFactor": upscale_factor},
                "outputOptions": {"mimeType": output_mime_type}
            }
        }
        
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(endpoint, json=payload, headers=self._get_auth_headers(), timeout=300.0)
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text}")
        
        result = response.json()
        predictions = result.get("predictions", [])
        
        if predictions:
            upscaled_image = predictions[0].get("bytesBase64Encoded", "")
            mime_type = predictions[0].get("mimeType", output_mime_type)
            if upscaled_image:
                return UpscaleResponse(image=upscaled_image, mime_type=mime_type)
        
        raise Exception("No upscaled image returned")