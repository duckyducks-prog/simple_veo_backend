import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from app.auth import verify_firebase_token, get_current_user, init_firebase


class TestInitFirebase:
    @patch("app.auth.firebase_admin.initialize_app")
    def test_init_firebase_first_time(self, mock_init):
        """First-time initialization succeeds"""
        import app.auth as auth_module
        auth_module._firebase_initialized = False
        
        init_firebase()
        
        mock_init.assert_called_once()
        assert auth_module._firebase_initialized is True

    @patch("app.auth.firebase_admin.initialize_app")
    def test_init_firebase_already_initialized(self, mock_init):
        """Already initialized Firebase doesn't reinitialize"""
        import app.auth as auth_module
        auth_module._firebase_initialized = True
        
        init_firebase()
        
        mock_init.assert_not_called()

    @patch("app.auth.firebase_admin.initialize_app")
    def test_init_firebase_value_error(self, mock_init):
        """ValueError from Firebase (already initialized externally) is handled"""
        import app.auth as auth_module
        auth_module._firebase_initialized = False
        mock_init.side_effect = ValueError("Already initialized")
        
        init_firebase()
        
        assert auth_module._firebase_initialized is True


class TestVerifyFirebaseToken:
    def test_missing_token_raises_401(self):
        """No token returns 401"""
        with pytest.raises(HTTPException) as exc:
            verify_firebase_token(None)
        assert exc.value.status_code == 401
        assert "No authorization token" in exc.value.detail

    def test_empty_token_raises_401(self):
        """Empty string returns 401"""
        with pytest.raises(HTTPException) as exc:
            verify_firebase_token("")
        assert exc.value.status_code == 401

    @patch("app.auth.firebase_auth.verify_id_token")
    @patch("app.auth.init_firebase")
    def test_valid_token_allowed_user(self, mock_init, mock_verify):
        """Valid token for whitelisted user returns user info"""
        mock_verify.return_value = {
            "uid": "user-123",
            "email": "ldebortolialves@hubspot.com"
        }
        
        result = verify_firebase_token("Bearer valid-token")
        
        assert result["uid"] == "user-123"
        assert result["email"] == "ldebortolialves@hubspot.com"

    @patch("app.auth.firebase_auth.verify_id_token")
    @patch("app.auth.init_firebase")
    def test_valid_token_unauthorized_user(self, mock_init, mock_verify):
        """Valid token for non-whitelisted user returns 403"""
        mock_verify.return_value = {
            "uid": "user-456",
            "email": "hacker@evil.com"
        }
        
        with pytest.raises(HTTPException) as exc:
            verify_firebase_token("Bearer valid-token")
        assert exc.value.status_code == 403
        assert "not authorized" in exc.value.detail

    @patch("app.auth.firebase_auth.verify_id_token")
    @patch("app.auth.init_firebase")
    def test_bearer_prefix_stripped(self, mock_init, mock_verify):
        """Bearer prefix is removed before verification"""
        mock_verify.return_value = {
            "uid": "user-123",
            "email": "ldebortolialves@hubspot.com"
        }
        
        verify_firebase_token("Bearer my-token")
        mock_verify.assert_called_once_with("my-token")

    @patch("app.auth.firebase_auth.verify_id_token")
    @patch("app.auth.init_firebase")
    def test_token_without_bearer_prefix(self, mock_init, mock_verify):
        """Token without Bearer prefix still works"""
        mock_verify.return_value = {
            "uid": "user-123",
            "email": "ldebortolialves@hubspot.com"
        }
        
        verify_firebase_token("raw-token")
        mock_verify.assert_called_once_with("raw-token")

    @patch("app.auth.firebase_auth.verify_id_token")
    @patch("app.auth.init_firebase")
    def test_email_case_insensitive(self, mock_init, mock_verify):
        """Email matching is case-insensitive"""
        mock_verify.return_value = {
            "uid": "user-123",
            "email": "LDEBORTOLIALVES@HUBSPOT.COM"
        }
        
        result = verify_firebase_token("Bearer token")
        assert result["email"] == "ldebortolialves@hubspot.com"

    @patch("app.auth.firebase_auth.verify_id_token")
    @patch("app.auth.init_firebase")
    def test_firebase_error_raises_401(self, mock_init, mock_verify):
        """Verification error returns 401"""
        mock_verify.side_effect = ValueError("Token validation failed")
        
        with pytest.raises(HTTPException) as exc:
            verify_firebase_token("Bearer invalid-token")
        assert exc.value.status_code == 401

    @patch("app.auth.firebase_auth.verify_id_token")
    @patch("app.auth.init_firebase")
    def test_unexpected_error_raises_401(self, mock_init, mock_verify):
        """Unexpected error returns 401"""
        mock_verify.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(HTTPException) as exc:
            verify_firebase_token("Bearer token")
        assert exc.value.status_code == 401
        assert "Token verification failed" in exc.value.detail


class TestGetCurrentUser:
    @pytest.mark.asyncio
    @patch("app.auth.verify_firebase_token")
    async def test_returns_user_info(self, mock_verify):
        """Dependency returns user info"""
        mock_verify.return_value = {"uid": "123", "email": "test@test.com"}
        
        result = await get_current_user("Bearer token")
        
        assert result["uid"] == "123"