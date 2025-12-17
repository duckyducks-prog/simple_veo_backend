import pytest

def test_default_settings():
    """Settings load with defaults"""
    from app.config import Settings
    s = Settings()
    assert s.project_id == "genmediastudio"
    assert s.location == "us-central1"

def test_env_override(monkeypatch):
    """Environment variables override defaults"""
    monkeypatch.setenv("PROJECT_ID", "test-project")
    from importlib import reload
    import app.config
    reload(app.config)
    from app.config import Settings
    s = Settings()
    assert s.project_id == "test-project"

def test_allowed_emails_is_class_var():
    """ALLOWED_EMAILS is a hardcoded class variable"""
    from app.config import Settings
    
    assert hasattr(Settings, 'ALLOWED_EMAILS')
    assert isinstance(Settings.ALLOWED_EMAILS, list)
    assert len(Settings.ALLOWED_EMAILS) > 0