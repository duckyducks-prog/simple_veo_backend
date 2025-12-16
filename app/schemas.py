from pydantic import BaseModel, ConfigDict
from typing import Optional, List

# ============== REQUEST MODELS ==============

class ImageRequest(BaseModel):
    prompt: str
    reference_images: Optional[List[str]] = None
    aspect_ratio: Optional[str] = "1:1"
    resolution: Optional[str] = "1K"

class VideoRequest(BaseModel):
    prompt: str
    first_frame: Optional[str] = None
    last_frame: Optional[str] = None
    reference_images: Optional[List[str]] = None
    aspect_ratio: Optional[str] = "16:9"
    duration_seconds: Optional[int] = 8
    generate_audio: Optional[bool] = True

class TextRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    context: Optional[str] = None
    temperature: Optional[float] = 0.7

class StatusRequest(BaseModel):
    operation_name: str
    prompt: Optional[str] = None

class UpscaleRequest(BaseModel):
    image: str
    upscale_factor: Optional[str] = "x2"
    output_mime_type: Optional[str] = "image/png"

class SaveAssetRequest(BaseModel):
    data: str
    asset_type: str
    prompt: Optional[str] = None
    mime_type: Optional[str] = None

# ============== RESPONSE MODELS ==============

class ImageResponse(BaseModel):
    images: List[str]

class TextResponse(BaseModel):
    response: str

class UpscaleResponse(BaseModel):
    image: str
    mime_type: str

class AssetResponse(BaseModel):
    id: str
    url: str
    asset_type: str
    prompt: Optional[str] = None
    created_at: str
    mime_type: str
    user_id: Optional[str] = None

class VideoStatusResponse(BaseModel):
    status: str
    video_base64: Optional[str] = None
    storage_uri: Optional[str] = None
    progress: Optional[int] = None
    error: Optional[dict] = None
    message: Optional[str] = None

class LibraryResponse(BaseModel):
    assets: List[AssetResponse]
    count: int

# ============== WORKFLOW MODELS ==============

class WorkflowNode(BaseModel):
    model_config = ConfigDict(extra="allow")
    
    id: str
    type: str
    position: dict
    data: dict

class WorkflowEdge(BaseModel):
    model_config = ConfigDict(extra="allow")
    
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None

class SaveWorkflowRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    is_public: bool = False
    nodes: List[dict]  # Accept any dict to be flexible
    edges: List[dict]  # Accept any dict to be flexible

class UpdateWorkflowRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    is_public: bool = False
    nodes: List[dict]  # Accept any dict to be flexible
    edges: List[dict]  # Accept any dict to be flexible

class WorkflowResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    
    id: str
    name: str
    description: Optional[str] = ""
    is_public: bool
    thumbnail: Optional[str] = None
    created_at: str
    updated_at: str
    user_id: str
    user_email: str
    node_count: int
    edge_count: int
    nodes: List[dict]  # Flexible to accept any node structure
    edges: List[dict]  # Flexible to accept any edge structure

class WorkflowListResponse(BaseModel):
    workflows: List[WorkflowResponse]

class WorkflowIdResponse(BaseModel):
    id: str

class WorkflowMessageResponse(BaseModel):
    message: str