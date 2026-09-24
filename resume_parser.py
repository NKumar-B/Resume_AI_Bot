import io
import re
import logging
from pathlib import Path
from pypdf import PdfReader
import docx

logger = logging.getLogger("ResumeParser")

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit


def extract_candidate_name(text: str) -> str:
    """
    Extract candidate name from the top lines of resume text using heuristics.
    Returns 'Not detected' if a high confidence name is not found.
    """
    if not text:
        return "Not detected"

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    top_lines = lines[:10]  # Check first 10 non-empty lines

    # Exclude common non-name headers/labels
    exclude_words = {
        "resume", "curriculum", "vitae", "cv", "profile", "contact",
        "experience", "education", "skills", "summary", "objective",
        "phone", "email", "address", "linkedin", "github", "portfolio",
        "page", "details", "work", "job", "description"
    }

    for line in top_lines:
        # Skip if contains email, URL, or numbers
        if "@" in line or "http" in line or "www." in line or re.search(r'\d', line):
            continue

        # Clean punctuation except hyphens and spaces
        cleaned = re.sub(r'[^a-zA-Z\s\-]', '', line).strip()
        words = cleaned.split()

        # Most candidate names are 2 to 4 capitalized words
        if 2 <= len(words) <= 4:
            lower_words = [w.lower() for w in words]
            if not any(w in exclude_words for w in lower_words):
                # Check capitalization pattern
                if all(w[0].isupper() for w in words if len(w) > 0):
                    return " ".join(words)

    return "Not detected"


def clean_text(raw_text: str) -> str:
    """
    Clean whitespace, strip null bytes and normalize line breaks.
    """
    if not raw_text:
        return ""
    # Remove null characters
    text = raw_text.replace("\x00", " ")
    # Replace multiple spaces with a single space
    text = re.sub(r'[ \t]+', ' ', text)
    # Replace more than 3 consecutive newlines with 2 newlines
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    return text.strip()


def parse_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF file bytes."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        extracted_text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                extracted_text.append(page_text)
        return "\n".join(extracted_text)
    except Exception as e:
        logger.error(f"Error reading PDF bytes: {e}")
        raise ValueError(f"Failed to parse PDF file: {str(e)}")


def parse_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX file bytes."""
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        extracted_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                extracted_text.append(para.text.strip())
        
        # Also extract text from tables if any
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    extracted_text.append(" | ".join(row_text))

        return "\n".join(extracted_text)
    except Exception as e:
        logger.error(f"Error reading DOCX bytes: {e}")
        raise ValueError(f"Failed to parse DOCX file: {str(e)}")


def parse_resume(file_bytes: bytes, filename: str) -> dict:
    """
    Main parser entrypoint.
    Determines file type from extension/filename, extracts text, cleans it,
    attempts candidate name extraction, and returns structured result dict.
    """
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        return {
            "success": False,
            "filename": filename,
            "text": "",
            "candidate_name": "Not detected",
            "error": "File size exceeds maximum allowed limit (10 MB)."
        }

    ext = Path(filename).suffix.lower()
    
    try:
        if ext == ".pdf":
            raw_text = parse_pdf(file_bytes)
        elif ext in [".docx", ".doc"]:
            raw_text = parse_docx(file_bytes)
        else:
            return {
                "success": False,
                "filename": filename,
                "text": "",
                "candidate_name": "Not detected",
                "error": f"Unsupported file extension '{ext}'. Only PDF and DOCX files are supported."
            }

        cleaned = clean_text(raw_text)
        if not cleaned:
            return {
                "success": False,
                "filename": filename,
                "text": "",
                "candidate_name": "Not detected",
                "error": "Resume file appears to be empty or contains unreadable scanned images."
            }

        candidate_name = extract_candidate_name(cleaned)

        return {
            "success": True,
            "filename": filename,
            "text": cleaned,
            "candidate_name": candidate_name,
            "error": None
        }

    except Exception as e:
        logger.exception(f"Unexpected error parsing resume '{filename}': {e}")
        return {
            "success": False,
            "filename": filename,
            "text": "",
            "candidate_name": "Not detected",
            "error": f"Unable to read '{filename}'. Please upload a valid PDF or DOCX resume."
        }
