import os
import pytest

def test_default_settings():
    """Settings load with defaults"""
    from app.config import Settings
    s = Settings()
    assert s.project_id == "remarkablenotion"
    assert s.location == "us-central1"

def test_env_override(monkeypatch):
    """Environment variables override defaults"""
    monkeypatch.setenv("PROJECT_ID", "test-project")
    from app.config import Settings
    s = Settings()
    assert s.project_id == "test-project"

def test_allowed_emails_parsing(monkeypatch):
    """Comma-separated emails parsed correctly"""
    monkeypatch.setenv("ALLOWED_EMAILS", '["a@test.com","b@test.com"]')
    from app.config import Settings
    s = Settings()
    assert "a@test.com" in s.allowed_emails