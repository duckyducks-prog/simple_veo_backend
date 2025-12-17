from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas import (
    SaveWorkflowRequest,
    UpdateWorkflowRequest,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowIdResponse,
    WorkflowMessageResponse
)
from app.auth import get_current_user
from app.services.workflow_firestore import WorkflowServiceFirestore
from app.logging_config import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


def get_workflow_service() -> WorkflowServiceFirestore:
    return WorkflowServiceFirestore()


@router.post("/save", response_model=WorkflowIdResponse)
async def save_workflow(
    request: SaveWorkflowRequest,
    user: dict = Depends(get_current_user),
    service: WorkflowServiceFirestore = Depends(get_workflow_service)
):
    """
    Create a new workflow.
    
    **Request Body:**
    - name: Workflow name (required, max 100 characters)
    - description: Workflow description (optional)
    - is_public: Whether the workflow is public (default: false)
    - nodes: List of workflow nodes (required, min 1, max 100)
    - edges: List of workflow edges (optional)
    
    **Returns:**
    - id: The unique workflow ID
    """
    try:
        logger.info(f"Save workflow request from user {user['email']}: {request.name}")
        
        workflow_id = await service.create_workflow(
            name=request.name,
            description=request.description or "",
            is_public=request.is_public,
            nodes=request.nodes,
            edges=request.edges,
            user_id=user["uid"],
            user_email=user["email"]
        )
        
        return {"id": workflow_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save workflow for user {user['email']}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save workflow: {str(e)}")


@router.get("")
async def list_workflows(
    scope: str = Query(..., description="Filter scope: 'my' or 'public'"),
    user: dict = Depends(get_current_user),
    service: WorkflowServiceFirestore = Depends(get_workflow_service)
):
    """
    List workflows based on scope.
    
    **Query Parameters:**
    - scope: 'my' to list user's workflows, 'public' to list all public workflows
    
    **Returns:**
    - workflows: List of workflow objects
    """
    try:
        logger.info(f"List workflows request from user {user['email']} with scope: {scope}")
        
        workflows = await service.list_workflows(
            scope=scope,
            user_id=user["uid"]
        )
        
        # Log details about returned workflows for debugging
        for wf in workflows:
            logger.info(f"Returning workflow {wf.get('id')}: {wf.get('name')} with {len(wf.get('nodes', []))} nodes, {len(wf.get('edges', []))} edges")
        
        return {"workflows": workflows}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list workflows for user {user['email']}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    user: dict = Depends(get_current_user),
    service: WorkflowServiceFirestore = Depends(get_workflow_service)
):
    """
    Get a specific workflow by ID.
    
    **Path Parameters:**
    - workflow_id: The unique workflow ID
    
    **Returns:**
    - Complete workflow object with all nodes and edges
    
    **Access Control:**
    - Must be the owner OR the workflow must be public
    """
    try:
        logger.info(f"Get workflow request from user {user['email']}: {workflow_id}")
        
        workflow = await service.get_workflow(
            workflow_id=workflow_id,
            user_id=user["uid"]
        )
        
        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow {workflow_id} for user {user['email']}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow: {str(e)}")


@router.put("/{workflow_id}", response_model=WorkflowMessageResponse)
async def update_workflow(
    workflow_id: str,
    request: UpdateWorkflowRequest,
    user: dict = Depends(get_current_user),
    service: WorkflowServiceFirestore = Depends(get_workflow_service)
):
    """
    Update an existing workflow.
    
    **Path Parameters:**
    - workflow_id: The unique workflow ID
    
    **Request Body:**
    - name: Workflow name (required, max 100 characters)
    - description: Workflow description (optional)
    - is_public: Whether the workflow is public
    - nodes: List of workflow nodes (required, min 1, max 100)
    - edges: List of workflow edges (optional)
    
    **Returns:**
    - message: Success message
    
    **Access Control:**
    - Must be the owner of the workflow
    """
    try:
        logger.info(f"Update workflow request from user {user['email']}: {workflow_id}")
        
        await service.update_workflow(
            workflow_id=workflow_id,
            name=request.name,
            description=request.description or "",
            is_public=request.is_public,
            nodes=request.nodes,
            edges=request.edges,
            user_id=user["uid"]
        )
        
        return {"message": "Workflow updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update workflow {workflow_id} for user {user['email']}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update workflow: {str(e)}")


@router.delete("/{workflow_id}", response_model=WorkflowMessageResponse)
async def delete_workflow(
    workflow_id: str,
    user: dict = Depends(get_current_user),
    service: WorkflowServiceFirestore = Depends(get_workflow_service)
):
    """
    Delete a workflow.
    
    **Path Parameters:**
    - workflow_id: The unique workflow ID
    
    **Returns:**
    - message: Success message
    
    **Access Control:**
    - Must be the owner of the workflow
    """
    try:
        logger.info(f"Delete workflow request from user {user['email']}: {workflow_id}")
        
        await service.delete_workflow(
            workflow_id=workflow_id,
            user_id=user["uid"]
        )
        
        return {"message": "Workflow deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workflow {workflow_id} for user {user['email']}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete workflow: {str(e)}")


@router.post("/{workflow_id}/clone", response_model=WorkflowIdResponse)
async def clone_workflow(
    workflow_id: str,
    user: dict = Depends(get_current_user),
    service: WorkflowServiceFirestore = Depends(get_workflow_service)
):
    """
    Clone an existing workflow.
    
    **Path Parameters:**
    - workflow_id: The unique workflow ID to clone
    
    **Returns:**
    - id: The new workflow ID
    
    **Behavior:**
    - Creates a copy with name "{original_name} (Copy)"
    - New workflow is always private (is_public = false)
    - New workflow is owned by the current user
    
    **Access Control:**
    - Must be the owner OR the workflow must be public
    """
    try:
        logger.info(f"Clone workflow request from user {user['email']}: {workflow_id}")
        
        new_workflow_id = await service.clone_workflow(
            workflow_id=workflow_id,
            user_id=user["uid"],
            user_email=user["email"]
        )
        
        return {"id": new_workflow_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clone workflow {workflow_id} for user {user['email']}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clone workflow: {str(e)}")
