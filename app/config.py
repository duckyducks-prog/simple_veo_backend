from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import ClassVar

class Settings(BaseSettings):
    project_id: str = "genmediastudio"
    location: str = "us-central1"
    gcs_bucket: str = "genmediastudio-assets"  
    workflows_bucket: str = "genmediastudio-workflows"
    firebase_project_id: str = "genmediastudio"
    
    # Hardcoded, not from env
    ALLOWED_EMAILS: ClassVar[list[str]] = [
        "ldebortolialves@hubspot.com",
        "meganzinka@gmail.com",
        "sfiske@hubspot.com"
    ]
    
    # Firebase config (for testing)
    firebase_api_key: str = ""
    firebase_service_account_key: str = "serviceAccountKey.json"
    
    # Model names
    gemini_image_model: str = "gemini-2.5-flash-image"
    gemini_text_model: str = "gemini-2.5-flash" 
    veo_model: str = "veo-3.1-generate-preview"
    upscale_model: str = "imagen-4.0-upscale-preview"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()