import os
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List
import httpx

from config import (
    WHATSAPP_API_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_API_VERSION,
    MAX_FILE_SIZE_BYTES
)
from resume_parser import parse_resume
from jd_parser import parse_job_description
from ai_analyzer import analyze_resume
from doc_classifier import classify_document

logger = logging.getLogger("WhatsAppBot")

# In-memory session store keyed by user phone number (wa_id)
whatsapp_sessions: Dict[str, Dict[str, Any]] = {}


def get_whatsapp_session(phone_number: str) -> Dict[str, Any]:
    """Get or initialize user session for a WhatsApp phone number."""
    if phone_number not in whatsapp_sessions:
        whatsapp_sessions[phone_number] = {
            "state": "WAITING_FOR_JD",
            "jd_text": "",
            "jd_filename": "",
            "resumes": [],
            "results": []
        }
    return whatsapp_sessions[phone_number]


def reset_whatsapp_session(phone_number: str) -> Dict[str, Any]:
    """Reset user session for a WhatsApp phone number."""
    whatsapp_sessions[phone_number] = {
        "state": "WAITING_FOR_JD",
        "jd_text": "",
        "jd_filename": "",
        "resumes": [],
        "results": []
    }
    return whatsapp_sessions[phone_number]


async def send_whatsapp_message(to_phone: str, text: str) -> bool:
    """
    Send text message to a WhatsApp user using Meta WhatsApp Business Cloud API.
    Fallback to logging if API credentials are not set (for dry runs / testing).
    """
    if not WHATSAPP_API_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.warning(f"WhatsApp credentials not set. Simulated sending to {to_phone}")
        try:
            print(f"\n[WHATSAPP MOCK OUTBOUND -> {to_phone}]\n{text}\n")
        except Exception:
            logger.info(f"[WHATSAPP MOCK OUTBOUND -> {to_phone}]\n{text}")
        return True

    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # WhatsApp API max message length is 4096 chars
    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]

    async with httpx.AsyncClient(verify=False, timeout=20.0) as client:
        for chunk in chunks:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_phone,
                "type": "text",
                "text": {"preview_url": False, "body": chunk}
            }
            try:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code not in [200, 201]:
                    logger.error(f"Failed to send WhatsApp message to {to_phone}: {resp.status_code} - {resp.text}")
                    return False
            except Exception as e:
                logger.exception(f"Error sending WhatsApp message to {to_phone}: {e}")
                return False

    return True


async def download_whatsapp_media(media_id_or_url: str) -> bytes | None:
    """
    Downloads media file bytes from Meta WhatsApp API (or direct URL).
    """
    if not media_id_or_url:
        return None

    # If already a direct HTTP/HTTPS URL (e.g. Twilio Media URL)
    if media_id_or_url.startswith("http://") or media_id_or_url.startswith("https://"):
        try:
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                res = await client.get(media_id_or_url)
                return res.content if res.status_code == 200 else None
        except Exception as e:
            logger.error(f"Error downloading media from URL {media_id_or_url}: {e}")
            return None

    if not WHATSAPP_API_TOKEN:
        logger.warning(f"Cannot download media {media_id_or_url}: WHATSAPP_API_TOKEN is missing.")
        return None

    # Meta Cloud API media download 2-step process
    meta_url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{media_id_or_url}"
    headers = {"Authorization": f"Bearer {WHATSAPP_API_TOKEN}"}

    try:
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            meta_resp = await client.get(meta_url, headers=headers)
            if meta_resp.status_code != 200:
                logger.error(f"Failed to fetch media metadata for {media_id_or_url}: {meta_resp.text}")
                return None

            download_url = meta_resp.json().get("url")
            if not download_url:
                return None

            media_resp = await client.get(download_url, headers=headers)
            if media_resp.status_code == 200:
                return media_resp.content
            else:
                logger.error(f"Failed to download media binary from {download_url}: {media_resp.status_code}")
                return None

    except Exception as e:
        logger.exception(f"Exception downloading WhatsApp media {media_id_or_url}: {e}")
        return None


