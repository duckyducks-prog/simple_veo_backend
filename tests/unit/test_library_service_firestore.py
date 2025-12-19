"""
Comprehensive tests for LibraryServiceFirestore
"""
import pytest
import base64
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@pytest.fixture
def mock_firestore_client():
    """Mock Firestore client"""
    with patch('app.services.library_firestore.get_firestore_client') as mock_get_client:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.collection.return_value = mock_collection
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_gcs():
    """Mock GCS client"""
    with patch('app.services.library_firestore.storage.Client') as mock_storage_class:
        mock_storage = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_storage_class.return_value = mock_storage
        yield mock_storage, mock_bucket, mock_blob


class TestLibraryServiceFirestoreSave:
    """Test asset saving"""
    
    async def test_save_image_success(self, mock_firestore_client, mock_gcs):
        """Test saving image asset"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        mock_storage, mock_bucket, mock_blob = mock_gcs
        mock_doc = MagicMock()
        mock_firestore_client.collection.return_value.document.return_value = mock_doc
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        
        # Simple 1x1 PNG base64
        image_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        result = await service.save_asset(
            data=image_data,
            asset_type="image",
            user_id="user123",
            prompt="Test image"
        )
        
        assert result.asset_type == "image"
        assert result.prompt == "Test image"
        assert result.id is not None
        mock_blob.upload_from_string.assert_called_once()
        mock_doc.set.assert_called_once()
    
    async def test_save_video_success(self, mock_firestore_client, mock_gcs):
        """Test saving video asset"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        mock_storage, mock_bucket, mock_blob = mock_gcs
        mock_doc = MagicMock()
        mock_firestore_client.collection.return_value.document.return_value = mock_doc
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        
        video_data = base64.b64encode(b"fake video data").decode()
        
        result = await service.save_asset(
            data=video_data,
            asset_type="video",
            user_id="user123",
            prompt="Test video",
            mime_type="video/mp4"
        )
        
        assert result.asset_type == "video"
        assert result.mime_type == "video/mp4"
        mock_blob.upload_from_string.assert_called_once()
    
    async def test_save_asset_strips_base64_prefix(self, mock_firestore_client, mock_gcs):
        """Test stripping data URL prefix"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        mock_storage, mock_bucket, mock_blob = mock_gcs
        mock_doc = MagicMock()
        mock_firestore_client.collection.return_value.document.return_value = mock_doc
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        
        # Data URL with prefix
        image_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        result = await service.save_asset(
            data=image_data,
            asset_type="image",
            user_id="user123"
        )
        
        assert result.id is not None
        mock_blob.upload_from_string.assert_called_once()
    
    async def test_save_asset_invalid_type(self, mock_firestore_client, mock_gcs):
        """Test invalid asset type raises error"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        mock_storage, _, _ = mock_gcs
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        
        with pytest.raises(ValueError, match="asset_type must be"):
            await service.save_asset(
                data="somedata",
                asset_type="invalid",
                user_id="user123"
            )
    
    async def test_save_asset_with_workflow_id(self, mock_firestore_client, mock_gcs):
        """Test saving asset with workflow reference"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        mock_storage, mock_bucket, mock_blob = mock_gcs
        mock_doc = MagicMock()
        mock_firestore_client.collection.return_value.document.return_value = mock_doc
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        
        image_data = base64.b64encode(b"test").decode()
        
        result = await service.save_asset(
            data=image_data,
            asset_type="image",
            user_id="user123",
            workflow_id="wf-123",
            source="generated"
        )
        
        assert result.id is not None
        # Verify workflow_id was included in Firestore doc
        call_args = mock_doc.set.call_args[0][0]
        assert call_args["workflow_id"] == "wf-123"
        assert call_args["source"] == "generated"


class TestLibraryServiceFirestoreList:
    """Test asset listing"""
    
    async def test_list_assets_empty(self, mock_firestore_client, mock_gcs):
        """Test listing with no assets"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        mock_storage, _, _ = mock_gcs
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_collection = mock_firestore_client.collection.return_value
        mock_collection.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        result = await service.list_assets(user_id="user123", limit=50)
        
        assert len(result.assets) == 0
        assert result.count == 0
    
    async def test_list_assets_with_results(self, mock_firestore_client, mock_gcs):
        """Test listing with assets"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        mock_storage, _, _ = mock_gcs
        
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            "id": "asset1",
            "user_id": "user123",
            "asset_type": "image",
            "blob_path": "users/user123/images/asset1.png",
            "mime_type": "image/png",
            "created_at": datetime.utcnow(),
            "prompt": "Test",
            "source": "generated"
        }
        
        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_doc]
        mock_collection = mock_firestore_client.collection.return_value
        mock_collection.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        result = await service.list_assets(user_id="user123", limit=50)
        
        assert len(result.assets) == 1
        assert result.assets[0].asset_type == "image"
        assert result.count == 1
    
    async def test_list_assets_filtered_by_type(self, mock_firestore_client, mock_gcs):
        """Test filtering by asset type"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        mock_storage, _, _ = mock_gcs
        
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            "id": "video1",
            "user_id": "user123",
            "asset_type": "video",
            "blob_path": "users/user123/videos/video1.mp4",
            "mime_type": "video/mp4",
            "created_at": datetime.utcnow(),
            "source": "generated"
        }
        
        mock_query = MagicMock()
        mock_query2 = MagicMock()
        mock_query2.stream.return_value = [mock_doc]
        mock_collection = mock_firestore_client.collection.return_value
        mock_collection.where.return_value = mock_query
        mock_query.where.return_value = mock_query2  # Chain the second where
        mock_query2.order_by.return_value = mock_query2
        mock_query2.limit.return_value = mock_query2
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        result = await service.list_assets(
            user_id="user123",
            asset_type="video",
            limit=50
        )
        
        assert len(result.assets) == 1
        assert result.assets[0].asset_type == "video"


