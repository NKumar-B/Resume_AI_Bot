import sys
import io
from pathlib import Path

# Force UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENAI_MODEL
import httpx
from openai import OpenAI

def verify_credentials():
    print("==========================================")
    print("🔍 VERIFYING CREDENTIALS IN .env")
    print("==========================================")

    # 1. Verify Telegram Bot Token
    print("\n1. Testing Telegram Bot Token...")
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN is empty in .env!")
    else:
        try:
            tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
            resp = httpx.get(tg_url, timeout=10.0)
            data = resp.json()
            if data.get("ok"):
                bot_info = data["result"]
                print(f"[OK] TELEGRAM BOT VALID!")
                print(f"     Bot Name: {bot_info.get('first_name')}")
                print(f"     Bot Username: @{bot_info.get('username')}")
                print(f"     Bot ID: {bot_info.get('id')}")
            else:
                print(f"❌ Telegram API Error: {data.get('description')}")
        except Exception as e:
            print(f"❌ Failed to reach Telegram API: {e}")

    # 2. Verify OpenRouter API Key
    print("\n2. Testing OpenRouter API Key...")
    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY is empty in .env!")
    else:
        try:
            client = OpenAI(
                api_key=OPENROUTER_API_KEY,
                base_url=OPENROUTER_BASE_URL,
                default_headers={
                    "HTTP-Referer": "https://github.com/AI-Resume-Matcher",
                    "X-Title": "AI Resume Matcher"
                }
            )
            model_name = OPENAI_MODEL
            if model_name == "gpt-4o-mini":
                model_name = "openai/gpt-4o-mini"

            print(f"     Connecting to OpenRouter ({OPENROUTER_BASE_URL})...")
            print(f"     Model selected: {model_name}")
            
            # Test simple completion request
            test_resp = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": "Hello, respond with 'OpenRouter OK'"}],
                max_tokens=15
            )
            reply = test_resp.choices[0].message.content.strip()
            print(f"[OK] OPENROUTER API KEY VALID & WORKING!")
            print(f"     OpenRouter Response Test: SUCCESS (Reply: '{reply}')")
        except Exception as e:
            print(f"❌ OpenRouter API Error: {e}")

    print("\n==========================================")
    print("Verification Completed.")

if __name__ == "__main__":
    verify_credentials()
