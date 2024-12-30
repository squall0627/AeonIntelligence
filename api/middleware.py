from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from api.auth.oauth2 import verify_token

security = HTTPBearer()


async def auth_middleware(
    request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Middleware to verify JWT token for protected routes
    """
    if not credentials:
        raise HTTPException(status_code=403, detail="Invalid authentication scheme.")

    token = credentials.credentials
    if not verify_token(token):
        raise HTTPException(status_code=403, detail="Invalid token or expired token.")

    return credentials
