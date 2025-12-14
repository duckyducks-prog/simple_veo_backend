import base64
import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
from typing import Optional, List
from app.config import settings
from app.schemas import ImageResponse, TextResponse, UpscaleResponse, VideoStatusResponse
from app.services.library import LibraryService
from app.logging_config import setup_logger

logger = setup_logger(__name__)

# Initialize Vertex AI once at module load
vertexai.init(project=settings.project_id, location=settings.location)


class GenerationService:
    def __init__(self, library_service: Optional[LibraryService] = None):
        self.library = library_service or LibraryService()
        
        # Initialize models from config
        self.text_model = GenerativeModel(settings.gemini_text_model)
        self.image_model = GenerativeModel(settings.gemini_image_model)
    
    def _strip_base64_prefix(self, data: str) -> str:
        """Remove data URL prefix if present"""
        if data and ',' in data and data.startswith('data:'):
            return data.split(',', 1)[1]
        return data
    
    def _get_auth_headers(self) -> dict:
        """Get authentication headers for REST API calls"""
        import google.auth
        import google.auth.transport.requests
        
        credentials, _ = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        return {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json"
        }

    async def generate_image(
        self,
        prompt: str,
        user_id: str,
        reference_images: Optional[List[str]] = None
    ) -> ImageResponse:
        """Generate images using Gemini"""
        parts = []
        
        if reference_images:
            for ref_image in reference_images:
                clean_image = self._strip_base64_prefix(ref_image)
                image_bytes = base64.b64decode(clean_image)
                parts.append(Part.from_data(image_bytes, mime_type="image/png"))
        
        parts.append(prompt)
        
        response = self.image_model.generate_content(
            parts,
            generation_config=GenerationConfig(
                response_modalities=["TEXT", "IMAGE"]
            )
        )
        
        images = []
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    images.append(base64.b64encode(part.inline_data.data).decode())
        
        if not images:
            raise Exception("No images generated")
        
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
        generate_audio: bool = True
    ) -> dict:
        """Start video generation using Veo (REST API - no SDK support yet)"""
        import httpx
        
        endpoint = f"https://{settings.location}-aiplatform.googleapis.com/v1/projects/{settings.project_id}/locations/{settings.location}/publishers/google/models/{settings.veo_model}:predictLongRunning"
        
        instance = {"prompt": prompt}
        
        if first_frame:
            instance["image"] = {
                "bytesBase64Encoded": self._strip_base64_prefix(first_frame),
                "mimeType": "image/png"
            }
        
        if last_frame:
            instance["lastFrame"] = {
                "bytesBase64Encoded": self._strip_base64_prefix(last_frame),
                "mimeType": "image/png"
            }
        
        if reference_images:
            instance["referenceImages"] = [
                {
                    "image": {
                        "bytesBase64Encoded": self._strip_base64_prefix(img),
                        "mimeType": "image/png"
                    },
                    "referenceType": "REFERENCE_TYPE_SUBJECT"
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
        
        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, json=payload, headers=self._get_auth_headers(), timeout=300.0)
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text}")
        
        result = response.json()
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
        """Check video generation status (REST API)"""
        import httpx
        
        endpoint = f"https://{settings.location}-aiplatform.googleapis.com/v1/{operation_name}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, headers=self._get_auth_headers(), timeout=60.0)
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        if result.get("done"):
            if "response" in result:
                videos = result["response"].get("generateVideoResponse", {}).get("generatedSamples", [])
                if videos:
                    video_data = videos[0].get("video", {})
                    if "bytesBase64Encoded" in video_data:
                        video_base64 = video_data["bytesBase64Encoded"]
                        
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
                    elif "uri" in video_data:
                        return VideoStatusResponse(status="complete", storage_uri=video_data["uri"])
                
                return VideoStatusResponse(status="complete", message="Video ready but no data returned")
            elif "error" in result:
                return VideoStatusResponse(status="error", error=result["error"])
        
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
        
        response = self.text_model.generate_content(
            full_prompt,
            generation_config=GenerationConfig(
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
        """Upscale an image using Imagen (REST API - no SDK support yet)"""
        import httpx
        
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
        
        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, json=payload, headers=self._get_auth_headers(), timeout=300.0)
        
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