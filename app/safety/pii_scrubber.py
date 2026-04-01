import re

# Aadhaar: 12 digits, often formatted as XXXX XXXX XXXX
AADHAAR_PATTERN = re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b')

# Indian phone numbers
PHONE_PATTERN = re.compile(r'\b(?:\+91[-\s]?)?\d{10}\b')

# Email
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

# PAN card
PAN_PATTERN = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b')


def scrub_pii(text: str) -> str:
    text = AADHAAR_PATTERN.sub('[AADHAAR_REMOVED]', text)
    text = PHONE_PATTERN.sub('[PHONE_REMOVED]', text)
    text = EMAIL_PATTERN.sub('[EMAIL_REMOVED]', text)
    text = PAN_PATTERN.sub('[PAN_REMOVED]', text)
    return text
