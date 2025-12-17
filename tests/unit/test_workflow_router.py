"""
Unit tests for workflow router
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, Mock
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException
from app.routers import workflow
from app.schemas import WorkflowIdResponse, WorkflowMessageResponse

# Create test app
app = FastAPI()
app.include_router(workflow.router, prefix="/workflows")

client = TestClient(app)


class TestWorkflowServiceFactory:
    """Test the workflow service factory function"""
    
    def test_get_workflow_service_returns_instance(self):
        """Verify get_workflow_service returns a WorkflowServiceFirestore instance"""
        from app.routers.workflow import get_workflow_service
        from app.services.workflow_firestore import WorkflowServiceFirestore
        
        with patch('app.services.workflow_firestore.get_firestore_client') as mock_fs:
            mock_fs.return_value.collection.return_value = Mock()
            service = get_workflow_service()
            assert isinstance(service, WorkflowServiceFirestore)


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    return {"uid": "user-123", "email": "test@test.com"}


@pytest.fixture
def mock_workflow_service():
    """Mock workflow service"""
    return AsyncMock()


@pytest.fixture
def sample_workflow():
    """Sample workflow data"""
    return {
        "id": "wf_123456789_abc",
        "name": "Test Workflow",
        "description": "Test description",
        "is_public": False,
        "thumbnail": None,
        "created_at": "2025-12-16T12:00:00Z",
        "updated_at": "2025-12-16T12:00:00Z",
        "user_id": "user-123",
        "user_email": "test@test.com",
        "node_count": 2,
        "edge_count": 1,
        "nodes": [
            {"id": "node-1", "type": "imageInput", "position": {"x": 0, "y": 0}, "data": {}},
            {"id": "node-2", "type": "generateImage", "position": {"x": 200, "y": 0}, "data": {}}
        ],
        "edges": [
            {"id": "edge-1", "source": "node-1", "target": "node-2"}
        ]
    }


@pytest.fixture
def sample_request():
    """Sample save workflow request"""
    return {
        "name": "Test Workflow",
        "description": "Test description",
        "is_public": False,
        "nodes": [
            {"id": "node-1", "type": "imageInput", "position": {"x": 0, "y": 0}, "data": {}}
        ],
        "edges": []
    }


class TestWorkflowRouterAuth:
    """Test authentication requirements"""
    
    def test_save_workflow_requires_auth(self, sample_request):
        """Save workflow requires authentication"""
        response = client.post("/workflows/save", json=sample_request)
        assert response.status_code == 401

    def test_list_workflows_requires_auth(self):
        """List workflows requires authentication"""
        response = client.get("/workflows?scope=my")
        assert response.status_code == 401

    def test_get_workflow_requires_auth(self):
        """Get workflow requires authentication"""
        response = client.get("/workflows/wf_123")
        assert response.status_code == 401

    def test_update_workflow_requires_auth(self, sample_request):
        """Update workflow requires authentication"""
        response = client.put("/workflows/wf_123", json=sample_request)
        assert response.status_code == 401

    def test_delete_workflow_requires_auth(self):
        """Delete workflow requires authentication"""
        response = client.delete("/workflows/wf_123")
        assert response.status_code == 401

    def test_clone_workflow_requires_auth(self):
        """Clone workflow requires authentication"""
        response = client.post("/workflows/wf_123/clone")
        assert response.status_code == 401


class TestSaveWorkflow:
    """Test save workflow endpoint"""
    
    def test_save_workflow_success(self, mock_user, sample_request):
        """Successfully save a workflow"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.create_workflow.return_value = "wf_new_123"
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.post("/workflows/save", json=sample_request)
        
        assert response.status_code == 200
        assert response.json()["id"] == "wf_new_123"
        
        mock_service.create_workflow.assert_called_once()
        
        app.dependency_overrides.clear()

    def test_save_workflow_validation_error(self, mock_user, sample_request):
        """Save workflow with validation error"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.create_workflow.side_effect = HTTPException(
            status_code=400, detail="Workflow name is required"
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.post("/workflows/save", json=sample_request)
        
        assert response.status_code == 400
        assert "required" in response.json()["detail"].lower()
        
        app.dependency_overrides.clear()

    def test_save_workflow_internal_error(self, mock_user, sample_request):
        """Save workflow with internal server error"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.create_workflow.side_effect = Exception("GCS connection failed")
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.post("/workflows/save", json=sample_request)
        
        assert response.status_code == 500
        assert "Failed to save workflow" in response.json()["detail"]
        
        app.dependency_overrides.clear()


