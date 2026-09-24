import json
import logging
import re
from openai import OpenAI
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENAI_MODEL
from course_recommender import sanitize_and_fill_courses

logger = logging.getLogger("AIAnalyzer")


SYSTEM_PROMPT = """You are an expert recruitment and resume analysis assistant.

Compare the provided Resume against the provided Job Description (JD).
Use ONLY information supported by the resume and JD. Do NOT invent experience, skills, education, certifications, companies, or achievements.

Scoring Methodology (0 to 100):
- Skill Match: 50%
- Experience Match: 20%
- Project/Responsibility Match: 15%
- Education/Certification Match: 10%
- Keyword/ATS Alignment: 5%

Important Rules:
1. Do not treat missing skills as proof that the candidate lacks capability; use neutral wording such as "Not found in the resume".
2. The score must be an integer between 0 and 100 reflecting ATS-style keyword and qualification alignment.
3. Identify all skills explicitly matched.
4. Identify important skills missing or not found in the resume.
5. Provide EXACTLY 3 improvement suggestions. CRITICAL: Each suggestion MUST be a single short concise sentence (maximum 12 words) on 1 single line without paragraph breaks.
6. Provide EXACTLY 3 relevant learning resources/courses corresponding to missing skills.

Return your response strictly in valid JSON matching this schema:
{
  "candidate_name": "Full Candidate Name or 'Not detected'",
  "resume_name": "Filename",
  "job_title": "Target Job Title from JD",
  "overall_score": 85,
  "score_breakdown": {
    "skill_match": "42/50",
    "experience_match": "18/20",
    "projects_match": "12/15",
    "education_match": "9/10",
    "ats_alignment": "4/5"
  },
  "matched_skills": ["Skill1", "Skill2"],
  "missing_skills": ["Skill3", "Skill4"],
  "suggestions": [
    "Build hands-on Docker project experience.",
    "Gain practical AWS deployment exposure.",
    "Master Kubernetes container orchestration."
  ],
  "courses": [
    {
      "title": "Course Title 1",
      "skill": "Skill3",
      "provider": "Provider Name",
      "url": "https://www.coursera.org/search?query=Skill3"
    },
    {
      "title": "Course Title 2",
      "skill": "Skill4",
      "provider": "Provider Name",
      "url": "https://www.coursera.org/search?query=Skill4"
    },
    {
      "title": "Course Title 3",
      "skill": "Skill Name",
      "provider": "Provider Name",
      "url": "https://www.coursera.org/search?query=Skill"
    }
  ]
}
"""


def extract_json_from_response(text: str) -> dict | None:
    """
    Safely extract JSON object from AI string output.
    """
    if not text:
        return None

    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try regex match for ```json ... ``` or { ... }
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def fallback_heuristic_analyzer(jd_text: str, resume_text: str, resume_name: str, detected_name: str) -> dict:
    """
    Fallback deterministic analysis when AI API is unavailable or returns errors.
    Ensures the application always provides a structured response.
    """
    logger.info(f"Running heuristic analysis fallback for '{resume_name}'")
    
    candidate_name = detected_name if detected_name and detected_name != "Not detected" else "Candidate"
    
    common_skills = [
        "Java", "Python", "JavaScript", "TypeScript", "React", "Angular", "Vue",
        "Spring Boot", "Node.js", "Express", "Django", "Flask", "SQL", "PostgreSQL",
        "MySQL", "MongoDB", "REST API", "GraphQL", "Docker", "Kubernetes", "AWS",
        "Azure", "GCP", "Git", "CI/CD", "Linux", "Agile", "Scrum", "C++", "C#", ".NET"
    ]

    jd_lower = jd_text.lower()
    resume_lower = resume_text.lower()

    jd_skills = [s for s in common_skills if s.lower() in jd_lower]
    if not jd_skills:
        jd_skills = ["Java", "Spring Boot", "React", "SQL", "REST API", "Docker", "AWS", "Kubernetes"]

    matched = [s for s in jd_skills if s.lower() in resume_lower]
    missing = [s for s in jd_skills if s.lower() not in resume_lower]

    if not missing:
        missing = ["Cloud Deployment", "Microservices Architecture", "Performance Tuning"]

    match_ratio = len(matched) / max(len(jd_skills), 1)
    skills_pts = int(match_ratio * 50)
    exp_pts = int(match_ratio * 20)
    proj_pts = int(match_ratio * 15)
    edu_pts = 8
    ats_pts = int(match_ratio * 5)
    
    overall_score = min(100, max(20, skills_pts + exp_pts + proj_pts + edu_pts + ats_pts))

    score_breakdown = {
        "skill_match": f"{skills_pts}/50",
        "experience_match": f"{exp_pts}/20",
        "projects_match": f"{proj_pts}/15",
        "education_match": f"{edu_pts}/10",
        "ats_alignment": f"{ats_pts}/5"
    }

    suggestions = [
        f"Build hands-on practical project in {missing[0]}." if len(missing) > 0 else "Expand architectural documentation for key projects.",
        f"Gain exposure to {missing[1]} cloud deployment." if len(missing) > 1 else "Include quantitative metrics for project impact.",
        f"Demonstrate proficiency in {missing[2]} setup." if len(missing) > 2 else "Highlight team leadership and code review experience."
    ]

    courses = sanitize_and_fill_courses([], missing)

    return {
        "candidate_name": candidate_name,
        "resume_name": resume_name,
        "job_title": "Target Role",
        "overall_score": overall_score,
        "score_breakdown": score_breakdown,
        "matched_skills": matched if matched else ["General Software Development"],
        "missing_skills": missing[:5],
        "suggestions": suggestions[:3],
        "courses": courses
    }


