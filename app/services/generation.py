import httpx
import google.auth
import google.auth.transport.requests
from typing import Optional, List
from app.config import settings
from app.schemas import ImageResponse, TextResponse, UpscaleResponse, VideoStatusResponse
from app.services.library import LibraryService

class GenerationService:
    def __init__(self, library_service: Optional[LibraryService] = None):
        self.library = library_service or LibraryService()
    
    def _get_auth_headers(self) -> dict:
        """Get authentication headers for Google Cloud APIs"""
        credentials, _ = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        return {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json"
        }
    
    def _strip_base64_prefix(self, data: str) -> str:
        """Remove data URL prefix if present"""
        if data and ',' in data and data.startswith('data:'):
            return data.split(',', 1)[1]
        return data

    async def generate_image(
        self,
        prompt: str,
        user_id: str,
        reference_images: Optional[List[str]] = None
    ) -> ImageResponse:
        """Generate images using Gemini 3 Pro Image"""
        endpoint = f"https://aiplatform.googleapis.com/v1/projects/{settings.project_id}/locations/global/publishers/google/models/{settings.gemini_image_model}:generateContent"
        
        parts = []
        
        if reference_images:
            for ref_image in reference_images:
                clean_image = self._strip_base64_prefix(ref_image)
                parts.append({
                    "inlineData": {
                        "mimeType": "image/png",
                        "data": clean_image
                    }
                })
        
        parts.append({"text": prompt})
        
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
                headers=self._get_auth_headers(),
                timeout=300.0
            )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text}")
        
        result = response.json()
        images = []
        
        candidates = result.get("candidates", [])
        for candidate in candidates:
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            for part in parts:
                if "inlineData" in part:
                    images.append(part["inlineData"]["data"])
        
        if not images:
            raise Exception("No images generated")
        
        # Auto-save to library
        for img_data in images:
            try:
                await self.library.save_asset(
                    data=img_data,
                    asset_type="image",
                    user_id=user_id,
                    prompt=prompt
                )
            except Exception as e:
                print(f"[METADATA ERROR] {type(e).__name__}: {e}")
        
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
        """Start video generation using Veo 3.1"""
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
            response = await client.post(
                endpoint,
                json=payload,
                headers=self._get_auth_headers(),
                timeout=300.0
            )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text}")
        
        result = response.json()
        return {
            "status": "processing",
            "operation_name": result.get("name", ""),
            "message": "Video generation started. Poll /video/status for completion."
        }

    async def check_video_status(
        self,
        operation_name: str,
        user_id: str,
        prompt: Optional[str] = None
    ) -> VideoStatusResponse:
        """Check video generation status"""
        endpoint = f"https://{settings.location}-aiplatform.googleapis.com/v1/{operation_name}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                endpoint,
                headers=self._get_auth_headers(),
                timeout=60.0
            )
        
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
                        
                        # Auto-save to library
                        try:
                            await self.library.save_asset(
                                data=video_base64,
                                asset_type="video",
                                user_id=user_id,
                                prompt=prompt
                            )
                        except Exception as e:
                            print(f"[VIDEO METADATA ERROR] {type(e).__name__}: {e}")
                        
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
        """Generate text using Gemini 3 Pro"""
        endpoint = f"https://{settings.location}-aiplatform.googleapis.com/v1/projects/{settings.project_id}/locations/{settings.location}/publishers/google/models/{settings.gemini_text_model}:generateContent"
        
        contents = []
        
        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System: {system_prompt}"}]
            })
        
        user_text = prompt
        if context:
            user_text = f"Context: {context}\n\nRequest: {prompt}"
        
        contents.append({
            "role": "user",
            "parts": [{"text": user_text}]
        })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 8192
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers=self._get_auth_headers(),
                timeout=120.0
            )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text}")
        
        result = response.json()
        candidates = result.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                return TextResponse(response=parts[0].get("text", ""))
        
        raise Exception("No text generated")

    async def upscale_image(
        self,
        image: str,
        upscale_factor: str = "x2",
        output_mime_type: str = "image/png"
    ) -> UpscaleResponse:
        """Upscale an image using Imagen 4.0"""
        endpoint = f"https://{settings.location}-aiplatform.googleapis.com/v1/projects/{settings.project_id}/locations/{settings.location}/publishers/google/models/{settings.upscale_model}:predict"
        
        payload = {
            "instances": [
                {
                    "prompt": "Upscale the image",
                    "image": {
                        "bytesBase64Encoded": self._strip_base64_prefix(image)
                    }
                }
            ],
            "parameters": {
                "mode": "upscale",
                "upscaleConfig": {
                    "upscaleFactor": upscale_factor
                },
                "outputOptions": {
                    "mimeType": output_mime_type
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers=self._get_auth_headers(),
                timeout=300.0
            )
        
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