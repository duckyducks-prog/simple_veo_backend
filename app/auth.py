import firebase_admin
from firebase_admin import auth as firebase_auth
from fastapi import HTTPException, Header
from typing import Optional
from app.config import settings

# Initialize Firebase Admin SDK
_firebase_initialized = False

def init_firebase():
    global _firebase_initialized
    if not _firebase_initialized:
        try:
            firebase_admin.initialize_app(options={
                'projectId': settings.firebase_project_id
            })
            _firebase_initialized = True
        except ValueError:
            _firebase_initialized = True  # Already initialized

def verify_firebase_token(authorization: Optional[str] = None) -> dict:
    """
    Verify Firebase ID token and return user info.
    Returns dict with 'uid' and 'email' if valid.
    Raises HTTPException if invalid.
    """
    init_firebase()
    
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization token provided")
    
    # Remove 'Bearer ' prefix if present
    token = authorization
    if token.startswith("Bearer "):
        token = token[7:]
    
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        user_email = decoded_token.get("email") or decoded_token.get("claims", {}).get("email") or ""
        user_email = user_email.lower().strip()
        user_id = decoded_token.get("uid")
        
        # Check whitelist
        allowed = [e.lower().strip() for e in settings.allowed_emails]
        if user_email not in allowed:
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied. User {user_email} not authorized."
            )
        
        return {"uid": user_id, "email": user_email}
    except firebase_admin.exceptions.FirebaseError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """FastAPI dependency for authenticated routes"""
    return verify_firebase_token(authorization)