def format_whatsapp_analysis(result: dict) -> str:
    """
    Formats individual candidate analysis for WhatsApp using WhatsApp Markdown (*bold*, _italic_).
    """
    candidate_name = result.get("candidate_name", "Not detected")
    resume_name = result.get("resume_name", "resume.pdf")
    score = result.get("overall_score", 0)

    matched_skills = result.get("matched_skills", [])
    missing_skills = result.get("missing_skills", [])
    suggestions = result.get("suggestions", [])
    courses = result.get("courses", [])

    matched_str = "\n".join([f"• {s}" for s in matched_skills]) if matched_skills else "• None explicitly identified"
    missing_str = "\n".join([f"• {s}" for s in missing_skills]) if missing_skills else "• No significant gaps identified"
    sugg_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(suggestions)]) if suggestions else "1. Tailor metrics to match core JD skills."

    course_items = []
    for i, c in enumerate(courses):
        title = c.get("title", "Course")
        provider = c.get("provider", "Coursera")
        url = c.get("url", "#")
        course_items.append(f"{i+1}. *{title}*\n   Provider: {provider}\n   Link: {url}")
    course_str = "\n\n".join(course_items) if course_items else "1. Coursera Professional Certificates\n   Link: https://www.coursera.org"

    score_bd = result.get("score_breakdown", {})
    skill_pts = score_bd.get("skill_match", "40/50")
    exp_pts = score_bd.get("experience_match", "15/20")
    proj_pts = score_bd.get("projects_match", "12/15")
    edu_pts = score_bd.get("education_match", "8/10")
    ats_pts = score_bd.get("ats_alignment", "4/5")

    return (
        f"──────────────────────────\n"
        f"📄 *RESUME ANALYSIS*\n"
        f"──────────────────────────\n\n"
        f"*Candidate:* {candidate_name}\n"
        f"*Resume:* {resume_name}\n\n"
        f"🎯 *OVERALL MATCH SCORE:* *{score}%*\n\n"
        f"📊 *Score Breakdown:*\n"
        f"• Skill Match: *{skill_pts}* (50% max)\n"
        f"• Experience Match: *{exp_pts}* (20% max)\n"
        f"• Project Relevance: *{proj_pts}* (15% max)\n"
        f"• Education & Certs: *{edu_pts}* (10% max)\n"
        f"• ATS Alignment: *{ats_pts}* (5% max)\n\n"
        f"✅ *MATCHED SKILLS*\n{matched_str}\n\n"
        f"❌ *MISSING SKILLS*\n{missing_str}\n\n"
        f"💡 *IMPROVEMENT SUGGESTIONS*\n{sugg_str}\n\n"
        f"🎓 *RECOMMENDED COURSES*\n{course_str}\n"
        f"──────────────────────────"
    )


def format_whatsapp_summary(results: list) -> str:
    """
    Formats final summary comparison table for WhatsApp.
    """
    if not results:
        return "No resumes analyzed yet."

    sorted_results = sorted(results, key=lambda x: x.get("overall_score", 0), reverse=True)

    lines = [
        "🏆 *FINAL RESUME SUMMARY TABLE*",
        "──────────────────────────"
    ]
    for idx, r in enumerate(sorted_results, start=1):
        filename = r.get("resume_name", "resume.pdf")
        cand_name = r.get("candidate_name", "Candidate")
        score = r.get("overall_score", 0)
        lines.append(f"{idx}. *{cand_name}* ({filename}) ➔ *{score}%* Match")

    lines.append("──────────────────────────")
    lines.append("ℹ️ _Scores based on ATS alignment with job description qualifications._")
    return "\n".join(lines)


