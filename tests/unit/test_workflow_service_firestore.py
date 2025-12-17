"""
Comprehensive tests for WorkflowServiceFirestore
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from fastapi import HTTPException


@pytest.fixture
def mock_firestore_client():
    """Mock Firestore client"""
    with patch('app.services.workflow_firestore.get_firestore_client') as mock_get_client:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.collection.return_value = mock_collection
        mock_get_client.return_value = mock_client
        yield mock_client


class TestWorkflowServiceFirestoreCreate:
    """Test workflow creation"""
    
    async def test_create_workflow_success(self, mock_firestore_client):
        """Test successful workflow creation"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        mock_doc = MagicMock()
        mock_firestore_client.collection.return_value.document.return_value = mock_doc
        
        service = WorkflowServiceFirestore()
        workflow_id = await service.create_workflow(
            name="Test Workflow",
            description="Test",
            is_public=False,
            nodes=[{"id": "1", "type": "text"}],
            edges=[],
            user_id="user123",
            user_email="test@example.com"
        )
        
        assert workflow_id is not None
        mock_doc.set.assert_called_once()


class TestWorkflowServiceFirestoreList:
    """Test workflow listing"""
    
    async def test_list_my_workflows(self, mock_firestore_client):
        """Test listing user's workflows"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            "id": "wf1",
            "name": "My Workflow",
            "description": "Test",
            "user_id": "user123",
            "user_email": "test@example.com",
            "is_public": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "node_count": 1,
            "edge_count": 0
        }
        
        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_doc]
        mock_collection = mock_firestore_client.collection.return_value
        mock_collection.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        
        service = WorkflowServiceFirestore()
        workflows = await service.list_workflows(scope="my", user_id="user123")
        
        assert len(workflows) == 1
        assert workflows[0]["name"] == "My Workflow"
    
    async def test_list_public_workflows(self, mock_firestore_client):
        """Test listing public workflows"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_collection = mock_firestore_client.collection.return_value
        mock_collection.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        
        service = WorkflowServiceFirestore()
        workflows = await service.list_workflows(scope="public", user_id="user123")
        
        assert isinstance(workflows, list)
    
    async def test_list_invalid_scope(self, mock_firestore_client):
        """Test invalid scope raises error"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        service = WorkflowServiceFirestore()
        
        with pytest.raises(HTTPException) as exc:
            await service.list_workflows(scope="invalid", user_id="user123")
        
        assert exc.value.status_code == 400


class TestWorkflowServiceFirestoreGet:
    """Test getting workflow"""
    
    async def test_get_workflow_success(self, mock_firestore_client):
        """Test getting workflow successfully"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": "wf1",
            "name": "Test Workflow",
            "description": "Test",
            "user_id": "user123",
            "user_email": "test@example.com",
            "is_public": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "nodes": [{"id": "1", "type": "text", "data": {"text": "Hello"}}],
            "edges": []
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        service = WorkflowServiceFirestore()
        workflow = await service.get_workflow(workflow_id="wf1", user_id="user123")
        
        assert workflow["id"] == "wf1"
        assert workflow["name"] == "Test Workflow"
    
    async def test_get_workflow_not_found(self, mock_firestore_client):
        """Test workflow not found"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        mock_doc = MagicMock()
        mock_doc.exists = False
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        service = WorkflowServiceFirestore()
        
        with pytest.raises(HTTPException) as exc:
            await service.get_workflow(workflow_id="nonexistent", user_id="user123")
        
        assert exc.value.status_code == 404
    
    async def test_get_workflow_access_denied(self, mock_firestore_client):
        """Test access denied for private workflow"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": "wf1",
            "user_id": "other-user",
            "is_public": False
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        service = WorkflowServiceFirestore()
        
        with pytest.raises(HTTPException) as exc:
            await service.get_workflow(workflow_id="wf1", user_id="user123")
        
        assert exc.value.status_code == 403


