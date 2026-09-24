import os
import html
import logging
import asyncio
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from config import TELEGRAM_BOT_TOKEN, MAX_FILE_SIZE_BYTES, validate_config
from resume_parser import parse_resume
from jd_parser import parse_job_description
from ai_analyzer import analyze_resume
from formatter import format_resume_analysis, format_final_summary

logger = logging.getLogger("TelegramBot")

# In-memory session store
sessions = {}


def get_user_session(user_id: int) -> dict:
    """Get or initialize user session."""
    if user_id not in sessions:
        sessions[user_id] = {
            "state": "WAITING_FOR_JD",
            "jd_text": "",
            "jd_filename": "",
            "resumes": [],
            "results": [],
            "last_status_msg_id": None
        }
    return sessions[user_id]


async def download_file_with_retry(context: ContextTypes.DEFAULT_TYPE, file_id: str, max_retries: int = 3) -> bytearray:
    """Robust download helper with retry logic for Telegram file downloads."""
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            telegram_file = await context.bot.get_file(file_id, read_timeout=30, connect_timeout=30)
            file_bytes = await telegram_file.download_as_bytearray()
            return file_bytes
        except Exception as e:
            last_err = e
            logger.warning(f"Telegram file download attempt {attempt}/{max_retries} failed: {e}")
            await asyncio.sleep(1)
    raise last_err if last_err else Exception("Download failed after retries")


