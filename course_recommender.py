import urllib.parse
import logging

logger = logging.getLogger("CourseRecommender")

# Default reputable providers mapping for specific skill domains
KNOWN_COURSE_MAP = {
    "docker": {
        "title": "Docker Technologies for DevOps and Developers",
        "provider": "Coursera / Docker",
        "url": "https://www.coursera.org/search?query=Docker"
    },
    "kubernetes": {
        "title": "Architecting with Google Kubernetes Engine",
        "provider": "Coursera / Google Cloud",
        "url": "https://www.coursera.org/search?query=Kubernetes"
    },
    "aws": {
        "title": "AWS Cloud Practitioner Essentials",
        "provider": "AWS Training / Coursera",
        "url": "https://www.coursera.org/search?query=AWS"
    },
    "azure": {
        "title": "Microsoft Azure Fundamentals (AZ-900)",
        "provider": "Microsoft Learn",
        "url": "https://learn.microsoft.com/en-us/credentials/certifications/azure-fundamentals/"
    },
    "gcp": {
        "title": "Google Cloud Big Data and Machine Learning",
        "provider": "Google Cloud Skills Boost",
        "url": "https://www.cloudskillsboost.google/"
    },
    "react": {
        "title": "Developing Front-End Apps with React",
        "provider": "IBM / Coursera",
        "url": "https://www.coursera.org/search?query=React"
    },
    "java": {
        "title": "Java Programming and Software Engineering Fundamentals",
        "provider": "Duke University / Coursera",
        "url": "https://www.coursera.org/search?query=Java"
    },
    "python": {
        "title": "Python for Everybody Specialization",
        "provider": "University of Michigan / Coursera",
        "url": "https://www.coursera.org/search?query=Python"
    },
    "spring boot": {
        "title": "Spring Boot Fundamentals & Microservices",
        "provider": "Udemy / Spring",
        "url": "https://www.udemy.com/courses/search/?q=Spring+Boot"
    },
    "sql": {
        "title": "Database Design and Basic SQL in PostgreSQL",
        "provider": "University of Michigan / Coursera",
        "url": "https://www.coursera.org/search?query=SQL"
    },
    "git": {
        "title": "Version Control with Git",
        "provider": "Atlassian / Coursera",
        "url": "https://www.coursera.org/search?query=Git"
    }
}


def build_fallback_course(skill_name: str, index: int) -> dict:
    """Generates a reputable course recommendation for any skill name."""
    cleaned_skill = skill_name.strip()
    skill_lower = cleaned_skill.lower()

    # Check known mapping first
    for known_key, known_data in KNOWN_COURSE_MAP.items():
        if known_key in skill_lower or skill_lower in known_key:
            return {
                "title": known_data["title"],
                "skill": cleaned_skill,
                "provider": known_data["provider"],
                "url": known_data["url"]
            }

    # Alternate reputable providers for general skills
    providers = [
        ("Coursera", f"https://www.coursera.org/search?query={urllib.parse.quote(cleaned_skill)}"),
        ("Udemy", f"https://www.udemy.com/courses/search/?q={urllib.parse.quote(cleaned_skill)}"),
        ("edX", f"https://www.edx.org/search?q={urllib.parse.quote(cleaned_skill)}")
    ]

    prov_name, prov_url = providers[index % len(providers)]

    return {
        "title": f"Mastering {cleaned_skill} - Complete Guide",
        "skill": cleaned_skill,
        "provider": prov_name,
        "url": prov_url
    }


def sanitize_and_fill_courses(courses_from_ai: list, missing_skills: list) -> list:
    """
    Validates and ensures exactly 3 course recommendations are returned.
    Sanitizes URLs to ensure they are valid clickable links to real providers.
    """
    valid_courses = []

    # Process AI courses if provided
    if isinstance(courses_from_ai, list):
        for c in courses_from_ai:
            if isinstance(c, dict):
                title = c.get("title", "").strip()
                skill = c.get("skill", "").strip()
                provider = c.get("provider", "").strip()
                url = c.get("url", "").strip()

                # Validate URL structure
                if not (url.startswith("http://") or url.startswith("https://")):
                    if skill:
                        url = f"https://www.coursera.org/search?query={urllib.parse.quote(skill)}"
                    else:
                        url = "https://www.coursera.org"

                if title and skill and provider:
                    valid_courses.append({
                        "title": title,
                        "skill": skill,
                        "provider": provider,
                        "url": url
                    })

    # If we have less than 3 valid courses, fill using missing skills
    idx = 0
    skills_to_use = list(missing_skills) if missing_skills else ["Software Architecture", "System Design", "Cloud Computing"]
    
    while len(valid_courses) < 3:
        target_skill = skills_to_use[idx % len(skills_to_use)]
        
        # Avoid duplicate skill recommendations
        existing_skills = [c["skill"].lower() for c in valid_courses]
        if target_skill.lower() in existing_skills and len(skills_to_use) > len(valid_courses):
            idx += 1
            continue

        course_obj = build_fallback_course(target_skill, idx)
        valid_courses.append(course_obj)
        idx += 1

    # Return exactly 3 courses
    return valid_courses[:3]
