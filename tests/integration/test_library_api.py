import pytest
import json
import base64
from unittest.mock import patch, MagicMock

class TestLibraryListAPI:
    """Integration tests for GET /library endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.get("/library")
        assert response.status_code == 401
    
    @patch("app.services.library.storage.Client")
    def test_returns_empty_list(self, mock_storage, client, mock_auth, mock_gcs_client):
        """Empty library returns empty list"""
        mock_storage.return_value = mock_gcs_client
        mock_gcs_client.bucket.return_value.list_blobs.return_value = []
        
        response = client.get("/library")
        
        assert response.status_code == 200
        data = response.json()
        assert data["assets"] == []
        assert data["count"] == 0
    
    @patch("app.services.library.storage.Client")
    def test_returns_user_assets_only(self, mock_storage, client, mock_auth, mock_gcs_bucket):
        """Only returns assets for authenticated user"""
        mock_storage.return_value.bucket.return_value = mock_gcs_bucket
        
        # Create mock blobs - one for user, one for other user
        user_blob = MagicMock()
        user_blob.name = "metadata/asset-1.json"
        user_blob.download_as_string.return_value = json.dumps({
            "id": "asset-1",
            "user_id": "test-user-123",
            "asset_type": "image",
            "prompt": "my image",
            "created_at": "2024-01-01T00:00:00Z",
            "mime_type": "image/png",
            "blob_path": "users/test-user-123/images/asset-1.png"
        }).encode()
        
        other_blob = MagicMock()
        other_blob.name = "metadata/asset-2.json"
        other_blob.download_as_string.return_value = json.dumps({
            "id": "asset-2",
            "user_id": "other-user",
            "asset_type": "image",
            "prompt": "their image",
            "created_at": "2024-01-01T00:00:00Z",
            "mime_type": "image/png",
            "blob_path": "users/other-user/images/asset-2.png"
        }).encode()
        
        mock_gcs_bucket.list_blobs.return_value = [user_blob, other_blob]
        
        response = client.get("/library")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["assets"][0]["id"] == "asset-1"
    
    @patch("app.services.library.storage.Client")
    def test_filters_by_asset_type(self, mock_storage, client, mock_auth, mock_gcs_bucket):
        """Filters by asset_type query param"""
        mock_storage.return_value.bucket.return_value = mock_gcs_bucket
        
        image_blob = MagicMock()
        image_blob.name = "metadata/img-1.json"
        image_blob.download_as_string.return_value = json.dumps({
            "id": "img-1",
            "user_id": "test-user-123",
            "asset_type": "image",
            "prompt": "an image",
            "created_at": "2024-01-01T00:00:00Z",
            "mime_type": "image/png",
            "blob_path": "users/test-user-123/images/img-1.png"
        }).encode()
        
        video_blob = MagicMock()
        video_blob.name = "metadata/vid-1.json"
        video_blob.download_as_string.return_value = json.dumps({
            "id": "vid-1",
            "user_id": "test-user-123",
            "asset_type": "video",
            "prompt": "a video",
            "created_at": "2024-01-01T00:00:00Z",
            "mime_type": "video/mp4",
            "blob_path": "users/test-user-123/videos/vid-1.mp4"
        }).encode()
        
        mock_gcs_bucket.list_blobs.return_value = [image_blob, video_blob]
        
        response = client.get("/library?asset_type=video")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["assets"][0]["asset_type"] == "video"


class TestLibrarySaveAPI:
    """Integration tests for POST /library/save endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.post("/library/save", json={
            "data": "base64data",
            "asset_type": "image"
        })
        assert response.status_code == 401
    
    @patch("app.services.library.storage.Client")
    def test_saves_image(self, mock_storage, client, mock_auth, mock_gcs_client):
        """Successfully saves an image"""
        mock_storage.return_value = mock_gcs_client
        
        test_data = base64.b64encode(b"fake image data").decode()
        
        response = client.post("/library/save", json={
            "data": test_data,
            "asset_type": "image",
            "prompt": "a test image"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["asset_type"] == "image"
        assert data["prompt"] == "a test image"
        assert data["user_id"] == "test-user-123"
        assert "id" in data
        assert "url" in data
    
    @patch("app.services.library.storage.Client")
    def test_saves_video(self, mock_storage, client, mock_auth, mock_gcs_client):
        """Successfully saves a video"""
        mock_storage.return_value = mock_gcs_client
        
        test_data = base64.b64encode(b"fake video data").decode()
        
        response = client.post("/library/save", json={
            "data": test_data,
            "asset_type": "video",
            "prompt": "a test video"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["asset_type"] == "video"
        assert data["mime_type"] == "video/mp4"
    
    @patch("app.services.library.storage.Client")
    def test_invalid_asset_type(self, mock_storage, client, mock_auth, mock_gcs_client):
        """Invalid asset type returns 400"""
        mock_storage.return_value = mock_gcs_client
        
        response = client.post("/library/save", json={
            "data": "base64data",
            "asset_type": "audio"
        })
        
        assert response.status_code == 400
        assert "must be 'image' or 'video'" in response.json()["detail"]


class TestLibraryGetAPI:
    """Integration tests for GET /library/{asset_id} endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.get("/library/asset-123")
        assert response.status_code == 401
    
    @patch("app.services.library.storage.Client")
    def test_returns_own_asset(self, mock_storage, client, mock_auth, mock_gcs_bucket):
        """Returns asset owned by user"""
        mock_storage.return_value.bucket.return_value = mock_gcs_bucket
        
        meta_blob = MagicMock()
        meta_blob.exists.return_value = True
        meta_blob.download_as_string.return_value = json.dumps({
            "id": "asset-123",
            "user_id": "test-user-123",
            "asset_type": "image",
            "prompt": "my image",
            "created_at": "2024-01-01T00:00:00Z",
            "mime_type": "image/png",
            "blob_path": "users/test-user-123/images/asset-123.png"
        }).encode()
        
        mock_gcs_bucket.blob.return_value = meta_blob
        
        response = client.get("/library/asset-123")
        
        assert response.status_code == 200
        assert response.json()["id"] == "asset-123"
    
    @patch("app.services.library.storage.Client")
    def test_cannot_access_others_asset(self, mock_storage, client, mock_auth, mock_gcs_bucket):
        """Cannot access asset owned by another user"""
        mock_storage.return_value.bucket.return_value = mock_gcs_bucket
        
        meta_blob = MagicMock()
        meta_blob.exists.return_value = True
        meta_blob.download_as_string.return_value = json.dumps({
            "id": "asset-456",
            "user_id": "other-user",
            "asset_type": "image",
            "prompt": "their image",
            "created_at": "2024-01-01T00:00:00Z",
            "mime_type": "image/png",
            "blob_path": "users/other-user/images/asset-456.png"
        }).encode()
        
        mock_gcs_bucket.blob.return_value = meta_blob
        
        response = client.get("/library/asset-456")
        
        assert response.status_code == 403
    
    @patch("app.services.library.storage.Client")
    def test_not_found(self, mock_storage, client, mock_auth, mock_gcs_bucket):
        """Non-existent asset returns 404"""
        mock_storage.return_value.bucket.return_value = mock_gcs_bucket
        
        meta_blob = MagicMock()
        meta_blob.exists.return_value = False
        mock_gcs_bucket.blob.return_value = meta_blob
        
        response = client.get("/library/fake-id")
        
        assert response.status_code == 404


class TestLibraryDeleteAPI:
    """Integration tests for DELETE /library/{asset_id} endpoint"""
    
    def test_requires_authentication(self, client):
        """Request without auth returns 401"""
        response = client.delete("/library/asset-123")
        assert response.status_code == 401
    
    @patch("app.services.library.storage.Client")
    def test_deletes_own_asset(self, mock_storage, client, mock_auth, mock_gcs_bucket):
        """Can delete own asset"""
        mock_storage.return_value.bucket.return_value = mock_gcs_bucket
        
        meta_blob = MagicMock()
        meta_blob.exists.return_value = True
        meta_blob.download_as_string.return_value = json.dumps({
            "id": "asset-123",
            "user_id": "test-user-123",
            "blob_path": "users/test-user-123/images/asset-123.png"
        }).encode()
        
        asset_blob = MagicMock()
        asset_blob.exists.return_value = True
        
        mock_gcs_bucket.blob.side_effect = lambda path: meta_blob if "metadata" in path else asset_blob
        
        response = client.delete("/library/asset-123")
        
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
        meta_blob.delete.assert_called_once()
        asset_blob.delete.assert_called_once()
    
    @patch("app.services.library.storage.Client")
    def test_cannot_delete_others_asset(self, mock_storage, client, mock_auth, mock_gcs_bucket):
        """Cannot delete asset owned by another user"""
        mock_storage.return_value.bucket.return_value = mock_gcs_bucket
        
        meta_blob = MagicMock()
        meta_blob.exists.return_value = True
        meta_blob.download_as_string.return_value = json.dumps({
            "id": "asset-456",
            "user_id": "other-user",
            "blob_path": "users/other-user/images/asset-456.png"
        }).encode()
        
        mock_gcs_bucket.blob.return_value = meta_blob
        
        response = client.delete("/library/asset-456")
        
        assert response.status_code == 403