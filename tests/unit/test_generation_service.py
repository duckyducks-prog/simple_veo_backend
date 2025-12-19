import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

@pytest.fixture
def mock_library_service():
    service = MagicMock()
    service.save_asset = AsyncMock()
    return service


class TestStripBase64Prefix:
    """Test base64 prefix stripping"""
    
    def test_strips_data_url_prefix(self, mock_library_service):
        """Strips data URL prefix from base64 string"""
        from app.services.generation import GenerationService
        with patch("app.services.generation.client"):
            service = GenerationService(library_service=mock_library_service)
        
        result = service._strip_base64_prefix("data:image/png;base64,abc123")
        assert result == "abc123"
    
    def test_returns_unchanged_without_prefix(self, mock_library_service):
        """Returns string unchanged if no prefix"""
        from app.services.generation import GenerationService
        with patch("app.services.generation.client"):
            service = GenerationService(library_service=mock_library_service)
        
        result = service._strip_base64_prefix("abc123")
        assert result == "abc123"
    
    def test_handles_empty_string(self, mock_library_service):
        """Handles empty string gracefully"""
        from app.services.generation import GenerationService
        with patch("app.services.generation.client"):
            service = GenerationService(library_service=mock_library_service)
        
        result = service._strip_base64_prefix("")
        assert result == ""
    
    def test_handles_none(self, mock_library_service):
        """Handles None gracefully"""
        from app.services.generation import GenerationService
        with patch("app.services.generation.client"):
            service = GenerationService(library_service=mock_library_service)
        
        result = service._strip_base64_prefix(None)
        assert result is None


class TestRetryWithBackoff:
    """Test retry logic with exponential backoff"""
    
    @pytest.mark.asyncio
    async def test_succeeds_first_try(self, mock_library_service):
        """Operation succeeds on first try"""
        from app.services.generation import GenerationService
        with patch("app.services.generation.client"):
            service = GenerationService(library_service=mock_library_service)
        
        async def success_op():
            return "success"
        
        result = await service._retry_with_backoff(success_op, "test")
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retries_on_rate_limit(self, mock_library_service):
        """Retries on 429 rate limit error"""
        from app.services.generation import GenerationService
        with patch("app.services.generation.client"):
            service = GenerationService(library_service=mock_library_service)
        
        call_count = 0
        async def rate_limited_then_success():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("429 Too Many Requests")
            return "success"
        
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._retry_with_backoff(rate_limited_then_success, "test")
        
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retries_on_resource_exhausted(self, mock_library_service):
        """Retries on RESOURCE_EXHAUSTED error"""
        from app.services.generation import GenerationService
        with patch("app.services.generation.client"):
            service = GenerationService(library_service=mock_library_service)
        
        call_count = 0
        async def exhausted_then_success():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("RESOURCE_EXHAUSTED: quota exceeded")
            return "success"
        
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._retry_with_backoff(exhausted_then_success, "test")
        
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_raises_non_rate_limit_error_immediately(self, mock_library_service):
        """Non-rate limit errors are raised immediately"""
        from app.services.generation import GenerationService
        with patch("app.services.generation.client"):
            service = GenerationService(library_service=mock_library_service)
        
        async def other_error():
            raise ValueError("Some other error")
        
        with pytest.raises(ValueError, match="Some other error"):
            await service._retry_with_backoff(other_error, "test")
    
    @pytest.mark.asyncio
    async def test_exhausts_retries(self, mock_library_service):
        """Raises after all retries exhausted"""
        from app.services.generation import GenerationService
        with patch("app.services.generation.client"):
            service = GenerationService(library_service=mock_library_service)
        
        async def always_rate_limited():
            raise Exception("429 Too Many Requests")
        
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception, match="429"):
                await service._retry_with_backoff(always_rate_limited, "test")

class TestGenerateImage:
    @pytest.mark.asyncio
    @patch("app.services.generation.image_client")
    @patch("app.services.generation.client")
    async def test_successful_generation(self, mock_genai_client, mock_image_client, mock_library_service):
        """Successful image generation returns images"""
        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = b"fake_image_bytes"
        
        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]
        
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        mock_image_client.models.generate_content.return_value = mock_response
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        result = await service.generate_image(prompt="a puppy", user_id="user-123")
        
        assert len(result.images) == 1
        mock_library_service.save_asset.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.generation.image_client")
    @patch("app.services.generation.client")
    async def test_no_images_raises(self, mock_genai_client, mock_image_client, mock_library_service):
        """No images in response raises exception"""
        mock_candidate = MagicMock()
        mock_candidate.content.parts = []
        
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        mock_image_client.models.generate_content.return_value = mock_response
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        with pytest.raises(Exception, match="No images generated"):
            await service.generate_image(prompt="a puppy", user_id="user-123")

