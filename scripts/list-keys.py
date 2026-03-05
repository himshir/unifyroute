#!/usr/bin/env python3
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'shared', 'src')))
from shared.database import async_session_maker
from shared.models import GatewayKey
from sqlalchemy import select

async def list_keys(token_type: str = None):
    async with async_session_maker() as session:
        result = await session.execute(select(GatewayKey))
        all_keys = result.scalars().all()
        
        # Filter by scope if token_type is provided
        if token_type:
            keys = [k for k in all_keys if k.scopes and token_type in k.scopes]
        else:
            keys = all_keys
        
        print(f"\n{'Label':<30} | {'Scopes':<20} | {'Token Hash (masked)':<25} | {'Raw Token':<55} | {'Enabled'}")
        print("-" * 145)
        for k in keys:
            scopes_str = ", ".join(k.scopes) if k.scopes else "None"
            raw_val = k.raw_token if hasattr(k, 'raw_token') and k.raw_token else "(not stored in DB)"
            hash_val = f"sk-...{k.key_hash[:8]}" if k.key_hash else "None"
            print(f"{k.label:<30} | {scopes_str:<20} | {hash_val:<25} | {raw_val:<55} | {k.enabled}")
        print("")
        
        # If admin type was explicitly requested, try to show the raw token
        if token_type == "admin":
            admin_token_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.admin_token'))
            try:
                with open(admin_token_path, "r") as f:
                    raw_token = f.read().strip()
                print("============================================================")
                print("CURRENT RAW ADMIN TOKEN (from .admin_token file):")
                print(raw_token)
                print("============================================================\n")
            except FileNotFoundError:
                print("No raw admin token found in .admin_token file.\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="List Gateway API Keys")
    parser.add_argument("--type", choices=["admin", "api"], default=None, help="Filter by token type")
    args = parser.parse_args()
    
    asyncio.run(list_keys(args.type))
