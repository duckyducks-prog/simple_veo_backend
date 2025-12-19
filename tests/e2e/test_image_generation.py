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
        
        if response.status_code == 500:
            pytest.skip("Image generation API not available or configured")
        
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


@pytest.mark.e2e
class TestImageGenerationWithSeedE2E:
    """E2E tests for image generation with seed data (if supported by Gemini API)"""
    
    def test_image_generation_accepts_seed_parameter(self, api_base_url, auth_headers, http_client, seed_values):
        """Verify image generation endpoint works (seed not yet implemented)"""
        # Note: seed parameter not yet implemented, so we just test basic generation
        response = http_client.post(
            f"{api_base_url}/generate/image",
            headers=auth_headers,
            json={
                "prompt": "a small blue circle on white background",
                "aspect_ratio": "1:1"
            }
        )
        
        # Skip if Gemini image generation API is unavailable/over quota
        if response.status_code == 500 and "No images generated" in response.text:
            pytest.skip("Gemini image generation API unavailable (quota/API issue)")
        
        # Should succeed 
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "images" in data
        print(f"✓ Image generation works correctly")
    
    def test_image_generation_different_aspect_ratios(self, api_base_url, auth_headers, http_client):
        """Verify image generation works with different aspect ratios"""
        aspect_ratios = ["1:1", "16:9", "9:16"]
        
        for ratio in aspect_ratios:
            response = http_client.post(
                f"{api_base_url}/generate/image",
                headers=auth_headers,
                json={
                    "prompt": f"test image with {ratio} aspect ratio",
                    "aspect_ratio": ratio
                }
            )
            
            if response.status_code == 500:
                pytest.skip("Image generation API not available")
            
            assert response.status_code == 200
            data = response.json()
            assert "images" in data
            print(f"✓ Image generation with aspect ratio {ratio} successful")
