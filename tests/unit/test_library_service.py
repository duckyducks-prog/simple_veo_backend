import pytest
import json
import base64
from unittest.mock import MagicMock, patch
from app.services.library import LibraryService

@pytest.fixture
def mock_gcs_client():
    client = MagicMock()
    bucket = MagicMock()
    client.bucket.return_value = bucket
    return client, bucket

@pytest.fixture
def library_service(mock_gcs_client):
    client, _ = mock_gcs_client
    return LibraryService(gcs_client=client)

class TestSaveAsset:
    @pytest.mark.asyncio
    async def test_save_image(self, library_service, mock_gcs_client):
        """Save image creates blob and metadata"""
        _, bucket = mock_gcs_client
        blob = MagicMock()
        bucket.blob.return_value = blob
        
        # Base64 encoded "test"
        test_data = base64.b64encode(b"test image data").decode()
        
        result = await library_service.save_asset(
            data=test_data,
            asset_type="image",
            user_id="user-123",
            prompt="a puppy"
        )
        
        assert result.asset_type == "image"
        assert result.user_id == "user-123"
        assert result.prompt == "a puppy"
        assert "user-123/images/" in result.url
        assert blob.upload_from_string.call_count == 2  # file + metadata

    @pytest.mark.asyncio
    async def test_save_video(self, library_service, mock_gcs_client):
        """Save video uses mp4 extension"""
        _, bucket = mock_gcs_client
        blob = MagicMock()
        bucket.blob.return_value = blob
        
        test_data = base64.b64encode(b"video data").decode()
        
        result = await library_service.save_asset(
            data=test_data,
            asset_type="video",
            user_id="user-123"
        )
        
        assert result.asset_type == "video"
        assert result.mime_type == "video/mp4"

    @pytest.mark.asyncio
    async def test_invalid_asset_type_raises(self, library_service):
        """Invalid asset type raises ValueError"""
        with pytest.raises(ValueError, match="must be 'image' or 'video'"):
            await library_service.save_asset(
                data="data",
                asset_type="audio",
                user_id="user-123"
            )

    @pytest.mark.asyncio
    async def test_strips_base64_prefix(self, library_service, mock_gcs_client):
        """Data URL prefix is stripped"""
        _, bucket = mock_gcs_client
        blob = MagicMock()
        bucket.blob.return_value = blob
        
        raw_data = base64.b64encode(b"test").decode()
        prefixed_data = f"data:image/png;base64,{raw_data}"
        
        result = await library_service.save_asset(
            data=prefixed_data,
            asset_type="image",
            user_id="user-123"
        )
        
        assert result.id is not None

class TestListAssets:
    @pytest.mark.asyncio
    async def test_filters_by_user(self, library_service, mock_gcs_client):
        """Only returns assets for the specified user"""
        _, bucket = mock_gcs_client
        
        # Mock blobs with metadata
        blob1 = MagicMock()
        blob1.name = "metadata/asset-1.json"
        blob1.download_as_string.return_value = json.dumps({
            "id": "asset-1",
            "user_id": "user-123",
            "asset_type": "image",
            "prompt": "test",
            "created_at": "2024-01-01T00:00:00Z",
            "mime_type": "image/png",
            "blob_path": "users/user-123/images/asset-1.png"
        }).encode()
        
        blob2 = MagicMock()
        blob2.name = "metadata/asset-2.json"
        blob2.download_as_string.return_value = json.dumps({
            "id": "asset-2",
            "user_id": "other-user",
            "asset_type": "image",
            "prompt": "test",
            "created_at": "2024-01-01T00:00:00Z",
            "mime_type": "image/png",
            "blob_path": "users/other-user/images/asset-2.png"
        }).encode()
        
        bucket.list_blobs.return_value = [blob1, blob2]
        
        result = await library_service.list_assets(user_id="user-123")
        
        assert result.count == 1
        assert result.assets[0].id == "asset-1"

    @pytest.mark.asyncio
    async def test_filters_by_asset_type(self, library_service, mock_gcs_client):
        """Filters by asset type when specified"""
        _, bucket = mock_gcs_client
        
        blob1 = MagicMock()
        blob1.name = "metadata/asset-1.json"
        blob1.download_as_string.return_value = json.dumps({
            "id": "asset-1",
            "user_id": "user-123",
            "asset_type": "image",
            "prompt": "test",
            "created_at": "2024-01-01T00:00:00Z",
            "mime_type": "image/png",
            "blob_path": "users/user-123/images/asset-1.png"
        }).encode()
        
        blob2 = MagicMock()
        blob2.name = "metadata/asset-2.json"
        blob2.download_as_string.return_value = json.dumps({
            "id": "asset-2",
            "user_id": "user-123",
            "asset_type": "video",
            "prompt": "test",
            "created_at": "2024-01-01T00:00:00Z",
            "mime_type": "video/mp4",
            "blob_path": "users/user-123/videos/asset-2.mp4"
        }).encode()
        
        bucket.list_blobs.return_value = [blob1, blob2]
        
        result = await library_service.list_assets(user_id="user-123", asset_type="video")
        
        assert result.count == 1
        assert result.assets[0].asset_type == "video"

