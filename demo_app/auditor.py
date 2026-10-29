"""Audit client and outbox queue for the Demo Expense App.

Sends audit events to the sidecar receiver with background retries and
fallback to an outbox JSONL file on disk.
"""
from datetime import datetime, timezone
import json
import os
import threading
import time
import urllib.error
import urllib.request
import uuid
from typing import Any


def assert_no_floats(value: Any, path: str = "payload") -> None:
    """Recursively ensure that no float types exist in the payload."""
    if isinstance(value, float):
        raise ValueError(f"Float detected at {path}: {value!r}. All amounts must be integers in paise.")
    if isinstance(value, dict):
        for k, v in value.items():
            assert_no_floats(v, f"{path}.{k}")
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            assert_no_floats(item, f"{path}[{i}]")


def build_audit_event(event_type: str, details: dict[str, Any]) -> dict[str, Any]:
    """Build a standardized audit event dictionary following the TraceLedger contract."""
    assert_no_floats(details, "details")
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": now_utc,
        "event_type": event_type,
        "source": "expense-demo",
        "details": details,
    }


class Auditor:
    """Thread-safe auditor that manages sending events and maintaining an outbox."""

    def __init__(
        self,
        sidecar_url: str | None = None,
        api_key: str | None = None,
        outbox_path: str | None = None,
        retry_interval: float = 10.0,
    ):
        self.sidecar_url = sidecar_url or os.environ.get("SIDECAR_URL", "http://127.0.0.1:8001/events")
        self.api_key = api_key if api_key is not None else os.environ.get("SIDECAR_API_KEY", "")
        self.outbox_path = outbox_path or os.environ.get("OUTBOX_PATH", "data/outbox.jsonl")
        self.retry_interval = retry_interval

        self.sent_count = 0
        self.lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None

        # Ensure directory exists for outbox file
        outbox_dir = os.path.dirname(self.outbox_path)
        if outbox_dir:
            os.makedirs(outbox_dir, exist_ok=True)

    def start_background_worker(self) -> None:
        """Start periodic background retry thread."""
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._retry_loop, daemon=True)
        self._worker_thread.start()

    def stop_background_worker(self) -> None:
        """Stop background retry thread."""
        self._stop_event.set()
        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
            self._worker_thread = None

    def _retry_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.flush_outbox()
            except Exception:
                pass
            self._stop_event.wait(self.retry_interval)

    def _send_http_sync(self, event: dict[str, Any]) -> bool:
        """Send an event via HTTP POST to the sidecar with a 2-second timeout."""
        body = json.dumps(event, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        req = urllib.request.Request(self.sidecar_url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                return 200 <= resp.status < 300
        except Exception:
            return False

    def _append_outbox(self, event: dict[str, Any]) -> None:
        """Append an un-sent event to the outbox JSONL file."""
        line = json.dumps(event, ensure_ascii=False) + "\n"
        with open(self.outbox_path, "a", encoding="utf-8") as fh:
            fh.write(line)

    def flush_outbox(self) -> int:
        """Attempt to flush queued events from the outbox file. Returns count sent."""
        with self.lock:
            if not os.path.exists(self.outbox_path):
                return 0

            with open(self.outbox_path, "r", encoding="utf-8") as fh:
                lines = [line.strip() for line in fh if line.strip()]

            if not lines:
                return 0

            still_failed: list[str] = []
            flushed_count = 0

            for line in lines:
                try:
                    event = json.loads(line)
                except Exception:
                    continue

                if self._send_http_sync(event):
                    self.sent_count += 1
                    flushed_count += 1
                else:
                    # Once a send fails during flush, retain this and all remaining events
                    still_failed.append(line)

            # Rewrite outbox with remaining events
            if still_failed:
                with open(self.outbox_path, "w", encoding="utf-8") as fh:
                    for line in still_failed:
                        fh.write(line + "\n")
            else:
                try:
                    os.remove(self.outbox_path)
                except OSError:
                    pass

            return flushed_count

    def _process_event_delivery(self, event: dict[str, Any]) -> None:
        """Worker function to flush previous outbox items and deliver the new event."""
        with self.lock:
            # 1. First attempt to drain any backlog
            if os.path.exists(self.outbox_path):
                # Run flush logic inline without re-acquiring self.lock
                with open(self.outbox_path, "r", encoding="utf-8") as fh:
                    lines = [line.strip() for line in fh if line.strip()]
                still_failed = []
                for line in lines:
                    try:
                        past_evt = json.loads(line)
                    except Exception:
                        continue
                    if self._send_http_sync(past_evt):
                        self.sent_count += 1
                    else:
                        still_failed.append(line)
                if still_failed:
                    with open(self.outbox_path, "w", encoding="utf-8") as fh:
                        for line in still_failed:
                            fh.write(line + "\n")
                    # If backlog couldn't be flushed, queue current event too to preserve order
                    self._append_outbox(event)
                    return
                else:
                    try:
                        os.remove(self.outbox_path)
                    except OSError:
                        pass

            # 2. Try sending the current event
            if self._send_http_sync(event):
                self.sent_count += 1
            else:
                self._append_outbox(event)

    def emit(self, event_type: str, details: dict[str, Any], sync: bool = False) -> dict[str, Any]:
        """Emit an audit event.

        If sync is True, runs synchronously (ideal for tests).
        Otherwise dispatches to a background thread with 2s timeout.
        Returns the constructed event payload immediately.
        """
        event = build_audit_event(event_type, details)
        if sync:
            self._process_event_delivery(event)
        else:
            threading.Thread(target=self._process_event_delivery, args=(event,), daemon=True).start()
        return event

    def get_status(self) -> dict[str, int]:
        """Return total events sent and current queued count."""
        with self.lock:
            queued = 0
            if os.path.exists(self.outbox_path):
                try:
                    with open(self.outbox_path, "r", encoding="utf-8") as fh:
                        queued = sum(1 for line in fh if line.strip())
                except Exception:
                    queued = 0
            return {
                "events_sent": self.sent_count,
                "queued": queued,
            }


# Module-level default auditor instance
default_auditor = Auditor()
