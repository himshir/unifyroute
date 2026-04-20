"""Credit balance tracking interface and implementations (Phase 1)

Each adapter can optionally implement get_credit_balance() to report USD remaining.
If not implemented, returns None (unknown state).
"""

from dataclasses import dataclass
from typing import Optional
from abc import ABC, abstractmethod


@dataclass
class CreditBalance:
    """USD-level balance information"""
    usd_remaining: Optional[float] = None
    usd_granted: Optional[float] = None
    usd_used: Optional[float] = None
    source: str = "provider_api"  # "provider_api" | "computed_from_usage"

    @property
    def usd_remaining_pct(self) -> Optional[float]:
        """Percentage of granted balance remaining"""
        if self.usd_granted and self.usd_granted > 0:
            return (self.usd_remaining or 0) / self.usd_granted
        return None

    @property
    def is_unknown(self) -> bool:
        """True if balance couldn't be determined"""
        return self.usd_remaining is None


class CreditBalanceAdapter(ABC):
    """Base adapter for fetching credit balances from providers"""

    @abstractmethod
    async def get_credit_balance(self, credential: dict) -> Optional[CreditBalance]:
        """
        Fetch USD remaining for credential.

        Returns CreditBalance if available, None if unsupported or error.
        Credential dict contains decrypted secret + provider-specific metadata.
        """
        pass


class OpenAICreditAdapter(CreditBalanceAdapter):
    """OpenAI credit balance via dashboard API"""

    async def get_credit_balance(self, credential: dict) -> Optional[CreditBalance]:
        """
        Fetch from OpenAI /dashboard/billing/credit_grants endpoint.
        Requires API key with billing scope.
        """
        try:
            import aiohttp

            api_key = credential.get('secret')
            if not api_key:
                return None

            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {api_key}'}

                # Get credit grants
                async with session.get(
                    'https://api.openai.com/dashboard/billing/credit_grants',
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Parse credits from response
                        total_granted = sum(
                            float(grant.get('grant_amount', 0))
                            for grant in data.get('data', [])
                        )
                        total_used = sum(
                            float(grant.get('used_amount', 0))
                            for grant in data.get('data', [])
                        )
                        return CreditBalance(
                            usd_remaining=total_granted - total_used,
                            usd_granted=total_granted,
                            usd_used=total_used,
                            source='provider_api'
                        )
        except Exception as e:
            import logging
            logging.warning(f"Failed to fetch OpenAI credit balance: {e}")

        return None


class AnthropicCreditAdapter(CreditBalanceAdapter):
    """Anthropic workspace spend tracking"""

    async def get_credit_balance(self, credential: dict) -> Optional[CreditBalance]:
        """
        Fetch workspace spend from Anthropic API.
        Returns granted credits minus current spend.
        """
        try:
            import aiohttp

            api_key = credential.get('secret')
            if not api_key:
                return None

            async with aiohttp.ClientSession() as session:
                headers = {'x-api-key': api_key}

                # Get workspace info (includes spend)
                async with session.get(
                    'https://api.anthropic.com/v1/workspace',
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Parse credit info
                        monthly_budget = float(data.get('monthly_budget', 0))
                        monthly_spend = float(data.get('monthly_spend', 0))
                        return CreditBalance(
                            usd_remaining=max(0, monthly_budget - monthly_spend),
                            usd_granted=monthly_budget,
                            usd_used=monthly_spend,
                            source='provider_api'
                        )
        except Exception as e:
            import logging
            logging.warning(f"Failed to fetch Anthropic credit balance: {e}")

        return None


class OpenRouterCreditAdapter(CreditBalanceAdapter):
    """OpenRouter account balance"""

    async def get_credit_balance(self, credential: dict) -> Optional[CreditBalance]:
        """Fetch account balance from OpenRouter /api/v1/auth/key endpoint"""
        try:
            import aiohttp

            api_key = credential.get('secret')
            if not api_key:
                return None

            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {api_key}'}

                async with session.get(
                    'https://openrouter.ai/api/v1/auth/key',
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        balance = float(data.get('balance', 0))
                        return CreditBalance(
                            usd_remaining=balance,
                            source='provider_api'
                        )
        except Exception as e:
            import logging
            logging.warning(f"Failed to fetch OpenRouter credit balance: {e}")

        return None


class TogetherCreditAdapter(CreditBalanceAdapter):
    """Together AI account balance"""

    async def get_credit_balance(self, credential: dict) -> Optional[CreditBalance]:
        """Fetch account info from Together /v1/user endpoint"""
        try:
            import aiohttp

            api_key = credential.get('secret')
            if not api_key:
                return None

            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {api_key}'}

                async with session.get(
                    'https://api.together.xyz/v1/user',
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        balance = float(data.get('credit_balance', 0))
                        return CreditBalance(
                            usd_remaining=balance,
                            source='provider_api'
                        )
        except Exception as e:
            import logging
            logging.warning(f"Failed to fetch Together credit balance: {e}")

        return None


class FireworksCreditAdapter(CreditBalanceAdapter):
    """Fireworks AI account balance"""

    async def get_credit_balance(self, credential: dict) -> Optional[CreditBalance]:
        """Fetch account info via Fireworks API"""
        try:
            import aiohttp

            api_key = credential.get('secret')
            if not api_key:
                return None

            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {api_key}'}

                async with session.get(
                    'https://api.fireworks.ai/v1/accounts/me',
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        balance = float(data.get('balance', {}).get('amount', 0))
                        return CreditBalance(
                            usd_remaining=balance,
                            source='provider_api'
                        )
        except Exception as e:
            import logging
            logging.warning(f"Failed to fetch Fireworks credit balance: {e}")

        return None


class GroqCreditAdapter(CreditBalanceAdapter):
    """Groq API balance tracking"""

    async def get_credit_balance(self, credential: dict) -> Optional[CreditBalance]:
        """Fetch account info from Groq (if available)"""
        # Groq may not expose credit balance via API
        # Return None to indicate unsupported
        return None


# Registry of adapters by provider name
CREDIT_ADAPTERS = {
    'openai': OpenAICreditAdapter(),
    'anthropic': AnthropicCreditAdapter(),
    'openrouter': OpenRouterCreditAdapter(),
    'together': TogetherCreditAdapter(),
    'fireworks': FireworksCreditAdapter(),
    'groq': GroqCreditAdapter(),
}


def get_credit_adapter(provider_name: str) -> Optional[CreditBalanceAdapter]:
    """Get credit adapter for provider, or None if unsupported"""
    return CREDIT_ADAPTERS.get(provider_name.lower())