async def handle_whatsapp_command_or_text(phone_number: str, text: str):
    """
    Process incoming text message or command from a WhatsApp user.
    """
    session = get_whatsapp_session(phone_number)
    text_clean = text.strip()
    text_lower = text_clean.lower()

    # Commands: /start, hello, hi, /help, /reset, /analyze
    if text_lower in ["/start", "start", "hello", "hi", "hey"]:
        welcome_msg = (
            "Welcome to *AI Resume Matcher* on WhatsApp! 🤖\n\n"
            "I can analyze multiple candidate resumes against a Job Description and provide:\n"
            "• Overall Match Score & Breakdown\n"
            "• Skill Gap Analysis\n"
            "• Improvement Suggestions\n"
            "• Recommended Courses\n"
            "• Final Candidate Comparison\n\n"
            "📌 *Step 1:* Please send or upload the *Job Description* (as text, PDF, or DOCX)."
        )
        await send_whatsapp_message(phone_number, welcome_msg)
        return

    if text_lower in ["/help", "help"]:
        help_msg = (
            "📋 *AI Resume Matcher WhatsApp Guide*\n\n"
            "*Commands:*\n"
            "• `/start` or `Hello` - Start session\n"
            "• `/help` - Show instructions\n"
            "• `/reset` - Clear current JD and uploaded resumes\n"
            "• `/analyze` - Run AI match analysis on all uploaded resumes\n\n"
            "*Workflow:*\n"
            "1. Send or upload the Job Description (text/PDF/DOCX)\n"
            "2. Upload one or more candidate resumes (PDF/DOCX)\n"
            "3. Send `/analyze` to process all candidates!"
        )
        await send_whatsapp_message(phone_number, help_msg)
        return

    if text_lower in ["/reset", "reset"]:
        reset_whatsapp_session(phone_number)
        await send_whatsapp_message(
            phone_number,
            "🔄 *Session Reset Successfully!*\n\nPlease send a new *Job Description* to begin."
        )
        return

    if text_lower in ["/analyze", "analyze"]:
        if not session["jd_text"]:
            await send_whatsapp_message(
                phone_number,
                "⚠️ *No Job Description found.*\n\nPlease send or upload a Job Description first."
            )
            return

        if not session["resumes"]:
            await send_whatsapp_message(
                phone_number,
                "⚠️ *No resumes uploaded.*\n\nPlease upload at least one PDF or DOCX resume before running `/analyze`."
            )
            return

        await send_whatsapp_message(
            phone_number,
            f"🔄 *Starting AI analysis for {len(session['resumes'])} candidate resume(s)...*"
        )

        session["results"] = []
        total = len(session["resumes"])

        for idx, res_item in enumerate(session["resumes"], start=1):
            filename = res_item["filename"]
            await send_whatsapp_message(phone_number, f"📄 Processing {idx}/{total}: *{filename}*...")

            try:
                analysis = analyze_resume(
                    jd_text=session["jd_text"],
                    resume_text=res_item["text"],
                    resume_name=filename,
                    detected_name=res_item["candidate_name"]
                )
                session["results"].append(analysis)
                card_text = format_whatsapp_analysis(analysis)
                await send_whatsapp_message(phone_number, card_text)

            except Exception as e:
                logger.exception(f"Error analyzing resume '{filename}': {e}")
                await send_whatsapp_message(phone_number, f"❌ Error analyzing *{filename}*: {str(e)}")

        # Send final summary
        summary = format_whatsapp_summary(session["results"])
        await send_whatsapp_message(phone_number, summary)
        await send_whatsapp_message(
            phone_number,
            "✅ *Analysis Complete!*\n\nYou can upload more resumes anytime to add to this JD, or send `/reset` for a new JD."
        )
        return

    # Regular text input (Pasted text JD or Resume)
    classification = classify_document(text_clean, filename="Pasted_Text.txt")
    doc_type = classification["type"]

    if doc_type == "JD":
        parsed_jd = parse_job_description(text_clean, filename="Pasted_JD.txt")
        session["jd_text"] = parsed_jd["text"]
        session["jd_filename"] = "Pasted Job Description"
        session["state"] = "WAITING_FOR_RESUMES"

        if not session["resumes"]:
            await send_whatsapp_message(
                phone_number,
                f"✅ *Job Description Received!*\n\n"
                f"📌 *Position:* {parsed_jd['title']}\n\n"
                f"Now upload candidate *Resume(s)* (PDF or DOCX)."
            )
        else:
            await send_whatsapp_message(
                phone_number,
                f"✅ *Job Description Updated:* *{parsed_jd['title']}*\n\n"
                f"You have {len(session['resumes'])} resume(s) in queue. Send `/analyze` to start analysis."
            )

    elif doc_type == "RESUME":
        candidate_name = classification.get("candidate_name", "Not detected")
        res_filename = f"Pasted_Resume_{len(session['resumes']) + 1}.txt"

        session["resumes"].append({
            "filename": res_filename,
            "text": text_clean,
            "candidate_name": candidate_name
        })

        if not session["jd_text"]:
            session["state"] = "WAITING_FOR_JD"
            await send_whatsapp_message(
                phone_number,
                f"📄 *Pasted Resume Queued:* Candidate: *{candidate_name}*\n\n"
                f"⚠️ *Job Description Required!*\n"
                f"I detected that you sent a Resume, but no Job Description has been set yet.\n"
                f"Please send the *Job Description* to begin analysis."
            )
        else:
            session["state"] = "WAITING_FOR_RESUMES"
            await send_whatsapp_message(
                phone_number,
                f"📄 *Resume Queued!* Total queued: *{len(session['resumes'])}*\n\n"
                f"Send more resumes or send `/analyze` when ready."
            )
    else:
        # Default handling if unclassified plain text
        if not session["jd_text"]:
            parsed_jd = parse_job_description(text_clean, filename="Pasted_JD.txt")
            session["jd_text"] = parsed_jd["text"]
            session["jd_filename"] = "Pasted Job Description"
            session["state"] = "WAITING_FOR_RESUMES"
            await send_whatsapp_message(
                phone_number,
                f"✅ *Job Description Received!*\n\n📌 *Position:* {parsed_jd['title']}\n\n"
                f"Now send candidate *Resume(s)*."
            )
        else:
            await send_whatsapp_message(
                phone_number,
                f"📄 Message received. You have {len(session['resumes'])} resume(s) queued.\nSend `/analyze` to run analysis or `/help` for instructions."
            )


