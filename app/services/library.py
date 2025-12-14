import json
import uuid
import base64
from datetime import datetime
from typing import Optional, List
from google.cloud import storage
from app.config import settings
from app.schemas import AssetResponse, LibraryResponse

class LibraryService:
    def __init__(self, gcs_client: Optional[storage.Client] = None):
        self.client = gcs_client or storage.Client()
        self.bucket = self.client.bucket(settings.gcs_bucket)
    
    def _generate_asset_id(self) -> str:
        return str(uuid.uuid4())
    
    def _get_timestamp(self) -> str:
        return datetime.utcnow().isoformat() + "Z"
    
    def _strip_base64_prefix(self, data: str) -> str:
        """Remove data URL prefix if present"""
        if data and ',' in data and data.startswith('data:'):
            return data.split(',', 1)[1]
        return data

    async def save_asset(
        self,
        data: str,
        asset_type: str,
        user_id: str,
        prompt: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> AssetResponse:
        """Save an image or video to the asset library"""
        asset_id = self._generate_asset_id()
        timestamp = self._get_timestamp()
        
        # Determine file extension and mime type
        if asset_type == "image":
            ext = "png" if not mime_type or "png" in mime_type else "jpg"
            mime_type = mime_type or "image/png"
        elif asset_type == "video":
            ext = "mp4"
            mime_type = mime_type or "video/mp4"
        else:
            raise ValueError("asset_type must be 'image' or 'video'")
        
        # Create blob path
        blob_path = f"users/{user_id}/{asset_type}s/{asset_id}.{ext}"
        
        # Decode and upload
        clean_data = self._strip_base64_prefix(data)
        file_bytes = base64.b64decode(clean_data)
        
        blob = self.bucket.blob(blob_path)
        blob.upload_from_string(file_bytes, content_type=mime_type)
        
        # Save metadata
        metadata = {
            "id": asset_id,
            "asset_type": asset_type,
            "prompt": prompt,
            "created_at": timestamp,
            "mime_type": mime_type,
            "blob_path": blob_path,
            "user_id": user_id
        }
        
        meta_blob = self.bucket.blob(f"metadata/{asset_id}.json")
        meta_blob.upload_from_string(json.dumps(metadata), content_type="application/json")
        
        url = f"https://storage.googleapis.com/{settings.gcs_bucket}/{blob_path}"
        
        return AssetResponse(
            id=asset_id,
            url=url,
            asset_type=asset_type,
            prompt=prompt,
            created_at=timestamp,
            mime_type=mime_type,
            user_id=user_id
        )

    async def list_assets(
        self,
        user_id: str,
        asset_type: Optional[str] = None,
        limit: int = 50
    ) -> LibraryResponse:
        """List assets for a user"""
        blobs = self.bucket.list_blobs(prefix="metadata/")
        
        assets = []
        for blob in blobs:
            if not blob.name.endswith(".json"):
                continue
            
            metadata = json.loads(blob.download_as_string())
            
            # Filter by user
            if metadata.get("user_id") != user_id:
                continue
            
            # Filter by type if specified
            if asset_type and metadata.get("asset_type") != asset_type:
                continue
            
            # Build URL
            blob_path = metadata["blob_path"]
            metadata["url"] = f"https://storage.googleapis.com/{settings.gcs_bucket}/{blob_path}"
            assets.append(AssetResponse(**metadata))
            
            if len(assets) >= limit:
                break
        
        # Sort newest first
        assets.sort(key=lambda x: x.created_at, reverse=True)
        
        return LibraryResponse(assets=assets, count=len(assets))

    async def get_asset(self, asset_id: str, user_id: str) -> AssetResponse:
        """Get a specific asset by ID"""
        meta_blob = self.bucket.blob(f"metadata/{asset_id}.json")
        
        if not meta_blob.exists():
            raise ValueError("Asset not found")
        
        metadata = json.loads(meta_blob.download_as_string())
        
        # Check ownership
        if metadata.get("user_id") != user_id:
            raise PermissionError("Access denied")
        
        blob_path = metadata["blob_path"]
        metadata["url"] = f"https://storage.googleapis.com/{settings.gcs_bucket}/{blob_path}"
        
        return AssetResponse(**metadata)

    async def delete_asset(self, asset_id: str, user_id: str) -> dict:
        """Delete an asset"""
        meta_blob = self.bucket.blob(f"metadata/{asset_id}.json")
        
        if not meta_blob.exists():
            raise ValueError("Asset not found")
        
        metadata = json.loads(meta_blob.download_as_string())
        
        # Check ownership
        if metadata.get("user_id") != user_id:
            raise PermissionError("Access denied. You can only delete your own assets.")
        
        # Delete asset file
        asset_blob = self.bucket.blob(metadata["blob_path"])
        if asset_blob.exists():
            asset_blob.delete()
        
        # Delete metadata
        meta_blob.delete()
        
        return {"status": "deleted", "id": asset_id}