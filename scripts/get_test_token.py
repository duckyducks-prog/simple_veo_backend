import firebase_admin
from firebase_admin import auth, credentials
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase Admin
cred_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY', 'serviceAccountKey.json')

if os.path.exists(cred_path):
    cred = credentials.Certificate(cred_path)
    try:
        firebase_admin.initialize_app(cred)
    except ValueError:
        pass  # Already initialized
else:
    print(f"Error: Service account key file not found at '{cred_path}'")
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
    print("Error: FIREBASE_API_KEY not found")
    exit(1)

response = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={API_KEY}",
    json={"token": custom_token.decode(), "returnSecureToken": True}
)

if response.status_code == 200:
    print(response.json()["idToken"])
else:
    print(f"Error: {response.json()}")