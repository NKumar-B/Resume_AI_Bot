import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from whatsapp_bot import (
    get_whatsapp_session,
    reset_whatsapp_session,
    handle_whatsapp_command_or_text,
    handle_whatsapp_document,
    process_whatsapp_webhook_payload
)
from telegram_bot import build_application

test_phone = "+15550199"

async def test_whatsapp():
    print("=== Testing WhatsApp Bot Integration Flow ===")
    
    # Reset session
    reset_whatsapp_session(test_phone)
    session = get_whatsapp_session(test_phone)
    assert session["state"] == "WAITING_FOR_JD"

    # Step 1: Send Hello / /start
    print("[1] Testing /start command...")
    await handle_whatsapp_command_or_text(test_phone, "Hello")

    # Step 2: Send Job Description
    print("[2] Testing Job Description input...")
    sample_jd = """
    Job Description: Senior Full Stack Developer
    Key Responsibilities:
    - Build REST APIs using Python, FastAPI, and Django
    - Manage PostgreSQL databases and Docker containers
    Requirements:
    - 3+ years experience with Python
    - Strong knowledge of Git and AWS cloud services
    """
    await handle_whatsapp_command_or_text(test_phone, sample_jd)
    assert session["jd_text"] != ""
    assert session["state"] == "WAITING_FOR_RESUMES"
    print("   [OK] Job Description parsed & stored!")

    # Step 3: Upload Resumes
    print("[3] Testing candidate Resume upload...")
    sample_resume_1 = """
    Alice Johnson
    Email: alice@example.com | Phone: +1-555-0188
    Software Engineer with 4 years experience.
    Work Experience:
    Developer at TechCorp (2021 - Present)
    - Built REST APIs in Python and Django
    - Managed Git version control and SQL databases
    Skills: Python, Django, SQL, Git
    """
    await handle_whatsapp_command_or_text(test_phone, sample_resume_1)
    assert len(session["resumes"]) == 1
    print("   [OK] Resume 1 stored! Total queued:", len(session["resumes"]))

    # Step 4: Run /analyze
    print("[4] Testing /analyze command...")
    await handle_whatsapp_command_or_text(test_phone, "/analyze")
    assert len(session["results"]) == 1
    print("   [OK] Analysis finished! Score:", session["results"][0]["overall_score"])

    # Step 5: Test Telegram bot remains unchanged
    print("[5] Verifying Telegram bot build_application()...")
    app = build_application()
    assert app is not None
    print("   [OK] Telegram bot build_application() intact & working!")

    print("\nALL WHATSAPP INTEGRATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_whatsapp())