class TestListWorkflows:
    """Test list workflows endpoint"""
    
    def test_list_my_workflows(self, mock_user, sample_workflow):
        """List user's workflows"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.list_workflows.return_value = [sample_workflow]
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.get("/workflows?scope=my")
        
        assert response.status_code == 200
        assert len(response.json()["workflows"]) == 1
        assert response.json()["workflows"][0]["name"] == "Test Workflow"
        
        mock_service.list_workflows.assert_called_once_with(
            scope="my", user_id="user-123"
        )
        
        app.dependency_overrides.clear()

    def test_list_workflows_multiple(self, mock_user):
        """List multiple workflows to cover logging loop"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        workflows = [
            {
                "id": "wf_1",
                "name": "Workflow 1",
                "nodes": [{"id": "n1"}],
                "edges": []
            },
            {
                "id": "wf_2",
                "name": "Workflow 2",
                "nodes": [{"id": "n1"}, {"id": "n2"}],
                "edges": [{"id": "e1"}]
            }
        ]
        
        mock_service = AsyncMock()
        mock_service.list_workflows.return_value = workflows
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.get("/workflows?scope=my")
        
        assert response.status_code == 200
        assert len(response.json()["workflows"]) == 2
        
        app.dependency_overrides.clear()

    def test_list_public_workflows(self, mock_user, sample_workflow):
        """List public workflows"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        public_workflow = sample_workflow.copy()
        public_workflow["is_public"] = True
        
        mock_service = AsyncMock()
        mock_service.list_workflows.return_value = [public_workflow]
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.get("/workflows?scope=public")
        
        assert response.status_code == 200
        mock_service.list_workflows.assert_called_once_with(
            scope="public", user_id="user-123"
        )
        
        app.dependency_overrides.clear()

    def test_list_workflows_empty(self, mock_user):
        """List workflows returns empty list"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.list_workflows.return_value = []
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.get("/workflows?scope=my")
        
        assert response.status_code == 200
        assert response.json()["workflows"] == []
        
        app.dependency_overrides.clear()

    def test_list_workflows_error(self, mock_user):
        """List workflows with internal error"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.list_workflows.side_effect = Exception("GCS error")
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.get("/workflows?scope=my")
        
        assert response.status_code == 500
        assert "Failed to list workflows" in response.json()["detail"]
        
        app.dependency_overrides.clear()


class TestGetWorkflow:
    """Test get workflow endpoint"""
    
    def test_get_workflow_success(self, mock_user, sample_workflow):
        """Get workflow by ID"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.get_workflow.return_value = sample_workflow
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.get("/workflows/wf_123")
        
        assert response.status_code == 200
        assert response.json()["name"] == "Test Workflow"
        assert len(response.json()["nodes"]) == 2
        
        mock_service.get_workflow.assert_called_once_with(
            workflow_id="wf_123", user_id="user-123"
        )
        
        app.dependency_overrides.clear()

    def test_get_workflow_not_found(self, mock_user):
        """Get non-existent workflow"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.get_workflow.side_effect = HTTPException(
            status_code=404, detail="Workflow not found"
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.get("/workflows/wf_nonexistent")
        
        assert response.status_code == 404
        
        app.dependency_overrides.clear()

    def test_get_workflow_forbidden(self, mock_user):
        """Get workflow without access"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.get_workflow.side_effect = HTTPException(
            status_code=403, detail="Access denied"
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.get("/workflows/wf_private")
        
        assert response.status_code == 403
        
        app.dependency_overrides.clear()

    def test_get_workflow_internal_error(self, mock_user):
        """Get workflow with internal error"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.get_workflow.side_effect = Exception("GCS read failed")
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.get("/workflows/wf_123")
        
        assert response.status_code == 500
        assert "Failed to get workflow" in response.json()["detail"]
        
        app.dependency_overrides.clear()


class TestUpdateWorkflow:
    """Test update workflow endpoint"""
    
    def test_update_workflow_success(self, mock_user, sample_request):
        """Update workflow successfully"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.update_workflow.return_value = None
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.put("/workflows/wf_123", json=sample_request)
        
        assert response.status_code == 200
        assert response.json()["message"] == "Workflow updated successfully"
        
        mock_service.update_workflow.assert_called_once()
        
        app.dependency_overrides.clear()

    def test_update_workflow_not_found(self, mock_user, sample_request):
        """Update non-existent workflow"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.update_workflow.side_effect = HTTPException(
            status_code=404, detail="Workflow not found"
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.put("/workflows/wf_nonexistent", json=sample_request)
        
        assert response.status_code == 404
        
        app.dependency_overrides.clear()

    def test_update_workflow_forbidden(self, mock_user, sample_request):
        """Update workflow without ownership"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.update_workflow.side_effect = HTTPException(
            status_code=403, detail="Only the owner can update this workflow"
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.put("/workflows/wf_other", json=sample_request)
        
        assert response.status_code == 403
        
        app.dependency_overrides.clear()

    def test_update_workflow_internal_error(self, mock_user, sample_request):
        """Update workflow with internal error"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.update_workflow.side_effect = Exception("GCS write failed")
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.put("/workflows/wf_123", json=sample_request)
        
        assert response.status_code == 500
        assert "Failed to update workflow" in response.json()["detail"]
        
        app.dependency_overrides.clear()


class TestDeleteWorkflow:
    """Test delete workflow endpoint"""
    
    def test_delete_workflow_success(self, mock_user):
        """Delete workflow successfully"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.delete_workflow.return_value = None
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.delete("/workflows/wf_123")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Workflow deleted successfully"
        
        mock_service.delete_workflow.assert_called_once_with(
            workflow_id="wf_123", user_id="user-123"
        )
        
        app.dependency_overrides.clear()

    def test_delete_workflow_not_found(self, mock_user):
        """Delete non-existent workflow"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.delete_workflow.side_effect = HTTPException(
            status_code=404, detail="Workflow not found"
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.delete("/workflows/wf_nonexistent")
        
        assert response.status_code == 404
        
        app.dependency_overrides.clear()

    def test_delete_workflow_forbidden(self, mock_user):
        """Delete workflow without ownership"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.delete_workflow.side_effect = HTTPException(
            status_code=403, detail="Only the owner can delete this workflow"
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.delete("/workflows/wf_other")
        
        assert response.status_code == 403
        
        app.dependency_overrides.clear()

    def test_delete_workflow_internal_error(self, mock_user):
        """Delete workflow with internal error"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.delete_workflow.side_effect = Exception("GCS delete failed")
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.delete("/workflows/wf_123")
        
        assert response.status_code == 500
        assert "Failed to delete workflow" in response.json()["detail"]
        
        app.dependency_overrides.clear()


class TestCloneWorkflow:
    """Test clone workflow endpoint"""
    
    def test_clone_workflow_success(self, mock_user):
        """Clone workflow successfully"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.clone_workflow.return_value = "wf_cloned_123"
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.post("/workflows/wf_123/clone")
        
        assert response.status_code == 200
        assert response.json()["id"] == "wf_cloned_123"
        
        mock_service.clone_workflow.assert_called_once_with(
            workflow_id="wf_123",
            user_id="user-123",
            user_email="test@test.com"
        )
        
        app.dependency_overrides.clear()

    def test_clone_workflow_not_found(self, mock_user):
        """Clone non-existent workflow"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.clone_workflow.side_effect = HTTPException(
            status_code=404, detail="Workflow not found"
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.post("/workflows/wf_nonexistent/clone")
        
        assert response.status_code == 404
        
        app.dependency_overrides.clear()

    def test_clone_private_workflow_forbidden(self, mock_user):
        """Clone private workflow without access"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.clone_workflow.side_effect = HTTPException(
            status_code=403, detail="Cannot clone private workflow"
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.post("/workflows/wf_private/clone")
        
        assert response.status_code == 403
        
        app.dependency_overrides.clear()

    def test_clone_workflow_internal_error(self, mock_user):
        """Clone workflow with internal error"""
        from app.auth import get_current_user
        from app.routers.workflow import get_workflow_service
        
        mock_service = AsyncMock()
        mock_service.clone_workflow.side_effect = Exception("GCS write failed")
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_workflow_service] = lambda: mock_service
        
        response = client.post("/workflows/wf_123/clone")
        
        assert response.status_code == 500
        assert "Failed to clone workflow" in response.json()["detail"]
        
        app.dependency_overrides.clear()