class TestDeleteAsset:
    @pytest.mark.asyncio
    async def test_delete_own_asset(self, library_service, mock_gcs_client):
        """User can delete their own asset"""
        _, bucket = mock_gcs_client
        
        meta_blob = MagicMock()
        meta_blob.exists.return_value = True
        meta_blob.download_as_string.return_value = json.dumps({
            "id": "asset-1",
            "user_id": "user-123",
            "blob_path": "users/user-123/images/asset-1.png"
        }).encode()
        
        asset_blob = MagicMock()
        asset_blob.exists.return_value = True
        
        bucket.blob.side_effect = lambda path: meta_blob if "metadata" in path else asset_blob
        
        result = await library_service.delete_asset(asset_id="asset-1", user_id="user-123")
        
        assert result["status"] == "deleted"
        meta_blob.delete.assert_called_once()
        asset_blob.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cannot_delete_others_asset(self, library_service, mock_gcs_client):
        """User cannot delete another user's asset"""
        _, bucket = mock_gcs_client
        
        meta_blob = MagicMock()
        meta_blob.exists.return_value = True
        meta_blob.download_as_string.return_value = json.dumps({
            "id": "asset-1",
            "user_id": "other-user",
            "blob_path": "users/other-user/images/asset-1.png"
        }).encode()
        
        bucket.blob.return_value = meta_blob
        
        with pytest.raises(PermissionError, match="Access denied"):
            await library_service.delete_asset(asset_id="asset-1", user_id="user-123")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_raises(self, library_service, mock_gcs_client):
        """Deleting nonexistent asset raises ValueError"""
        _, bucket = mock_gcs_client
        
        meta_blob = MagicMock()
        meta_blob.exists.return_value = False
        bucket.blob.return_value = meta_blob
        
        with pytest.raises(ValueError, match="Asset not found"):
            await library_service.delete_asset(asset_id="fake-id", user_id="user-123")

    @pytest.mark.asyncio
    async def test_get_asset_not_found(self, library_service, mock_gcs_client):
        """Getting nonexistent asset raises ValueError"""
        _, bucket = mock_gcs_client
        
        meta_blob = MagicMock()
        meta_blob.exists.return_value = False
        bucket.blob.return_value = meta_blob
        
        with pytest.raises(ValueError, match="Asset not found"):
            await library_service.get_asset(asset_id="fake-id", user_id="user-123")

    @pytest.mark.asyncio
    async def test_get_asset_permission_denied(self, library_service, mock_gcs_client):
        """Getting another user's asset raises PermissionError"""
        _, bucket = mock_gcs_client
        
        meta_blob = MagicMock()
        meta_blob.exists.return_value = True
        meta_blob.download_as_string.return_value = json.dumps({
            "id": "asset-1",
            "user_id": "other-user",
            "blob_path": "users/other-user/images/asset-1.png"
        }).encode()
        
        bucket.blob.return_value = meta_blob
        
        with pytest.raises(PermissionError, match="Access denied"):
            await library_service.get_asset(asset_id="asset-1", user_id="user-123")