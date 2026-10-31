"""Remove or mask sensitive data BEFORE storing or hashing."""
import ipaddress
import re

REDACTED = "[REDACTED]"

# Key matching works on word tokens, not substrings, so "token_count" or "secretary"
# survive while "access_token", "API_KEY" and "userPassword" are dropped.
# A key is sensitive if ANY of its tokens is in SENSITIVE_TOKENS ...
SENSITIVE_TOKENS = frozenset({
    "password", "passwd", "pwd", "passphrase", "secret", "secrets", "apikey",
    "authorization", "cookie", "cookies", "credential", "credentials",
    "ssn", "cvv", "cvc", "privatekey", "jwt", "otp", "pin",
})
# ... or if its LAST token is one of these (the head noun names the value):
SENSITIVE_LAST_TOKENS = frozenset({"token", "tokens", "key", "sessionid"})
# ... or if it contains one of these adjacent token pairs:
SENSITIVE_PAIRS = frozenset({
    ("api", "key"), ("private", "key"), ("secret", "key"), ("access", "key"),
    ("session", "id"), ("credit", "card"), ("card", "number"),
})
# Non-secret keys that would otherwise match the last-token rule.
SAFE_KEYS = frozenset({"key", "public_key", "sort_key", "partition_key", "primary_key", "idempotency_key"})

_TOKEN_SPLIT_RE = re.compile(r"[^A-Za-z0-9]+|(?<=[a-z0-9])(?=[A-Z])")

EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
IPV4_RE = re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3})\.\d{1,3}\b")
# Candidate IPv6 text (validated with ipaddress before masking, so times like 10:30:00 are left alone)
IPV6_CANDIDATE_RE = re.compile(r"(?<![0-9A-Za-z:.])(?=[0-9A-Fa-f:.]*:[0-9A-Fa-f:.]*:)[0-9A-Fa-f:.]{2,}(?![0-9A-Za-z:])")
# e.g. "password=hunter2", "token: abc123", "Authorization: Bearer xyz"
INLINE_SECRET_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|authorization)\b\s*[=:]\s*(?:bearer\s+|basic\s+)?\S+"
)
# Well-known credential shapes that are dangerous regardless of the key they appear under.
SECRET_VALUE_RES = (
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{8,}=*"),
    re.compile(r"\b(?:sk|pk|rk)[-_](?:live|test)[-_][A-Za-z0-9]{6,}\b"),   # Stripe-style keys
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                                  # AWS access key id
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),                        # GitHub tokens
    re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b"),  # JWT
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)"),
)


def _key_tokens(key: str) -> list[str]:
    return [t.lower() for t in _TOKEN_SPLIT_RE.split(key) if t]


def _is_sensitive_key(key: str) -> bool:
    if key.lower() in SAFE_KEYS:
        return False
    tokens = _key_tokens(key)
    if not tokens:
        return False
    if any(t in SENSITIVE_TOKENS for t in tokens):
        return True
    if tokens[-1] in SENSITIVE_LAST_TOKENS:
        return True
    return any(pair in SENSITIVE_PAIRS for pair in zip(tokens, tokens[1:]))


def mask_email(text: str) -> str:
    """alice@example.com -> a***@example.com"""
    return EMAIL_RE.sub(lambda m: f"{m.group(1)}***@{m.group(2)}", text)


def _mask_ipv6_match(m: re.Match) -> str:
    text = m.group(0)
    trailing = ""
    while text.endswith("."):  # sentence punctuation, e.g. "from ::1."
        text, trailing = text[:-1], trailing + "."
    try:
        addr = ipaddress.IPv6Address(text)
    except ValueError:
        return m.group(0)
    prefix = ipaddress.IPv6Network(f"{addr}/64", strict=False).network_address
    return f"{prefix}xxx{trailing}"


def mask_ip(text: str) -> str:
    """192.168.1.45 -> 192.168.1.xxx ; 2001:db8:85a3:1:2:3:4:5 -> 2001:db8:85a3:1::xxx"""
    text = IPV6_CANDIDATE_RE.sub(_mask_ipv6_match, text)
    return IPV4_RE.sub(lambda m: f"{m.group(1)}.xxx", text)


def _sanitize_string(s: str) -> str:
    s = INLINE_SECRET_RE.sub(lambda m: f"{m.group(1)}={REDACTED}", s)
    for pattern in SECRET_VALUE_RES:
        s = pattern.sub(REDACTED, s)
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
