import asyncio
import httpx

async def main():
    admin_token = open(".admin_token-raw").read().split("RAW TOKEN:\n")[1].split("\n=")[0].strip()
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    async with httpx.AsyncClient(base_url="http://localhost:6565/api/admin", headers=headers) as client:
        print("Finding OpenAI provider to hijack api_base...")
        r = await client.get("/providers")
        providers = r.json()
        openai_prov = next((p for p in providers if p["name"] == "openai"), None)
        
        if openai_prov:
            print(f"Setting base_url for {openai_prov['name']} to localhost:9999")
            await client.patch(f"/providers/{openai_prov['id']}", json={"base_url": "http://localhost:9999/v1"})
            print("Done")
            
if __name__ == "__main__":
    asyncio.run(main())
