import logging
from pathlib import Path
from resume_parser import parse_pdf, parse_docx, clean_text, MAX_FILE_SIZE_BYTES

logger = logging.getLogger("JDParser")


def extract_job_title(jd_text: str) -> str:
    """
    Attempt to extract a job title from the first few lines of the JD text.
    """
    if not jd_text:
        return "Job Position"
        
    lines = [l.strip() for l in jd_text.split("\n") if l.strip()]
    for line in lines[:5]:
        # Clean line
        cleaned = line.strip("#*: \t-")
        if 5 <= len(cleaned) <= 60 and not cleaned.lower().startswith("about") and not cleaned.lower().startswith("we are"):
            return cleaned
            
    return "Job Position"


def parse_job_description(content: bytes | str, filename: str = "text_jd.txt") -> dict:
    """
    Parses job description provided either as raw bytes (PDF/DOCX) or plain text string.
    """
    try:
        if isinstance(content, bytes):
            if len(content) > MAX_FILE_SIZE_BYTES:
                return {
                    "success": False,
                    "filename": filename,
                    "text": "",
                    "title": "Job Position",
                    "error": "File size exceeds maximum allowed limit (10 MB)."
                }

            ext = Path(filename).suffix.lower()
            if ext == ".pdf":
                raw_text = parse_pdf(content)
            elif ext in [".docx", ".doc"]:
                raw_text = parse_docx(content)
            else:
                raw_text = content.decode("utf-8", errors="ignore")
        else:
            raw_text = content

        cleaned = clean_text(raw_text)
        if not cleaned:
            return {
                "success": False,
                "filename": filename,
                "text": "",
                "title": "Job Position",
                "error": "Job description content is empty."
            }

        job_title = extract_job_title(cleaned)

        return {
            "success": True,
            "filename": filename,
            "text": cleaned,
            "title": job_title,
            "error": None
        }

    except Exception as e:
        logger.error(f"Failed to parse JD file '{filename}': {e}")
        return {
            "success": False,
            "filename": filename,
            "text": "",
            "title": "Job Position",
            "error": f"Failed to read Job Description file: {str(e)}"
        }