async def handle_whatsapp_document(phone_number: str, file_bytes: bytes, filename: str):
    """
    Process incoming document upload (PDF, DOCX) from a WhatsApp user.
    """
    session = get_whatsapp_session(phone_number)

    parsed_res = parse_resume(file_bytes, filename=filename)
    if not parsed_res["success"]:
        await send_whatsapp_message(phone_number, f"❌ Unable to read *{filename}*: {parsed_res['error']}")
        return

    raw_text = parsed_res["text"]
    classification = classify_document(raw_text, filename=filename)
    doc_type = classification["type"]

    if doc_type == "JD":
        parsed_jd = parse_job_description(file_bytes, filename=filename)
        session["jd_text"] = parsed_jd["text"]
        session["jd_filename"] = filename
        session["state"] = "WAITING_FOR_RESUMES"

        if not session["resumes"]:
            await send_whatsapp_message(
                phone_number,
                f"✅ *Job Description Identified & Received!*\n\n"
                f"📌 *Position:* {parsed_jd['title']}\n"
                f"📁 *File:* `{filename}`\n\n"
                f"Now upload one or more candidate *Resumes* (PDF or DOCX)."
            )
        else:
            await send_whatsapp_message(
                phone_number,
                f"✅ *Job Description Updated:* *{parsed_jd['title']}*\n\n"
                f"You have {len(session['resumes'])} resume(s) in queue. Send `/analyze` to start analysis."
            )

    elif doc_type == "RESUME":
        # Deduplicate filename if needed
        existing_names = [r["filename"].lower() for r in session["resumes"]]
        if filename.lower() in existing_names:
            count = 1
            stem = Path(filename).stem
            ext_str = Path(filename).suffix
            new_filename = f"{stem}_{count}{ext_str}"
            while new_filename.lower() in existing_names:
                count += 1
                new_filename = f"{stem}_{count}{ext_str}"
            filename = new_filename

        candidate_name = classification.get("candidate_name") or parsed_res.get("candidate_name") or "Not detected"
        if candidate_name == "Not detected":
            candidate_name = parsed_res.get("candidate_name", "Not detected")

        session["resumes"].append({
            "filename": filename,
            "text": raw_text,
            "candidate_name": candidate_name
        })

        if not session["jd_text"]:
            session["state"] = "WAITING_FOR_JD"
            await send_whatsapp_message(
                phone_number,
                f"📄 *Resume Identified & Queued:* `{filename}`\n"
                f"👤 *Candidate:* {candidate_name}\n\n"
                f"⚠️ *Job Description Required!*\n"
                f"I detected that you uploaded a Resume, but no Job Description has been provided yet.\n\n"
                f"Please upload or send the *Job Description* so I can perform resume analysis."
            )
        else:
            session["state"] = "WAITING_FOR_RESUMES"
            await send_whatsapp_message(
                phone_number,
                f"📄 *Resume Queued:* `{filename}` (Candidate: *{candidate_name}*)\n"
                f"Total Resumes Queued: *{len(session['resumes'])}*\n\n"
                f"Upload more resumes or send `/analyze` when ready!"
            )
    else:
        # Fallback based on state
        if session["state"] == "WAITING_FOR_JD" and not session["jd_text"]:
            parsed_jd = parse_job_description(file_bytes, filename=filename)
            session["jd_text"] = parsed_jd["text"]
            session["jd_filename"] = filename
            session["state"] = "WAITING_FOR_RESUMES"
            await send_whatsapp_message(
                phone_number,
                f"✅ *Job Description Received!*\n\n"
                f"📌 *Position:* {parsed_jd['title']}\n\n"
                f"Now send candidate *Resumes* (PDF or DOCX)."
            )
        else:
            session["resumes"].append({
                "filename": filename,
                "text": raw_text,
                "candidate_name": parsed_res.get("candidate_name", "Not detected")
            })
            await send_whatsapp_message(
                phone_number,
                f"📄 *Document Queued:* `{filename}`\nTotal Queued: *{len(session['resumes'])}*\n\nSend `/analyze` when ready."
            )


