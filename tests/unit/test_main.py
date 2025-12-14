from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_app_has_routes():
    """App registers all expected routes"""
    routes = [route.path for route in app.routes]
    
    assert "/" in routes
    assert "/generate/image" in routes
    assert "/generate/video" in routes
    assert "/generate/text" in routes
    assert "/library" in routes

def test_health_endpoint():
    """Health check works on main app"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_cors_headers():
    """CORS headers are present"""
    response = client.options(
        "/generate/image",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST"
        }
    )
    assert response.status_code == 200