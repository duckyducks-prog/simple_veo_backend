"""
Workflow service using Firestore for metadata and GCS for large assets
"""
from typing import List, Dict, Optional
from datetime import datetime
import secrets
from fastapi import HTTPException
from google.cloud.firestore_v1.base_query import FieldFilter
from app.firestore import get_firestore_client, WORKFLOWS_COLLECTION, ASSETS_COLLECTION
from app.config import settings
from app.logging_config import setup_logger

logger = setup_logger(__name__)


class WorkflowServiceFirestore:
    """
    Workflow service backed by Firestore.
    
    Schema:
    /workflows/{workflow_id}
        - id: string
        - name: string
        - description: string
        - user_id: string (indexed)
        - user_email: string
        - is_public: boolean (indexed)
        - created_at: datetime (indexed)
        - updated_at: datetime
        - thumbnail_ref: string (asset_id, optional)
        - node_count: number
        - edge_count: number
        - nodes: array (stored inline - typically < 100KB)
        - edges: array
    """
    
    def __init__(self):
        self.db = get_firestore_client()
        self.workflows_ref = self.db.collection(WORKFLOWS_COLLECTION)
        self.assets_ref = self.db.collection(ASSETS_COLLECTION)
    
    def _generate_workflow_id(self) -> str:
        """Generate a unique workflow ID"""
        timestamp = int(datetime.utcnow().timestamp())
        random_part = secrets.token_urlsafe(6)
        return f"wf_{timestamp}_{random_part}"
    
    def _resolve_asset_urls(self, nodes: List[Dict]) -> List[Dict]:
        """
        Resolve asset references to URLs in node data.
        Handles missing assets gracefully.
        """
        # Collect all asset refs from nodes
        asset_refs = set()
        for node in nodes:
            data = node.get("data", {})
            # Check common asset reference fields
            for key in ["assetRef", "imageRef", "videoRef"]:
                if key in data:
                    asset_refs.add(data[key])
            # Check outputs
            outputs = data.get("outputs", {})
            for key, value in outputs.items():
                if key.endswith("Ref") and isinstance(value, str):
                    asset_refs.add(value)
        
        if not asset_refs:
            return nodes
        
        # Batch fetch assets
        asset_map = {}
        for ref in asset_refs:
            try:
                doc = self.assets_ref.document(ref).get()
                if doc.exists:
                    asset_data = doc.to_dict()
                    asset_map[ref] = {
                        "url": f"https://storage.googleapis.com/{settings.gcs_bucket}/{asset_data.get('blob_path', '')}",
                        "exists": True,
                        "mime_type": asset_data.get("mime_type"),
                        "asset_type": asset_data.get("asset_type")
                    }
                else:
                    asset_map[ref] = {"url": None, "exists": False}
            except Exception as e:
                logger.warning(f"Failed to resolve asset {ref}: {e}")
                asset_map[ref] = {"url": None, "exists": False}
        
        # Inject resolved URLs into nodes
        resolved_nodes = []
        for node in nodes:
            node_copy = node.copy()
            data = node_copy.get("data", {}).copy()
            
            # Resolve main asset refs
            for key in ["assetRef", "imageRef", "videoRef"]:
                if key in data:
                    ref = data[key]
                    resolved = asset_map.get(ref, {"url": None, "exists": False})
                    url_key = key.replace("Ref", "Url")
                    data[url_key] = resolved["url"]
                    data[f"{key}Exists"] = resolved["exists"]
            
            # Resolve output refs
            if "outputs" in data:
                outputs = data["outputs"].copy()
                for key, value in list(outputs.items()):
                    if key.endswith("Ref") and isinstance(value, str):
                        resolved = asset_map.get(value, {"url": None, "exists": False})
                        url_key = key.replace("Ref", "Url")
                        outputs[url_key] = resolved["url"]
                        outputs[f"{key}Exists"] = resolved["exists"]
                data["outputs"] = outputs
            
            node_copy["data"] = data
            resolved_nodes.append(node_copy)
        
        return resolved_nodes
    
    async def create_workflow(
        self,
        name: str,
        description: str,
        is_public: bool,
        nodes: List[Dict],
        edges: List[Dict],
        user_id: str,
        user_email: str
    ) -> str:
        """Create a new workflow"""
        # Validate inputs
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Workflow name is required")
        
        if len(name) > 100:
            raise HTTPException(status_code=400, detail="Workflow name must be 100 characters or less")
        
        if len(nodes) == 0:
            raise HTTPException(status_code=400, detail="At least one node is required")
        
        if len(nodes) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 nodes allowed per workflow")
        
        workflow_id = self._generate_workflow_id()
        now = datetime.utcnow()
        
        workflow_data = {
            "id": workflow_id,
            "name": name.strip(),
            "description": description.strip() if description else "",
            "is_public": is_public,
            "thumbnail_ref": None,
            "created_at": now,
            "updated_at": now,
            "user_id": user_id,
            "user_email": user_email,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges
        }
        
        # Save to Firestore
        self.workflows_ref.document(workflow_id).set(workflow_data)
        
        logger.info(f"Created workflow {workflow_id} for user {user_id}")
        return workflow_id
    
    async def list_workflows(
        self,
        scope: str,
        user_id: str
    ) -> List[Dict]:
        """List workflows based on scope"""
        if scope not in ["my", "public"]:
            raise HTTPException(status_code=400, detail="Invalid scope. Must be 'my' or 'public'")
        
        if scope == "my":
            query = self.workflows_ref.where(filter=FieldFilter("user_id", "==", user_id))
        else:  # public
            query = self.workflows_ref.where(filter=FieldFilter("is_public", "==", True))
        
        # Order by created_at descending
        query = query.order_by("created_at", direction="DESCENDING")
        
        docs = query.stream()
        
        workflows = []
        for doc in docs:
            wf = doc.to_dict()
            # Don't resolve URLs for list view (too expensive)
            # Just return metadata without full nodes/edges
            workflows.append({
                "id": wf["id"],
                "name": wf["name"],
                "description": wf.get("description", ""),
                "is_public": wf.get("is_public", False),
                "thumbnail_ref": wf.get("thumbnail_ref"),
                "created_at": wf["created_at"].isoformat() if hasattr(wf["created_at"], 'isoformat') else wf["created_at"],
                "updated_at": wf["updated_at"].isoformat() if hasattr(wf["updated_at"], 'isoformat') else wf["updated_at"],
                "user_id": wf["user_id"],
                "user_email": wf.get("user_email", ""),
                "node_count": wf.get("node_count", 0),
                "edge_count": wf.get("edge_count", 0)
            })
        
        return workflows
    
    async def get_workflow(
        self,
        workflow_id: str,
        user_id: str
    ) -> Dict:
        """Get a workflow by ID with resolved asset URLs"""
        doc = self.workflows_ref.document(workflow_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        workflow = doc.to_dict()
        
        # Check access: must be owner or public
        if workflow.get("user_id") != user_id and not workflow.get("is_public"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Resolve asset URLs in nodes
        resolved_nodes = self._resolve_asset_urls(workflow.get("nodes", []))
        
        # Format timestamps
        created_at = workflow["created_at"]
        updated_at = workflow["updated_at"]
        
        return {
            "id": workflow["id"],
            "name": workflow["name"],
            "description": workflow.get("description", ""),
            "is_public": workflow.get("is_public", False),
            "thumbnail_ref": workflow.get("thumbnail_ref"),
            "created_at": created_at.isoformat() if hasattr(created_at, 'isoformat') else created_at,
            "updated_at": updated_at.isoformat() if hasattr(updated_at, 'isoformat') else updated_at,
            "user_id": workflow["user_id"],
            "user_email": workflow.get("user_email", ""),
            "node_count": workflow.get("node_count", 0),
            "edge_count": workflow.get("edge_count", 0),
            "nodes": resolved_nodes,
            "edges": workflow.get("edges", [])
        }
    
    async def update_workflow(
        self,
        workflow_id: str,
        name: str,
        description: str,
        is_public: bool,
        nodes: List[Dict],
        edges: List[Dict],
        user_id: str
    ) -> Dict:
        """Update an existing workflow"""
        doc_ref = self.workflows_ref.document(workflow_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        workflow = doc.to_dict()
        
        # Check ownership
        if workflow.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="You can only update your own workflows")
        
        # Validate inputs
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Workflow name is required")
        
        if len(name) > 100:
            raise HTTPException(status_code=400, detail="Workflow name must be 100 characters or less")
        
        if len(nodes) == 0:
            raise HTTPException(status_code=400, detail="At least one node is required")
        
        if len(nodes) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 nodes allowed per workflow")
        
        now = datetime.utcnow()
        
        update_data = {
            "name": name.strip(),
            "description": description.strip() if description else "",
            "is_public": is_public,
            "updated_at": now,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges
        }
        
        doc_ref.update(update_data)
        
        logger.info(f"Updated workflow {workflow_id} for user {user_id}")
        
        # Return updated workflow
        workflow.update(update_data)
        return workflow
    
    async def delete_workflow(
        self,
        workflow_id: str,
        user_id: str
    ):
        """Delete a workflow"""
        doc_ref = self.workflows_ref.document(workflow_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        workflow = doc.to_dict()
        
        # Check ownership
        if workflow.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="You can only delete your own workflows")
        
        # Delete the document (don't delete associated assets)
        doc_ref.delete()
        
        logger.info(f"Deleted workflow {workflow_id} for user {user_id}")
    
    async def clone_workflow(
        self,
        workflow_id: str,
        user_id: str,
        user_email: str
    ) -> str:
        """Clone an existing workflow"""
        doc = self.workflows_ref.document(workflow_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        original = doc.to_dict()
        
        # Check access: must be public OR owned by user
        if not (original.get("is_public") or original.get("user_id") == user_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Create new workflow
        new_workflow_id = self._generate_workflow_id()
        now = datetime.utcnow()
        
        cloned_workflow = {
            "id": new_workflow_id,
            "name": f"{original['name']} (Copy)",
            "description": original.get("description", ""),
            "is_public": False,  # Clones are always private
            "thumbnail_ref": None,
            "created_at": now,
            "updated_at": now,
            "user_id": user_id,
            "user_email": user_email,
            "node_count": original.get("node_count", 0),
            "edge_count": original.get("edge_count", 0),
            "nodes": original.get("nodes", []),  # Keep same asset refs (point to original assets)
            "edges": original.get("edges", [])
        }
        
        self.workflows_ref.document(new_workflow_id).set(cloned_workflow)
        
        logger.info(f"Cloned workflow {workflow_id} to {new_workflow_id} for user {user_id}")
        return new_workflow_id