class TestWorkflowServiceFirestoreUpdate:
    """Test workflow update"""
    
    async def test_update_workflow_success(self, mock_firestore_client):
        """Test successful workflow update"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": "wf1",
            "user_id": "user123",
            "name": "Old Name"
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        service = WorkflowServiceFirestore()
        await service.update_workflow(
            workflow_id="wf1",
            name="New Name",
            description="Updated",
            is_public=True,
            nodes=[{"id": "1"}],
            edges=[],
            user_id="user123"
        )
        
        mock_doc_ref.update.assert_called_once()
    
    async def test_update_workflow_not_found(self, mock_firestore_client):
        """Test update non-existent workflow"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        mock_doc = MagicMock()
        mock_doc.exists = False
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        service = WorkflowServiceFirestore()
        
        with pytest.raises(HTTPException) as exc:
            await service.update_workflow(
                workflow_id="nonexistent",
                name="New",
                description="",
                is_public=False,
                nodes=[],
                edges=[],
                user_id="user123"
            )
        
        assert exc.value.status_code == 404
    
    async def test_update_workflow_access_denied(self, mock_firestore_client):
        """Test update other user's workflow"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": "wf1",
            "user_id": "other-user"
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        service = WorkflowServiceFirestore()
        
        with pytest.raises(HTTPException) as exc:
            await service.update_workflow(
                workflow_id="wf1",
                name="New",
                description="",
                is_public=False,
                nodes=[],
                edges=[],
                user_id="user123"
            )
        
        assert exc.value.status_code == 403


class TestWorkflowServiceFirestoreDelete:
    """Test workflow deletion"""
    
    async def test_delete_workflow_success(self, mock_firestore_client):
        """Test successful workflow deletion"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": "wf1",
            "user_id": "user123"
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        service = WorkflowServiceFirestore()
        await service.delete_workflow(workflow_id="wf1", user_id="user123")
        
        mock_doc_ref.delete.assert_called_once()
    
    async def test_delete_workflow_not_found(self, mock_firestore_client):
        """Test delete non-existent workflow"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        mock_doc = MagicMock()
        mock_doc.exists = False
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        service = WorkflowServiceFirestore()
        
        with pytest.raises(HTTPException) as exc:
            await service.delete_workflow(workflow_id="nonexistent", user_id="user123")
        
        assert exc.value.status_code == 404


class TestWorkflowServiceFirestoreClone:
    """Test workflow cloning"""
    
    async def test_clone_workflow_success(self, mock_firestore_client):
        """Test successful workflow cloning"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": "wf1",
            "name": "Original",
            "description": "Original workflow",
            "user_id": "user123",
            "is_public": True,
            "nodes": [{"id": "1"}],
            "edges": []
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        
        mock_new_doc = MagicMock()
        
        def mock_document(doc_id):
            if doc_id == "wf1":
                return mock_doc_ref
            return mock_new_doc
        
        mock_firestore_client.collection.return_value.document = mock_document
        
        service = WorkflowServiceFirestore()
        new_id = await service.clone_workflow(
            workflow_id="wf1",
            user_id="user123",
            user_email="test@example.com"
        )
        
        assert new_id != "wf1"
        mock_new_doc.set.assert_called_once()
    
    async def test_clone_public_workflow_by_other_user(self, mock_firestore_client):
        """Test cloning public workflow by different user"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": "wf1",
            "name": "Public Workflow",
            "user_id": "other-user",
            "is_public": True,
            "nodes": [],
            "edges": []
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        
        mock_new_doc = MagicMock()
        
        def mock_document(doc_id):
            if doc_id == "wf1":
                return mock_doc_ref
            return mock_new_doc
        
        mock_firestore_client.collection.return_value.document = mock_document
        
        service = WorkflowServiceFirestore()
        new_id = await service.clone_workflow(
            workflow_id="wf1",
            user_id="user123",
            user_email="test@example.com"
        )
        
        assert new_id is not None
        mock_new_doc.set.assert_called_once()


class TestWorkflowServiceFirestoreURLResolution:
    """Test asset URL resolution"""
    
    async def test_resolve_asset_urls_with_refs(self, mock_firestore_client):
        """Test resolving asset references in nodes"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        # Mock asset lookup
        mock_asset_doc = MagicMock()
        mock_asset_doc.exists = True
        mock_asset_doc.to_dict.return_value = {
            "id": "asset1",
            "blob_path": "users/user123/images/asset1.png"
        }
        
        mock_asset_ref = MagicMock()
        mock_asset_ref.get.return_value = mock_asset_doc
        
        mock_collection = mock_firestore_client.collection.return_value
        mock_collection.document.return_value = mock_asset_ref
        
        service = WorkflowServiceFirestore()
        
        nodes = [
            {
                "id": "1",
                "type": "image",
                "data": {"imageRef": "asset1", "prompt": "test"}
            }
        ]
        
        resolved = service._resolve_asset_urls(nodes)
        
        assert "imageUrl" in resolved[0]["data"]
        assert "genmediastudio-assets" in resolved[0]["data"]["imageUrl"]
    
    async def test_resolve_asset_urls_missing_asset(self, mock_firestore_client):
        """Test handling missing assets gracefully"""
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        # Mock asset not found
        mock_asset_doc = MagicMock()
        mock_asset_doc.exists = False
        
        mock_asset_ref = MagicMock()
        mock_asset_ref.get.return_value = mock_asset_doc
        
        mock_collection = mock_firestore_client.collection.return_value
        mock_collection.document.return_value = mock_asset_ref
        
        service = WorkflowServiceFirestore()
        
        nodes = [
            {
                "id": "1",
                "type": "image",
                "data": {"imageRef": "missing-asset"}
            }
        ]
        
        # Should not raise error, just skip resolution
        resolved = service._resolve_asset_urls(nodes)
        
        # Missing asset should have imageUrl: None and imageRefExists: False
        assert resolved[0]["data"]["imageUrl"] is None
        assert resolved[0]["data"]["imageRefExists"] == False
