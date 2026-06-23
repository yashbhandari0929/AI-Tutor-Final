import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

# Fallback chain: fastest/latest first, drop to older free-tier models on quota exhaustion
MODELS = [
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",   # lightest, highest free-tier RPD
    "gemini-1.5-pro",
]

def _make_llm(model: str) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=0.7,
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )


def generate_response(prompt: str) -> str | None:
    for model in MODELS:
        try:
            llm = _make_llm(model)
            response = llm.invoke(prompt)
            content = response.content.strip()
            if content:
                if model != MODELS[0]:
                    print(f"[LLM] Used fallback model: {model}")
                return content

        except Exception as e:
            err = str(e)
            if "RESOURCE_EXHAUSTED" in err or "429" in err:
                print(f"[LLM] Quota exhausted for {model}, trying next model…")
                continue          # try the next model in chain
            else:
                print(f"[LLM] ERROR on {model}: {e}")
                return None       # non-quota error — don't retry

    print("[LLM] All models exhausted their quota.")
    return None