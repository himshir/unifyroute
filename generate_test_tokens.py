import asyncio
import secrets
import hashlib
import uuid
from shared.database import async_session_maker
from shared.models import GatewayKey

async def main():
    async with async_session_maker() as session:
        admin_id = uuid.uuid4()
        admin_raw = f"{admin_id}_ad_{secrets.token_urlsafe(32)}"
        admin_hash = hashlib.sha256(admin_raw.encode()).hexdigest()
        
        api_id = uuid.uuid4()
        api_raw = f"{api_id}_ap_{secrets.token_urlsafe(32)}"
        api_hash = hashlib.sha256(api_raw.encode()).hexdigest()
        
        admin_key = GatewayKey(id=admin_id, label="TestAdmin", key_hash=admin_hash, scopes=["admin"], enabled=True)
        api_key = GatewayKey(id=api_id, label="TestApi", key_hash=api_hash, scopes=["api"], enabled=True)
        
        session.add_all([admin_key, api_key])
        
        with open(".admin_token", "w") as f:
            f.write(f"{admin_raw}\n")
            
        with open(".api_token", "w") as f:
            f.write(f"{api_raw}\n")
            
        await session.commit()
        print("Tokens created!")

if __name__ == "__main__":
    asyncio.run(main())
