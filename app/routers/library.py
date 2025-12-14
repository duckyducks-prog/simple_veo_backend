from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from app.schemas import SaveAssetRequest, AssetResponse, LibraryResponse
from app.auth import get_current_user
from app.services.library import LibraryService

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
        return await service.save_asset(
            data=request.data,
            asset_type=request.asset_type,
            user_id=user["uid"],
            prompt=request.prompt,
            mime_type=request.mime_type
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
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
        return await service.list_assets(
            user_id=user["uid"],
            asset_type=asset_type,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    user: dict = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service)
):
    """Get a specific asset"""
    try:
        return await service.get_asset(asset_id=asset_id, user_id=user["uid"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    user: dict = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service)
):
    """Delete an asset"""
    try:
        return await service.delete_asset(asset_id=asset_id, user_id=user["uid"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))