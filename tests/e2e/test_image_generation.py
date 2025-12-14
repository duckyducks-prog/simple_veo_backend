import pytest
import base64

@pytest.mark.e2e
class TestImageGenerationE2E:
    """E2E tests for image generation - COSTS MONEY"""
    
    def test_generate_simple_image(self, api_base_url, auth_headers, http_client, cleanup_asset):
        """Generate a simple image end-to-end"""
        response = http_client.post(
            f"{api_base_url}/generate/image",
            headers=auth_headers,
            json={"prompt": "a small red dot on white background"}  # Simple = faster/cheaper
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "images" in data
        assert len(data["images"]) >= 1
        
        # Verify it's valid base64
        try:
            decoded = base64.b64decode(data["images"][0])
            assert len(decoded) > 0
        except Exception as e:
            pytest.fail(f"Invalid base64 image: {e}")
    
    def test_unauthorized_request(self, api_base_url, http_client):
        """Request without token returns 401"""
        response = http_client.post(
            f"{api_base_url}/generate/image",
            json={"prompt": "test"}
        )
        
        assert response.status_code == 401
    
    def test_missing_prompt(self, api_base_url, auth_headers, http_client):
        """Request without prompt returns 422"""
        response = http_client.post(
            f"{api_base_url}/generate/image",
            headers=auth_headers,
            json={}
        )
        
        assert response.status_code == 422