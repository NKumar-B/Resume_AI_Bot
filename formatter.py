import html
import logging

logger = logging.getLogger("Formatter")


def format_resume_analysis(result: dict) -> str:
    """
    Formats individual candidate resume analysis into clean Telegram HTML message.
    Escapes user text to prevent Telegram HTML parse errors.
    """
    candidate_name = html.escape(str(result.get("candidate_name", "Not detected")))
    resume_name = html.escape(str(result.get("resume_name", "resume.pdf")))
    score = result.get("overall_score", 0)

    matched_skills = result.get("matched_skills", [])
    missing_skills = result.get("missing_skills", [])
    suggestions = result.get("suggestions", [])
    courses = result.get("courses", [])

    # Skill match list
    if matched_skills:
        matched_str = "\n".join([f"• {html.escape(str(s))}" for s in matched_skills])
    else:
        matched_str = "• None explicitly identified"

    # Skill mismatch list
    if missing_skills:
        missing_str = "\n".join([f"• {html.escape(str(s))}" for s in missing_skills])
    else:
        missing_str = "• No significant skill gaps identified"

    # Suggestions list - single line per item
    if suggestions:
        sugg_str = "\n".join([f"{i+1}. {html.escape(str(s))}" for i, s in enumerate(suggestions)])
    else:
        sugg_str = "1. Tailor resume metrics to highlight core JD qualifications."

    # Courses list
    course_items = []
    for i, c in enumerate(courses):
        title = html.escape(str(c.get("title", "Recommended Course")))
        provider = html.escape(str(c.get("provider", "Online Provider")))
        url = c.get("url", "#")

        # Sanitize URL for HTML href attribute
        clean_url = html.escape(str(url))

        course_items.append(
            f"{i+1}. <b>{title}</b>\n"
            f"   Provider: {provider}\n"
            f'   🔗 <a href="{clean_url}">Course Link</a>'
        )

    course_str = "\n\n".join(course_items) if course_items else "1. Coursera Professional Certificates\n   🔗 <a href='https://www.coursera.org'>Course Link</a>"

    score_bd = result.get("score_breakdown", {})
    skill_pts = html.escape(str(score_bd.get("skill_match", "40/50")))
    exp_pts = html.escape(str(score_bd.get("experience_match", "15/20")))
    proj_pts = html.escape(str(score_bd.get("projects_match", "12/15")))
    edu_pts = html.escape(str(score_bd.get("education_match", "8/10")))
    ats_pts = html.escape(str(score_bd.get("ats_alignment", "4/5")))

    formatted_msg = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 <b>RESUME ANALYSIS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Candidate:</b>\n"
        f"{candidate_name}\n\n"
        f"<b>Resume:</b>\n"
        f"{resume_name}\n\n"
        f"<b>OVERALL MATCH SCORE</b>\n"
        f"<b>{score}%</b>\n\n"
        f"📊 <b>Score Basis & Breakdown:</b>\n\n"
        f"• Skill Match: <b>{skill_pts}</b> (50% max)\n"
        f"• Experience Match: <b>{exp_pts}</b> (20% max)\n"
        f"• Project Relevance: <b>{proj_pts}</b> (15% max)\n"
        f"• Education & Certs: <b>{edu_pts}</b> (10% max)\n"
        f"• ATS Alignment: <b>{ats_pts}</b> (5% max)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ <b>SKILL MATCH</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{matched_str}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"❌ <b>SKILL MISMATCH</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{missing_str}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <b>IMPROVEMENT SUGGESTIONS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{sugg_str}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎓 <b>COURSE CORRECTION</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{course_str}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    return formatted_msg


def format_final_summary(results: list) -> str:
    """
    Formats final summary comparison table of all processed candidate resumes,
    sorted by match score in descending order.
    Uses neutral language ('Highest JD match score').
    """
    if not results:
        return "No resumes available for summary."

    # Sort candidates by overall_score descending
    sorted_results = sorted(results, key=lambda x: x.get("overall_score", 0), reverse=True)

    lines = []
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("📊 <b>FINAL RESUME SUMMARY</b>")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    lines.append("<code>Resume                         Score</code>")
    lines.append("<code>────────────────────────────────────</code>")

    for r in sorted_results:
        raw_filename = str(r.get("resume_name", "resume.pdf"))
        # Truncate filename if too long for clean table formatting
        display_name = raw_filename if len(raw_filename) <= 24 else raw_filename[:21] + "..."
        score_str = f"{r.get('overall_score', 0)}%"

        # Right-pad filename to align table
        padded_line = f"{display_name:<26} {score_str:>5}"
        lines.append(f"<code>{html.escape(padded_line)}</code>")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("ℹ️ <i>Match-score comparison based strictly on job description qualifications.</i>")

    return "\n".join(lines)
