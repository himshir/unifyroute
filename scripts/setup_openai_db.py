import asyncio
import httpx

async def main():
    admin_token = open(".admin_token-raw").read().split("RAW TOKEN:\n")[1].split("\n=")[0].strip()
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    async with httpx.AsyncClient(base_url="http://localhost:6565/api/admin", headers=headers) as client:
        print("Checking if openai provider exists...")
        r = await client.get("/providers")
        r.raise_for_status()
        providers = r.json()
        prov = next((p for p in providers if p["name"] == "openai"), None)
        
        if prov:
            print("Provider already exists, patching base_url to localhost:9999...")
            await client.patch(f"/providers/{prov['id']}", json={"base_url": "http://localhost:9999/v1"})
        else:
            print("Creating mock openai provider pointing to localhost:9999")
            r = await client.post("/providers", json={
                "name": "openai",
                "display_name": "OpenAI Stream Mock",
                "auth_type": "api_key",
                "base_url": "http://localhost:9999/v1",
                "enabled": True
            })
            r.raise_for_status()
            prov = r.json()
            
        print("Provider ID:", prov["id"])

        print("Testing if credential exists, creating if not...")
        r = await client.get(f"/providers/{prov['id']}/credentials")
        r.raise_for_status()
        if not r.json():
            r = await client.post("/credentials", json={
                "provider_id": prov["id"],
                "label": "mock-api-key",
                "secret_key": "sk-mock-doesntexist",
                "enabled": True
            })
            r.raise_for_status()

        print("Testing if model exists mapping to tier 'lite'...")
        r = await client.get("/models")
        r.raise_for_status()
        models_data = r.json()
        models_list = models_data.get("data", models_data) if isinstance(models_data, dict) else models_data
            
        if not any(m.get("tier") == "lite" and m.get("provider_id") == prov["id"] for m in models_list):
            r = await client.post("/models", json={
                "provider_id": prov["id"],
                "model_id": "gpt-mock-stream",
                "tier": "lite",
                "cost_in_1m": 0.5,
                "cost_out_1m": 1.5,
                "enabled": True
            })
            r.raise_for_status()
        
        print("OpenAI Mock setup complete!")

if __name__ == "__main__":
    asyncio.run(main())
