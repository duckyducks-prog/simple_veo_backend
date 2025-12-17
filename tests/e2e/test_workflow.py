"""
End-to-end tests for workflow functionality with Firestore + GCS
Tests the full stack with real cloud services
"""
import pytest
import base64
import time


@pytest.mark.e2e
class TestWorkflowE2E:
    """E2E tests for workflow management with Firestore"""
    
    def test_create_workflow(self, api_base_url, auth_headers, http_client):
        """Create a basic workflow"""
        response = http_client.post(
            f"{api_base_url}/workflows/save",
            headers=auth_headers,
            json={
                "name": "E2E Test Workflow",
                "description": "Created by E2E test",
                "is_public": False,
                "nodes": [
                    {
                        "id": "node-1",
                        "type": "text",
                        "data": {"text": "Hello from E2E test"}
                    }
                ],
                "edges": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
    
    def test_list_my_workflows(self, api_base_url, auth_headers, http_client):
        """List user's workflows"""
        response = http_client.get(
            f"{api_base_url}/workflows?scope=my",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert isinstance(data["workflows"], list)
    
    def test_list_public_workflows(self, api_base_url, auth_headers, http_client):
        """List public workflows"""
        response = http_client.get(
            f"{api_base_url}/workflows?scope=public",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert isinstance(data["workflows"], list)
    
    def test_workflow_crud_lifecycle(self, api_base_url, auth_headers, http_client):
        """Test complete CRUD lifecycle of a workflow"""
        # CREATE
        create_response = http_client.post(
            f"{api_base_url}/workflows/save",
            headers=auth_headers,
            json={
                "name": "CRUD Test Workflow",
                "description": "Testing full lifecycle",
                "is_public": False,
                "nodes": [
                    {"id": "1", "type": "text", "data": {"text": "Original"}}
                ],
                "edges": []
            }
        )
        assert create_response.status_code == 200
        workflow_id = create_response.json()["id"]
        
        # READ
        get_response = http_client.get(
            f"{api_base_url}/workflows/{workflow_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        workflow = get_response.json()
        assert workflow["name"] == "CRUD Test Workflow"
        assert len(workflow["nodes"]) == 1
        
        # UPDATE
        update_response = http_client.put(
            f"{api_base_url}/workflows/{workflow_id}",
            headers=auth_headers,
            json={
                "name": "Updated Workflow",
                "description": "Updated description",
                "is_public": True,
                "nodes": [
                    {"id": "1", "type": "text", "data": {"text": "Updated"}},
                    {"id": "2", "type": "text", "data": {"text": "New node"}}
                ],
                "edges": []
            }
        )
        assert update_response.status_code == 200
        
        # Verify update
        get_updated = http_client.get(
            f"{api_base_url}/workflows/{workflow_id}",
            headers=auth_headers
        )
        updated_wf = get_updated.json()
        assert updated_wf["name"] == "Updated Workflow"
        assert len(updated_wf["nodes"]) == 2
        assert updated_wf["is_public"] == True
        
        # DELETE
        delete_response = http_client.delete(
            f"{api_base_url}/workflows/{workflow_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200
        
        # Verify deletion
        get_deleted = http_client.get(
            f"{api_base_url}/workflows/{workflow_id}",
            headers=auth_headers
        )
        assert get_deleted.status_code == 404
    
    def test_clone_workflow(self, api_base_url, auth_headers, http_client):
        """Clone a workflow"""
        # Create original
        create_response = http_client.post(
            f"{api_base_url}/workflows/save",
            headers=auth_headers,
            json={
                "name": "Original Workflow",
                "description": "To be cloned",
                "is_public": True,
                "nodes": [{"id": "1", "type": "text"}],
                "edges": []
            }
        )
        original_id = create_response.json()["id"]
        
        # Clone it
        clone_response = http_client.post(
            f"{api_base_url}/workflows/{original_id}/clone",
            headers=auth_headers
        )
        assert clone_response.status_code == 200
        cloned_id = clone_response.json()["id"]
        assert cloned_id != original_id
        
        # Verify clone
        get_clone = http_client.get(
            f"{api_base_url}/workflows/{cloned_id}",
            headers=auth_headers
        )
        cloned_wf = get_clone.json()
        assert "Copy" in cloned_wf["name"]
        assert cloned_wf["is_public"] == False  # Clones are private
        
        # Cleanup
        http_client.delete(f"{api_base_url}/workflows/{original_id}", headers=auth_headers)
        http_client.delete(f"{api_base_url}/workflows/{cloned_id}", headers=auth_headers)
    
    def test_workflow_with_asset_references(self, api_base_url, auth_headers, http_client):
        """Test workflow with asset references that get resolved to URLs"""
        # First, create an asset in the library
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        test_data = base64.b64encode(png_data).decode()
        
        asset_response = http_client.post(
            f"{api_base_url}/library/save",
            headers=auth_headers,
            json={
                "data": test_data,
                "asset_type": "image",
                "prompt": "Test image for workflow"
            }
        )
        asset_id = asset_response.json()["id"]
        
        # Create workflow with asset reference
        workflow_response = http_client.post(
            f"{api_base_url}/workflows/save",
            headers=auth_headers,
            json={
                "name": "Workflow with Asset",
                "description": "Has image reference",
                "is_public": False,
                "nodes": [
                    {
                        "id": "image-node",
                        "type": "image",
                        "data": {
                            "imageRef": asset_id,
                            "prompt": "Referenced image"
                        }
                    }
                ],
                "edges": []
            }
        )
        workflow_id = workflow_response.json()["id"]
        
        # Get workflow - should have URLs resolved
        get_response = http_client.get(
            f"{api_base_url}/workflows/{workflow_id}",
            headers=auth_headers
        )
        workflow = get_response.json()
        
        # Verify URL was resolved
        image_node = workflow["nodes"][0]
        assert "imageUrl" in image_node["data"]
        assert image_node["data"]["imageUrl"] is not None
        assert "genmedia-assets" in image_node["data"]["imageUrl"]
        
        # Cleanup
        http_client.delete(f"{api_base_url}/workflows/{workflow_id}", headers=auth_headers)
        http_client.delete(f"{api_base_url}/library/{asset_id}", headers=auth_headers)
    
    def test_workflow_access_control(self, api_base_url, auth_headers, http_client):
        """Test that private workflows are not accessible without proper auth"""
        # Create private workflow
        create_response = http_client.post(
            f"{api_base_url}/workflows/save",
            headers=auth_headers,
            json={
                "name": "Private Workflow",
                "description": "Should be private",
                "is_public": False,
                "nodes": [{"id": "1", "type": "text"}],
                "edges": []
            }
        )
        workflow_id = create_response.json()["id"]
        
        # Try to access without auth - should fail
        no_auth_response = http_client.get(
            f"{api_base_url}/workflows/{workflow_id}"
        )
        assert no_auth_response.status_code == 401
        
        # Access with auth - should succeed
        with_auth_response = http_client.get(
            f"{api_base_url}/workflows/{workflow_id}",
            headers=auth_headers
        )
        assert with_auth_response.status_code == 200
        
        # Cleanup
        http_client.delete(f"{api_base_url}/workflows/{workflow_id}", headers=auth_headers)
    
    def test_public_workflow_visibility(self, api_base_url, auth_headers, http_client):
        """Test that public workflows appear in public list"""
        # Create public workflow
        create_response = http_client.post(
            f"{api_base_url}/workflows/save",
            headers=auth_headers,
            json={
                "name": "Public Test Workflow",
                "description": "Should be public",
                "is_public": True,
                "nodes": [{"id": "1", "type": "text"}],
                "edges": []
            }
        )
        workflow_id = create_response.json()["id"]
        
        # Wait a moment for Firestore to index
        time.sleep(1)
        
        # Check it appears in public list
        public_list = http_client.get(
            f"{api_base_url}/workflows?scope=public",
            headers=auth_headers
        )
        public_workflows = public_list.json()["workflows"]
        
        # Should find our workflow in the list
        found = any(wf["id"] == workflow_id for wf in public_workflows)
        assert found, "Public workflow not found in public list"
        
        # Cleanup
        http_client.delete(f"{api_base_url}/workflows/{workflow_id}", headers=auth_headers)


@pytest.mark.e2e
class TestWorkflowLibraryIntegrationE2E:
    """E2E tests for workflow + library integration"""
    
    def test_generated_image_auto_saves_to_library(self, api_base_url, auth_headers, http_client):
        """Test that generated images automatically save to library"""
        # Generate an image
        gen_response = http_client.post(
            f"{api_base_url}/generate/image",
            headers=auth_headers,
            json={
                "prompt": "A simple test image for E2E"
            },
            timeout=30.0
        )
        
        if gen_response.status_code != 200:
            pytest.skip(f"Image generation failed: {gen_response.status_code}")
        
        # Check library - should have the generated image
        time.sleep(2)  # Give it time to save
        library_response = http_client.get(
            f"{api_base_url}/library?asset_type=image",
            headers=auth_headers
        )
        
        assert library_response.status_code == 200
        assets = library_response.json()["assets"]
        
        # Should have at least one image with our prompt
        found = any("test image" in (a.get("prompt") or "").lower() for a in assets)
        assert found, "Generated image not found in library"
    
    def test_workflow_with_multiple_assets(self, api_base_url, auth_headers, http_client):
        """Test workflow with multiple asset types"""
        # Create multiple assets
        png_data = base64.b64encode(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )).decode()
        
        asset_ids = []
        for i in range(3):
            asset_response = http_client.post(
                f"{api_base_url}/library/save",
                headers=auth_headers,
                json={
                    "data": png_data,
                    "asset_type": "image",
                    "prompt": f"Test image {i+1}"
                }
            )
            asset_ids.append(asset_response.json()["id"])
        
        # Create workflow with all assets
        workflow_response = http_client.post(
            f"{api_base_url}/workflows/save",
            headers=auth_headers,
            json={
                "name": "Multi-Asset Workflow",
                "description": "Has multiple images",
                "is_public": False,
                "nodes": [
                    {
                        "id": f"node-{i}",
                        "type": "image",
                        "data": {"imageRef": asset_id}
                    }
                    for i, asset_id in enumerate(asset_ids)
                ],
                "edges": []
            }
        )
        workflow_id = workflow_response.json()["id"]
        
        # Get workflow - all URLs should be resolved
        get_response = http_client.get(
            f"{api_base_url}/workflows/{workflow_id}",
            headers=auth_headers
        )
        workflow = get_response.json()
        
        # Verify all nodes have URLs
        for node in workflow["nodes"]:
            assert "imageUrl" in node["data"]
            assert node["data"]["imageUrl"] is not None
        
        # Cleanup
        http_client.delete(f"{api_base_url}/workflows/{workflow_id}", headers=auth_headers)
        for asset_id in asset_ids:
            http_client.delete(f"{api_base_url}/library/{asset_id}", headers=auth_headers)
