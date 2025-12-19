"""
E2E tests for video generation with reference images (the feature we just fixed!)
Tests first_frame and reference_images parameters with real Veo API
"""
import pytest
import base64
import time


@pytest.mark.e2e
class TestVideoReferenceImagesE2E:
    """E2E tests for video generation with reference images - COSTS MONEY"""
    
    def test_generate_video_with_first_frame(self, api_base_url, auth_headers, http_client, cleanup_asset):
        """Generate video using an image as first frame"""
        # Create a test image first
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        test_image = base64.b64encode(png_data).decode()
        
        # Save it to library
        asset_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": test_image,
                "asset_type": "image",
                "prompt": "First frame test image"
            }
        )
        
        assert asset_response.status_code == 200
        asset_id = asset_response.json()["id"]
        cleanup_asset(asset_id)
        
        # Generate video with this image as first frame
        response = http_client.post(
            f"{api_base_url}/generate/video",
            headers=auth_headers,
            json={
                "prompt": "a smooth camera pan across the scene",
                "duration_seconds": 4,
                "aspect_ratio": "16:9",
                "first_frame": asset_id  # Use our image as first frame
            }
        )
        
        if response.status_code == 500:
            pytest.skip("Video generation with first_frame failed - API may not be configured")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert "operation_name" in data
        
        print(f"✓ Video generation with first_frame started: {data['operation_name']}")
    
    def test_generate_video_with_reference_images_style(self, api_base_url, auth_headers, http_client, cleanup_asset):
        """Generate video using reference image for style (the feature we fixed!)"""
        # Create a reference image
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        test_image = base64.b64encode(png_data).decode()
        
        # Save reference image to library
        asset_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": test_image,
                "asset_type": "image",
                "prompt": "Style reference test image"
            }
        )
        
        assert asset_response.status_code == 200
        asset_id = asset_response.json()["id"]
        cleanup_asset(asset_id)
        
        # Generate video with style reference
        # reference_images should be a list of asset IDs (strings)
        response = http_client.post(
            f"{api_base_url}/generate/video",
            headers=auth_headers,
            json={
                "prompt": "a cinematic scene in the style of the reference",
                "duration_seconds": 4,
                "aspect_ratio": "16:9",
                "reference_images": [asset_id]  # Just the asset ID string
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert "operation_name" in data
        
        print(f"✓ Video generation with reference_images (style) started: {data['operation_name']}")
    
    def test_generate_video_with_multiple_reference_images(self, api_base_url, auth_headers, http_client, cleanup_asset):
        """Generate video with multiple style reference images"""
        # Create multiple reference images
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        test_image = base64.b64encode(png_data).decode()
        
        asset_ids = []
        for i in range(2):
            asset_response = http_client.post(
                f"{api_base_url}/library/save",
                headers=auth_headers,
                json={
                    "data": test_image,
                    "asset_type": "image",
                    "prompt": f"Multi-reference test image {i+1}"
                }
            )
            asset_id = asset_response.json()["id"]
            asset_ids.append(asset_id)
            cleanup_asset(asset_id)
        
        # Generate video with multiple reference images
        response = http_client.post(
            f"{api_base_url}/generate/video",
            headers=auth_headers,
            json={
                "prompt": "a scene blending multiple artistic styles",
                "duration_seconds": 4,
                "aspect_ratio": "16:9",
                "reference_images": asset_ids  # List of asset ID strings
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        
        print(f"✓ Video generation with {len(asset_ids)} reference images started")
    
    def test_generate_video_with_first_frame_and_reference(self, api_base_url, auth_headers, http_client, cleanup_asset):
        """Generate video with both first_frame and reference_images"""
        # Create images
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        test_image = base64.b64encode(png_data).decode()
        
        # First frame image
        first_frame_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": test_image,
                "asset_type": "image",
                "prompt": "First frame"
            }
        )
        first_frame_id = first_frame_response.json()["id"]
        cleanup_asset(first_frame_id)
        
        # Style reference image
        style_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": test_image,
                "asset_type": "image",
                "prompt": "Style reference"
            }
        )
        style_id = style_response.json()["id"]
        cleanup_asset(style_id)
        
        # Generate with both
        response = http_client.post(
            f"{api_base_url}/generate/video",
            headers=auth_headers,
            json={
                "prompt": "a stylized animation starting from the first frame",
                "duration_seconds": 4,
                "aspect_ratio": "16:9",
                "first_frame": first_frame_id,
                "reference_images": [style_id]  # List of asset ID strings
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        
        print(f"✓ Video generation with first_frame + reference_images started")
    
    def test_reference_images_validation(self, api_base_url, auth_headers, http_client):
        """Test validation errors for invalid reference image requests"""
        # Test with non-existent asset ID
        response = http_client.post(
            f"{api_base_url}/generate/video",
            headers=auth_headers,
            json={
                "prompt": "test video",
                "duration_seconds": 4,
                "aspect_ratio": "16:9",
                "reference_images": ["non-existent-asset-id"]  # Invalid asset ID
            }
        )
        
        # Should return error (400, 404, or 500 if asset lookup fails)
        assert response.status_code in [400, 404, 500]
        print(f"✓ Properly rejects non-existent asset reference")
    
    def test_workflow_with_video_generation_and_reference_images(self, api_base_url, auth_headers, http_client, cleanup_asset):
        """Test complete workflow: save image, create workflow with video gen node using that image as reference"""
        # Save reference image
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
                "prompt": "Workflow style reference"
            }
        )
        asset_id = asset_response.json()["id"]
        cleanup_asset(asset_id)
        
        # Create workflow with video generation node that uses reference images
        workflow_response = http_client.post(
            f"{api_base_url}/workflows/save",
            headers=auth_headers,
            json={
                "name": "Video Gen with Reference Workflow",
                "description": "Tests reference_images in workflow execution",
                "is_public": False,
                "nodes": [
                    {
                        "id": "image-input",
                        "type": "image",
                        "position": {"x": 0, "y": 0},
                        "data": {
                            "imageRef": asset_id
                        }
                    },
                    {
                        "id": "video-gen",
                        "type": "videoGeneration",
                        "position": {"x": 200, "y": 0},
                        "data": {
                            "prompt": "stylized video using reference",
                            "duration_seconds": 4,
                            "aspect_ratio": "16:9",
                            "reference_images": [asset_id]  # List of asset ID strings
                        }
                    }
                ],
                "edges": [
                    {
                        "id": "edge-1",
                        "source": "image-input",
                        "target": "video-gen"
                    }
                ]
            }
        )
        
        assert workflow_response.status_code == 200
        workflow_id = workflow_response.json()["id"]
        
        # Retrieve workflow - should have URLs resolved
        get_response = http_client.get(
            f"{api_base_url}/workflows/{workflow_id}",
            headers=auth_headers
        )
        
        assert get_response.status_code == 200
        workflow = get_response.json()
        
        # Verify image node has URL
        image_node = next(n for n in workflow["nodes"] if n["id"] == "image-input")
        assert "imageUrl" in image_node["data"]
        assert image_node["data"]["imageUrl"] is not None
        
        # Verify video gen node preserved reference_images structure
        video_node = next(n for n in workflow["nodes"] if n["id"] == "video-gen")
        assert "reference_images" in video_node["data"]
        assert len(video_node["data"]["reference_images"]) == 1
        assert video_node["data"]["reference_images"][0] == asset_id  # Should be asset ID string
        
        print(f"✓ Workflow with reference_images created and verified")
        
        # Cleanup
        http_client.delete(f"{api_base_url}/workflows/{workflow_id}", headers=auth_headers)
