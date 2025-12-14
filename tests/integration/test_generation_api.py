import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

class TestImageGenerationAPI:
    """Integration tests for /generate/image endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.post("/generate/image", json={"prompt": "a puppy"})
        assert response.status_code == 401
        assert "No authorization token" in response.json()["detail"]
    
    @patch("app.services.library.storage.Client")
    def test_requires_prompt(self, mock_storage, client, mock_auth, mock_gcs_client):
        """Request without prompt returns 422"""
        mock_storage.return_value = mock_gcs_client
        
        response = client.post("/generate/image", json={})
        assert response.status_code == 422
    
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.google.auth.default")
    @patch("app.services.library.storage.Client")
    def test_successful_generation(
        self, 
        mock_storage, 
        mock_auth_default, 
        mock_httpx,
        client, 
        mock_auth,
        mock_gcs_client,
        mock_vertex_response_image
    ):
        """Full successful image generation flow"""
        # Setup mocks
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        mock_auth_default.return_value = (mock_creds, "project")
        mock_storage.return_value = mock_gcs_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_vertex_response_image
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Make request
        response = client.post("/generate/image", json={
            "prompt": "a cute puppy",
            "aspect_ratio": "16:9"
        })
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "images" in data
        assert len(data["images"]) == 1
        assert data["images"][0] == "base64encodedimagedata"
    
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.google.auth.default")
    @patch("app.services.library.storage.Client")
    def test_with_reference_images(
        self,
        mock_storage,
        mock_auth_default,
        mock_httpx,
        client,
        mock_auth,
        mock_gcs_client,
        mock_vertex_response_image
    ):
        """Generation with reference images"""
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        mock_auth_default.return_value = (mock_creds, "project")
        mock_storage.return_value = mock_gcs_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_vertex_response_image
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        response = client.post("/generate/image", json={
            "prompt": "same style as reference",
            "reference_images": ["base64refimage1", "base64refimage2"]
        })
        
        assert response.status_code == 200
        
        # Verify reference images were included in API call
        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        parts = payload["contents"][0]["parts"]
        assert len(parts) == 3  # 2 images + 1 text prompt
    
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.google.auth.default")
    @patch("app.services.library.storage.Client")
    def test_api_error_returns_500(
        self,
        mock_storage,
        mock_auth_default,
        mock_httpx,
        client,
        mock_auth,
        mock_gcs_client
    ):
        """Vertex AI error returns 500"""
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        mock_auth_default.return_value = (mock_creds, "project")
        mock_storage.return_value = mock_gcs_client
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        response = client.post("/generate/image", json={"prompt": "test"})
        
        assert response.status_code == 500
        assert "API error: 500" in response.json()["detail"]


class TestVideoGenerationAPI:
    """Integration tests for /generate/video endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.post("/generate/video", json={"prompt": "dancing cat"})
        assert response.status_code == 401
    
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.google.auth.default")
    @patch("app.services.library.storage.Client")
    def test_returns_operation_name(
        self,
        mock_storage,
        mock_auth_default,
        mock_httpx,
        client,
        mock_auth,
        mock_gcs_client,
        mock_vertex_response_video_started
    ):
        """Video generation returns operation name for polling"""
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        mock_auth_default.return_value = (mock_creds, "project")
        mock_storage.return_value = mock_gcs_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_vertex_response_video_started
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        response = client.post("/generate/video", json={
            "prompt": "a cat dancing",
            "duration_seconds": 8,
            "aspect_ratio": "16:9"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert "operation_name" in data
        assert "op-123" in data["operation_name"]


class TestVideoStatusAPI:
    """Integration tests for /generate/video/status endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.post("/generate/video/status", json={
            "operation_name": "projects/test/operations/123"
        })
        assert response.status_code == 401
    
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.google.auth.default")
    @patch("app.services.library.storage.Client")
    def test_returns_complete_with_video(
        self,
        mock_storage,
        mock_auth_default,
        mock_httpx,
        client,
        mock_auth,
        mock_gcs_client,
        mock_vertex_response_video_complete
    ):
        """Completed video returns base64 data"""
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        mock_auth_default.return_value = (mock_creds, "project")
        mock_storage.return_value = mock_gcs_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_vertex_response_video_complete
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        response = client.post("/generate/video/status", json={
            "operation_name": "projects/test/operations/123",
            "prompt": "dancing cat"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"
        assert data["video_base64"] == "base64videodata"


class TestTextGenerationAPI:
    """Integration tests for /generate/text endpoint"""
    
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.google.auth.default")
    @patch("app.services.library.storage.Client")
    def test_successful_generation(
        self,
        mock_storage,
        mock_auth_default,
        mock_httpx,
        client,
        mock_gcs_client,
        mock_vertex_response_text
    ):
        """Text generation works without auth"""
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        mock_auth_default.return_value = (mock_creds, "project")
        mock_storage.return_value = mock_gcs_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_vertex_response_text
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        response = client.post("/generate/text", json={
            "prompt": "Write a haiku about coding"
        })
        
        assert response.status_code == 200
        assert response.json()["response"] == "Generated text response"
    
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.google.auth.default")
    @patch("app.services.library.storage.Client")
    def test_with_system_prompt(
        self,
        mock_storage,
        mock_auth_default,
        mock_httpx,
        client,
        mock_gcs_client,
        mock_vertex_response_text
    ):
        """Text generation with system prompt"""
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        mock_auth_default.return_value = (mock_creds, "project")
        mock_storage.return_value = mock_gcs_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_vertex_response_text
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        response = client.post("/generate/text", json={
            "prompt": "Say hello",
            "system_prompt": "You are a pirate",
            "temperature": 0.9
        })
        
        assert response.status_code == 200


class TestUpscaleAPI:
    """Integration tests for /generate/upscale endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.post("/generate/upscale", json={
            "image": "base64data"
        })
        assert response.status_code == 401
    
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.google.auth.default")
    @patch("app.services.library.storage.Client")
    def test_successful_upscale(
        self,
        mock_storage,
        mock_auth_default,
        mock_httpx,
        client,
        mock_auth,
        mock_gcs_client,
        mock_vertex_response_upscale
    ):
        """Successful image upscale"""
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        mock_auth_default.return_value = (mock_creds, "project")
        mock_storage.return_value = mock_gcs_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_vertex_response_upscale
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        response = client.post("/generate/upscale", json={
            "image": "smallimagebase64",
            "upscale_factor": "x2"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["image"] == "upscaledimagedata"
        assert data["mime_type"] == "image/png"