async def update_resume_status_message(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict):
    """
    Updates or posts a consolidated list of uploaded resumes with count and Analyze button.
    Edits existing message in-place to prevent individual upload message spam.
    """
    resumes = session.get("resumes", [])
    total_count = len(resumes)
    user_id = update.effective_user.id

    file_list_str = "\n".join([f"  {i}. <code>{html.escape(r['filename'])}</code>" for i, r in enumerate(resumes, start=1)])

    status_text = (
        f"📄 <b>RESUMES QUEUED FOR ANALYSIS ({total_count})</b>\n"
        f"──────────────────────────\n"
        f"{file_list_str}\n\n"
        f"📎 <i>Upload more resumes anytime or tap below to analyze:</i>"
    )

    btn_label = f"⚡ ANALYZE {total_count} RESUME{'S' if total_count > 1 else ''} NOW"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(btn_label, callback_data="run_analyze")],
        [InlineKeyboardButton("🔄 Reset Session", callback_data="run_reset")]
    ])

    last_msg_id = session.get("last_status_msg_id")

    if last_msg_id:
        try:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=last_msg_id,
                text=status_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return
        except Exception as e:
            logger.debug(f"Could not edit previous status message: {e}")

    # Fallback to sending new message if edit fails or first upload
    new_msg = await update.message.reply_text(
        status_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    session["last_status_msg_id"] = new_msg.message_id


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command."""
    user_id = update.effective_user.id
    sessions[user_id] = {
        "state": "WAITING_FOR_JD",
        "jd_text": "",
        "jd_filename": "",
        "resumes": [],
        "results": [],
        "last_status_msg_id": None
    }

    welcome_text = (
        "Welcome to <b>AI Resume Matcher</b>.\n\n"
        "I can compare multiple resumes against a Job Description and provide:\n\n"
        "• Overall Match Score\n"
        "• Skill Match\n"
        "• Skill Mismatch\n"
        "• 3 Concise 1-Line Improvement Suggestions\n"
        "• 3 Relevant Courses\n"
        "• Final Candidate Comparison\n\n"
        "First, please upload or paste the Job Description."
    )
    await update.message.reply_text(welcome_text, parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help command."""
    help_text = (
        "<b>AI Resume Matcher Guide</b>\n\n"
        "<b>Commands:</b>\n"
        "/start - Start or restart the bot session\n"
        "/help - Display this help guide\n"
        "/reset - Clear current JD and uploaded resumes\n"
        "/analyze - Start analyzing all uploaded resumes\n\n"
        "<b>Workflow:</b>\n"
        "1. Send Job Description (upload PDF/DOCX or paste text)\n"
        "2. Upload one or more resumes (PDF/DOCX)\n"
        "3. Tap the ⚡ <b>ANALYZE RESUMES NOW</b> button or send /analyze."
    )
    await update.message.reply_text(help_text, parse_mode="HTML")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /reset command."""
    user_id = update.effective_user.id
    sessions[user_id] = {
        "state": "WAITING_FOR_JD",
        "jd_text": "",
        "jd_filename": "",
        "resumes": [],
        "results": [],
        "last_status_msg_id": None
    }
    reset_text = (
        "🔄 Session reset successfully.\n\n"
        "Please upload a new Job Description to begin."
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(reset_text)
    else:
        await update.message.reply_text(reset_text)


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /analyze command."""
    user_id = update.effective_user.id
    session = get_user_session(user_id)

    reply_target = update.message if update.message else (update.callback_query.message if update.callback_query else None)

    if not session["jd_text"]:
        if reply_target:
            await reply_target.reply_text("⚠️ No Job Description found.\n\nPlease upload or paste a Job Description first.")
        return

    if not session["resumes"]:
        if reply_target:
            await reply_target.reply_text("⚠️ No resumes uploaded.\n\nPlease upload at least one PDF or DOCX resume before running analysis.")
        return

    session["state"] = "ANALYZING"
    total_resumes = len(session["resumes"])

    if reply_target:
        await reply_target.reply_text("🔄 Starting resume analysis...")

    session["results"] = []

    for idx, res_item in enumerate(session["resumes"], start=1):
        filename = res_item["filename"]
        resume_text = res_item["text"]
        detected_name = res_item["candidate_name"]

        if reply_target:
            await reply_target.reply_text(f"📄 Processing {idx}/{total_resumes} ({filename})...")

        try:
            result = analyze_resume(
                jd_text=session["jd_text"],
                resume_text=resume_text,
                resume_name=filename,
                detected_name=detected_name
            )

            session["results"].append(result)

            card_text = format_resume_analysis(result)
            if reply_target:
                await reply_target.reply_text(card_text, parse_mode="HTML", disable_web_page_preview=True)

        except Exception as e:
            logger.exception(f"Error analyzing resume '{filename}': {e}")
            if reply_target:
                await reply_target.reply_text(f"❌ Error processing resume '{filename}': {str(e)}")

    if reply_target:
        await reply_target.reply_text("✅ Analysis completed successfully.")
        summary_text = format_final_summary(session["results"])
        await reply_target.reply_text(summary_text, parse_mode="HTML")

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ ANALYZE ALL RESUMES", callback_data="run_analyze")],
            [InlineKeyboardButton("🔄 Start New Job Description (/reset)", callback_data="run_reset")]
        ])
        await reply_target.reply_text(
            f"📊 <b>Analysis Complete for {len(session['results'])} candidate(s)!</b>\n\n"
            "You can upload more resumes anytime to add to this Job Description, or tap below:",
            parse_mode="HTML",
            reply_markup=keyboard
        )

    session["state"] = "WAITING_FOR_RESUMES"
    session["last_status_msg_id"] = None


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for Telegram inline keyboard button taps."""
    query = update.callback_query
    await query.answer()

    if query.data == "run_analyze":
        await analyze_command(update, context)
    elif query.data == "run_reset":
        await reset_command(update, context)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for document uploads (PDF, DOCX)."""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    doc = update.message.document

    if not doc:
        return

    filename = doc.file_name or "document.pdf"
    file_size = doc.file_size or 0

    if file_size > MAX_FILE_SIZE_BYTES:
        await update.message.reply_text(
            f"❌ File '{filename}' is too large.\n\nPlease upload a file smaller than 10 MB."
        )
        return

    ext = Path(filename).suffix.lower()
    if ext not in [".pdf", ".docx", ".doc"]:
        await update.message.reply_text(
            f"❌ Unsupported file format for '{filename}'.\n\nPlease upload a valid PDF or DOCX file."
        )
        return

    # Download file bytes with retry logic
    try:
        file_bytes = await download_file_with_retry(context, doc.file_id)
    except Exception as e:
        logger.error(f"Telegram file download failed for '{filename}': {e}")
        await update.message.reply_text(
            f"❌ Failed to download '{filename}' from Telegram. Please try uploading again."
        )
        return

    if session["state"] == "WAITING_FOR_JD":
        parsed_jd = parse_job_description(bytes(file_bytes), filename=filename)
        if not parsed_jd["success"]:
            await update.message.reply_text(
                f"❌ Failed to parse Job Description file: {parsed_jd['error']}"
            )
            return

        session["jd_text"] = parsed_jd["text"]
        session["jd_filename"] = filename
        session["state"] = "WAITING_FOR_RESUMES"

        await update.message.reply_text(
            "✅ <b>Job Description received successfully.</b>\n\n"
            "Now upload one or more resumes.\n"
            "📎 <i>Use the paperclip icon below to select and send PDF or DOCX file(s).</i>",
            parse_mode="HTML"
        )

    elif session["state"] in ["WAITING_FOR_RESUMES", "ANALYZING"]:
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

        parsed_res = parse_resume(bytes(file_bytes), filename=filename)
        if not parsed_res["success"]:
            await update.message.reply_text(
                f"❌ Unable to read '{filename}'.\n{parsed_res['error']}"
            )
            return

        session["resumes"].append({
            "filename": filename,
            "text": parsed_res["text"],
            "candidate_name": parsed_res["candidate_name"]
        })

        # Dynamically update consolidated status message without individual message spam
        await update_resume_status_message(update, context, session)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for plain text messages."""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    text = update.message.text.strip()

    if session["state"] == "WAITING_FOR_JD":
        parsed_jd = parse_job_description(text, filename="Pasted_JD.txt")
        if not parsed_jd["success"]:
            await update.message.reply_text(
                f"❌ Unable to read Job Description: {parsed_jd['error']}"
            )
            return

        session["jd_text"] = parsed_jd["text"]
        session["jd_filename"] = "Pasted Job Description"
        session["state"] = "WAITING_FOR_RESUMES"

        await update.message.reply_text(
            "✅ <b>Job Description received successfully.</b>\n\n"
            "Now upload one or more resumes.\n"
            "📎 <i>Use the paperclip icon below to select and send PDF or DOCX file(s).</i>",
            parse_mode="HTML"
        )
    elif session["state"] == "WAITING_FOR_RESUMES":
        await update_resume_status_message(update, context, session)


def build_application():
    """Build python-telegram-bot application instance."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment or .env file.")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("analyze", analyze_command))

    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))

    return app


def run_bot():
    """Start Telegram Bot polling mode."""
    logger.info("Starting Telegram Bot...")
    is_valid, errors = validate_config(require_telegram=True, require_ai=False)
    if not is_valid:
        print("\n".join(errors))
        return

    app = build_application()
    print("🤖 Telegram Bot is running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    run_bot()
