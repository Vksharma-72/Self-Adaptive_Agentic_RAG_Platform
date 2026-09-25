import logfire
import time
from portkey_ai import Portkey, createHeaders, PORTKEY_GATEWAY_URL
from langchain_openai import ChatOpenAI

from app.config import settings


# Models: Groq decommissioned the old llama-3.3/3.1 chat models in 2026.
# Primary: gpt-oss-120b → fallback gpt-oss-20b on failure.
# NOTE: the saved dashboard config (PORTKEY_CONFIG slug) still references the
# retired llama models and inline configs are disabled on this workspace, so
# we call the virtual keys directly with an explicit model and implement
# fallback here. Update the dashboard config and you can switch back.
PRIMARY_MODEL = f"@{settings.GROQ_SLUG}/openai/gpt-oss-120b"

# GROQ_SLUG_2 defaults to the literal 'GROQ_SLUG' placeholder in some .env
# templates — treat that as unset and route the fallback through the primary key
_FALLBACK_VK = settings.GROQ_SLUG_2
if not _FALLBACK_VK or _FALLBACK_VK == "GROQ_SLUG":
    _FALLBACK_VK = settings.GROQ_SLUG
FALLBACK_MODEL = f"@{_FALLBACK_VK}/openai/gpt-oss-20b"

portkey_client = Portkey(
    api_key=settings.PORTKEY_API_KEY,
)


def chat_completion(messages: list[dict], temperature: float = 0.1):
    """Chat via Portkey with manual primary→fallback routing and 429 backoff.

    Rate limits (TPM windows) are waited out briefly per model before
    falling back, since the fallback model has its own quota.
    """
    last_error = None
    for model in (PRIMARY_MODEL, FALLBACK_MODEL):
        for attempt in range(2):
            try:
                return portkey_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                )
            except Exception as e:
                last_error = e
                is_rate_limit = "429" in str(e) or "rate_limit" in str(e).lower()
                if is_rate_limit and attempt == 0:
                    time.sleep(15)
                    continue
                logfire.warning(f"LLM call failed on {model}: {str(e)[:150]}")
                break
    raise last_error


def get_langchain_llm(feature: str = "rag") -> ChatOpenAI:
    """
    Returns a Portkey-backed ChatOpenAI — a drop-in for ChatGroq in LangChain nodes.

    Why ChatOpenAI and not ChatGroq:
      Portkey is a proxy. It exposes an OpenAI-compatible endpoint at PORTKEY_GATEWAY_URL.
      ChatGroq is hardwired to Groq's API and does not support routing through a proxy.
      ChatOpenAI supports base_url (points at Portkey) and default_headers (passes Portkey
      auth + config). The @virtual-key/model format is Portkey-specific — Groq's own client
      does not understand it. You are still using Groq-hosted models; Portkey is just in the middle.
    """
    return ChatOpenAI(
        api_key=settings.PORTKEY_API_KEY,
        base_url=PORTKEY_GATEWAY_URL,
        model=PRIMARY_MODEL,
        temperature=0,
        default_headers=createHeaders(
            api_key=settings.PORTKEY_API_KEY,
            metadata={
                "feature": feature,
                "_user": "rag-system",
                "environment": "production"
            }
        )
    )

def extract_cache_status(response) -> str:
    """
    Pull x-portkey-cache-status from the Portkey native client response headers.
    Tries multiple attribute paths defensively — returns 'MISS' if not found.
    """
    for attr in ("_raw_response", "_response", "_http_response"):
        raw = getattr(response, attr, None)
        if raw is not None:
            status = getattr(raw, "headers", {}).get("x-portkey-cache-status", "")
            if status:
                return status.upper()
    return "MISS"
