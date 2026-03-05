import asyncio
import httpx
import uuid

async def main():
    admin_token = open(".admin_token-raw").read().split("RAW TOKEN:\n")[1].split("\n=")[0].strip()
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    async with httpx.AsyncClient(base_url="http://localhost:6565/api/admin", headers=headers) as client:
        print("Creating mock provider pointing to localhost:9999")
        r = await client.post("/providers", json={
            "name": f"openai-{uuid.uuid4().hex[:6]}",
            "display_name": "Mock Streaming Provider",
            "auth_type": "api_key",
            "base_url": "http://localhost:9999/v1",
            "enabled": True
        })
        r.raise_for_status()
        prov = r.json()
        print("Provider ID:", prov["id"])

        print("Creating dummy credential")
        r = await client.post("/credentials", json={
            "provider_id": prov["id"],
            "label": "mock-api-key",
            "secret_key": "sk-mock-doesntexist",
            "enabled": True
        })
        r.raise_for_status()

        print("Creating mock model mapping to tier 'lite'")
        r = await client.post("/models", json={
            "provider_id": prov["id"],
            "model_id": "openai/gpt-mock-stream",
            "tier": "lite",
            "cost_in_1m": 0.5,
            "cost_out_1m": 1.5,
            "enabled": True
        })
        r.raise_for_status()
        
        print("Mock setup complete!")

if __name__ == "__main__":
    asyncio.run(main())
