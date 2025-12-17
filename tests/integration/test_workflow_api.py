"""
Integration tests for workflow API endpoints
Tests mock Firestore interactions but use real FastAPI routing
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestWorkflowCreateAPI:
    """Integration tests for POST /workflows/save endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.post("/workflows/save", json={
            "name": "Test",
            "nodes": [{"id": "1"}],
            "edges": []
        })
        assert response.status_code == 401
    
    @patch("app.services.workflow_firestore.get_firestore_client")
    def test_creates_workflow_successfully(self, mock_get_client, client, mock_auth):
        """Successfully creates a workflow"""
        # Mock Firestore
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        mock_client.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc
        mock_get_client.return_value = mock_client
        
        response = client.post("/workflows/save", json={
            "name": "My Workflow",
            "description": "Test workflow",
            "is_public": False,
            "nodes": [{"id": "node1", "type": "text", "data": {"text": "Hello"}}],
            "edges": []
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert isinstance(data["id"], str)
        mock_doc.set.assert_called_once()
    
    @patch("app.services.workflow_firestore.get_firestore_client")
    def test_validates_required_fields(self, mock_get_client, client, mock_auth):
        """Validates required fields"""
        mock_get_client.return_value = MagicMock()
        
        response = client.post("/workflows/save", json={
            "description": "Missing name",
            "nodes": [],
            "edges": []
        })
        
        assert response.status_code == 422  # Validation error


class TestWorkflowListAPI:
    """Integration tests for GET /workflows endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.get("/workflows?scope=my")
        assert response.status_code == 401
    
    @patch("app.services.workflow_firestore.get_firestore_client")
    def test_lists_user_workflows(self, mock_get_client, client, mock_auth):
        """Lists workflows for authenticated user"""
        # Mock Firestore
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_doc = MagicMock()
        
        # Mock workflow document
        mock_doc.to_dict.return_value = {
            "id": "wf1",
            "name": "My Workflow",
            "description": "Test",
            "user_id": "test-user-123",
            "user_email": "test@example.com",
            "is_public": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "nodes": [{"id": "1", "type": "text"}],
            "edges": []
        }
        
        mock_query.stream.return_value = [mock_doc]
        mock_collection.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_client.collection.return_value = mock_collection
        mock_get_client.return_value = mock_client
        
        response = client.get("/workflows?scope=my")
        
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert len(data["workflows"]) == 1
        assert data["workflows"][0]["name"] == "My Workflow"
    
    @patch("app.services.workflow_firestore.get_firestore_client")
    def test_lists_public_workflows(self, mock_get_client, client, mock_auth):
        """Lists public workflows"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()
        
        mock_query.stream.return_value = []
        mock_collection.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_client.collection.return_value = mock_collection
        mock_get_client.return_value = mock_client
        
        response = client.get("/workflows?scope=public")
        
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert isinstance(data["workflows"], list)


class TestWorkflowGetAPI:
    """Integration tests for GET /workflows/{id} endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.get("/workflows/test-id")
        assert response.status_code == 401
    
    @patch("app.services.workflow_firestore.get_firestore_client")
    def test_gets_workflow_by_id(self, mock_get_client, client, mock_auth):
        """Gets a specific workflow"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": "wf1",
            "name": "My Workflow",
            "description": "Test",
            "user_id": "test-user-123",
            "user_email": "test@example.com",
            "is_public": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "nodes": [{"id": "1", "type": "text"}],
            "edges": []
        }
        
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc
        mock_client.collection.return_value = mock_collection
        mock_get_client.return_value = mock_client
        
        response = client.get("/workflows/wf1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "wf1"
        assert data["name"] == "My Workflow"
    
    @patch("app.services.workflow_firestore.get_firestore_client")
    def test_returns_404_for_missing_workflow(self, mock_get_client, client, mock_auth):
        """Returns 404 when workflow doesn't exist"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        
        mock_doc.exists = False
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc
        mock_client.collection.return_value = mock_collection
        mock_get_client.return_value = mock_client
        
        response = client.get("/workflows/nonexistent")
        
        assert response.status_code == 404


class TestWorkflowUpdateAPI:
    """Integration tests for PUT /workflows/{id} endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.put("/workflows/test-id", json={
            "name": "Updated",
            "nodes": [],
            "edges": []
        })
        assert response.status_code == 401
    
    @patch("app.services.workflow_firestore.get_firestore_client")
    def test_updates_workflow(self, mock_get_client, client, mock_auth):
        """Successfully updates a workflow"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": "wf1",
            "user_id": "test-user-123",
            "name": "Old Name"
        }
        
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc
        mock_client.collection.return_value = mock_collection
        mock_get_client.return_value = mock_client
        
        response = client.put("/workflows/wf1", json={
            "name": "New Name",
            "description": "Updated",
            "is_public": True,
            "nodes": [{"id": "1", "type": "text"}],
            "edges": []
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Workflow updated successfully"


class TestWorkflowDeleteAPI:
    """Integration tests for DELETE /workflows/{id} endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.delete("/workflows/test-id")
        assert response.status_code == 401
    
    @patch("app.services.workflow_firestore.get_firestore_client")
    def test_deletes_workflow(self, mock_get_client, client, mock_auth):
        """Successfully deletes a workflow"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": "wf1",
            "user_id": "test-user-123",
            "name": "To Delete"
        }
        
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc
        mock_client.collection.return_value = mock_collection
        mock_get_client.return_value = mock_client
        
        response = client.delete("/workflows/wf1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Workflow deleted successfully"
        mock_doc_ref.delete.assert_called_once()


class TestWorkflowCloneAPI:
    """Integration tests for POST /workflows/{id}/clone endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.post("/workflows/test-id/clone")
        assert response.status_code == 401
    
    @patch("app.services.workflow_firestore.get_firestore_client")
    def test_clones_workflow(self, mock_get_client, client, mock_auth):
        """Successfully clones a workflow"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        mock_new_doc = MagicMock()
        
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": "wf1",
            "name": "Original",
            "description": "Original workflow",
            "user_id": "test-user-123",
            "is_public": True,
            "nodes": [{"id": "1", "type": "text"}],
            "edges": []
        }
        
        def mock_document(doc_id):
            if doc_id == "wf1":
                return mock_doc_ref
            return mock_new_doc
        
        mock_collection.document = mock_document
        mock_doc_ref.get.return_value = mock_doc
        mock_client.collection.return_value = mock_collection
        mock_get_client.return_value = mock_client
        
        response = client.post("/workflows/wf1/clone")
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["id"] != "wf1"  # New ID
        mock_new_doc.set.assert_called_once()
