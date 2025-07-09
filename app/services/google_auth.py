from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from app.config import settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_google_auth_flow() -> Flow:
    flow = Flow.from_client_config(
        {
            "installed": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    return flow


def get_auth_url(flow: Flow) -> str:
    auth_url, _ = flow.authorization_url(
        prompt='consent', access_type='offline', include_granted_scopes='true'
    )
    return auth_url


def fetch_tokens(flow: Flow, code: str) -> Credentials:
    flow.fetch_token(code=code)
    return flow.credentials


def build_credentials(
    access_token: str,
    refresh_token: str,
    expiry: str,
) -> Credentials:
    return Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    ) 