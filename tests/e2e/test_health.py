import pytest

@pytest.mark.e2e
class TestHealthE2E:
    """E2E tests for health endpoint"""
    
    def test_health_check(self, api_base_url, http_client):
        """API is reachable and healthy"""
        response = http_client.get(f"{api_base_url}/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "project" in data
        assert "models" in data