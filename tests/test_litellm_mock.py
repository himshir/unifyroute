import pytest
import litellm

def test_mock_generate_error():
    try:
        raise litellm.RateLimitError(
            message=b'{\n  "error": {\n    "code": 429,\n    "message": "Quota exceeded",\n    "status": "RESOURCE_EXHAUSTED"\n  }\n}',
            model="gemini-3-pro",
            llm_provider="gemini",
            response=""
        )
    except Exception as e:
        print(f"str(e): {str(e)}")
        if hasattr(e, "message"):
            print(f"e.message: {e.message}")
