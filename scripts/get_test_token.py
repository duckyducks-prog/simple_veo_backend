import firebase_admin
from firebase_admin import auth, credentials
import requests
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add app directory to path for logging_config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.logging_config import setup_logger

logger = setup_logger(__name__)
load_dotenv()

# Initialize Firebase Admin
# Get project root directory (parent of scripts directory)
project_root = Path(__file__).parent.parent
default_key_path = project_root / 'serviceAccountKey.json'
cred_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY', str(default_key_path))

if os.path.exists(cred_path):
    cred = credentials.Certificate(cred_path)
    try:
        firebase_admin.initialize_app(cred)
    except ValueError:
        pass  # Already initialized
else:
    logger.error(f"Service account key file not found at '{cred_path}'")
    exit(1)

# Test user details - MUST match your allowed_emails
TEST_USER_UID = 'test-user-e2e'
TEST_USER_EMAIL = 'ldebortolialves@hubspot.com'

# Create custom token WITH email claim
custom_token = auth.create_custom_token(
    TEST_USER_UID,
    developer_claims={'email': TEST_USER_EMAIL}
)

# Exchange for ID token
API_KEY = os.environ.get('FIREBASE_API_KEY')
if not API_KEY:
    logger.error("FIREBASE_API_KEY not found in environment variables")
    exit(1)

response = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={API_KEY}",
    json={"token": custom_token.decode(), "returnSecureToken": True}
)

if response.status_code == 200:
    # Print to stdout for script output (not logging)
    print(response.json()["idToken"])
else:
    logger.error(f"Failed to exchange token: {response.json()}")
    exit(1)