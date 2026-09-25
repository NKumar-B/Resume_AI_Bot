import re
import logging
from pathlib import Path
from resume_parser import extract_candidate_name

logger = logging.getLogger("DocClassifier")


def classify_document(text: str, filename: str = "") -> dict:
    """
    Classifies content as either 'JD' (Job Description) or 'RESUME' (Resume/CV).
    
    Returns a dictionary:
    {
        "type": "JD" | "RESUME" | "UNKNOWN",
        "confidence": float (0.0 to 1.0),
        "jd_score": int,
        "resume_score": int,
        "candidate_name": str,
        "reason": str
    }
    """
    if not text or not text.strip():
        return {
            "type": "UNKNOWN",
            "confidence": 0.0,
            "jd_score": 0,
            "resume_score": 0,
            "candidate_name": "Not detected",
            "reason": "Text content is empty."
        }

    text_lower = text.lower()
    fn_lower = Path(filename).name.lower() if filename else ""

    jd_score = 0
    resume_score = 0

    # 1. Filename checks
    if fn_lower:
        jd_filename_tokens = ["jd", "job", "job_description", "job-description", "jobdescription", "posting", "vacancy", "opening", "role_spec", "description", "requirement"]
        resume_filename_tokens = ["resume", "cv", "curriculum", "vitae", "biodata", "profile"]
        
        for token in jd_filename_tokens:
            if token in fn_lower:
                jd_score += 25
                break
                
        for token in resume_filename_tokens:
            if token in fn_lower:
                resume_score += 25
                break

    # 2. Contact Info Signals (Strong Resume Indicator)
    has_email = bool(re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text))
    has_phone = bool(re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)) or bool(re.search(r'\+?\d{10,12}', text))
    has_linkedin = "linkedin.com" in text_lower or "github.com" in text_lower or "portfolio" in text_lower

    if has_email:
        resume_score += 25
    if has_phone:
        resume_score += 20
    if has_linkedin:
        resume_score += 15

    # 3. Resume specific section headers & keywords
    resume_keywords = [
        "curriculum vitae", "resume", "work experience", "employment history",
        "academic background", "technical skills", "personal profile",
        "career objective", "professional summary", "key projects",
        "certifications", "declaration", "hobbies", "languages spoken",
        "achievements", "responsibilities included", "education"
    ]
    for kw in resume_keywords:
        if kw in text_lower:
            resume_score += 10

    # 4. Resume Candidate Name check
    candidate_name = extract_candidate_name(text)
    if candidate_name != "Not detected":
        resume_score += 20

    # 5. Date Ranges (Common in Work Experience on Resumes, e.g. 2020 - 2023, Jan 2019 – Present)
    date_range_match = re.findall(r'(19|20)\d{2}\s*[-–—]\s*((19|20)\d{2}|present|current|now)', text_lower)
    if date_range_match:
        resume_score += min(len(date_range_match) * 8, 30)

    # 6. Job Description (JD) specific section headers & keywords
    jd_keywords = [
        "job description", "job title", "role overview", "about the role", "about the job",
        "job summary", "position summary", "key responsibilities", "responsibilities:",
        "what you will do", "duties and responsibilities", "requirements:", "qualifications:",
        "basic qualifications", "preferred qualifications", "what we are looking for",
        "skills required", "must have:", "nice to have:", "about us", "who we are",
        "about the company", "company profile", "equal opportunity employer",
        "employment type", "full-time", "part-time", "benefits:", "salary range",
        "job location", "reporting to"
    ]
    for kw in jd_keywords:
        if kw in text_lower:
            jd_score += 12

    # 7. Job Description phrasing
    jd_phrases = [
        "we are looking for", "we are hiring", "the ideal candidate will",
        "you will be responsible for", "years of experience required",
        "bachelor's degree required", "ability to work in", "must be proficient in",
        "looking for a", "seeking a", "minimum qualifications", "preferred qualifications"
    ]
    for phrase in jd_phrases:
        if phrase in text_lower:
            jd_score += 15

    logger.info(f"Doc Classification scores for '{filename}': JD={jd_score}, Resume={resume_score}")

    # Decision logic
    if jd_score > resume_score and jd_score >= 15:
        doc_type = "JD"
        confidence = min(1.0, 0.5 + (jd_score - resume_score) / max(jd_score + resume_score, 1))
        reason = f"Identified as Job Description based on job requirements and role indicators (JD Score: {jd_score})."
    elif resume_score > jd_score and resume_score >= 15:
        doc_type = "RESUME"
        confidence = min(1.0, 0.5 + (resume_score - jd_score) / max(jd_score + resume_score, 1))
        reason = f"Identified as Candidate Resume based on experience, candidate contact, or education markers (Resume Score: {resume_score})."
    else:
        # Tie-breaker / Low confidence fallback
        if has_email or has_phone or candidate_name != "Not detected":
            doc_type = "RESUME"
            confidence = 0.6
            reason = "Identified as Resume due to candidate contact info or detected name."
        elif jd_score > 0:
            doc_type = "JD"
            confidence = 0.6
            reason = "Identified as Job Description based on positional keywords."
        else:
            # Default to JD if no resume markers found
            doc_type = "JD"
            confidence = 0.5
            reason = "Default classification as Job Description."

    if doc_type == "JD":
        candidate_name = "Not detected"

    return {
        "type": doc_type,
        "confidence": confidence,
        "jd_score": jd_score,
        "resume_score": resume_score,
        "candidate_name": candidate_name,
        "reason": reason
    }
