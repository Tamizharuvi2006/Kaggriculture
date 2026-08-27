"""KiosAPI OpenAI-Compatible Client & CLI Helper.

Configured with base_url="https://kiosapi.com/v1" and API key.
Allows querying KiosAPI models (e.g. glm-5.2, gpt-5.5, gpt-5.4, etc.) directly from Python or CLI.
"""
from __future__ import annotations
import os
import sys
import argparse
from openai import OpenAI

# Default credentials
KIOS_BASE_URL = os.environ.get("KIOS_BASE_URL", "https://kiosapi.com/v1")
KIOS_API_KEY = os.environ.get("KIOS_API_KEY", "sk-1jzoOodS99DHUEEYkTvJSvSs4PoehwvEL91ikqgR5MquKIWG")
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def get_client(api_key: str | None = None, base_url: str | None = None) -> OpenAI:
    return OpenAI(
        base_url=base_url or KIOS_BASE_URL,
        api_key=api_key or KIOS_API_KEY,
        default_headers=DEFAULT_HEADERS,
    )

def list_models(client: OpenAI | None = None) -> list[str]:
    c = client or get_client()
    try:
        models = c.models.list()
        return [m.id for m in models.data]
    except Exception as e:
        print(f"Error listing models: {e}")
        return []

def complete(prompt: str, model: str = "glm-5.2", system_prompt: str | None = None, client: OpenAI | None = None) -> str:
    c = client or get_client()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = c.chat.completions.create(
        model=model,
        messages=messages,
    )
    return response.choices[0].message.content or ""

def main():
    parser = argparse.ArgumentParser(description="Query KiosAPI models from the terminal.")
    parser.add_argument("prompt", nargs="?", help="Prompt to send to the model")
    parser.add_argument("--model", "-m", default="glm-5.2", help="Model name (default: glm-5.2)")
    parser.add_argument("--list-models", "-l", action="store_true", help="List available models")
    parser.add_argument("--system", "-s", help="Optional system prompt")
    args = parser.parse_args()

    client = get_client()

    if args.list_models:
        print("Available models on KiosAPI:")
        models = list_models(client)
        for m in models:
            print(f"  - {m}")
        return

    if not args.prompt:
        parser.print_help()
        return

    try:
        reply = complete(args.prompt, model=args.model, system_prompt=args.system, client=client)
        print(reply)
    except Exception as e:
        print(f"API Error: {e}")

if __name__ == "__main__":
    main()
