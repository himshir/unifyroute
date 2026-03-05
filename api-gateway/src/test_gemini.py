import asyncio
import httpx
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import pprint

# Fake classes to let us parse the DB
from shared.database import engine, get_db_session
from shared.models import Credential, Provider
from shared.security import decrypt_secret

async def test():
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(
            select(Credential).join(Provider).where(Provider.name == "google-antigravity")
        )
        cred = result.scalars().first()
        if not cred:
            print("No google-antigravity credential found")
            return
            
        token = decrypt_secret(cred.secret_enc, cred.iv)
        print("Token summary:", token[:10] + "...")
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {token}",
                "x-goog-user-project": "700944069866" # Or something else? Let's just try without and read the error payload
            }
            resp = await client.get("https://generativelanguage.googleapis.com/v1beta/models", headers=headers)
            print("Response:", resp.status_code)
            print("Body:", resp.text)

asyncio.run(test())
