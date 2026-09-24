import os
import sys
from pathlib import Path

# Ensure root directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resume_parser import parse_resume, extract_candidate_name, clean_text
from jd_parser import parse_job_description
from course_recommender import sanitize_and_fill_courses
from ai_analyzer import analyze_resume, fallback_heuristic_analyzer
from formatter import format_resume_analysis, format_final_summary

import io

# Force UTF-8 stdout for Windows console test script
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_pipeline():
    print("=== Testing AI Resume Matcher Pipeline ===")

    # 1. Test JD parsing
    sample_jd = """
    We are looking for a Senior Full Stack Java Developer with:
    - Java, Spring Boot, React, SQL, REST APIs
    - Hands-on experience with Docker, Kubernetes, and AWS cloud deployment.
    - Strong database design, Git version control, and microservices experience.
    """
    parsed_jd = parse_job_description(sample_jd, filename="Sample_JD.txt")
    assert parsed_jd["success"] is True
    print("[OK] JD Parsing Passed:", parsed_jd["title"])

    # 2. Test Resume text parsing & candidate name extraction
    sample_resume_1 = """
    Rahul Kumar
    Software Engineer | Java Developer
    Email: rahul@example.com | Phone: +91 9876543210

    EXPERIENCE
    Java Developer at Tech Corp (2021 - Present)
    - Developed web services using Java, Spring Boot, React, and SQL.
    - Built REST APIs and integrated Git for version control.
    - Worked on microservices architecture.
    """
    
    cand_name = extract_candidate_name(sample_resume_1)
    print("[OK] Candidate Name Extraction Passed:", cand_name)
    assert cand_name == "Rahul Kumar"

    # 3. Test Course Recommender
    missing_skills = ["Docker", "AWS", "Kubernetes"]
    courses = sanitize_and_fill_courses([], missing_skills)
    assert len(courses) == 3
    print("[OK] Course Recommendation Passed:", [c['title'] for c in courses])

    # 4. Test AI Analyzer (Heuristic & Format)
    res_analysis_1 = fallback_heuristic_analyzer(
        jd_text=parsed_jd["text"],
        resume_text=sample_resume_1,
        resume_name="Rahul_Resume.pdf",
        detected_name="Rahul Kumar"
    )
    assert res_analysis_1["overall_score"] > 0
    assert len(res_analysis_1["suggestions"]) == 3
    assert len(res_analysis_1["courses"]) == 3
    print("[OK] Analysis Engine Heuristic Passed! Score:", res_analysis_1["overall_score"])

    # 5. Test Formatter HTML
    formatted_card = format_resume_analysis(res_analysis_1)
    assert "Rahul Kumar" in formatted_card
    assert "Rahul_Resume.pdf" in formatted_card
    assert "OVERALL MATCH SCORE" in formatted_card
    print("[OK] Formatter HTML Card Generation Passed!")

    # 6. Test Summary Table
    sample_resume_2_analysis = {
        "candidate_name": "Priya Sharma",
        "resume_name": "Priya_Resume.pdf",
        "overall_score": 88
    }
    summary_text = format_final_summary([res_analysis_1, sample_resume_2_analysis])
    assert "FINAL RESUME SUMMARY" in summary_text
    print("[OK] Summary Table Formatting Passed!")

    print("\nALL PIPELINE TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_pipeline()