class TestGenerateText:
    @pytest.mark.asyncio
    @patch("app.services.generation.client")
    async def test_successful_generation(self, mock_genai_client, mock_library_service):
        """Text generation returns response"""
        mock_response = MagicMock()
        mock_response.text = "Hello, I am Gemini!"
        mock_genai_client.models.generate_content.return_value = mock_response
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        result = await service.generate_text(prompt="Say hello")
        
        assert result.response == "Hello, I am Gemini!"

    @pytest.mark.asyncio
    @patch("app.services.generation.client")
    async def test_with_system_prompt(self, mock_genai_client, mock_library_service):
        """Text generation includes system prompt"""
        mock_response = MagicMock()
        mock_response.text = "Arrr!"
        mock_genai_client.models.generate_content.return_value = mock_response
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        await service.generate_text(prompt="Say hello", system_prompt="You are a pirate")
        
        call_args = mock_genai_client.models.generate_content.call_args
        assert "System: You are a pirate" in call_args.kwargs["contents"]

    @pytest.mark.asyncio
    @patch("app.services.generation.client")
    async def test_with_context(self, mock_genai_client, mock_library_service):
        """Text generation includes context"""
        mock_response = MagicMock()
        mock_response.text = "Based on the context..."
        mock_genai_client.models.generate_content.return_value = mock_response
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        await service.generate_text(prompt="Summarize", context="This is some context data")
        
        call_args = mock_genai_client.models.generate_content.call_args
        assert "Context: This is some context data" in call_args.kwargs["contents"]

    @pytest.mark.asyncio
    @patch("app.services.generation.client")
    async def test_no_text_raises(self, mock_genai_client, mock_library_service):
        """No text in response raises exception"""
        mock_response = MagicMock()
        mock_response.text = None
        mock_genai_client.models.generate_content.return_value = mock_response
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        with pytest.raises(Exception, match="No text generated"):
            await service.generate_text(prompt="Say hello")


