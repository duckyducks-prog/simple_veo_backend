import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.generation import GenerationService

@pytest.fixture
def mock_library_service():
    service = MagicMock()
    service.save_asset = AsyncMock()
    return service

@pytest.fixture
def generation_service(mock_library_service):
    return GenerationService(library_service=mock_library_service)

class TestGenerateImage:
    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.google.auth.default")
    async def test_successful_generation(self, mock_auth, mock_client, generation_service):
        """Successful image generation returns images"""
        # Mock auth
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        mock_auth.return_value = (mock_creds, "project")
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{"inlineData": {"data": "base64imagedata"}}]
                }
            }]
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        result = await generation_service.generate_image(
            prompt="a puppy",
            user_id="user-123"
        )
        
        assert len(result.images) == 1
        assert result.images[0] == "base64imagedata"

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.google.auth.default")
    async def test_saves_to_library(self, mock_auth, mock_client, generation_service, mock_library_service):
        """Generated images are saved to library"""
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        mock_auth.return_value = (mock_creds, "project")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{"inlineData": {"data": "base64imagedata"}}]
                }
            }]
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        await generation_service.generate_image(
            prompt="a puppy",
            user_id="user-123"
        )
        
        mock_library_service.save_asset.assert_called_once_with(
            data="base64imagedata",
            asset_type="image",
            user_id="user-123",
            prompt="a puppy"
        )

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.google.auth.default")
    async def test_api_error_raises(self, mock_auth, mock_client, generation_service):
        """API error raises exception"""
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        mock_auth.return_value = (mock_creds, "project")
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        with pytest.raises(Exception, match="API error: 500"):
            await generation_service.generate_image(
                prompt="a puppy",
                user_id="user-123"
            )

    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.google.auth.default")
    async def test_no_images_raises(self, mock_auth, mock_client, generation_service):
        """No images in response raises exception"""
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        mock_auth.return_value = (mock_creds, "project")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"candidates": []}
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        with pytest.raises(Exception, match="No images generated"):
            await generation_service.generate_image(
                prompt="a puppy",
                user_id="user-123"
            )

class TestGenerateVideo:
    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.google.auth.default")
    async def test_returns_operation_name(self, mock_auth, mock_client, generation_service):
        """Video generation returns operation name for polling"""
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        mock_auth.return_value = (mock_creds, "project")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "operations/video-op-123"}
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        result = await generation_service.generate_video(
            prompt="dancing cat",
            user_id="user-123"
        )
        
        assert result["status"] == "processing"
        assert result["operation_name"] == "operations/video-op-123"

class TestGenerateText:
    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.google.auth.default")
    async def test_successful_generation(self, mock_auth, mock_client, generation_service):
        """Text generation returns response"""
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        mock_auth.return_value = (mock_creds, "project")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Hello, I am Claude!"}]
                }
            }]
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        result = await generation_service.generate_text(prompt="Say hello")
        
        assert result.response == "Hello, I am Claude!"

class TestUpscaleImage:
    @pytest.mark.asyncio
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.google.auth.default")
    async def test_successful_upscale(self, mock_auth, mock_client, generation_service):
        """Upscale returns larger image"""
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        mock_auth.return_value = (mock_creds, "project")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "predictions": [{
                "bytesBase64Encoded": "upscaled-image-data",
                "mimeType": "image/png"
            }]
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        result = await generation_service.upscale_image(image="small-image")
        
        assert result.image == "upscaled-image-data"
        assert result.mime_type == "image/png"