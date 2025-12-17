import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.auth import get_current_user
from app.routers.generation import get_generation_service
from app.routers.library import get_library_service
from app.routers.workflow import get_workflow_service
from app.routers.workflow import get_workflow_service

@pytest.fixture
def client():
    """Test client for the app"""
    return TestClient(app)

@pytest.fixture
def authenticated_user():
    """Mock authenticated user"""
    return {"uid": "test-user-123", "email": "ldebortolialves@hubspot.com"}

@pytest.fixture
def mock_auth(authenticated_user):
    """Override auth dependency"""
    app.dependency_overrides[get_current_user] = lambda: authenticated_user
    yield authenticated_user
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
def mock_gcs_bucket():
    """Mock GCS bucket"""
    bucket = MagicMock()
    blob = MagicMock()
    blob.exists.return_value = True
    blob.public_url = "https://storage.googleapis.com/test-bucket/test.png"
    bucket.blob.return_value = blob
    bucket.list_blobs.return_value = []
    return bucket

@pytest.fixture
def mock_firestore_client():
    """Mock Firestore client for integration tests"""
    with patch('app.services.workflow_firestore.get_firestore_client') as mock_fs, \
         patch('app.services.library_firestore.get_firestore_client') as mock_lib_fs:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.collection.return_value = mock_collection
        mock_fs.return_value = mock_client
        mock_lib_fs.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_gcs_client(mock_gcs_bucket):
    """Mock GCS client"""
    client = MagicMock()
    client.bucket.return_value = mock_gcs_bucket
    return client

@pytest.fixture
def mock_vertex_response_image():
    """Mock successful Vertex AI image response"""
    return {
        "candidates": [{
            "content": {
                "parts": [{"inlineData": {"data": "base64encodedimagedata"}}]
            }
        }]
    }

@pytest.fixture
def mock_vertex_response_text():
    """Mock successful Vertex AI text response"""
    return {
        "candidates": [{
            "content": {
                "parts": [{"text": "Generated text response"}]
            }
        }]
    }

@pytest.fixture
def mock_vertex_response_video_started():
    """Mock video generation started"""
    return {"name": "projects/test/locations/us-central1/operations/op-123"}

@pytest.fixture
def mock_vertex_response_video_complete():
    """Mock video generation complete"""
    return {
        "done": True,
        "response": {
            "generateVideoResponse": {
                "generatedSamples": [{
                    "video": {"bytesBase64Encoded": "base64videodata"}
                }]
            }
        }
    }

@pytest.fixture
def mock_vertex_response_upscale():
    """Mock upscale response"""
    return {
        "predictions": [{
            "bytesBase64Encoded": "upscaledimagedata",
            "mimeType": "image/png"
        }]
    }