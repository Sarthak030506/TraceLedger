"""Shared security-event schema and validation.

Raw event (input to the pipeline):
    event_id, timestamp, event_type, source, details
Record (after sequence number assignment):
    event_id, sequence_number, timestamp, event_type, source, details
Hash record (what Person 2 consumes):
    event_id, sequence_number, timestamp, event_type, record_hash
"""
from datetime import datetime, timezone

RAW_FIELDS = ("event_id", "timestamp", "event_type", "source", "details")
RECORD_FIELDS = ("event_id", "sequence_number", "timestamp", "event_type", "source", "details")


class ValidationError(ValueError):
    """Raised when an event does not follow the agreed schema."""


def normalize_timestamp(value) -> str:
    """Return the timestamp as UTC ISO-8601 'YYYY-MM-DDTHH:MM:SSZ'.

    Timezone is required, so the same instant always yields the same string
    (and therefore the same hash).
    """
    if not isinstance(value, str):
        raise ValidationError("timestamp must be an ISO-8601 string")
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"invalid ISO-8601 timestamp: {value!r}") from exc
    if dt.tzinfo is None:
        raise ValidationError("timestamp must include a timezone (use 'Z' for UTC)")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _check_json_safe(value, path="details"):
    """Allow only str/int/bool/None/list/dict(str keys). Floats are rejected
    because their text form is not guaranteed stable across systems."""
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        raise ValidationError(f"{path}: floats are not allowed (use int or str)")
    if isinstance(value, list):
        for i, v in enumerate(value):
            _check_json_safe(v, f"{path}[{i}]")
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValidationError(f"{path}: keys must be strings")
            _check_json_safe(v, f"{path}.{k}")
        return
    raise ValidationError(f"{path}: unsupported type {type(value).__name__}")


def validate_raw_event(raw: dict) -> dict:
    """Validate a raw event and return a minimized copy.

    Unknown fields are dropped (data minimization). Raises ValidationError.
    """
    if not isinstance(raw, dict):
        raise ValidationError("event must be a dict")
    missing = [f for f in RAW_FIELDS if f not in raw or raw[f] in (None, "")]
    if missing and missing != ["details"]:
        raise ValidationError(f"missing required fields: {', '.join(missing)}")
    if "details" not in raw or raw["details"] is None:
        raise ValidationError("missing required fields: details")
    for f in ("event_id", "event_type", "source"):
        if not isinstance(raw[f], str) or not raw[f].strip():
            raise ValidationError(f"{f} must be a non-empty string")
    if not isinstance(raw["details"], dict):
        raise ValidationError("details must be an object")
    _check_json_safe(raw["details"])
    return {
        "event_id": raw["event_id"].strip(),
        "timestamp": normalize_timestamp(raw["timestamp"]),
        "event_type": raw["event_type"].strip(),
        "source": raw["source"].strip(),
        "details": raw["details"],
    }


def build_record(clean_event: dict, sequence_number: int) -> dict:
    """Attach a sequence number to a validated, sanitized event."""
    if not isinstance(sequence_number, int) or isinstance(sequence_number, bool) or sequence_number < 1:
        raise ValidationError("sequence_number must be an integer >= 1")
    rec = {"sequence_number": sequence_number}
    rec.update({k: clean_event[k] for k in RAW_FIELDS})
    return rec
