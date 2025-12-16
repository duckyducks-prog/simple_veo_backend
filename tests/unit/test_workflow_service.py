"""
Unit tests for workflow service
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.workflow import WorkflowService
from fastapi import HTTPException
import json


@pytest.fixture
def workflow_service():
    """Create a workflow service instance with mocked GCS client"""
    with patch('app.services.workflow.storage.Client') as mock_client:
        service = WorkflowService()
        service.bucket_name = "test-bucket"
        yield service


@pytest.fixture
def mock_bucket():
    """Create a mock GCS bucket"""
    bucket = MagicMock()
    return bucket


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for testing"""
    return {
        "name": "Test Workflow",
        "description": "Test description",
        "is_public": False,
        "nodes": [
            {
                "id": "node-1",
                "type": "imageInput",
                "position": {"x": 100, "y": 100},
                "data": {"label": "Image Input"}
            }
        ],
        "edges": []
    }


class TestWorkflowService:
    
    def test_generate_workflow_id(self, workflow_service):
        """Test workflow ID generation"""
        wf_id = workflow_service._generate_workflow_id()
        assert wf_id.startswith("wf_")
        assert len(wf_id) > 10
    
    @pytest.mark.asyncio
    async def test_create_workflow_success(self, workflow_service, sample_workflow_data):
        """Test successful workflow creation"""
        with patch.object(workflow_service, '_save_workflow') as mock_save, \
             patch.object(workflow_service, '_update_index') as mock_update_index:
            
            workflow_id = await workflow_service.create_workflow(
                name=sample_workflow_data["name"],
                description=sample_workflow_data["description"],
                is_public=sample_workflow_data["is_public"],
                nodes=sample_workflow_data["nodes"],
                edges=sample_workflow_data["edges"],
                user_id="test_user_123",
                user_email="test@example.com"
            )
            
            assert workflow_id.startswith("wf_")
            mock_save.assert_called_once()
            mock_update_index.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_workflow_empty_name(self, workflow_service, sample_workflow_data):
        """Test workflow creation with empty name"""
        with pytest.raises(HTTPException) as exc_info:
            await workflow_service.create_workflow(
                name="",
                description=sample_workflow_data["description"],
                is_public=sample_workflow_data["is_public"],
                nodes=sample_workflow_data["nodes"],
                edges=sample_workflow_data["edges"],
                user_id="test_user_123",
                user_email="test@example.com"
            )
        
        assert exc_info.value.status_code == 400
        assert "name is required" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_create_workflow_name_too_long(self, workflow_service, sample_workflow_data):
        """Test workflow creation with name exceeding max length"""
        with pytest.raises(HTTPException) as exc_info:
            await workflow_service.create_workflow(
                name="A" * 101,  # 101 characters
                description=sample_workflow_data["description"],
                is_public=sample_workflow_data["is_public"],
                nodes=sample_workflow_data["nodes"],
                edges=sample_workflow_data["edges"],
                user_id="test_user_123",
                user_email="test@example.com"
            )
        
        assert exc_info.value.status_code == 400
        assert "100 characters" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_create_workflow_no_nodes(self, workflow_service, sample_workflow_data):
        """Test workflow creation with no nodes"""
        with pytest.raises(HTTPException) as exc_info:
            await workflow_service.create_workflow(
                name=sample_workflow_data["name"],
                description=sample_workflow_data["description"],
                is_public=sample_workflow_data["is_public"],
                nodes=[],  # Empty nodes
                edges=sample_workflow_data["edges"],
                user_id="test_user_123",
                user_email="test@example.com"
            )
        
        assert exc_info.value.status_code == 400
        assert "at least one node" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_create_workflow_too_many_nodes(self, workflow_service, sample_workflow_data):
        """Test workflow creation with too many nodes"""
        with pytest.raises(HTTPException) as exc_info:
            nodes = [{"id": f"node-{i}", "type": "test", "position": {}, "data": {}} for i in range(101)]
            
            await workflow_service.create_workflow(
                name=sample_workflow_data["name"],
                description=sample_workflow_data["description"],
                is_public=sample_workflow_data["is_public"],
                nodes=nodes,
                edges=sample_workflow_data["edges"],
                user_id="test_user_123",
                user_email="test@example.com"
            )
        
        assert exc_info.value.status_code == 400
        assert "100 nodes" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_list_workflows_my_scope(self, workflow_service):
        """Test listing user's workflows"""
        mock_index = {
            "wf_1": {"user_id": "user_123", "name": "My Workflow 1"},
            "wf_2": {"user_id": "user_456", "name": "Other Workflow"},
            "wf_3": {"user_id": "user_123", "name": "My Workflow 2"}
        }
        
        with patch.object(workflow_service, '_load_index', return_value=mock_index), \
             patch.object(workflow_service, '_load_workflow') as mock_load:
            
            mock_load.side_effect = lambda wf_id: mock_index[wf_id]
            
            workflows = await workflow_service.list_workflows(
                scope="my",
                user_id="user_123"
            )
            
            assert len(workflows) == 2
            assert all(w["user_id"] == "user_123" for w in workflows)
    
    @pytest.mark.asyncio
    async def test_list_workflows_public_scope(self, workflow_service):
        """Test listing public workflows"""
        mock_index = {
            "wf_1": {"user_id": "user_123", "is_public": True, "name": "Public 1"},
            "wf_2": {"user_id": "user_456", "is_public": False, "name": "Private"},
            "wf_3": {"user_id": "user_789", "is_public": True, "name": "Public 2"}
        }
        
        with patch.object(workflow_service, '_load_index', return_value=mock_index), \
             patch.object(workflow_service, '_load_workflow') as mock_load:
            
            mock_load.side_effect = lambda wf_id: mock_index[wf_id]
            
            workflows = await workflow_service.list_workflows(
                scope="public",
                user_id="user_123"
            )
            
            assert len(workflows) == 2
            assert all(w.get("is_public") is True for w in workflows)
    
    @pytest.mark.asyncio
    async def test_list_workflows_invalid_scope(self, workflow_service):
        """Test listing workflows with invalid scope"""
        with pytest.raises(HTTPException) as exc_info:
            await workflow_service.list_workflows(
                scope="invalid",
                user_id="user_123"
            )
        
        assert exc_info.value.status_code == 400
        assert "invalid scope" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_get_workflow_owner(self, workflow_service):
        """Test getting workflow as owner"""
        mock_workflow = {
            "id": "wf_123",
            "user_id": "user_123",
            "is_public": False,
            "name": "Test Workflow"
        }
        
        with patch.object(workflow_service, '_load_workflow', return_value=mock_workflow):
            workflow = await workflow_service.get_workflow(
                workflow_id="wf_123",
                user_id="user_123"
            )
            
            assert workflow["id"] == "wf_123"
    
    @pytest.mark.asyncio
    async def test_get_workflow_public(self, workflow_service):
        """Test getting public workflow"""
        mock_workflow = {
            "id": "wf_123",
            "user_id": "user_456",
            "is_public": True,
            "name": "Public Workflow"
        }
        
        with patch.object(workflow_service, '_load_workflow', return_value=mock_workflow):
            workflow = await workflow_service.get_workflow(
                workflow_id="wf_123",
                user_id="user_123"  # Different user
            )
            
            assert workflow["id"] == "wf_123"
    
    @pytest.mark.asyncio
    async def test_get_workflow_access_denied(self, workflow_service):
        """Test getting private workflow of another user"""
        mock_workflow = {
            "id": "wf_123",
            "user_id": "user_456",
            "is_public": False,
            "name": "Private Workflow"
        }
        
        with patch.object(workflow_service, '_load_workflow', return_value=mock_workflow):
            with pytest.raises(HTTPException) as exc_info:
                await workflow_service.get_workflow(
                    workflow_id="wf_123",
                    user_id="user_123"  # Different user
                )
            
            assert exc_info.value.status_code == 403
    
    @pytest.mark.asyncio
    async def test_get_workflow_not_found(self, workflow_service):
        """Test getting non-existent workflow"""
        with patch.object(workflow_service, '_load_workflow', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await workflow_service.get_workflow(
                    workflow_id="wf_999",
                    user_id="user_123"
                )
            
            assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_workflow_success(self, workflow_service, sample_workflow_data):
        """Test successful workflow update"""
        existing_workflow = {
            "id": "wf_123",
            "user_id": "user_123",
            "name": "Old Name",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        with patch.object(workflow_service, '_load_workflow', return_value=existing_workflow), \
             patch.object(workflow_service, '_save_workflow') as mock_save, \
             patch.object(workflow_service, '_update_index') as mock_update_index:
            
            result = await workflow_service.update_workflow(
                workflow_id="wf_123",
                name="New Name",
                description="New description",
                is_public=True,
                nodes=sample_workflow_data["nodes"],
                edges=sample_workflow_data["edges"],
                user_id="user_123"
            )
            
            assert result["name"] == "New Name"
            assert result["is_public"] is True
            mock_save.assert_called_once()
            mock_update_index.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_workflow_not_owner(self, workflow_service, sample_workflow_data):
        """Test updating workflow by non-owner"""
        existing_workflow = {
            "id": "wf_123",
            "user_id": "user_456",  # Different owner
            "name": "Old Name"
        }
        
        with patch.object(workflow_service, '_load_workflow', return_value=existing_workflow):
            with pytest.raises(HTTPException) as exc_info:
                await workflow_service.update_workflow(
                    workflow_id="wf_123",
                    name="New Name",
                    description="",
                    is_public=False,
                    nodes=sample_workflow_data["nodes"],
                    edges=sample_workflow_data["edges"],
                    user_id="user_123"
                )
            
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_workflow_not_found(self, workflow_service, sample_workflow_data):
        """Test updating non-existent workflow"""
        with patch.object(workflow_service, '_load_workflow', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await workflow_service.update_workflow(
                    workflow_id="wf_999",
                    name="New Name",
                    description="",
                    is_public=False,
                    nodes=sample_workflow_data["nodes"],
                    edges=sample_workflow_data["edges"],
                    user_id="user_123"
                )
            
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_workflow_empty_name(self, workflow_service, sample_workflow_data):
        """Test updating workflow with empty name"""
        existing_workflow = {
            "id": "wf_123",
            "user_id": "user_123",
            "name": "Old Name"
        }
        
        with patch.object(workflow_service, '_load_workflow', return_value=existing_workflow):
            with pytest.raises(HTTPException) as exc_info:
                await workflow_service.update_workflow(
                    workflow_id="wf_123",
                    name="",
                    description="",
                    is_public=False,
                    nodes=sample_workflow_data["nodes"],
                    edges=sample_workflow_data["edges"],
                    user_id="user_123"
                )
            
            assert exc_info.value.status_code == 400
            assert "name is required" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_update_workflow_name_too_long(self, workflow_service, sample_workflow_data):
        """Test updating workflow with name too long"""
        existing_workflow = {
            "id": "wf_123",
            "user_id": "user_123",
            "name": "Old Name"
        }
        
        with patch.object(workflow_service, '_load_workflow', return_value=existing_workflow):
            with pytest.raises(HTTPException) as exc_info:
                await workflow_service.update_workflow(
                    workflow_id="wf_123",
                    name="A" * 101,
                    description="",
                    is_public=False,
                    nodes=sample_workflow_data["nodes"],
                    edges=sample_workflow_data["edges"],
                    user_id="user_123"
                )
            
            assert exc_info.value.status_code == 400
            assert "100 characters" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_workflow_no_nodes(self, workflow_service):
        """Test updating workflow with no nodes"""
        existing_workflow = {
            "id": "wf_123",
            "user_id": "user_123",
            "name": "Old Name"
        }
        
        with patch.object(workflow_service, '_load_workflow', return_value=existing_workflow):
            with pytest.raises(HTTPException) as exc_info:
                await workflow_service.update_workflow(
                    workflow_id="wf_123",
                    name="New Name",
                    description="",
                    is_public=False,
                    nodes=[],
                    edges=[],
                    user_id="user_123"
                )
            
            assert exc_info.value.status_code == 400
            assert "at least one node" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_update_workflow_too_many_nodes(self, workflow_service):
        """Test updating workflow with too many nodes"""
        existing_workflow = {
            "id": "wf_123",
            "user_id": "user_123",
            "name": "Old Name"
        }
        
        nodes = [{"id": f"node-{i}", "type": "test", "position": {}, "data": {}} for i in range(101)]
        
        with patch.object(workflow_service, '_load_workflow', return_value=existing_workflow):
            with pytest.raises(HTTPException) as exc_info:
                await workflow_service.update_workflow(
                    workflow_id="wf_123",
                    name="New Name",
                    description="",
                    is_public=False,
                    nodes=nodes,
                    edges=[],
                    user_id="user_123"
                )
            
            assert exc_info.value.status_code == 400
            assert "100 nodes" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_workflow_not_found(self, workflow_service):
        """Test deleting non-existent workflow"""
        with patch.object(workflow_service, '_load_workflow', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await workflow_service.delete_workflow(
                    workflow_id="wf_999",
                    user_id="user_123"
                )
            
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_clone_workflow_not_found(self, workflow_service):
        """Test cloning non-existent workflow"""
        with patch.object(workflow_service, '_load_workflow', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await workflow_service.clone_workflow(
                    workflow_id="wf_999",
                    user_id="user_123",
                    user_email="test@example.com"
                )
            
            assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_workflow_success(self, workflow_service):
        """Test successful workflow deletion"""
        existing_workflow = {
            "id": "wf_123",
            "user_id": "user_123",
            "name": "Test Workflow"
        }
        
        with patch.object(workflow_service, '_load_workflow', return_value=existing_workflow), \
             patch.object(workflow_service, '_delete_workflow_file') as mock_delete, \
             patch.object(workflow_service, '_remove_from_index') as mock_remove:
            
            await workflow_service.delete_workflow(
                workflow_id="wf_123",
                user_id="user_123"
            )
            
            mock_delete.assert_called_once_with("wf_123")
            mock_remove.assert_called_once_with("wf_123")
    
    @pytest.mark.asyncio
    async def test_delete_workflow_not_owner(self, workflow_service):
        """Test deleting workflow by non-owner"""
        existing_workflow = {
            "id": "wf_123",
            "user_id": "user_456",
            "name": "Test Workflow"
        }
        
        with patch.object(workflow_service, '_load_workflow', return_value=existing_workflow):
            with pytest.raises(HTTPException) as exc_info:
                await workflow_service.delete_workflow(
                    workflow_id="wf_123",
                    user_id="user_123"
                )
            
            assert exc_info.value.status_code == 403
    
    @pytest.mark.asyncio
    async def test_clone_workflow_success(self, workflow_service):
        """Test successful workflow cloning"""
        original_workflow = {
            "id": "wf_123",
            "user_id": "user_456",
            "is_public": True,
            "name": "Original Workflow",
            "nodes": [{"id": "node-1", "type": "test", "position": {}, "data": {}}],
            "edges": []
        }
        
        with patch.object(workflow_service, '_load_workflow', return_value=original_workflow), \
             patch.object(workflow_service, '_save_workflow') as mock_save, \
             patch.object(workflow_service, '_update_index') as mock_update_index:
            
            new_id = await workflow_service.clone_workflow(
                workflow_id="wf_123",
                user_id="user_789",
                user_email="newuser@example.com"
            )
            
            assert new_id.startswith("wf_")
            assert new_id != "wf_123"
            mock_save.assert_called_once()
            
            # Verify cloned workflow has correct properties
            saved_workflow = mock_save.call_args[0][1]
            assert saved_workflow["name"] == "Original Workflow (Copy)"
            assert saved_workflow["is_public"] is False
            assert saved_workflow["user_id"] == "user_789"
    
    @pytest.mark.asyncio
    async def test_clone_workflow_access_denied(self, workflow_service):
        """Test cloning private workflow by non-owner"""
        original_workflow = {
            "id": "wf_123",
            "user_id": "user_456",
            "is_public": False,  # Private
            "name": "Private Workflow"
        }
        
        with patch.object(workflow_service, '_load_workflow', return_value=original_workflow):
            with pytest.raises(HTTPException) as exc_info:
                await workflow_service.clone_workflow(
                    workflow_id="wf_123",
                    user_id="user_789",
                    user_email="newuser@example.com"
                )
            
            assert exc_info.value.status_code == 403


class TestWorkflowServiceInternalMethods:
    """Test internal helper methods for GCS operations"""
    
    def test_get_bucket(self, workflow_service):
        """Test getting the GCS bucket"""
        with patch.object(workflow_service, 'storage_client') as mock_client:
            mock_bucket = MagicMock()
            mock_client.bucket.return_value = mock_bucket
            
            result = workflow_service._get_bucket()
            
            mock_client.bucket.assert_called_once_with(workflow_service.bucket_name)
            assert result == mock_bucket

    def test_load_index_success(self, workflow_service):
        """Test loading workflow index from GCS"""
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_blob.download_as_text.return_value = '{"wf_1": {"name": "Test"}}'
        
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        
        with patch.object(workflow_service, '_get_bucket', return_value=mock_bucket):
            result = workflow_service._load_index()
            
            assert result == {"wf_1": {"name": "Test"}}
            mock_bucket.blob.assert_called_once_with("workflows/metadata/index.json")

    def test_load_index_not_exists(self, workflow_service):
        """Test loading index when file doesn't exist"""
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        
        with patch.object(workflow_service, '_get_bucket', return_value=mock_bucket):
            result = workflow_service._load_index()
            
            assert result == {}

    def test_load_index_error(self, workflow_service):
        """Test loading index with GCS error returns empty dict"""
        mock_bucket = MagicMock()
        mock_bucket.blob.side_effect = Exception("GCS error")
        
        with patch.object(workflow_service, '_get_bucket', return_value=mock_bucket):
            result = workflow_service._load_index()
            
            assert result == {}

    def test_save_index_success(self, workflow_service):
        """Test saving workflow index to GCS"""
        mock_blob = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        
        with patch.object(workflow_service, '_get_bucket', return_value=mock_bucket):
            workflow_service._save_index({"wf_1": {"name": "Test"}})
            
            mock_blob.upload_from_string.assert_called_once()
            call_args = mock_blob.upload_from_string.call_args
            assert "wf_1" in call_args[0][0]

    def test_save_index_error(self, workflow_service):
        """Test saving index with GCS error raises HTTPException"""
        mock_blob = MagicMock()
        mock_blob.upload_from_string.side_effect = Exception("GCS write failed")
        
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        
        with patch.object(workflow_service, '_get_bucket', return_value=mock_bucket):
            with pytest.raises(HTTPException) as exc_info:
                workflow_service._save_index({"wf_1": {}})
            
            assert exc_info.value.status_code == 500
            assert "workflow index" in str(exc_info.value.detail).lower()

    def test_update_index(self, workflow_service):
        """Test updating index entry"""
        workflow = {
            "id": "wf_123",
            "name": "Test Workflow",
            "nodes": [{"id": "node1"}],
            "edges": []
        }
        
        with patch.object(workflow_service, '_load_index', return_value={}) as mock_load, \
             patch.object(workflow_service, '_save_index') as mock_save:
            
            workflow_service._update_index("wf_123", workflow)
            
            mock_save.assert_called_once()
            saved_index = mock_save.call_args[0][0]
            assert "wf_123" in saved_index
            # Nodes and edges should be excluded from index
            assert "nodes" not in saved_index["wf_123"]
            assert "edges" not in saved_index["wf_123"]

    def test_remove_from_index_exists(self, workflow_service):
        """Test removing existing entry from index"""
        existing_index = {"wf_123": {"name": "Test"}, "wf_456": {"name": "Other"}}
        
        with patch.object(workflow_service, '_load_index', return_value=existing_index), \
             patch.object(workflow_service, '_save_index') as mock_save:
            
            workflow_service._remove_from_index("wf_123")
            
            mock_save.assert_called_once()
            saved_index = mock_save.call_args[0][0]
            assert "wf_123" not in saved_index
            assert "wf_456" in saved_index

    def test_remove_from_index_not_exists(self, workflow_service):
        """Test removing non-existent entry from index"""
        existing_index = {"wf_456": {"name": "Other"}}
        
        with patch.object(workflow_service, '_load_index', return_value=existing_index), \
             patch.object(workflow_service, '_save_index') as mock_save:
            
            workflow_service._remove_from_index("wf_123")
            
            # Should not call save if entry doesn't exist
            mock_save.assert_not_called()

    def test_load_workflow_success(self, workflow_service):
        """Test loading workflow from GCS"""
        workflow_data = {"id": "wf_123", "name": "Test Workflow"}
        
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_blob.download_as_text.return_value = json.dumps(workflow_data)
        
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        
        with patch.object(workflow_service, '_get_bucket', return_value=mock_bucket):
            result = workflow_service._load_workflow("wf_123")
            
            assert result == workflow_data
            mock_bucket.blob.assert_called_once_with("workflows/data/wf_123.json")

    def test_load_workflow_not_exists(self, workflow_service):
        """Test loading non-existent workflow"""
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        
        with patch.object(workflow_service, '_get_bucket', return_value=mock_bucket):
            result = workflow_service._load_workflow("wf_999")
            
            assert result is None

    def test_load_workflow_error(self, workflow_service):
        """Test loading workflow with GCS error"""
        mock_bucket = MagicMock()
        mock_bucket.blob.side_effect = Exception("GCS read error")
        
        with patch.object(workflow_service, '_get_bucket', return_value=mock_bucket):
            result = workflow_service._load_workflow("wf_123")
            
            assert result is None

    def test_save_workflow_success(self, workflow_service):
        """Test saving workflow to GCS"""
        workflow_data = {"id": "wf_123", "name": "Test"}
        
        mock_blob = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        
        with patch.object(workflow_service, '_get_bucket', return_value=mock_bucket):
            workflow_service._save_workflow("wf_123", workflow_data)
            
            mock_bucket.blob.assert_called_once_with("workflows/data/wf_123.json")
            mock_blob.upload_from_string.assert_called_once()

    def test_save_workflow_error(self, workflow_service):
        """Test saving workflow with GCS error"""
        mock_blob = MagicMock()
        mock_blob.upload_from_string.side_effect = Exception("GCS write error")
        
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        
        with patch.object(workflow_service, '_get_bucket', return_value=mock_bucket):
            with pytest.raises(HTTPException) as exc_info:
                workflow_service._save_workflow("wf_123", {"id": "wf_123"})
            
            assert exc_info.value.status_code == 500

    def test_delete_workflow_file_success(self, workflow_service):
        """Test deleting workflow file from GCS"""
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        
        with patch.object(workflow_service, '_get_bucket', return_value=mock_bucket):
            workflow_service._delete_workflow_file("wf_123")
            
            mock_blob.delete.assert_called_once()

    def test_delete_workflow_file_not_exists(self, workflow_service):
        """Test deleting non-existent workflow file"""
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        
        with patch.object(workflow_service, '_get_bucket', return_value=mock_bucket):
            workflow_service._delete_workflow_file("wf_123")
            
            # Should not call delete if file doesn't exist
            mock_blob.delete.assert_not_called()

    def test_delete_workflow_file_error(self, workflow_service):
        """Test deleting workflow file with GCS error"""
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_blob.delete.side_effect = Exception("GCS delete error")
        
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        
        with patch.object(workflow_service, '_get_bucket', return_value=mock_bucket):
            with pytest.raises(HTTPException) as exc_info:
                workflow_service._delete_workflow_file("wf_123")
            
            assert exc_info.value.status_code == 500
