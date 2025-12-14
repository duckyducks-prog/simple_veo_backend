import pytest
import base64

@pytest.mark.e2e
class TestLibraryE2E:
    """E2E tests for asset library"""
    
    def test_list_empty_library(self, api_base_url, auth_headers, http_client):
        """List assets returns valid response"""
        response = http_client.get(
            f"{api_base_url}/library",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "assets" in data
        assert "count" in data
        assert isinstance(data["assets"], list)
    
    def test_save_and_retrieve_asset(self, api_base_url, auth_headers, http_client, cleanup_asset):
        """Save an asset and retrieve it"""
        # Create a minimal valid PNG (1x1 red pixel)
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        test_data = base64.b64encode(png_data).decode()
        
        # Save
        save_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": test_data,
                "asset_type": "image",
                "prompt": "E2E test image"
            }
        )
        
        assert save_response.status_code == 200
        saved = save_response.json()
        asset_id = saved["id"]
        cleanup_asset(asset_id)  # Track for cleanup
        
        # Retrieve
        get_response = http_client.get(
            f"{api_base_url}/library/{asset_id}",
            headers=auth_headers
        )
        
        assert get_response.status_code == 200
        retrieved = get_response.json()
        assert retrieved["id"] == asset_id
        assert retrieved["prompt"] == "E2E test image"
    
    def test_delete_asset(self, api_base_url, auth_headers, http_client):
        """Save and delete an asset"""
        # Create minimal PNG
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        test_data = base64.b64encode(png_data).decode()
        
        # Save
        save_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": test_data,
                "asset_type": "image",
                "prompt": "Delete test"
            }
        )
        asset_id = save_response.json()["id"]
        
        # Delete
        delete_response = http_client.delete(
            f"{api_base_url}/library/{asset_id}",
            headers=auth_headers
        )
        
        assert delete_response.status_code == 200
        assert delete_response.json()["status"] == "deleted"
        
        # Verify deleted
        get_response = http_client.get(
            f"{api_base_url}/library/{asset_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
    
    def test_filter_by_asset_type(self, api_base_url, auth_headers, http_client):
        """Filter library by asset type"""
        response = http_client.get(
            f"{api_base_url}/library?asset_type=image",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned assets should be images
        for asset in data["assets"]:
            assert asset["asset_type"] == "image"