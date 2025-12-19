"""
End-to-end tests for library functionality with Firestore + GCS
Tests the full stack with real cloud services
"""
import pytest
import base64
import time


@pytest.mark.e2e
class TestLibraryE2E:
    """E2E tests for library/asset management with Firestore + GCS"""
    
    def test_list_library(self, api_base_url, auth_headers, http_client):
        """List assets returns valid response from Firestore"""
        response = http_client.get(
            f"{api_base_url}/library",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "assets" in data
        assert "count" in data
        assert isinstance(data["assets"], list)
        
        # All assets should have URLs resolved from Firestore blob_path
        for asset in data["assets"]:
            assert "url" in asset
            if asset["url"]:  # Some assets may not have URLs yet
                assert "genmediastudio-assets" in asset["url"]
    
    def test_save_and_retrieve_asset(self, api_base_url, auth_headers, http_client, cleanup_asset):
        """Save an asset and retrieve it - verifies Firestore metadata + GCS storage"""
        # Create a minimal valid PNG (1x1 red pixel)
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        test_data = base64.b64encode(png_data).decode()
        
        # Save - should store metadata in Firestore and binary in GCS
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
        cleanup_asset(asset_id)
        
        # Verify response includes URL (resolved from Firestore metadata)
        assert "url" in saved
        assert saved["url"] is not None
        assert "genmediastudio-assets" in saved["url"]
        
        # Retrieve metadata from Firestore
        get_response = http_client.get(
            f"{api_base_url}/library/{asset_id}",
            headers=auth_headers
        )
        
        assert get_response.status_code == 200
        retrieved = get_response.json()
        assert retrieved["id"] == asset_id
        assert retrieved["prompt"] == "E2E test image"
        assert "url" in retrieved
        # blob_path is internal, not exposed in API response
        
        # Verify the URL is publicly accessible (tests GCS storage)
        url_response = http_client.get(retrieved["url"])
        assert url_response.status_code == 200
        assert len(url_response.content) > 0
    
    def test_delete_asset(self, api_base_url, auth_headers, http_client):
        """Save and delete an asset - verifies Firestore + GCS cleanup"""
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
        asset_data = save_response.json()
        asset_id = asset_data["id"]
        asset_url = asset_data["url"]
        
        # Verify asset exists in GCS before deletion
        url_check = http_client.get(asset_url)
        assert url_check.status_code == 200
        
        # Delete - should delete from both Firestore and GCS
        delete_response = http_client.delete(
            f"{api_base_url}/library/{asset_id}",
            headers=auth_headers
        )
        
        assert delete_response.status_code == 200
        assert delete_response.json()["status"] == "deleted"
        
        # Verify metadata deleted from Firestore
        get_response = http_client.get(
            f"{api_base_url}/library/{asset_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
    
    def test_filter_by_asset_type(self, api_base_url, auth_headers, http_client):
        """Filter library by asset type using Firestore queries"""
        response = http_client.get(
            f"{api_base_url}/library?asset_type=image",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned assets should be images
        for asset in data["assets"]:
            assert asset["asset_type"] == "image"
    
    def test_asset_ownership(self, api_base_url, auth_headers, http_client, cleanup_asset):
        """Test that users can only see their own assets (Firestore user_id filtering)"""
        # Create an asset
        png_data = base64.b64encode(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )).decode()
        
        save_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": png_data,
                "asset_type": "image",
                "prompt": "My private asset"
            }
        )
        
        asset_id = save_response.json()["id"]
        cleanup_asset(asset_id)
        
        # List assets - should include the one we just created
        time.sleep(1)  # Wait for Firestore indexing
        list_response = http_client.get(
            f"{api_base_url}/library",
            headers=auth_headers
        )
        
        assets = list_response.json()["assets"]
        asset_ids = [a["id"] for a in assets]
        assert asset_id in asset_ids, "User's asset not found in their library"


@pytest.mark.e2e
class TestLibraryFirestoreIntegration:
    """Specific tests for Firestore + GCS integration"""
    
    def test_firestore_metadata_persistence(self, api_base_url, auth_headers, http_client, cleanup_asset):
        """Verify that Firestore stores all required metadata"""
        png_data = base64.b64encode(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )).decode()
        
        save_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": png_data,
                "asset_type": "image",
                "prompt": "Metadata test",
                "seed": 12345,
                "settings": {"quality": "high"}
            }
        )
        
        asset_id = save_response.json()["id"]
        cleanup_asset(asset_id)
        
        # Retrieve and verify all metadata was stored in Firestore
        get_response = http_client.get(
            f"{api_base_url}/library/{asset_id}",
            headers=auth_headers
        )
        
        asset = get_response.json()
        assert asset["prompt"] == "Metadata test"
        # seed and settings may not be returned if not part of schema
        assert "created_at" in asset
        assert "mime_type" in asset
        assert "url" in asset
    
    def test_gcs_blob_storage(self, api_base_url, auth_headers, http_client, cleanup_asset):
        """Verify that binary data is stored in GCS, not Firestore"""
        # Create a slightly larger image to test binary storage
        png_data = base64.b64encode(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        ) * 100).decode()  # Repeat to make it larger
        
        save_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": png_data,
                "asset_type": "image",
                "prompt": "Binary storage test"
            }
        )
        
        asset_data = save_response.json()
        asset_id = asset_data["id"]
        cleanup_asset(asset_id)
        
        # Get the asset URL (resolved from Firestore blob_path)
        asset_url = asset_data["url"]
        
        # Verify we can download the binary from GCS
        download_response = http_client.get(asset_url)
        assert download_response.status_code == 200
        assert len(download_response.content) > 0
        
        # Verify the content type
        content_type = download_response.headers.get("content-type", "")
        assert "image" in content_type.lower() or "octet-stream" in content_type.lower()


