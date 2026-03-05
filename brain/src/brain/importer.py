"""Brain importer — bulk import of providers, credentials, and brain assignments.

Accepts YAML or JSON payloads and idempotently upserts providers/credentials
into the DB, then creates brain_configs entries for the assignments.

Input format (YAML or JSON):
    providers:
      - name: fireworks
        display_name: "Fireworks AI"     # optional, defaults to name
        credentials:
          - label: "my-fw-key"
            api_key: "fw-..."
        models:                          # models to auto-add for this provider
          - accounts/fireworks/models/llama-v3p1-8b-instruct
    brain_assignments:
      - provider: fireworks
        credential_label: "my-fw-key"
        models:
          - accounts/fireworks/models/llama-v3p1-8b-instruct
        priority: 10                     # optional, default 100
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Provider, Credential, ProviderModel, BrainConfig
from shared.security import encrypt_secret

from .errors import brain_safe_message


@dataclass
class ImportResult:
    providers_created: List[str] = field(default_factory=list)
    providers_skipped: List[str] = field(default_factory=list)
    credentials_created: List[str] = field(default_factory=list)
    credentials_skipped: List[str] = field(default_factory=list)
    models_created: int = 0
    brain_assignments_created: int = 0
    brain_assignments_skipped: int = 0
    errors: List[str] = field(default_factory=list)


async def import_from_dict(data: dict, session: AsyncSession) -> ImportResult:
    """Idempotently import providers, credentials, models, and brain assignments from a dict."""
    result = ImportResult()

    # ── Step 1: Upsert providers + credentials + models ──────────────────────
    for prov_data in data.get("providers", []):
        pname = prov_data.get("name", "").strip()
        if not pname:
            result.errors.append("Provider entry missing 'name'.")
            continue

        # Find or create provider
        prov_stmt = select(Provider).where(Provider.name == pname)
        prov_res = await session.execute(prov_stmt)
        provider = prov_res.scalar_one_or_none()

        if provider is None:
            provider = Provider(
                name=pname,
                display_name=prov_data.get("display_name", pname),
                auth_type=prov_data.get("auth_type", "api_key"),
                base_url=prov_data.get("base_url"),
                enabled=True,
            )
            session.add(provider)
            await session.flush()  # get provider.id
            result.providers_created.append(pname)
        else:
            result.providers_skipped.append(pname)

        # Upsert credentials
        for cred_data in prov_data.get("credentials", []):
            label = cred_data.get("label", "").strip()
            api_key = cred_data.get("api_key", "").strip()
            if not label or not api_key:
                result.errors.append(f"Credential for provider '{pname}' missing 'label' or 'api_key'.")
                continue

            cred_stmt = select(Credential).where(
                Credential.provider_id == provider.id,
                Credential.label == label,
            )
            cred_res = await session.execute(cred_stmt)
            existing_cred = cred_res.scalar_one_or_none()

            if existing_cred is None:
                cred = Credential(
                    provider_id=provider.id,
                    label=label,
                    auth_type=cred_data.get("auth_type", "api_key"),
                    **dict(zip(('secret_enc', 'iv'), encrypt_secret(api_key))),
                    enabled=True,
                )
                session.add(cred)
                result.credentials_created.append(f"{pname}/{label}")
            else:
                result.credentials_skipped.append(f"{pname}/{label}")

        # Upsert models
        existing_models_stmt = select(ProviderModel.model_id).where(
            ProviderModel.provider_id == provider.id
        )
        existing_models_res = await session.execute(existing_models_stmt)
        existing_model_ids = {row[0] for row in existing_models_res.fetchall()}

        for model_id in prov_data.get("models", []):
            if model_id in existing_model_ids:
                continue
            model_obj = ProviderModel(
                provider_id=provider.id,
                model_id=model_id,
                display_name=model_id,
                context_window=131072,
                input_cost_per_1k=0.0,
                output_cost_per_1k=0.0,
                tier="",
                enabled=True,
            )
            session.add(model_obj)
            result.models_created += 1

    await session.flush()

    # ── Step 2: Create brain assignments ─────────────────────────────────────
    for assign in data.get("brain_assignments", []):
        pname = assign.get("provider", "").strip()
        clabel = assign.get("credential_label", "").strip()
        priority = int(assign.get("priority", 100))
        models = assign.get("models", [])

        if not pname or not clabel:
            result.errors.append("Brain assignment missing 'provider' or 'credential_label'.")
            continue

        prov_stmt = select(Provider).where(Provider.name == pname)
        prov_res = await session.execute(prov_stmt)
        provider = prov_res.scalar_one_or_none()
        if not provider:
            result.errors.append(f"Provider '{pname}' not found for brain assignment.")
            continue

        cred_stmt = select(Credential).where(
            Credential.provider_id == provider.id,
            Credential.label == clabel,
        )
        cred_res = await session.execute(cred_stmt)
        credential = cred_res.scalar_one_or_none()
        if not credential:
            result.errors.append(f"Credential '{clabel}' for provider '{pname}' not found.")
            continue

        for model_id in models:
            # Check if this (provider, credential, model) triple already exists
            exists_stmt = select(BrainConfig).where(
                BrainConfig.provider_id == provider.id,
                BrainConfig.credential_id == credential.id,
                BrainConfig.model_id == model_id,
            )
            exists_res = await session.execute(exists_stmt)
            existing = exists_res.scalar_one_or_none()

            if existing:
                result.brain_assignments_skipped += 1
                continue

            brain_entry = BrainConfig(
                provider_id=provider.id,
                credential_id=credential.id,
                model_id=model_id,
                priority=priority,
                enabled=True,
            )
            session.add(brain_entry)
            result.brain_assignments_created += 1

    await session.commit()
    return result


async def import_from_yaml_str(yaml_str: str, session: AsyncSession) -> ImportResult:
    """Import from a YAML-formatted string."""
    try:
        data = yaml.safe_load(yaml_str)
        if not isinstance(data, dict):
            r = ImportResult()
            r.errors.append("YAML must be a mapping (dict) at top level.")
            return r
        return await import_from_dict(data, session)
    except yaml.YAMLError as exc:
        r = ImportResult()
        r.errors.append(f"YAML parse error: {brain_safe_message(exc)}")
        return r


async def import_from_json_str(json_str: str, session: AsyncSession) -> ImportResult:
    """Import from a JSON-formatted string."""
    try:
        data = json.loads(json_str)
        if not isinstance(data, dict):
            r = ImportResult()
            r.errors.append("JSON must be an object at top level.")
            return r
        return await import_from_dict(data, session)
    except json.JSONDecodeError as exc:
        r = ImportResult()
        r.errors.append(f"JSON parse error: {brain_safe_message(exc)}")
        return r
