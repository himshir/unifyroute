import asyncio
import sys
from uuid import UUID

from shared.database import async_session_maker
from sqlalchemy import select
from shared.models import GatewayKey

async def main():
    if len(sys.argv) < 3:
        print("Usage: python update-key.py <key_id> <new_label>")
        sys.exit(1)
        
    try:
        key_id = UUID(sys.argv[1])
    except ValueError:
        print("Error: Invalid UUID format for key_id")
        sys.exit(1)
        
    new_label = sys.argv[2]
    
    async with async_session_maker() as session:
        result = await session.execute(select(GatewayKey).where(GatewayKey.id == key_id))
        key = result.scalar_one_or_none()
        
        if not key:
            print(f"Error: Gateway key with ID {key_id} not found.")
            sys.exit(1)
            
        old_label = key.label
        key.label = new_label
        await session.commit()
        
        print(f"Success! Updated key label from '{old_label}' to '{new_label}'.")

if __name__ == "__main__":
    asyncio.run(main())
