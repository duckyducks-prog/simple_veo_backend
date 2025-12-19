import pytest
import os
import httpx

# Skip all E2E tests unless explicitly enabled
def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: mark test as end-to-end (requires real services)")

def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-e2e", default=False):
        skip_e2e = pytest.mark.skip(reason="E2E tests skipped. Use --run-e2e to run.")
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_e2e)

def pytest_addoption(parser):
    parser.addoption("--run-e2e", action="store_true", default=False, help="Run E2E tests")

@pytest.fixture(scope="session")
def api_base_url():
    """Base URL for API - use deployed or local"""
    return os.getenv("API_URL", "https://veo-api-otfo2ctxma-uc.a.run.app")

@pytest.fixture(scope="session")
def firebase_token():
    """
    Real Firebase token for testing.
    Set via environment variable or generate programmatically.
    """
    token = os.getenv("FIREBASE_TEST_TOKEN")
    if not token:
        pytest.skip("FIREBASE_TEST_TOKEN environment variable not set")
    return token

@pytest.fixture(scope="session")
def auth_headers(firebase_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {firebase_token}",
        "Content-Type": "application/json"
    }

@pytest.fixture(scope="session")
def http_client():
    """HTTP client for E2E tests"""
    with httpx.Client(timeout=120.0) as client:
        yield client

@pytest.fixture
def created_assets():
    """Track created assets for cleanup"""
    assets = []
    yield assets
    # Cleanup happens in test teardown

@pytest.fixture
def cleanup_asset(api_base_url, auth_headers, http_client):
    """Factory to cleanup assets after test"""
    asset_ids = []
    
    def _track(asset_id):
        asset_ids.append(asset_id)
        return asset_id
    
    yield _track
    
    # Cleanup
    for asset_id in asset_ids:
        try:
            http_client.delete(
                f"{api_base_url}/library/{asset_id}",
                headers=auth_headers
            )
        except Exception:
            pass  # Best effort cleanup

# ============== SEED DATA FIXTURES ==============

@pytest.fixture
def seed_values():
    """Predefined seed values for testing consistent generation"""
    return {
        "seed_1": 42,
        "seed_2": 12345,
        "seed_3": 999,
        "seed_4": 1,
        "seed_zero": 0,
    }

@pytest.fixture
def video_generation_with_seed():
    """Template for video generation with seed data"""
    def _create(seed=None, prompt="a simple test animation"):
        return {
            "prompt": prompt,
            "aspect_ratio": "16:9",
            "duration_seconds": 4,
            "generate_audio": True,
            "seed": seed
        }
    return _create

@pytest.fixture
def image_generation_with_seed():
    """Template for image generation with seed data"""
    def _create(seed=None, prompt="a simple test image"):
        return {
            "prompt": prompt,
            "aspect_ratio": "1:1",
            "seed": seed
        }
    return _create

@pytest.fixture
def library_asset_with_seed():
    """Template for creating library assets with seed metadata"""
    import base64
    # Create a minimal valid PNG (1x1 red pixel)
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
    )
    test_data = base64.b64encode(png_data).decode()
    
    def _create(seed=None, asset_type="image", prompt="test asset"):
        payload = {
            "data": test_data,
            "asset_type": asset_type,
            "prompt": prompt
        }
        if seed is not None:
            payload["seed"] = seed
        return payload
    
    return _create

@pytest.fixture
def workflow_with_seed_generation():
    """Template for workflow with seed data in generation nodes"""
    def _create(seed=None):
        workflow = {
            "name": "Seed Test Workflow",
            "description": "Testing seed data in workflow generation",
            "is_public": False,
            "nodes": [
                {
                    "id": "video-gen-1",
                    "type": "videoGeneration",
                    "position": {"x": 0, "y": 0},
                    "data": {
                        "prompt": "workflow test animation",
                        "duration_seconds": 4,
                        "aspect_ratio": "16:9"
                    }
                }
            ],
            "edges": []
        }
        # Add seed to node data if provided
        if seed is not None:
            workflow["nodes"][0]["data"]["seed"] = seed
        return workflow
    
    return _create