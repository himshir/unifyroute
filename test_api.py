"""
End-to-End Test Suite for UnifyRoute

This script tests the entire user journey:
1. API Health Check
2. Admin Login
3. Creating a Provider
4. Adding an API Key Credential
5. Syncing Models from Provider
6. Enabling a Model
7. Generating a User Client API Key
8. Testing a Chat Completion Request
9. Cleanup (Optional)
"""

import os
import sys
import uuid
import httpx
import time
import asyncio

API_BASE = os.getenv("API_URL", "http://localhost:6565/api")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

# Target provider and model
PROVIDER_NAME = os.getenv("E2E_PROVIDER", "openai")

PROVIDER_KEY = os.getenv("E2E_PROVIDER_KEY")

async def main():
    print("=====================================================")
    print("🚀 Starting UnifyRoute E2E Test Suite")
    print("=====================================================\n")
    
    if not PROVIDER_KEY:
        print("⚠️  Warning: E2E_PROVIDER_KEY is not set.")
        print("   The chat completion step will fail unless you provide a valid API key.")
        print(f"   Usage: E2E_PROVIDER_KEY='sk-...' python test_api.py\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health Check
        print("1️⃣  Checking API Health...")
        try:
            r = await client.get(f"{API_BASE}/")
            r.raise_for_status()
            print(f"   ✅ API Status: {r.json().get('status', 'OK')}")
        except Exception as e:
            print(f"   ❌ API Health check failed: {e}")
            print("   Please ensure the UnifyRoute server is running.")
            sys.exit(1)

        # 2. Admin Login
        print("\n2️⃣  Logging in as Admin...")
        r = await client.post(f"{API_BASE}/admin/login", json={"password": ADMIN_PASSWORD})
        if r.status_code != 200:
            print(f"   ❌ Login failed: {r.text}")
            sys.exit(1)
        
        token = r.json().get("token")
        if not token:
            print("   ❌ No token received.")
            sys.exit(1)
        
        print("   ✅ Logged in successfully.")
        admin_headers = {"Authorization": f"Bearer {token}"}

        # 3. Create Provider
        print(f"\n3️⃣  Setting up test Provider '{PROVIDER_NAME}'...")
        r = await client.post(
            f"{API_BASE}/admin/providers", 
            headers=admin_headers,
            json={
                "name": f"e2e-{PROVIDER_NAME}-{str(uuid.uuid4())[:4]}",
                "display_name": f"E2E Test {PROVIDER_NAME.capitalize()}",
                "auth_type": "api_key",
                "enabled": True
            }
        )
        if r.status_code == 200:
            provider_id = r.json()["id"]
            print(f"   ✅ Created Provider ID: {provider_id}")
        else:
            print(f"   ❌ Could not create provider: {r.text}")
            sys.exit(1)

        # 4. Add Credential
        credential_id = None
        if PROVIDER_KEY:
            print(f"\n4️⃣  Adding API Key Credential...")
            cred_label = f"e2e-key-{str(uuid.uuid4())[:6]}"
            r = await client.post(
                f"{API_BASE}/admin/credentials",
                headers=admin_headers,
                json={
                    "provider_id": provider_id,
                    "label": cred_label,
                    "auth_type": "api_key",
                    "secret_key": PROVIDER_KEY,
                    "enabled": True
                }
            )
            if r.status_code == 200:
                credential_id = r.json()["id"]
                print(f"   ✅ Added Credential ID: {credential_id} ({cred_label})")
            else:
                print(f"   ❌ Failed to add credential: {r.text}")
        else:
            print("\n4️⃣  Skipping Credential (No E2E_PROVIDER_KEY set).")

        # 5. Sync Models
        print("\n5️⃣  Syncing Models...")
        r = await client.post(f"{API_BASE}/admin/providers/{provider_id}/sync-models", headers=admin_headers)
        if r.status_code == 200:
            sync_res = r.json()
            print(f"   ✅ Synced {sync_res.get('total', 0)} models. Source: {sync_res.get('source', 'unknown')}")
        else:
            print(f"   ❌ Failed to sync models: {r.text}")

        # 6. Select a Target Model
        print(f"\n6️⃣  Selecting and Enabling a Model...")
        r_models = await client.get(f"{API_BASE}/admin/models", headers=admin_headers)
        all_models = r_models.json()
        
        provider_models = [m for m in all_models if m["provider_id"] == provider_id]
        
        if not provider_models:
            print(f"   ⚠️ No live models found for this provider (possibly due to an invalid test key).")
            print(f"   ℹ️ Proceeding with a fallback default model 'gpt-4o-mini' to test proxy resolution.")
            MODEL_ID = "gpt-4o-mini"
        else:
            print(f"   ℹ️  Found {len(provider_models)} models for {PROVIDER_NAME}.")
            # Predictably pick the first model available for the completion test
            target_model = provider_models[0]
            MODEL_ID = target_model["model_id"]
            
            print(f"   🎯 Automatically selected model: '{MODEL_ID}'")
            
            r = await client.patch(
                f"{API_BASE}/admin/models/{target_model['id']}",
                headers=admin_headers,
                json={"enabled": True, "tier": "default"}
            )
            if r.status_code == 200:
                print(f"   ✅ Target model '{MODEL_ID}' enabled and mapped to 'default' tier.")
            else:
                print(f"   ❌ Failed to enable model: {r.text}")

        # 7. Generate Client API Key
        print("\n7️⃣  Generating Client Routing Key...")
        key_label = f"e2e-client-{str(uuid.uuid4())[:6]}"
        r = await client.post(
            f"{API_BASE}/admin/keys",
            headers=admin_headers,
            json={
                "label": key_label,
                "scopes": ["chat"]
            }
        )
        if r.status_code == 200:
            client_key_info = r.json()
            client_token = client_key_info["token"]
            client_key_id = client_key_info["id"]
            print(f"   ✅ Generated Client Key!")
        else:
            print(f"   ❌ Failed to generate client key: {r.text}")
            sys.exit(1)

        # 8. Test Chat Completion
        print(f"\n8️⃣  Testing /v1/chat/completions (Routing to '{MODEL_ID}')...")
        if not PROVIDER_KEY:
            print("   ⚠️ Skipping completion execution because E2E_PROVIDER_KEY was not provided.")
        else:
            client_headers = {
                "Authorization": f"Bearer {client_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": MODEL_ID,
                "messages": [{"role": "user", "content": "You are a test bot. Say 'success'."}],
                "max_tokens": 50,
                "stream": False
            }
            
            start_time = time.time()
            r = await client.post(f"{API_BASE}/v1/chat/completions", headers=client_headers, json=payload, timeout=60.0)
            elapsed = time.time() - start_time
            
            if r.status_code == 200:
                resp_json = r.json()
                content = resp_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(f"   ✅ Success! ({elapsed:.2f}s)")
                print(f"   🤖 Response: {content.strip()}")
            else:
                print(f"   ❌ Chat Completion failed (HTTP {r.status_code}): {r.text}")

        # 9. Cleanup
        print("\n9️⃣  Test Cleanup...")
        # Delete Key
        await client.delete(f"{API_BASE}/admin/keys/{client_key_id}", headers=admin_headers)
        print("   ✅ Deleted temporary Client Routing Key.")
        
        # We also delete the test provider to keep DB clean, this cascades to models/credentials
        # But we must ensure it isn't forbidden (e.g. active credentials). The api requires us to delete creds first
        if credential_id:
            await client.delete(f"{API_BASE}/admin/credentials/{credential_id}", headers=admin_headers)
            print("   ✅ Deleted API Key Credential.")
            
        r = await client.delete(f"{API_BASE}/admin/providers/{provider_id}", headers=admin_headers)
        if r.status_code == 200:
            print("   ✅ Deleted temporary Provider and Models.")
        
        print("\n🎉 E2E Test Suite run completed!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Test cancelled by user.")
