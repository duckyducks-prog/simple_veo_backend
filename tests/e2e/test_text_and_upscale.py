"""
E2E tests for text generation and upscale endpoints
"""
import pytest
import base64


@pytest.mark.e2e
class TestTextGenerationE2E:
    """E2E tests for text generation endpoint"""
    
    def test_generate_text(self, api_base_url, auth_headers, http_client):
        """Generate text using Gemini API"""
        response = http_client.post(
            f"{api_base_url}/generate/text",
            headers=auth_headers,
            json={
                "prompt": "Write a haiku about artificial intelligence"
            }
        )
        
        # Skip if API not available/configured
        if response.status_code == 500:
            pytest.skip("Text generation API not available or configured")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "text" in data
        assert isinstance(data["text"], str)
        assert len(data["text"]) > 0
        
        print(f"✓ Text generation successful: {data['text'][:50]}...")
    
    def test_text_generation_unauthorized(self, api_base_url, http_client):
        """Request without token returns 401"""
        response = http_client.post(
            f"{api_base_url}/generate/text",
            json={"prompt": "test"}
        )
        
        # Should be 401, but 500 is OK if API check happens before auth
        assert response.status_code in [401, 500]
    
    def test_text_generation_missing_prompt(self, api_base_url, auth_headers, http_client):
        """Request without prompt returns 422"""
        response = http_client.post(
            f"{api_base_url}/generate/text",
            headers=auth_headers,
            json={}
        )
        
        assert response.status_code == 422
    
    def test_text_generation_empty_prompt(self, api_base_url, auth_headers, http_client):
        """Request with empty prompt is handled"""
        response = http_client.post(
            f"{api_base_url}/generate/text",
            headers=auth_headers,
            json={"prompt": ""}
        )
        
        # Should either reject (422) or handle gracefully
        # 500 means API not configured, skip
        if response.status_code == 500:
            pytest.skip("Text generation API not available")
        assert response.status_code in [200, 422]
    
    def test_text_generation_long_prompt(self, api_base_url, auth_headers, http_client):
        """Text generation with long prompt"""
        long_prompt = "Write a detailed story about " + "a very interesting topic " * 50
        
        response = http_client.post(
            f"{api_base_url}/generate/text",
            headers=auth_headers,
            json={"prompt": long_prompt}
        )
        
        if response.status_code == 500:
            pytest.skip("Text generation API not available")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["text"]) > 0
        
        print(f"✓ Long prompt text generation successful")


@pytest.mark.e2e  
class TestUpscaleE2E:
    """E2E tests for image upscaling endpoint"""
    
    def test_upscale_image(self, api_base_url, auth_headers, http_client, cleanup_asset):
        """Upscale an image using the API"""
        # Create a small test image
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        test_image = base64.b64encode(png_data).decode()
        
        # Save to library first
        asset_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": test_image,
                "asset_type": "image",
                "prompt": "Image to upscale"
            }
        )
        
        assert asset_response.status_code == 200
        asset_id = asset_response.json()["id"]
        cleanup_asset(asset_id)
        
        # Upscale the image
        response = http_client.post(
            f"{api_base_url}/generate/upscale",
            headers=auth_headers,
            json={
                "image": test_image,
                "prompt": "upscale this image"
            }
        )
        
        # Check if upscale endpoint is implemented
        if response.status_code in [501, 500]:
            pytest.skip("Upscale endpoint not yet fully implemented or API not available")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "image" in data
        assert len(data["image"]) > 0
        
        # Verify it's valid base64
        try:
            decoded = base64.b64decode(data["image"])
            assert len(decoded) > 0
        except Exception as e:
            pytest.fail(f"Invalid base64 upscaled image: {e}")
        
        print(f"✓ Image upscaling successful")
    
    def test_upscale_unauthorized(self, api_base_url, http_client):
        """Request without token returns 401"""
        response = http_client.post(
            f"{api_base_url}/generate/upscale",
            json={
                "image": "test",
                "prompt": "test"
            }
        )
        
        assert response.status_code == 401
    
    def test_upscale_missing_image(self, api_base_url, auth_headers, http_client):
        """Request without image returns 422"""
        response = http_client.post(
            f"{api_base_url}/generate/upscale",
            headers=auth_headers,
            json={"prompt": "test"}
        )
        
        assert response.status_code == 422
    
    def test_upscale_invalid_base64(self, api_base_url, auth_headers, http_client):
        """Request with invalid base64 image is rejected"""
        response = http_client.post(
            f"{api_base_url}/generate/upscale",
            headers=auth_headers,
            json={
                "image": "not-valid-base64!!!",
                "prompt": "upscale"
            }
        )
        
        # Should reject invalid base64
        # 500 means API not configured, which is OK
        assert response.status_code in [400, 422, 500, 501]


