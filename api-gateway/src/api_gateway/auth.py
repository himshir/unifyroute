import os
import hashlib
import time
import jwt
from fastapi import Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database import get_db_session
from shared.models import GatewayKey
from router.quota import get_redis

# Extract from main.py
JWT_SECRET = os.environ.get("JWT_SECRET", "super-secret-default")
JWT_ALGORITHM = "HS256"

async def get_current_key(
    request: Request,
    session: AsyncSession = Depends(get_db_session)
) -> GatewayKey:
    """Auth middleware that handles Bearer token OR JWT cookie, with rate limiting."""
    
    auth_header = request.headers.get("Authorization")
    cookie_token = request.cookies.get("gateway_jwt")
    
    gateway_key = None
    
    if auth_header and auth_header.startswith("Bearer "):
        api_key = auth_header.split(" ")[1]
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        stmt = select(GatewayKey).where(GatewayKey.key_hash == key_hash, GatewayKey.enabled == True)
        result = await session.execute(stmt)
        gateway_key = result.scalar_one_or_none()
        if not gateway_key:
            raise HTTPException(status_code=401, detail="Invalid or disabled API key")
            
    elif cookie_token:
        # GUI Session Auth via HTTPOnly Cookie
        try:
            payload = jwt.decode(cookie_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            if payload.get("sub") == "admin":
                gateway_key = GatewayKey(id=None, label="Admin GUI Session", scopes=["admin"], enabled=True)
            else:
                raise HTTPException(status_code=401, detail="Invalid session token subject")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Session expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid session token")
    else:
        raise HTTPException(status_code=401, detail="Missing authorization")

    # Optional Rate Limiting (per-key)
    if gateway_key and getattr(gateway_key, 'rate_limit_rpm', None) is not None and gateway_key.id is not None:
        redis_client = await get_redis()
        current_minute = int(time.time() // 60)
        # Unique bucket per key per minute
        rl_key = f"rate_limit:{gateway_key.id}:{current_minute}"
        
        count = await redis_client.incr(rl_key)
        if count == 1:
            await redis_client.expire(rl_key, 60)
            
        if count > gateway_key.rate_limit_rpm:
            raise HTTPException(status_code=429, detail="API rate limit exceeded for this key")

    return gateway_key

async def require_admin_key(key: GatewayKey = Depends(get_current_key)) -> GatewayKey:
    """Auth middleware that additionally checks for admin scope."""
    if "admin" not in key.scopes:
        raise HTTPException(status_code=403, detail="Admin scope required")
    return key
