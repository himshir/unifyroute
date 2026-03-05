from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from uuid import UUID
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx
import logging

from shared.database import get_db_session, async_session_maker
from shared.models import Credential
from shared.security import decrypt_secret, encrypt_secret

logger = logging.getLogger("credential-vault")


async def refresh_oauth_tokens():
    """Background task: refresh OAuth2 tokens that expire within 15 minutes."""
    logger.info("Checking for expiring OAuth2 tokens...")
    now = datetime.now(timezone.utc)
    threshold = now + timedelta(minutes=15)

    async with async_session_maker() as session:
        stmt = select(Credential).where(
            Credential.auth_type == "oauth2",
            Credential.enabled == True,
            Credential.expires_at <= threshold
        )
        result = await session.execute(stmt)
        credentials = result.scalars().all()

        refreshed = 0
        failed = 0

        for cred in credentials:
            if not cred.oauth_meta:
                continue

            refresh_token_enc = cred.oauth_meta.get("refresh_token_enc")
            refresh_token_plain = cred.oauth_meta.get("refresh_token")

            # Prefer encrypted, fall back to plain (stored during initial OAuth callback)
            if refresh_token_enc:
                try:
                    refresh_token = decrypt_secret(refresh_token_enc.encode()
                                                   if isinstance(refresh_token_enc, str)
                                                   else refresh_token_enc)
                except Exception:
                    refresh_token = None
            else:
                refresh_token = refresh_token_plain

            if not refresh_token:
                logger.warning(f"No refresh token available for credential {cred.id} ({cred.label})")
                continue

            token_url = cred.oauth_meta.get("token_url") or cred.oauth_meta.get("token_endpoint")
            client_id = cred.oauth_meta.get("client_id")
            client_secret = cred.oauth_meta.get("client_secret")

            # Default to Google token URL (most common OAuth2 provider in this system)
            if not token_url:
                token_url = "https://oauth2.googleapis.com/token"

            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    payload: dict = {
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    }
                    if client_id:
                        payload["client_id"] = client_id
                    if client_secret:
                        payload["client_secret"] = client_secret

                    resp = await client.post(token_url, data=payload)

                if resp.status_code != 200:
                    logger.error(
                        f"Token refresh failed for {cred.id} ({cred.label}): "
                        f"HTTP {resp.status_code} — {resp.text[:200]}"
                    )
                    failed += 1
                    continue

                token_data = resp.json()
                new_access_token = token_data.get("access_token", "")
                expires_in = int(token_data.get("expires_in", 3600))
                new_refresh_token = token_data.get("refresh_token", refresh_token)  # some providers rotate it

                if not new_access_token:
                    logger.error(f"Empty access_token in refresh response for {cred.id}")
                    failed += 1
                    continue

                # Encrypt and persist
                new_secret_enc, new_iv = encrypt_secret(new_access_token)
                new_expires = now + timedelta(seconds=expires_in)

                # Update oauth_meta with new refresh token if rotated
                updated_meta = dict(cred.oauth_meta)
                if new_refresh_token != refresh_token:
                    updated_meta["refresh_token"] = new_refresh_token
                updated_meta["token_type"] = token_data.get("token_type", "Bearer")

                cred.secret_enc = new_secret_enc
                cred.iv = new_iv
                cred.expires_at = new_expires
                cred.oauth_meta = updated_meta

                logger.info(f"Refreshed token for credential {cred.id} ({cred.label}), expires at {new_expires}")
                refreshed += 1

            except Exception as exc:
                logger.error(f"Exception refreshing token for {cred.id}: {exc}")
                failed += 1

        if credentials:
            await session.commit()
            logger.info(f"Token refresh complete: {refreshed} refreshed, {failed} failed out of {len(credentials)} due.")
        else:
            logger.info("No tokens due for refresh.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # APScheduler runs the refresh loop every 10 minutes
    scheduler = AsyncIOScheduler()
    scheduler.add_job(refresh_oauth_tokens, "interval", minutes=10, id="oauth_refresh")
    scheduler.start()
    logger.info("Credential Vault started — OAuth refresh scheduler active (every 10 min).")
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Credential Vault", lifespan=lifespan)


@app.post("/internal/decrypt/{credential_id}")
async def decrypt_credential(
    credential_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """Internal API to decrypt a provider credential."""
    stmt = select(Credential).where(Credential.id == credential_id).where(Credential.enabled == True)
    result = await session.execute(stmt)
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found or disabled")

    try:
        plaintext = decrypt_secret(credential.secret_enc, credential.iv)
        return {"plaintext_secret": plaintext}
    except Exception:
        # Avoid exposing raw crypto errors or keys
        raise HTTPException(status_code=500, detail="Failed to decrypt credential")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("credential_vault.main:app", host="0.0.0.0", port=8001, reload=True)
