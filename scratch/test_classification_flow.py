import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from doc_classifier import classify_document

sample_jd_text = """
Job Title: Full Stack Developer
Company: Acme Systems
Responsibilities:
- Develop web applications using Python, FastAPI, and React
- Maintain PostgreSQL database
- Manage CI/CD pipelines
Requirements:
- 3+ years experience in web development
- Bachelor's degree in Computer Science
- Proficient in SQL and Docker
"""

sample_resume_text = """
Alice Johnson
Email: alice.j@example.com | Phone: +1-555-0188 | GitHub: github.com/alicej
Summary:
Experienced Software Developer with 4 years of experience building web applications.
Work History:
Software Developer | TechCorp (2022 - Present)
- Developed APIs using Python, FastAPI and Flask
- Created frontend components using React
Education:
B.Tech in Information Technology, 2022
Skills: Python, FastAPI, React, SQL, Git, Docker
"""

def test_flow():
    print("=== Testing Document Classification Routing ===")
    
    # Test 1: Uploading JD text/file
    jd_res = classify_document(sample_jd_text, filename="Job_Spec.pdf")
    print("JD Classification:", jd_res)
    assert jd_res["type"] == "JD"

    # Test 2: Uploading Resume text/file when JD expected
    resume_as_jd_res = classify_document(sample_resume_text, filename="Resume_Alice.pdf")
    print("Resume when JD expected:", resume_as_jd_res)
    assert resume_as_jd_res["type"] == "RESUME"
    # Should NOT be classified as JD!
    assert resume_as_jd_res["type"] != "JD"

    # Test 3: Uploading JD text/file when Resume expected
    jd_as_resume_res = classify_document(sample_jd_text, filename="Requirement_Doc.docx")
    print("JD when Resume expected:", jd_as_resume_res)
    assert jd_as_resume_res["type"] == "JD"
    # Should NOT be classified as RESUME!
    assert jd_as_resume_res["type"] != "RESUME"

    print("ALL CLASSIFICATION ROUTING TESTS PASSED!")

if __name__ == "__main__":
    test_flow()
