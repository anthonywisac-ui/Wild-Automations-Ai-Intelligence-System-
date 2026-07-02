# Inspired By: crawl4AI (data validation patterns)
# Repository: https://github.com/unclecode/crawl4AI
# Feature: Email, phone, UUID validation and normalisation
# Reason: Reusable validation for lead data
# ============================================================

import re, uuid

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
PHONE_PATTERN = re.compile(r"^\+?[0-9\s\-()]{7,20}$")

def validate_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.match(email))

def validate_phone(phone: str) -> bool:
    return bool(PHONE_PATTERN.match(phone))

def validate_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False

def normalize_phone(phone: str) -> str:
    if phone.startswith("+"):
        return "+" + "".join(ch for ch in phone[1:] if ch.isdigit())
    return "".join(ch for ch in phone if ch.isdigit())