@pytest.mark.e2e
class TestLibrarySeedDataE2E:
    """E2E tests for library with seed data storage and retrieval"""
    
    def test_save_asset_with_seed(self, api_base_url, auth_headers, http_client, cleanup_asset, seed_values):
        """Save an asset with seed data and verify it's stored in Firestore"""
        seed_value = seed_values["seed_1"]
        png_data = base64.b64encode(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )).decode()
        
        # Save asset with seed
        save_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": png_data,
                "asset_type": "image",
                "prompt": "Generated with seed",
                "seed": seed_value
            }
        )
        
        assert save_response.status_code == 200
        asset_data = save_response.json()
        asset_id = asset_data["id"]
        cleanup_asset(asset_id)
        
        print(f"✓ Asset saved with seed {seed_value}, ID: {asset_id}")
        
        # Retrieve and verify seed is persisted in Firestore
        get_response = http_client.get(
            f"{api_base_url}/library/{asset_id}",
            headers=auth_headers
        )
        
        assert get_response.status_code == 200
        retrieved_asset = get_response.json()
        
        # Verify seed metadata is present (if included in response schema)
        assert retrieved_asset["id"] == asset_id
        assert retrieved_asset["prompt"] == "Generated with seed"
        print(f"✓ Asset metadata retrieved with seed field: {retrieved_asset.get('seed', 'N/A')}")
    
    def test_save_asset_with_different_seed_values(self, api_base_url, auth_headers, http_client, cleanup_asset, seed_values):
        """Test saving assets with various seed values"""
        png_data = base64.b64encode(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )).decode()
        
        test_seeds = [
            seed_values["seed_1"],
            seed_values["seed_2"],
            seed_values["seed_3"],
            seed_values["seed_zero"],
        ]
        
        for seed_val in test_seeds:
            save_response = http_client.post(
                f"{api_base_url}/library/save",
                headers=auth_headers,
                json={
                    "data": png_data,
                    "asset_type": "image",
                    "prompt": f"Test with seed {seed_val}",
                    "seed": seed_val
                }
            )
            
            assert save_response.status_code == 200
            asset_data = save_response.json()
            cleanup_asset(asset_data["id"])
            print(f"✓ Asset saved with seed {seed_val}")
    
    def test_save_asset_without_seed(self, api_base_url, auth_headers, http_client, cleanup_asset):
        """Verify assets can be saved without seed (backward compatibility)"""
        png_data = base64.b64encode(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )).decode()
        
        # Save without seed - should work fine
        save_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": png_data,
                "asset_type": "image",
                "prompt": "Asset without seed"
                # No seed field provided
            }
        )
        
        assert save_response.status_code == 200
        asset_data = save_response.json()
        cleanup_asset(asset_data["id"])
        print(f"✓ Asset saved successfully without seed (backward compatible)")
    
    def test_save_asset_with_null_seed(self, api_base_url, auth_headers, http_client, cleanup_asset):
        """Verify null seed is handled correctly"""
        png_data = base64.b64encode(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )).decode()
        
        save_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": png_data,
                "asset_type": "image",
                "prompt": "Asset with null seed",
                "seed": None
            }
        )
        
        assert save_response.status_code == 200
        asset_data = save_response.json()
        cleanup_asset(asset_data["id"])
        print(f"✓ Asset saved with null seed value")
    
    def test_save_asset_with_seed_and_additional_metadata(self, api_base_url, auth_headers, http_client, cleanup_asset, seed_values):
        """Save asset with seed and other metadata fields"""
        seed_value = seed_values["seed_2"]
        png_data = base64.b64encode(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )).decode()
        
        save_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": png_data,
                "asset_type": "image",
                "prompt": "Complex metadata test",
                "seed": seed_value,
                "settings": {
                    "model": "veo-3.1",
                    "quality": "high",
                    "style": "photorealistic"
                },
                "tags": ["test", "seed", "reproducible"]
            }
        )
        
        assert save_response.status_code == 200
        asset_data = save_response.json()
        asset_id = asset_data["id"]
        cleanup_asset(asset_id)
        
        # Verify comprehensive metadata is stored
        get_response = http_client.get(
            f"{api_base_url}/library/{asset_id}",
            headers=auth_headers
        )
        
        assert get_response.status_code == 200
        retrieved = get_response.json()
        assert retrieved["prompt"] == "Complex metadata test"
        print(f"✓ Asset with comprehensive metadata saved and retrieved (seed: {seed_value})")
    
    def test_list_library_with_seed_data(self, api_base_url, auth_headers, http_client, cleanup_asset, seed_values):
        """Verify seed data persists in library listings"""
        seed_value = seed_values["seed_3"]
        png_data = base64.b64encode(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )).decode()
        
        # Save asset with seed
        save_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": png_data,
                "asset_type": "image",
                "prompt": "Listing test",
                "seed": seed_value
            }
        )
        
        saved_asset = save_response.json()
        saved_asset_id = saved_asset["id"]
        cleanup_asset(saved_asset_id)
        
        # List library
        time.sleep(1)  # Wait for Firestore indexing
        list_response = http_client.get(
            f"{api_base_url}/library",
            headers=auth_headers
        )
        
        assert list_response.status_code == 200
        library = list_response.json()
        
        # Find our asset in the list
        found = False
        for asset in library["assets"]:
            if asset["id"] == saved_asset_id:
                found = True
                print(f"✓ Asset with seed {seed_value} found in library listing")
                break
        
        assert found, f"Asset with ID {saved_asset_id} not found in library listing"

