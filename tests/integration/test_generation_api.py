import pytest
import base64
from unittest.mock import patch, MagicMock, AsyncMock

class TestImageGenerationAPI:
    """Integration tests for /generate/image endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.post("/generate/image", json={"prompt": "a puppy"})
        assert response.status_code == 401
        assert "No authorization token" in response.json()["detail"]
    
    @patch("app.services.generation.image_client")
    @patch("app.services.generation.client")
    @patch("app.services.library_firestore.storage.Client")
    def test_requires_prompt(self, mock_storage, mock_genai_client, mock_image_client, client, mock_auth, mock_gcs_client):
        """Request without prompt returns 422"""
        mock_storage.return_value = mock_gcs_client
        
        response = client.post("/generate/image", json={})
        assert response.status_code == 422
    
    @patch("app.services.generation.image_client")
    @patch("app.services.generation.client")
    @patch("app.services.library_firestore.storage.Client")
    def test_successful_generation(
        self, 
        mock_storage, 
        mock_genai_client,
        mock_image_client,
        client, 
        mock_auth,
        mock_gcs_client
    ):
        """Full successful image generation flow"""
        mock_storage.return_value = mock_gcs_client
        
        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = b"fake_image_bytes"
        
        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]
        
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        mock_image_client.models.generate_content.return_value = mock_response
        
        response = client.post("/generate/image", json={
            "prompt": "a cute puppy",
            "aspect_ratio": "16:9"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "images" in data
        assert len(data["images"]) == 1
    
    @patch("app.services.generation.image_client")
    @patch("app.services.generation.client")
    @patch("app.services.library_firestore.storage.Client")
    def test_with_reference_images(
        self,
        mock_storage,
        mock_genai_client,
        mock_image_client,
        client,
        mock_auth,
        mock_gcs_client
    ):
        """Generation with reference images"""
        mock_storage.return_value = mock_gcs_client
        
        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = b"fake_image_bytes"
        
        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]
        
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        mock_image_client.models.generate_content.return_value = mock_response
        
        ref_image = base64.b64encode(b"reference image").decode()
        
        response = client.post("/generate/image", json={
            "prompt": "same style as reference",
            "reference_images": [ref_image]
        })
        
        assert response.status_code == 200
    
    @patch("app.services.generation.image_client")
    @patch("app.services.generation.client")
    @patch("app.services.library_firestore.storage.Client")
    def test_no_images_returns_500(
        self,
        mock_storage,
        mock_genai_client,
        mock_image_client,
        client,
        mock_auth,
        mock_gcs_client
    ):
        """No images generated returns 500"""
        mock_storage.return_value = mock_gcs_client
        
        mock_candidate = MagicMock()
        mock_candidate.content.parts = []
        
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        mock_image_client.models.generate_content.return_value = mock_response
        
        response = client.post("/generate/image", json={"prompt": "test"})
        
        assert response.status_code == 500
        assert "No images generated" in response.json()["detail"]

class TestVideoGenerationAPI:
    """Integration tests for /generate/video endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.post("/generate/video", json={"prompt": "dancing cat"})
        assert response.status_code == 401
    
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    @patch("app.services.library_firestore.storage.Client")
    def test_returns_operation_name(
        self,
        mock_storage,
        mock_genai_client,
        mock_httpx,
        client,
        mock_auth,
        mock_gcs_client,
        mock_vertex_response_video_started
    ):
        """Video generation returns operation name for polling"""
        mock_storage.return_value = mock_gcs_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_vertex_response_video_started
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        response = client.post("/generate/video", json={
            "prompt": "a cat dancing",
            "duration_seconds": 8,
            "aspect_ratio": "16:9"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert "operation_name" in data


class TestVideoStatusAPI:
    """Integration tests for /generate/video/status endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.post("/generate/video/status", json={
            "operation_name": "projects/test/operations/123"
        })
        assert response.status_code == 401
    
    @patch("app.services.generation.httpx.AsyncClient")
    @patch("app.services.generation.client")
    @patch("app.services.library_firestore.storage.Client")
    def test_returns_complete_with_video(
        self,
        mock_storage,
        mock_genai_client,
        mock_httpx,
        client,
        mock_auth,
        mock_gcs_client,
        mock_vertex_response_video_complete
    ):
        """Completed video returns base64 data"""
        mock_storage.return_value = mock_gcs_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_vertex_response_video_complete
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
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
    
    @patch("app.services.generation.client")
    @patch("app.services.library_firestore.storage.Client")
    def test_successful_generation(
        self,
        mock_storage,
        mock_genai_client,
        client,
        mock_gcs_client
    ):
        """Text generation works without auth"""
        mock_storage.return_value = mock_gcs_client
        
        mock_response = MagicMock()
        mock_response.text = "Generated text response"
        mock_genai_client.models.generate_content.return_value = mock_response
        
        response = client.post("/generate/text", json={
            "prompt": "Write a haiku about coding"
        })
        
        assert response.status_code == 200
        assert response.json()["response"] == "Generated text response"
    
    @patch("app.services.generation.client")
    @patch("app.services.library_firestore.storage.Client")
    def test_with_system_prompt(
        self,
        mock_storage,
        mock_genai_client,
        client,
        mock_gcs_client
    ):
        """Text generation with system prompt"""
        mock_storage.return_value = mock_gcs_client
        
        mock_response = MagicMock()
        mock_response.text = "Arrr, hello matey!"
        mock_genai_client.models.generate_content.return_value = mock_response
        
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
    @patch("app.services.generation.client")
    @patch("app.services.library_firestore.storage.Client")
    def test_successful_upscale(
        self,
        mock_storage,
        mock_genai_client,
        mock_httpx,
        client,
        mock_auth,
        mock_gcs_client,
        mock_vertex_response_upscale
    ):
        """Successful image upscale"""
        mock_storage.return_value = mock_gcs_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_vertex_response_upscale
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client
        
        response = client.post("/generate/upscale", json={
            "image": "smallimagebase64",
            "upscale_factor": "x2"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["image"] == "upscaledimagedata"
        assert data["mime_type"] == "image/png"