class TestLibraryServiceFirestoreGet:
    """Test getting single asset"""
    
    async def test_get_asset_success(self, mock_firestore_client, mock_gcs):
        """Test getting asset by ID"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        mock_storage, _, _ = mock_gcs
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": "asset1",
            "user_id": "user123",
            "asset_type": "image",
            "blob_path": "users/user123/images/asset1.png",
            "mime_type": "image/png",
            "created_at": datetime.utcnow(),
            "prompt": "Test"
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        result = await service.get_asset(asset_id="asset1", user_id="user123")
        
        assert result.id == "asset1"
        assert result.asset_type == "image"
    
    async def test_get_asset_not_found(self, mock_firestore_client, mock_gcs):
        """Test asset not found"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        mock_storage, _, _ = mock_gcs
        
        mock_doc = MagicMock()
        mock_doc.exists = False
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        
        with pytest.raises(ValueError, match="not found"):
            await service.get_asset(asset_id="nonexistent", user_id="user123")
    
    async def test_get_asset_access_denied(self, mock_firestore_client, mock_gcs):
        """Test accessing other user's asset"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        mock_storage, _, _ = mock_gcs
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": "asset1",
            "user_id": "other-user",
            "asset_type": "image"
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        
        with pytest.raises(PermissionError, match="Access denied"):
            await service.get_asset(asset_id="asset1", user_id="user123")


class TestLibraryServiceFirestoreDelete:
    """Test asset deletion"""
    
    async def test_delete_asset_success(self, mock_firestore_client, mock_gcs):
        """Test deleting asset"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        mock_storage, mock_bucket, mock_blob = mock_gcs
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": "asset1",
            "user_id": "user123",
            "blob_path": "users/user123/images/asset1.png"
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        result = await service.delete_asset(asset_id="asset1", user_id="user123")
        
        assert result is not None
        mock_blob.delete.assert_called_once()
        mock_doc_ref.delete.assert_called_once()
    
    async def test_delete_asset_not_found(self, mock_firestore_client, mock_gcs):
        """Test deleting non-existent asset"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        mock_storage, _, _ = mock_gcs
        
        mock_doc = MagicMock()
        mock_doc.exists = False
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        
        with pytest.raises(ValueError, match="not found"):
            await service.delete_asset(asset_id="nonexistent", user_id="user123")
    
    async def test_delete_asset_access_denied(self, mock_firestore_client, mock_gcs):
        """Test deleting other user's asset"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        mock_storage, _, _ = mock_gcs
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": "asset1",
            "user_id": "other-user"
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        
        with pytest.raises(PermissionError, match="Access denied"):
            await service.delete_asset(asset_id="asset1", user_id="user123")


class TestLibraryServiceFirestoreURLResolution:
    """Test batch URL resolution"""
    
    async def test_resolve_asset_urls_batch(self, mock_firestore_client, mock_gcs):
        """Test resolving multiple asset URLs"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        mock_storage, _, _ = mock_gcs
        
        mock_doc1 = MagicMock()
        mock_doc1.exists = True
        mock_doc1.to_dict.return_value = {
            "id": "asset1",
            "blob_path": "users/user123/images/asset1.png",
            "asset_type": "image",
            "mime_type": "image/png"
        }
        
        mock_doc2 = MagicMock()
        mock_doc2.exists = True
        mock_doc2.to_dict.return_value = {
            "id": "asset2",
            "blob_path": "users/user123/images/asset2.png",
            "asset_type": "image",
            "mime_type": "image/png"
        }
        
        def mock_get(asset_id):
            if asset_id == "asset1":
                doc_ref = MagicMock()
                doc_ref.get.return_value = mock_doc1
                return doc_ref
            elif asset_id == "asset2":
                doc_ref = MagicMock()
                doc_ref.get.return_value = mock_doc2
                return doc_ref
        
        mock_firestore_client.collection.return_value.document = mock_get
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        
        result = await service.resolve_asset_urls(["asset1", "asset2"])
        
        assert len(result) == 2
        assert "asset1" in result
        assert "asset2" in result
        assert result["asset1"]["exists"] == True
        assert result["asset1"]["url"] is not None
        assert "genmediastudio-assets" in result["asset1"]["url"]
    
    async def test_resolve_asset_urls_missing_assets(self, mock_firestore_client, mock_gcs):
        """Test handling missing assets in batch"""
        from app.services.library_firestore import LibraryServiceFirestore
        
        mock_storage, _, _ = mock_gcs
        
        mock_doc = MagicMock()
        mock_doc.exists = False
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        service = LibraryServiceFirestore(gcs_client=mock_storage)
        
        result = await service.resolve_asset_urls(["missing1", "missing2"])
        
        # Missing assets return dict with exists: False
        assert len(result) == 2
        assert result["missing1"]["exists"] == False
        assert result["missing1"]["url"] is None
