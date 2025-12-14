from fastapi import APIRouter
from app.config import settings

router = APIRouter()

@router.get("/")
def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "project": settings.project_id,
        "location": settings.location,
        "firebase_project": settings.firebase_project_id,
        "models": {
            "image": "Gemini 3 Pro Image",
            "video": "Veo 3.1",
            "text": "Gemini 3 Pro",
            "upscale": "Imagen 4.0 Upscale"
        }
    }