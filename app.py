import os
import sys
import logging
import asyncio
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, Response, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

from config import PORT, TELEGRAM_BOT_TOKEN, WHATSAPP_API_TOKEN, WHATSAPP_VERIFY_TOKEN, OPENROUTER_API_KEY, validate_config
from resume_parser import parse_resume
from jd_parser import parse_job_description
from ai_analyzer import analyze_resume
from formatter import format_final_summary
from doc_classifier import classify_document
from whatsapp_bot import process_whatsapp_webhook_payload

logger = logging.getLogger("ResumeMatcherApp")

# Create FastAPI application
app = FastAPI(
    title="AI Resume & Job Description Matcher API",
    description="Production REST API with Telegram & WhatsApp Bot integration for AI Resume Screening.",
    version="1.1.0"
)


@app.get("/")
async def root():
    """Health check & status endpoint."""
    return {
        "status": "online",
        "service": "AI Resume & Job Description Matcher",
        "telegram_bot_configured": bool(TELEGRAM_BOT_TOKEN),
        "whatsapp_bot_configured": bool(WHATSAPP_API_TOKEN),
        "ai_engine_configured": bool(OPENROUTER_API_KEY),
        "whatsapp_webhook_url": "/whatsapp/webhook"
    }


@app.get("/whatsapp/webhook")
async def verify_whatsapp_webhook(request: Request):
    """
    Verification endpoint for Meta WhatsApp Cloud API Webhook.
    Returns hub.challenge when hub.verify_token matches WHATSAPP_VERIFY_TOKEN.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp Webhook verified successfully!")
        return Response(content=challenge, media_type="text/plain")

    logger.warning(f"WhatsApp Webhook verification failed: Token mismatch (Received: {token}).")
    raise HTTPException(status_code=403, detail="Webhook verification failed.")


@app.post("/whatsapp/webhook")
async def receive_whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives incoming WhatsApp messages (text, PDF, DOCX) and processes them asynchronously.
    """
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = await request.json()
        else:
            form_data = await request.form()
            payload = dict(form_data)

        background_tasks.add_task(process_whatsapp_webhook_payload, payload)
        return {"status": "ok"}
    except Exception as e:
        logger.exception(f"Error handling WhatsApp webhook: {e}")
        return JSONResponse(status_code=200, content={"status": "error", "detail": str(e)})


@app.post("/analyze")
async def analyze_resumes_api(
    jd_text: Optional[str] = Form(None),
    jd_file: Optional[UploadFile] = File(None),
    resumes: List[UploadFile] = File(...)
):
    """
    REST API endpoint for multi-resume analysis against a Job Description.
    Supports future React, Discord, WhatsApp, or Slack dashboard integrations.
    """
    if not jd_text and not jd_file:
        raise HTTPException(status_code=400, detail="Must provide either jd_text or jd_file.")

    if not resumes:
        raise HTTPException(status_code=400, detail="At least one resume file must be uploaded.")

    # Parse Job Description
    if jd_file:
        jd_bytes = await jd_file.read()
        parsed_jd = parse_job_description(jd_bytes, filename=jd_file.filename)
    else:
        parsed_jd = parse_job_description(jd_text, filename="API_Pasted_JD.txt")

    if not parsed_jd["success"]:
        raise HTTPException(status_code=400, detail=f"Failed to parse JD: {parsed_jd['error']}")

    jd_classification = classify_document(parsed_jd["text"], filename=parsed_jd["filename"])
    if jd_classification["type"] == "RESUME":
        raise HTTPException(status_code=400, detail="The input provided as Job Description was identified as a Resume instead of a Job Description.")

    results = []

    # Process uploaded resumes sequentially
    for res_file in resumes:
        res_bytes = await res_file.read()
        parsed_res = parse_resume(res_bytes, filename=res_file.filename)

        if not parsed_res["success"]:
            results.append({
                "filename": res_file.filename,
                "error": parsed_res["error"],
                "success": False
            })
            continue

        res_classification = classify_document(parsed_res["text"], filename=res_file.filename)
        if res_classification["type"] == "JD":
            results.append({
                "filename": res_file.filename,
                "error": f"File '{res_file.filename}' was identified as a Job Description, not a Resume.",
                "success": False
            })
            continue

        candidate_name = res_classification.get("candidate_name") or parsed_res["candidate_name"]
        if candidate_name == "Not detected":
            candidate_name = parsed_res["candidate_name"]

        analysis = analyze_resume(
            jd_text=parsed_jd["text"],
            resume_text=parsed_res["text"],
            resume_name=res_file.filename,
            detected_name=candidate_name
        )
        analysis["success"] = True
        results.append(analysis)

    successful_results = [r for r in results if r.get("success")]
    summary = format_final_summary(successful_results) if successful_results else ""

    return {
        "job_title": parsed_jd["title"],
        "total_processed": len(resumes),
        "successful_count": len(successful_results),
        "results": results,
        "summary_text": summary
    }


def main():
    """Main entrypoint when running python app.py"""
    logger.info("Initializing AI Resume Matcher application...")

    is_valid, errors = validate_config(require_telegram=False, require_ai=False)
    if errors:
        print("\n=== Configuration Notice ===")
        for err in errors:
            print(f"⚠️  {err}")
        print("Set TELEGRAM_BOT_TOKEN and OPENROUTER_API_KEY in your .env file to enable full features.\n")

    if len(sys.argv) > 1 and sys.argv[1] == "--bot":
        from telegram_bot import run_bot
        run_bot()
    else:
        print(f"🚀 Starting API server on http://localhost:{PORT}")
        print("Tip: To run Telegram bot polling directly, execute: python telegram_bot.py (or python app.py --bot)")
        uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=False)


if __name__ == "__main__":
    main()
