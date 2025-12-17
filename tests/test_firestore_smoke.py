"""
Simple smoke test for Firestore services
Run with: pytest tests/test_firestore_smoke.py -v
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@pytest.fixture
def mock_firestore_client():
    """Mock Firestore client"""
    with patch('app.firestore.firestore') as mock_firestore:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.collection.return_value = mock_collection
        mock_firestore.client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_gcs_client():
    """Mock GCS client"""
    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_storage.bucket.return_value = mock_bucket
    return mock_storage


class TestWorkflowServiceFirestore:
    """Test WorkflowServiceFirestore"""
    
    @patch('app.services.workflow_firestore.get_firestore_client')
    async def test_create_workflow(self, mock_get_client):
        """Test creating a workflow"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        mock_client.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc
        mock_get_client.return_value = mock_client
        
        service = WorkflowServiceFirestore()
        
        # Create workflow
        workflow_id = await service.create_workflow(
            name="Test Workflow",
            description="Test Description",
            is_public=False,
            nodes=[{"id": "node1", "type": "text"}],
            edges=[],
            user_id="test-user",
            user_email="test@example.com"
        )
        
        # Verify
        assert workflow_id is not None
        mock_collection.document.assert_called()
        mock_doc.set.assert_called_once()
    
    @patch('app.services.workflow_firestore.get_firestore_client')
    async def test_list_workflows(self, mock_get_client):
        """Test listing workflows"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_doc = MagicMock()
        
        # Mock document data
        mock_doc.to_dict.return_value = {
            "id": "workflow1",
            "name": "Test Workflow",
            "description": "Test",
            "user_id": "test-user",
            "is_public": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "nodes": [],
            "edges": []
        }
        
        mock_query.stream.return_value = [mock_doc]
        mock_collection.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_client.collection.return_value = mock_collection
        mock_get_client.return_value = mock_client
        
        service = WorkflowServiceFirestore()
        
        # List workflows
        workflows = await service.list_workflows(scope="my", user_id="test-user")
        
        # Verify
        assert len(workflows) == 1
        assert workflows[0]["name"] == "Test Workflow"


class TestLibraryServiceFirestore:
    """Test LibraryServiceFirestore"""
    
    @patch('app.services.library_firestore.get_firestore_client')
    @patch('app.services.library_firestore.storage.Client')
    async def test_save_asset(self, mock_storage_class, mock_get_client):
        """Test saving an asset"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        # Setup Firestore mock
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        mock_client.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc
        mock_get_client.return_value = mock_client
        
        # Setup GCS mock
        mock_storage = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_storage_class.return_value = mock_storage
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        
        # Save asset
        result = await service.save_asset(
            data="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            asset_type="image",
            user_id="test-user",
            prompt="Test prompt"
        )
        
        # Verify
        assert result.asset_type == "image"
        assert result.prompt == "Test prompt"
        mock_blob.upload_from_string.assert_called_once()
        mock_doc.set.assert_called_once()
    
    @patch('app.services.library_firestore.get_firestore_client')
    @patch('app.services.library_firestore.storage.Client')
    async def test_list_assets(self, mock_storage_class, mock_get_client):
        """Test listing assets"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        # Setup Firestore mock
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_doc = MagicMock()
        
        # Mock document data
        mock_doc.to_dict.return_value = {
            "id": "asset1",
            "user_id": "test-user",
            "asset_type": "image",
            "blob_path": "users/test-user/images/asset1.png",
            "mime_type": "image/png",
            "created_at": datetime.utcnow(),
            "prompt": "Test",
            "source": "generated"
        }
        
        mock_query.stream.return_value = [mock_doc]
        mock_collection.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_client.collection.return_value = mock_collection
        mock_get_client.return_value = mock_client
        
        # Setup GCS mock
        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        
        # List assets
        result = await service.list_assets(user_id="test-user", limit=50)
        
        # Verify
        assert len(result.assets) == 1
        assert result.assets[0].asset_type == "image"
        assert result.assets[0].url is not None
