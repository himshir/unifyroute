import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from shared.models import GatewayKey

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed():
    engine = create_async_engine("sqlite+aiosqlite:///llmway.db")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Create an admin token
        admin_token_hash = pwd_context.hash("admin-token-123")
        admin_key = GatewayKey(
            label="test_admin",
            key_hash=admin_token_hash,
            raw_token="admin-token-123",
            scopes=["admin"],
            enabled=True
        )
        
        # Create an api token
        api_token_hash = pwd_context.hash("api-token-123")
        api_key = GatewayKey(
            label="test_api",
            key_hash=api_token_hash,
            raw_token="api-token-123",
            scopes=["api"],
            enabled=True
        )
        
        session.add(admin_key)
        session.add(api_key)
        await session.commit()
    print("Tokens seeded!")

asyncio.run(seed())
