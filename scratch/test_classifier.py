from doc_classifier import classify_document

sample_jd = """
Senior Python Developer - Job Description
About Us: We are a fast-growing tech company looking for an experienced Python developer.
Key Responsibilities:
- Build scalable REST APIs using Django and FastAPI
- Work with PostgreSQL and Docker containers
Requirements:
- 3+ years of experience with Python
- Strong knowledge of Git and AWS
- Bachelor's degree in Computer Science
What We Offer:
- Competitive salary and health benefits
"""

sample_resume = """
John Doe
Email: john.doe@example.com | Phone: +1-555-0199 | LinkedIn: linkedin.com/in/johndoe
Work Experience:
Software Engineer | Acme Corp (2021 - Present)
- Developed REST APIs using Python and Django
- Managed PostgreSQL databases and Docker deployments
Education:
B.S. in Computer Science, State University (2017 - 2021)
Skills: Python, Django, FastAPI, SQL, Docker, Git
"""

res_jd = classify_document(sample_jd, filename="job_desc.pdf")
print("Sample JD Classification:", res_jd)

res_resume = classify_document(sample_resume, filename="john_doe_resume.pdf")
print("Sample Resume Classification:", res_resume)

res_resume_as_jd_name = classify_document(sample_resume, filename="document.pdf")
print("Sample Resume without filename hints:", res_resume_as_jd_name)

res_jd_as_resume_name = classify_document(sample_jd, filename="document.pdf")
print("Sample JD without filename hints:", res_jd_as_resume_name)
