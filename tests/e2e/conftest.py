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
    return os.getenv("API_URL", "https://veo-api-82187245577.us-central1.run.app")

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