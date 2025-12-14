from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    project_id: str = "remarkablenotion"
    location: str = "us-central1"
    gcs_bucket: str = "genmedia-assets-remarkablenotion"
    firebase_project_id: str = "genmediastudio"
    allowed_emails: list[str] = ["ldebortolialves@hubspot.com", "meganzinka@gmail.com"]
    
    # Firebase config (for testing)
    firebase_api_key: str = ""
    firebase_service_account_key: str = "serviceAccountKey.json"
    
    # Model names
    gemini_image_model: str = "gemini-3-pro-image-preview"
    gemini_text_model: str = "gemini-3-pro-preview"
    veo_model: str = "veo-3.1-generate-preview"
    upscale_model: str = "imagen-4.0-upscale-preview"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Or add this to ignore unknown env vars
    )

settings = Settings()