class TestGenerateVideo:
    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_returns_operation_name(self, mock_genai_client, mock_httpx, mock_library_service):
        """Video generation returns operation name for polling"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "operations/video-op-123"}
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        result = await service.generate_video(prompt="dancing cat", user_id="user-123")
        
        assert result["status"] == "processing"
        assert result["operation_name"] == "operations/video-op-123"

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_video_with_first_frame(self, mock_genai_client, mock_httpx, mock_library_service):
        """Video generation with first frame"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "operations/video-op-123"}
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        result = await service.generate_video(
            prompt="animate this", 
            user_id="user-123",
            first_frame="data:image/png;base64,abc123"
        )
        
        assert result["status"] == "processing"

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_video_with_last_frame(self, mock_genai_client, mock_httpx, mock_library_service):
        """Video generation with last frame"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "operations/video-op-123"}
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        result = await service.generate_video(
            prompt="animate this", 
            user_id="user-123",
            last_frame="abc123"
        )
        
        assert result["status"] == "processing"

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_video_with_reference_images(self, mock_genai_client, mock_httpx, mock_library_service):
        """Video generation with reference images"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "operations/video-op-123"}
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        result = await service.generate_video(
            prompt="video with subjects", 
            user_id="user-123",
            reference_images=["img1", "img2"]
        )
        
        assert result["status"] == "processing"

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_video_rate_limit_error(self, mock_genai_client, mock_httpx, mock_library_service):
        """Video generation handles 429 rate limit"""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception, match="429"):
                await service.generate_video(prompt="test", user_id="user-123")

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_video_api_error(self, mock_genai_client, mock_httpx, mock_library_service):
        """Video generation handles API errors"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        with pytest.raises(Exception, match="API error"):
            await service.generate_video(prompt="test", user_id="user-123")


class TestVideoStatus:
    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_status_processing(self, mock_genai_client, mock_httpx, mock_library_service):
        """Video status returns processing state"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "done": False,
            "metadata": {"progressPercent": 50}
        }
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        result = await service.check_video_status("operations/123", "user-123", "test prompt")
        
        assert result.status == "processing"
        assert result.progress == 50

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_status_complete_with_base64(self, mock_genai_client, mock_httpx, mock_library_service):
        """Video status returns completed video with base64"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "done": True,
            "response": {
                "generateVideoResponse": {
                    "generatedSamples": [{
                        "video": {"bytesBase64Encoded": "video-data-base64"}
                    }]
                }
            }
        }
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        result = await service.check_video_status("operations/123", "user-123", "test prompt")
        
        assert result.status == "complete"
        assert result.video_base64 == "video-data-base64"
        mock_library_service.save_asset.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_status_complete_with_uri(self, mock_genai_client, mock_httpx, mock_library_service):
        """Video status returns completed video with URI"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "done": True,
            "response": {
                "generateVideoResponse": {
                    "generatedSamples": [{
                        "video": {"uri": "gs://bucket/video.mp4"}
                    }]
                }
            }
        }
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        result = await service.check_video_status("operations/123", "user-123", "test prompt")
        
        assert result.status == "complete"
        assert result.storage_uri == "gs://bucket/video.mp4"

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_status_complete_veo31_format(self, mock_genai_client, mock_httpx, mock_library_service):
        """Video status handles Veo 3.1 response format"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "done": True,
            "response": {
                "videos": [{
                    "bytesBase64Encoded": "veo31-video-data"
                }]
            }
        }
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        result = await service.check_video_status("operations/123", "user-123", "test prompt")
        
        assert result.status == "complete"
        assert result.video_base64 == "veo31-video-data"

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_status_complete_no_video_data(self, mock_genai_client, mock_httpx, mock_library_service):
        """Video status handles missing video data"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "done": True,
            "response": {"someOtherKey": "value"}
        }
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        result = await service.check_video_status("operations/123", "user-123", "test prompt")
        
        assert result.status == "error"
        assert "no video data found" in result.error["message"].lower()

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_status_error(self, mock_genai_client, mock_httpx, mock_library_service):
        """Video status returns error state"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "done": True,
            "error": {"message": "Video generation failed", "code": 500}
        }
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        result = await service.check_video_status("operations/123", "user-123", "test prompt")
        
        assert result.status == "error"
        assert result.error["message"] == "Video generation failed"

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_status_library_save_failure(self, mock_genai_client, mock_httpx, mock_library_service):
        """Video status handles library save failure gracefully"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "done": True,
            "response": {
                "generateVideoResponse": {
                    "generatedSamples": [{
                        "video": {"bytesBase64Encoded": "video-data"}
                    }]
                }
            }
        }
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        mock_library_service.save_asset.side_effect = Exception("Storage error")
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        # Should still return video even if save fails
        result = await service.check_video_status("operations/123", "user-123", "test prompt")
        
        assert result.status == "complete"
        assert result.video_base64 == "video-data"

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_status_rate_limit(self, mock_genai_client, mock_httpx, mock_library_service):
        """Video status handles rate limit"""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception, match="429"):
                await service.check_video_status("operations/123", "user-123", "test prompt")

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_status_api_error(self, mock_genai_client, mock_httpx, mock_library_service):
        """Video status handles API errors"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal error"
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        with pytest.raises(Exception, match="API error"):
            await service.check_video_status("operations/123", "user-123", "test prompt")


class TestUpscaleImage:
    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_successful_upscale(self, mock_genai_client, mock_httpx, mock_library_service):
        """Upscale returns larger image"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "predictions": [{
                "bytesBase64Encoded": "upscaled-image-data",
                "mimeType": "image/png"
            }]
        }
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        result = await service.upscale_image(image="small-image")
        
        assert result.image == "upscaled-image-data"
        assert result.mime_type == "image/png"

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_upscale_api_error(self, mock_genai_client, mock_httpx, mock_library_service):
        """Upscale handles API errors"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        with pytest.raises(Exception, match="API error"):
            await service.upscale_image(image="small-image")

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_upscale_no_predictions(self, mock_genai_client, mock_httpx, mock_library_service):
        """Upscale handles empty predictions"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"predictions": []}
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        with pytest.raises(Exception, match="No upscaled image returned"):
            await service.upscale_image(image="small-image")

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    async def test_upscale_empty_image_data(self, mock_genai_client, mock_httpx, mock_library_service):
        """Upscale handles empty image data in prediction"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "predictions": [{"bytesBase64Encoded": "", "mimeType": "image/png"}]
        }
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        with pytest.raises(Exception, match="No upscaled image returned"):
            await service.upscale_image(image="small-image")


class TestLibrarySaveErrors:
    @pytest.mark.asyncio
    @patch("app.services.generation.image_client")
    @patch("app.services.generation.client")
    async def test_save_to_library_failure_logged(self, mock_genai_client, mock_image_client, mock_library_service):
        """Failed library save is logged but doesn't crash generation"""
        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = b"fake_image_bytes"
        
        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]
        
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        mock_image_client.models.generate_content.return_value = mock_response
        
        # Make library save fail
        mock_library_service.save_asset.side_effect = Exception("Storage error")
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        # Should still return images even if save fails
        result = await service.generate_image(prompt="a puppy", user_id="user-123")
        
        assert len(result.images) == 1
        mock_library_service.save_asset.assert_called_once()