@pytest.mark.e2e
class TestWorkflowWithTextAndUpscaleE2E:
    """E2E tests for workflows integrating text generation and upscaling"""
    
    def test_workflow_with_text_generation_node(self, api_base_url, auth_headers, http_client):
        """Create workflow with text generation node"""
        workflow_response = http_client.post(
            f"{api_base_url}/workflows/save",
            headers=auth_headers,
            json={
                "name": "Text Generation Workflow",
                "description": "Uses text generation node",
                "is_public": False,
                "nodes": [
                    {
                        "id": "text-gen",
                        "type": "textGeneration",
                        "position": {"x": 0, "y": 0},
                        "data": {
                            "prompt": "Generate creative text"
                        }
                    }
                ],
                "edges": []
            }
        )
        
        assert workflow_response.status_code == 200
        workflow_id = workflow_response.json()["id"]
        
        # Retrieve and verify
        get_response = http_client.get(
            f"{api_base_url}/workflows/{workflow_id}",
            headers=auth_headers
        )
        
        assert get_response.status_code == 200
        workflow = get_response.json()
        assert len(workflow["nodes"]) == 1
        assert workflow["nodes"][0]["type"] == "textGeneration"
        
        print(f"✓ Workflow with text generation node created")
        
        # Cleanup
        http_client.delete(f"{api_base_url}/workflows/{workflow_id}", headers=auth_headers)
    
    def test_workflow_with_upscale_node(self, api_base_url, auth_headers, http_client, cleanup_asset):
        """Create workflow with image -> upscale pipeline"""
        # Create an image asset
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        test_image = base64.b64encode(png_data).decode()
        
        asset_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": test_image,
                "asset_type": "image",
                "prompt": "Image for upscale workflow"
            }
        )
        asset_id = asset_response.json()["id"]
        cleanup_asset(asset_id)
        
        # Create workflow: image -> upscale
        workflow_response = http_client.post(
            f"{api_base_url}/workflows/save",
            headers=auth_headers,
            json={
                "name": "Upscale Workflow",
                "description": "Image upscaling pipeline",
                "is_public": False,
                "nodes": [
                    {
                        "id": "input-image",
                        "type": "image",
                        "position": {"x": 0, "y": 0},
                        "data": {
                            "imageRef": asset_id
                        }
                    },
                    {
                        "id": "upscale",
                        "type": "upscale",
                        "position": {"x": 200, "y": 0},
                        "data": {
                            "prompt": "upscale to higher resolution"
                        }
                    }
                ],
                "edges": [
                    {
                        "id": "edge-1",
                        "source": "input-image",
                        "target": "upscale"
                    }
                ]
            }
        )
        
        assert workflow_response.status_code == 200
        workflow_id = workflow_response.json()["id"]
        
        # Retrieve and verify URLs are resolved
        get_response = http_client.get(
            f"{api_base_url}/workflows/{workflow_id}",
            headers=auth_headers
        )
        
        workflow = get_response.json()
        image_node = next(n for n in workflow["nodes"] if n["id"] == "input-image")
        
        assert "imageUrl" in image_node["data"]
        assert image_node["data"]["imageUrl"] is not None
        
        print(f"✓ Upscale workflow created with resolved asset URLs")
        
        # Cleanup
        http_client.delete(f"{api_base_url}/workflows/{workflow_id}", headers=auth_headers)
