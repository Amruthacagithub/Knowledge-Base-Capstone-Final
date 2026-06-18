"""
Gemini client — ordered API-key and model fallback (quota, 503 overload).
"""
from google import genai

from backend.config import get_gemini_api_keys, get_gemini_models


def is_retryable_gemini_error(exc: Exception) -> bool:
    """True when another key or model may succeed (quota, overload, 503)."""
    msg = str(exc).lower()
    return any(
        token in msg
        for token in (
            "429",
            "503",
            "resource_exhausted",
            "quota",
            "rate limit",
            "rate_limit",
            "too many requests",
            "exceeded your current quota",
            "high demand",
            "unavailable",
            "overloaded",
            "temporarily",
        )
    )


# Backward-compatible alias for tests/imports
is_retryable_key_error = is_retryable_gemini_error


def generate_text(prompt: str, model: str | None = None) -> str:
    """
    Call Gemini with fallback across models, then API keys.

    Tries GEMINI_MODEL first, then GEMINI_MODEL_FALLBACK (default: lite → 3.1-lite → 2.5-flash → 3.5-flash).
    On 429/503, tries the next model on the same key, then the next key from the start.

    Raises ValueError if no keys are configured.
    Raises the last exception if all combinations fail.
    """
    keys = get_gemini_api_keys()
    if not keys:
        raise ValueError(
            "No Gemini API keys configured. Set GEMINI_API_KEY in .env "
            "(optional: GEMINI_API_KEY_2, GEMINI_API_KEY_3, … for fallback)."
        )

    models = [model] if model else get_gemini_models()
    last_error: Exception | None = None

    for key_index, api_key in enumerate(keys):
        client = genai.Client(api_key=api_key)
        for model_index, model_name in enumerate(models):
            try:
                response = client.models.generate_content(
                    model=model_name, contents=prompt
                )
                text = response.text
                if text:
                    if key_index > 0 or model_index > 0:
                        print(
                            f"  ✓ Gemini answered with {model_name} "
                            f"(key #{key_index + 1})"
                        )
                    return text
                raise RuntimeError("Gemini returned empty response")
            except Exception as e:
                last_error = e
                if not is_retryable_gemini_error(e):
                    raise

                last_model = model_index >= len(models) - 1
                last_key = key_index >= len(keys) - 1
                if last_model and last_key:
                    raise

                if not last_model:
                    next_model = models[model_index + 1]
                    print(
                        f"  ⚠ {model_name} failed ({str(e)[:80]}…), "
                        f"trying model {next_model}…"
                    )
                    continue

                print(
                    f"  ⚠ Key #{key_index + 1} exhausted on all models, "
                    f"trying key #{key_index + 2}…"
                )
                break

    if last_error:
        raise last_error
    raise RuntimeError("Gemini call failed with no error details")