def analyze_resume(jd_text: str, resume_text: str, resume_name: str = "resume.pdf", detected_name: str = "Not detected") -> dict:
    """
    Main analysis engine function using OpenRouter / OpenAI compatible client.
    """
    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set. Using heuristic fallback analyzer.")
        return fallback_heuristic_analyzer(jd_text, resume_text, resume_name, detected_name)

    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        timeout=25.0,
        default_headers={
            "HTTP-Referer": "https://github.com/AI-Resume-Matcher",
            "X-Title": "AI Resume Matcher"
        }
    )

    model_name = OPENAI_MODEL
    if model_name == "gpt-4o-mini":
        model_name = "openai/gpt-4o-mini"
    elif model_name == "openrouter/free":
        # Free router model on OpenRouter
        model_name = "openrouter/free"

    user_prompt = f"""
    JOB DESCRIPTION:
    {jd_text[:4000]}

    RESUME (Filename: {resume_name}, Detected Name: {detected_name}):
    {resume_text[:4000]}
    """

    try:
        logger.info(f"Sending analysis request to OpenRouter ({model_name}) for '{resume_name}'...")
        
        # Omit response_format for free router models to ensure broad compatibility across all free models
        req_params = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 1500
        }
        if "gpt" in model_name or "claude" in model_name or "gemini" in model_name:
            req_params["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**req_params)

        if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
            logger.warning("Empty response from AI provider. Using fallback heuristic analyzer.")
            return fallback_heuristic_analyzer(jd_text, resume_text, resume_name, detected_name)

        content = response.choices[0].message.content
        parsed = extract_json_from_response(content)

        if not parsed or not isinstance(parsed, dict):
            logger.warning("Invalid JSON from OpenRouter. Using fallback heuristic analyzer.")
            return fallback_heuristic_analyzer(jd_text, resume_text, resume_name, detected_name)

        score = parsed.get("overall_score", 50)
        try:
            score = int(score)
            score = max(0, min(100, score))
        except (ValueError, TypeError):
            score = 50

        candidate_name = parsed.get("candidate_name", "").strip()
        if not candidate_name or candidate_name == "Not detected":
            candidate_name = detected_name if detected_name != "Not detected" else "Not detected"

        matched_skills = parsed.get("matched_skills", [])
        if not isinstance(matched_skills, list):
            matched_skills = []

        missing_skills = parsed.get("missing_skills", [])
        if not isinstance(missing_skills, list):
            missing_skills = []

        suggestions = parsed.get("suggestions", [])
        if not isinstance(suggestions, list) or len(suggestions) < 3:
            suggestions = [
                "Build practical project experience in core missing skills.",
                "Highlight cloud architecture and deployment practices.",
                "Quantify technical achievements and project impacts."
            ]
        
        # Ensure each suggestion is strictly 1 single line
        clean_suggestions = []
        for s in suggestions[:3]:
            # Replace newlines with spaces and take the first sentence
            single_line = str(s).replace("\n", " ").strip()
            first_sentence = single_line.split(". ")[0].strip()
            if not first_sentence.endswith("."):
                first_sentence += "."
            clean_suggestions.append(first_sentence)
        suggestions = clean_suggestions

        raw_courses = parsed.get("courses", [])
        validated_courses = sanitize_and_fill_courses(raw_courses, missing_skills)

        score_breakdown = parsed.get("score_breakdown", {})
        if not isinstance(score_breakdown, dict):
            score_breakdown = {}

        return {
            "candidate_name": candidate_name,
            "resume_name": resume_name,
            "job_title": parsed.get("job_title", "Target Position"),
            "overall_score": score,
            "score_breakdown": {
                "skill_match": str(score_breakdown.get("skill_match", "40/50")),
                "experience_match": str(score_breakdown.get("experience_match", "15/20")),
                "projects_match": str(score_breakdown.get("projects_match", "12/15")),
                "education_match": str(score_breakdown.get("education_match", "8/10")),
                "ats_alignment": str(score_breakdown.get("ats_alignment", "4/5"))
            },
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "suggestions": suggestions,
            "courses": validated_courses
        }

    except Exception as e:
        logger.exception(f"OpenRouter API error during resume analysis: {e}")
        return fallback_heuristic_analyzer(jd_text, resume_text, resume_name, detected_name)
