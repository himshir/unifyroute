import asyncio
import httpx
import json

async def main():
    api_key = open(".api_token-raw").read().split("RAW TOKEN:\n")[1].split("\n=")[0].strip()
    
    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {api_key}"}) as client:
        print("Sending streaming request to test cost...")
        request_body = {
            "model": "lite",
            "messages": [{"role": "user", "content": "Hello, count to 10!"}],
            "stream": True
        }
        
        async with client.stream("POST", "http://localhost:6565/api/v1/chat/completions", json=request_body, timeout=30) as response:
            async for line in response.aiter_lines():
                if line:
                    print(line)

        print("\n\nChecking logs...")
        admin_token = open(".admin_token-raw").read().split("RAW TOKEN:\n")[1].split("\n=")[0].strip()
        r = await client.get("http://localhost:6565/api/admin/logs?limit=1", headers={"Authorization": f"Bearer {admin_token}"})
        logs = r.json()
        print(json.dumps(logs, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
