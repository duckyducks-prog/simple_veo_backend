from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from app.schemas import SaveAssetRequest, AssetResponse, LibraryResponse
from app.auth import get_current_user
from app.services.library import LibraryService
from app.logging_config import setup_logger

logger = setup_logger(__name__)
router = APIRouter()

def get_library_service() -> LibraryService:
    return LibraryService()

@router.post("/save", response_model=AssetResponse)
async def save_asset(
    request: SaveAssetRequest,
    user: dict = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service)
):
    """Save an asset to the library"""
    try:
        logger.info(f"Save asset request from user {user['email']}: {request.asset_type}")
        return await service.save_asset(
            data=request.data,
            asset_type=request.asset_type,
            user_id=user["uid"],
            prompt=request.prompt,
            mime_type=request.mime_type
        )
    except ValueError as e:
        logger.warning(f"Invalid asset save request from {user['email']}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Asset save failed for user {user['email']}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=LibraryResponse)
async def list_assets(
    asset_type: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service)
):
    """List assets for the authenticated user"""
    try:
        logger.info(f"List assets request from user {user['email']} (type={asset_type}, limit={limit})")
        return await service.list_assets(
            user_id=user["uid"],
            asset_type=asset_type,
            limit=limit
        )
    except Exception as e:
        logger.error(f"List assets failed for user {user['email']}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    user: dict = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service)
):
    """Get a specific asset"""
    try:
        logger.info(f"Get asset request from user {user['email']}: {asset_id}")
        return await service.get_asset(asset_id=asset_id, user_id=user["uid"])
    except ValueError as e:
        logger.warning(f"Asset not found for user {user['email']}: {asset_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        logger.warning(f"Permission denied for user {user['email']} accessing asset {asset_id}")
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Get asset failed for user {user['email']}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    user: dict = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service)
):
    """Delete an asset"""
    try:
        logger.info(f"Delete asset request from user {user['email']}: {asset_id}")
        result = await service.delete_asset(asset_id=asset_id, user_id=user["uid"])
        logger.info(f"Successfully deleted asset {asset_id} for user {user['email']}")
        return result
    except ValueError as e:
        logger.warning(f"Asset not found for deletion by user {user['email']}: {asset_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        logger.warning(f"Permission denied for user {user['email']} deleting asset {asset_id}")
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Delete asset failed for user {user['email']}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))