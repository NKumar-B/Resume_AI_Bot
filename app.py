import os
import sys
import logging
import asyncio
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from config import PORT, TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY, validate_config
from resume_parser import parse_resume
from jd_parser import parse_job_description
from ai_analyzer import analyze_resume
from formatter import format_final_summary

logger = logging.getLogger("ResumeMatcherApp")

# Create FastAPI application
app = FastAPI(
    title="AI Resume & Job Description Matcher API",
    description="Production-structured REST API & Telegram Bot integration for AI Resume Screening.",
    version="1.0.0"
)


@app.get("/")
async def root():
    """Health check & status endpoint."""
    return {
        "status": "online",
        "service": "AI Resume & Job Description Matcher",
        "telegram_bot_configured": bool(TELEGRAM_BOT_TOKEN),
        "ai_engine_configured": bool(OPENROUTER_API_KEY)
    }


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

        analysis = analyze_resume(
            jd_text=parsed_jd["text"],
            resume_text=parsed_res["text"],
            resume_name=res_file.filename,
            detected_name=parsed_res["candidate_name"]
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
