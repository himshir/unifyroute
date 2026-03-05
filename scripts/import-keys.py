import argparse
import asyncio
import sys
import yaml
import json
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import LLMWay internals
from shared.database import async_session_maker
from shared.models import Credential, Provider
from shared.security import encrypt_secret

async def main():
    parser = argparse.ArgumentParser(description="Bulk import API keys into LLMWay.")
    parser.add_argument("file", help="Path to JSON or YAML file containing provider -> key mapping.")
    args = parser.parse_args()

    try:
        with open(args.file, "r") as f:
            if args.file.endswith(".yaml") or args.file.endswith(".yml"):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load file: {e}")
        sys.exit(1)

    if not isinstance(data, dict):
        print("❌ Invalid format. Expected a dictionary mapping provider names to API keys.")
        sys.exit(1)

    async with async_session_maker() as session:
        # Load all existing providers mapped by name
        res = await session.execute(select(Provider))
        providers = {p.name: p for p in res.scalars().all()}
        
        imported = 0
        skipped = 0

        for provider_name, api_key in data.items():
            if not isinstance(api_key, str) or not api_key.strip():
                print(f"⚠️  Skipping '{provider_name}': API key must be a non-empty string.")
                skipped += 1
                continue
                
            provider_name = provider_name.lower().strip()
            if provider_name not in providers:
                print(f"⚠️  Skipping '{provider_name}': Unknown provider. Check 'llmway get providers' (if implemented) or use standard names like 'openai', 'anthropic'.")
                skipped += 1
                continue
                
            provider = providers[provider_name]
            
            # Encrypt key
            secret_enc, iv = encrypt_secret(api_key.strip())
            
            # Check if an identical credential exists (by label or simply by provider)
            # We'll just create a new one with a distinct label indicating it was imported.
            label = f"{provider.display_name} (Bulk Imported)"
            
            cred = Credential(
                # id=uuid4() - handled by default
                provider_id=provider.id,
                label=label,
                auth_type="api_key",
                secret_enc=secret_enc,
                iv=iv,
                enabled=True
            )
            session.add(cred)
            imported += 1
            print(f"✅ Imported credential for {provider.display_name}")

        await session.commit()
        print(f"\n🎉 Done! Imported {imported} keys. Skipped {skipped}.")

if __name__ == "__main__":
    asyncio.run(main())