async def process_whatsapp_webhook_payload(payload: dict):
    """
    Main webhook entrypoint processing incoming Meta Cloud API or Twilio payloads.
    """
    try:
        # 1. Check for Meta WhatsApp Cloud API format
        entry = payload.get("entry", [])
        if entry:
            for e in entry:
                for change in e.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    for msg in messages:
                        from_number = msg.get("from")
                        msg_type = msg.get("type")

                        if msg_type == "text":
                            text_body = msg.get("text", {}).get("body", "")
                            await handle_whatsapp_command_or_text(from_number, text_body)

                        elif msg_type in ["document", "image"]:
                            doc_info = msg.get("document", {}) or msg.get("image", {})
                            media_id = doc_info.get("id")
                            filename = doc_info.get("filename") or "document.pdf"

                            if media_id:
                                file_bytes = await download_whatsapp_media(media_id)
                                if file_bytes:
                                    await handle_whatsapp_document(from_number, file_bytes, filename)
                                else:
                                    await send_whatsapp_message(from_number, f"❌ Failed to download file '{filename}'. Please try sending again.")
            return

        # 2. Check for Twilio / Form-data JSON payload fallback
        from_number = payload.get("From", "").replace("whatsapp:", "").strip()
        body = payload.get("Body", "").strip()
        media_url = payload.get("MediaUrl0", "").strip()

        if from_number:
            if media_url:
                filename = payload.get("MediaFilename0") or "uploaded_document.pdf"
                file_bytes = await download_whatsapp_media(media_url)
                if file_bytes:
                    await handle_whatsapp_document(from_number, file_bytes, filename)
                else:
                    await send_whatsapp_message(from_number, f"❌ Failed to download attachment. Please try sending again.")
            elif body:
                await handle_whatsapp_command_or_text(from_number, body)

    except Exception as e:
        logger.exception(f"Error processing WhatsApp webhook payload: {e}")
