import pytest
from unittest.mock import MagicMock, AsyncMock, patch

@pytest.fixture
def mock_library_service():
    service = MagicMock()
    service.save_asset = AsyncMock()
    return service

class TestGenerateImage:
    @pytest.mark.asyncio
    @patch("app.services.generation.client")
    async def test_successful_generation(self, mock_genai_client, mock_library_service):
        """Successful image generation returns images"""
        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = b"fake_image_bytes"
        
        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]
        
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        mock_genai_client.models.generate_content.return_value = mock_response
        
        from app.services.generation import GenerationService
        service = GenerationService(library_service=mock_library_service)
        
        result = await service.generate_image(prompt="a puppy", user_id="user-123")
        
        assert len(result.images) == 1
        mock_library_service.save_asset.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.generation.client")
    async def test_no_images_raises(self, mock_genai_client, mock_library_service):
        """No images in response raises exception"""
        mock_candidate = MagicMock()
        mock_candidate.content.parts = []
        
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        mock_genai_client.models.generate_content.return_value = mock_response
        
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