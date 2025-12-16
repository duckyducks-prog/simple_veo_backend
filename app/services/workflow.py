from google.cloud import storage
from fastapi import HTTPException
from typing import List, Dict, Optional
import json
from datetime import datetime
import secrets
from app.config import settings
from app.logging_config import setup_logger

logger = setup_logger(__name__)


class WorkflowService:
    def __init__(self):
        self.storage_client = storage.Client()
        self.bucket_name = settings.workflows_bucket
        
    def _get_bucket(self):
        """Get the GCS bucket for workflows"""
        return self.storage_client.bucket(self.bucket_name)
    
    def _generate_workflow_id(self) -> str:
        """Generate a unique workflow ID"""
        timestamp = int(datetime.utcnow().timestamp())
        random_part = secrets.token_urlsafe(6)
        return f"wf_{timestamp}_{random_part}"
    
    def _load_index(self) -> Dict:
        """Load the workflow index from GCS"""
        try:
            bucket = self._get_bucket()
            blob = bucket.blob("workflows/metadata/index.json")
            
            if blob.exists():
                index_data = blob.download_as_text()
                return json.loads(index_data)
            return {}
        except Exception as e:
            logger.error(f"Failed to load workflow index: {str(e)}")
            return {}
    
    def _save_index(self, index: Dict):
        """Save the workflow index to GCS"""
        try:
            bucket = self._get_bucket()
            blob = bucket.blob("workflows/metadata/index.json")
            blob.upload_from_string(
                json.dumps(index, indent=2),
                content_type="application/json"
            )
        except Exception as e:
            logger.error(f"Failed to save workflow index: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to update workflow index")
    
    def _update_index(self, workflow_id: str, workflow: Dict):
        """Add or update a workflow entry in the index"""
        index = self._load_index()
        
        # Create metadata entry (exclude nodes and edges to keep index lightweight)
        index[workflow_id] = {
            k: v for k, v in workflow.items()
            if k not in ["nodes", "edges"]
        }
        
        self._save_index(index)
    
    def _remove_from_index(self, workflow_id: str):
        """Remove a workflow entry from the index"""
        index = self._load_index()
        
        if workflow_id in index:
            del index[workflow_id]
            self._save_index(index)
    
    def _load_workflow(self, workflow_id: str) -> Optional[Dict]:
        """Load a complete workflow from GCS"""
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(f"workflows/data/{workflow_id}.json")
            
            if not blob.exists():
                return None
            
            workflow_data = blob.download_as_text()
            return json.loads(workflow_data)
        except Exception as e:
            logger.error(f"Failed to load workflow {workflow_id}: {str(e)}")
            return None
    
    def _save_workflow(self, workflow_id: str, workflow: Dict):
        """Save a complete workflow to GCS"""
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(f"workflows/data/{workflow_id}.json")
            blob.upload_from_string(
                json.dumps(workflow, indent=2),
                content_type="application/json"
            )
        except Exception as e:
            logger.error(f"Failed to save workflow {workflow_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to save workflow")
    
    def _delete_workflow_file(self, workflow_id: str):
        """Delete a workflow file from GCS"""
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(f"workflows/data/{workflow_id}.json")
            
            if blob.exists():
                blob.delete()
        except Exception as e:
            logger.error(f"Failed to delete workflow {workflow_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to delete workflow")
    
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
        
        # Generate workflow ID
        workflow_id = self._generate_workflow_id()
        now = datetime.utcnow().isoformat() + "Z"
        
        # Create workflow object
        workflow = {
            "id": workflow_id,
            "name": name.strip(),
            "description": description.strip() if description else "",
            "is_public": is_public,
            "thumbnail": None,
            "created_at": now,
            "updated_at": now,
            "user_id": user_id,
            "user_email": user_email,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges
        }
        
        # Save to GCS
        self._save_workflow(workflow_id, workflow)
        
        # Update index
        self._update_index(workflow_id, workflow)
        
        logger.info(f"Created workflow {workflow_id} for user {user_email}")
        return workflow_id
    
    async def list_workflows(
        self,
        scope: str,
        user_id: str
    ) -> List[Dict]:
        """List workflows based on scope (my or public)"""
        index = self._load_index()
        
        # Filter workflows based on scope
        if scope == "my":
            filtered_ids = [
                wf_id for wf_id, metadata in index.items()
                if metadata.get("user_id") == user_id
            ]
        elif scope == "public":
            filtered_ids = [
                wf_id for wf_id, metadata in index.items()
                if metadata.get("is_public") is True
            ]
        else:
            raise HTTPException(status_code=400, detail="Invalid scope. Must be 'my' or 'public'")
        
        # Load full workflow data
        workflows = []
        for workflow_id in filtered_ids:
            workflow = self._load_workflow(workflow_id)
            if workflow:
                workflows.append(workflow)
        
        # Sort by updated_at (most recent first)
        workflows.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        logger.info(f"Listed {len(workflows)} workflows with scope '{scope}' for user {user_id}")
        return workflows
    
    async def get_workflow(
        self,
        workflow_id: str,
        user_id: str
    ) -> Dict:
        """Get a specific workflow by ID"""
        workflow = self._load_workflow(workflow_id)
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Check access: must be public OR owned by user
        if not (workflow.get("is_public") or workflow.get("user_id") == user_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        logger.info(f"Retrieved workflow {workflow_id} for user {user_id}")
        return workflow
    
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
        # Load existing workflow
        workflow = self._load_workflow(workflow_id)
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
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
        
        # Update workflow
        workflow.update({
            "name": name.strip(),
            "description": description.strip() if description else "",
            "is_public": is_public,
            "nodes": nodes,
            "edges": edges,
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "node_count": len(nodes),
            "edge_count": len(edges)
        })
        
        # Save updated workflow
        self._save_workflow(workflow_id, workflow)
        
        # Update index
        self._update_index(workflow_id, workflow)
        
        logger.info(f"Updated workflow {workflow_id} for user {user_id}")
        return workflow
    
    async def delete_workflow(
        self,
        workflow_id: str,
        user_id: str
    ):
        """Delete a workflow"""
        # Load existing workflow
        workflow = self._load_workflow(workflow_id)
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Check ownership
        if workflow.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="You can only delete your own workflows")
        
        # Delete workflow file
        self._delete_workflow_file(workflow_id)
        
        # Remove from index
        self._remove_from_index(workflow_id)
        
        logger.info(f"Deleted workflow {workflow_id} for user {user_id}")
    
    async def clone_workflow(
        self,
        workflow_id: str,
        user_id: str,
        user_email: str
    ) -> str:
        """Clone an existing workflow"""
        # Load original workflow
        original = self._load_workflow(workflow_id)
        
        if not original:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Check access: must be public OR owned by user
        if not (original.get("is_public") or original.get("user_id") == user_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Create new workflow
        new_workflow_id = self._generate_workflow_id()
        now = datetime.utcnow().isoformat() + "Z"
        
        cloned_workflow = {
            "id": new_workflow_id,
            "name": f"{original['name']} (Copy)",
            "description": original.get("description", ""),
            "is_public": False,  # Clones are always private
            "thumbnail": None,
            "created_at": now,
            "updated_at": now,
            "user_id": user_id,
            "user_email": user_email,
            "node_count": original.get("node_count", 0),
            "edge_count": original.get("edge_count", 0),
            "nodes": original.get("nodes", []),
            "edges": original.get("edges", [])
        }
        
        # Save cloned workflow
        self._save_workflow(new_workflow_id, cloned_workflow)
        
        # Update index
        self._update_index(new_workflow_id, cloned_workflow)
        
        logger.info(f"Cloned workflow {workflow_id} to {new_workflow_id} for user {user_email}")
        return new_workflow_id
