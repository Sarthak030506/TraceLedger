"""Remove or mask sensitive data BEFORE storing or hashing."""
import re

REDACTED = "[REDACTED]"

# Keys whose values are dropped entirely (case-insensitive substring match).
SENSITIVE_KEY_PARTS = (
    "password", "passwd", "pwd", "secret", "token", "api_key", "apikey",
    "authorization", "cookie", "private_key", "session_id", "ssn",
    "credit_card", "card_number", "cvv",
)

EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
IPV4_RE = re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3})\.\d{1,3}\b")
# e.g. "password=hunter2", "token: abc123"
INLINE_SECRET_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key)\b\s*[=:]\s*\S+"
)


def _is_sensitive_key(key: str) -> bool:
    k = key.lower()
    return any(part in k for part in SENSITIVE_KEY_PARTS)


def mask_email(text: str) -> str:
    """alice@example.com -> a***@example.com"""
    return EMAIL_RE.sub(lambda m: f"{m.group(1)}***@{m.group(2)}", text)


def mask_ip(text: str) -> str:
    """192.168.1.45 -> 192.168.1.xxx"""
    return IPV4_RE.sub(lambda m: f"{m.group(1)}.xxx", text)


def _sanitize_string(s: str) -> str:
    s = INLINE_SECRET_RE.sub(lambda m: f"{m.group(1)}={REDACTED}", s)
    return mask_ip(mask_email(s))


def sanitize_value(value):
    if isinstance(value, str):
        return _sanitize_string(value)
    if isinstance(value, list):
        return [sanitize_value(v) for v in value]
    if isinstance(value, dict):
        return sanitize_details(value)
    return value


def sanitize_details(details: dict) -> dict:
    """Return a sanitized deep copy of `details`. Input is never mutated."""
    clean = {}
    for key, val in details.items():
        if _is_sensitive_key(key):
            continue  # drop the field completely
        clean[key] = sanitize_value(val)
    return clean


def sanitize_event(event: dict) -> dict:
    """Sanitize a validated event (only `details` and `source` can leak data)."""
    out = dict(event)
    out["details"] = sanitize_details(event["details"])
    out["source"] = _sanitize_string(event["source"])
    return out
