"""Test error handling in routers"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from app.routers.generation import generate_image, generate_video, generate_text, check_video_status, upscale_image
from app.routers.library import save_asset, list_assets, get_asset, delete_asset
from app.schemas import (
    ImageRequest, VideoRequest, TextRequest, StatusRequest, UpscaleRequest,
    SaveAssetRequest
)


class TestGenerationRouterErrors:
    @pytest.mark.asyncio
    async def test_generate_image_error(self):
        """Image generation error returns 500"""
        mock_service = AsyncMock()
        mock_service.generate_image.side_effect = Exception("API Error")
        
        user = {"uid": "user-123", "email": "test@test.com"}
        request = ImageRequest(prompt="test")
        
        with pytest.raises(HTTPException) as exc:
            await generate_image(request, user, mock_service)
        
        assert exc.value.status_code == 500
        assert "API Error" in exc.value.detail

    @pytest.mark.asyncio
    async def test_generate_video_error(self):
        """Video generation error returns 500"""
        mock_service = AsyncMock()
        mock_service.generate_video.side_effect = Exception("Video API Error")
        
        user = {"uid": "user-123", "email": "test@test.com"}
        request = VideoRequest(prompt="test video")
        
        with pytest.raises(HTTPException) as exc:
            await generate_video(request, user, mock_service)
        
        assert exc.value.status_code == 500
        assert "Video API Error" in exc.value.detail

    @pytest.mark.asyncio
    async def test_generate_text_error(self):
        """Text generation error returns 500"""
        mock_service = AsyncMock()
        mock_service.generate_text.side_effect = Exception("Text API Error")
        
        request = TextRequest(prompt="test text")
        
        with pytest.raises(HTTPException) as exc:
            await generate_text(request, mock_service)
        
        assert exc.value.status_code == 500
        assert "Text API Error" in exc.value.detail

    @pytest.mark.asyncio
    async def test_check_video_status_error(self):
        """Video status check error returns 500"""
        mock_service = AsyncMock()
        mock_service.check_video_status.side_effect = Exception("Status check failed")
        
        user = {"uid": "user-123", "email": "test@test.com"}
        request = StatusRequest(operation_name="operations/123")
        
        with pytest.raises(HTTPException) as exc:
            await check_video_status(request, user, mock_service)
        
        assert exc.value.status_code == 500
        assert "Status check failed" in exc.value.detail

    @pytest.mark.asyncio
    async def test_upscale_image_error(self):
        """Image upscale error returns 500"""
        mock_service = AsyncMock()
        mock_service.upscale_image.side_effect = Exception("Upscale failed")
        
        user = {"uid": "user-123", "email": "test@test.com"}
        request = UpscaleRequest(image="base64data")
        
        with pytest.raises(HTTPException) as exc:
            await upscale_image(request, user, mock_service)
        
        assert exc.value.status_code == 500
        assert "Upscale failed" in exc.value.detail


class TestLibraryRouterErrors:
    @pytest.mark.asyncio
    async def test_save_asset_value_error(self):
        """Save asset with invalid type returns 400"""
        mock_service = AsyncMock()
        mock_service.save_asset.side_effect = ValueError("Invalid asset type")
        
        user = {"uid": "user-123", "email": "test@test.com"}
        request = SaveAssetRequest(data="base64", asset_type="invalid")
        
        with pytest.raises(HTTPException) as exc:
            await save_asset(request, user, mock_service)
        
        assert exc.value.status_code == 400
        assert "Invalid asset type" in exc.value.detail

    @pytest.mark.asyncio
    async def test_save_asset_general_error(self):
        """Save asset general error returns 500"""
        mock_service = AsyncMock()
        mock_service.save_asset.side_effect = Exception("Storage error")
        
        user = {"uid": "user-123", "email": "test@test.com"}
        request = SaveAssetRequest(data="base64", asset_type="image")
        
        with pytest.raises(HTTPException) as exc:
            await save_asset(request, user, mock_service)
        
        assert exc.value.status_code == 500
        assert "Storage error" in exc.value.detail

    @pytest.mark.asyncio
    async def test_list_assets_error(self):
        """List assets error returns 500"""
        mock_service = AsyncMock()
        mock_service.list_assets.side_effect = Exception("List failed")
        
        user = {"uid": "user-123", "email": "test@test.com"}
        
        with pytest.raises(HTTPException) as exc:
            await list_assets(None, 50, user, mock_service)
        
        assert exc.value.status_code == 500
        assert "List failed" in exc.value.detail

    @pytest.mark.asyncio
    async def test_get_asset_not_found(self):
        """Get asset not found returns 404"""
        mock_service = AsyncMock()
        mock_service.get_asset.side_effect = ValueError("Asset not found")
        
        user = {"uid": "user-123", "email": "test@test.com"}
        
        with pytest.raises(HTTPException) as exc:
            await get_asset("asset-123", user, mock_service)
        
        assert exc.value.status_code == 404
        assert "Asset not found" in exc.value.detail

    @pytest.mark.asyncio
    async def test_get_asset_permission_denied(self):
        """Get asset permission denied returns 403"""
        mock_service = AsyncMock()
        mock_service.get_asset.side_effect = PermissionError("Access denied")
        
        user = {"uid": "user-123", "email": "test@test.com"}
        
        with pytest.raises(HTTPException) as exc:
            await get_asset("asset-456", user, mock_service)
        
        assert exc.value.status_code == 403
        assert "Access denied" in exc.value.detail

    @pytest.mark.asyncio
    async def test_get_asset_general_error(self):
        """Get asset general error returns 500"""
        mock_service = AsyncMock()
        mock_service.get_asset.side_effect = Exception("Database error")
        
        user = {"uid": "user-123", "email": "test@test.com"}
        
        with pytest.raises(HTTPException) as exc:
            await get_asset("asset-789", user, mock_service)
        
        assert exc.value.status_code == 500
        assert "Database error" in exc.value.detail

    @pytest.mark.asyncio
    async def test_delete_asset_not_found(self):
        """Delete asset not found returns 404"""
        mock_service = AsyncMock()
        mock_service.delete_asset.side_effect = ValueError("Asset not found")
        
        user = {"uid": "user-123", "email": "test@test.com"}
        
        with pytest.raises(HTTPException) as exc:
            await delete_asset("asset-123", user, mock_service)
        
        assert exc.value.status_code == 404
        assert "Asset not found" in exc.value.detail

    @pytest.mark.asyncio
    async def test_delete_asset_permission_denied(self):
        """Delete asset permission denied returns 403"""
        mock_service = AsyncMock()
        mock_service.delete_asset.side_effect = PermissionError("Not your asset")
        
        user = {"uid": "user-123", "email": "test@test.com"}
        
        with pytest.raises(HTTPException) as exc:
            await delete_asset("asset-456", user, mock_service)
        
        assert exc.value.status_code == 403
        assert "Not your asset" in exc.value.detail

    @pytest.mark.asyncio
    async def test_delete_asset_general_error(self):
        """Delete asset general error returns 500"""
        mock_service = AsyncMock()
        mock_service.delete_asset.side_effect = Exception("Delete failed")
        
        user = {"uid": "user-123", "email": "test@test.com"}
        
        with pytest.raises(HTTPException) as exc:
            await delete_asset("asset-789", user, mock_service)
        
        assert exc.value.status_code == 500
        assert "Delete failed" in exc.value.detail
