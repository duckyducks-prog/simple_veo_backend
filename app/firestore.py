"""
Firestore client setup and utilities
"""
from firebase_admin import firestore
from app.auth import init_firebase
from app.logging_config import setup_logger

logger = setup_logger(__name__)

_firestore_client = None


def get_firestore_client():
    """Get or create Firestore client (singleton)"""
    global _firestore_client
    if _firestore_client is None:
        init_firebase()  # Ensure Firebase is initialized
        _firestore_client = firestore.client()
        logger.info("Firestore client initialized")
    return _firestore_client


# Collection names
WORKFLOWS_COLLECTION = "workflows"
ASSETS_COLLECTION = "assets"
