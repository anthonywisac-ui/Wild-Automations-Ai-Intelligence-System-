"""Cover Letter & Outreach Email Generator using the LLM chain."""
from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_COVER_LETTER_SYSTEM = """You are an expert career coach who writes compelling, personalized cover letters.
Write in a confident, professional tone. Keep it under 300 words. No fluff or clichés.
Format: 3 short paragraphs — hook, value, close. No placeholders like [Your Name]."""

_OUTREACH_SYSTEM = """You are an expert recruiter and career strategist.
Write a short cold outreach email (under 150 words) to a hiring manager or recruiter.
Subject line on first line prefixed with 'Subject:'. Then blank line, then email body.
Be specific, direct, and compelling. No generic opener like 'I hope this email finds you well'."""

_MATCH_SYSTEM = """You are a job application specialist. Given a CV summary and job description,
score the match from 0-100 and explain in 2 sentences why. Be honest and specific.
Format: SCORE: <number>\nREASON: <explanation>"""


async def generate_cover_letter(
    job_title: str,
    company: str,
    job_description: str,
    cv_summary: str,
) -> str:
    """Generate a tailored cover letter for a specific job."""
    from core.llm_client import get_llm
    llm = get_llm()
    if not llm:
        return _fallback_cover_letter(job_title, company, cv_summary)

    prompt = f"""Job Title: {job_title}
Company: {company}
Job Description (excerpt):
{job_description[:1500]}

Candidate Background:
{cv_summary[:800]}

Write a compelling cover letter."""

    try:
        return await llm.complete(prompt, system=_COVER_LETTER_SYSTEM, max_tokens=500, temperature=0.7)
    except Exception as e:
        logger.warning("cover_letter LLM failed: %s", e)
        return _fallback_cover_letter(job_title, company, cv_summary)


async def generate_outreach_email(
    job_title: str,
    company: str,
    recruiter_name: Optional[str],
    cv_summary: str,
) -> str:
    """Generate a cold outreach email to a recruiter/hiring manager."""
    from core.llm_client import get_llm
    llm = get_llm()
    if not llm:
        return _fallback_outreach(job_title, company, recruiter_name)

    to = f"Hi {recruiter_name}," if recruiter_name else "Hi there,"
    prompt = f"""I want to reach out about the {job_title} role at {company}.

My background: {cv_summary[:600]}

Write a short, compelling cold outreach email. Start with: {to}"""

    try:
        return await llm.complete(prompt, system=_OUTREACH_SYSTEM, max_tokens=300, temperature=0.7)
    except Exception as e:
        logger.warning("outreach_email LLM failed: %s", e)
        return _fallback_outreach(job_title, company, recruiter_name)


async def compute_match_score(
    job_title: str,
    job_description: str,
    cv_summary: str,
) -> dict:
    """Compute AI job match score vs CV. Returns {"score": int, "reason": str}."""
    from core.llm_client import get_llm
    llm = get_llm()
    if not llm:
        return {"score": 0, "reason": "LLM not available for match scoring."}

    prompt = f"""Job Title: {job_title}
Job Description:
{job_description[:1200]}

Candidate CV Summary:
{cv_summary[:600]}

Score the match 0-100."""

    try:
        raw = await llm.complete(prompt, system=_MATCH_SYSTEM, max_tokens=120, temperature=0.2)
        score = 0
        reason = raw
        for line in raw.split("\n"):
            if line.upper().startswith("SCORE:"):
                try:
                    score = int(line.split(":")[1].strip().split()[0])
                except Exception:
                    pass
            if line.upper().startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()
        return {"score": score, "reason": reason}
    except Exception as e:
        logger.warning("match_score LLM failed: %s", e)
        return {"score": 0, "reason": str(e)}


def _fallback_cover_letter(title: str, company: str, cv: str) -> str:
    return (
        f"Dear Hiring Team at {company},\n\n"
        f"I am writing to express my interest in the {title} position. "
        f"Based on my background — {cv[:200]} — I believe I would be a strong fit.\n\n"
        f"I would welcome the opportunity to discuss how my skills align with your needs.\n\n"
        f"Best regards"
    )


def _fallback_outreach(title: str, company: str, recruiter: Optional[str]) -> str:
    greeting = f"Hi {recruiter}," if recruiter else "Hi there,"
    return (
        f"Subject: Interest in {title} at {company}\n\n"
        f"{greeting}\n\n"
        f"I came across the {title} role at {company} and wanted to reach out directly. "
        f"I'd love to connect and learn more about the position.\n\n"
        f"Would you have 15 minutes this week?\n\nBest regards"
    )
