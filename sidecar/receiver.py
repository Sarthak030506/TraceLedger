"""Authenticated HTTP event receiver for the TraceLedger sidecar.

Standard library only (http.server, urllib, json, hmac, etc.).
Listens by default on 127.0.0.1:8001.
"""
import argparse
import hmac
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .collector import ingest_event
from .models import ValidationError
from .storage import DuplicateEventError, RecordStore

MAX_BODY_SIZE = 64 * 1024  # 64 KB limit


class ReceiverHandler(BaseHTTPRequestHandler):
    """Request handler for receiving security events and serving health checks."""

    def log_message(self, format: str, *args: Any) -> None:
        """Silence standard request logging to keep CLI and test output clean."""
        pass

    def _drain_body(self) -> None:
        """Drain unread body bytes to prevent Windows TCP reset on connection close."""
        try:
            content_length_str = self.headers.get("Content-Length")
            if content_length_str:
                content_length = int(content_length_str)
                remaining = max(0, content_length)
                while remaining > 0:
                    chunk = self.rfile.read(min(remaining, 65536))
                    if not chunk:
                        break
                    remaining -= len(chunk)
        except Exception:
            pass

    def _send_json(self, status: int, data: Any) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _check_auth(self) -> bool:
        api_key = self.headers.get("X-API-Key")
        if not api_key:
            return False
        expected_key = getattr(self.server, "api_key", "")
        return hmac.compare_digest(api_key.strip(), expected_key.strip())

    def do_GET(self) -> None:
        path = self.path.split("?")[0].rstrip("/")
        if path == "/health":
            with self.server.lock:  # type: ignore[attr-defined]
                store = RecordStore(self.server.db_path)  # type: ignore[attr-defined]
                try:
                    count = store.count()
                finally:
                    store.close()
            self._send_json(200, {"status": "ok", "record_count": count})
        elif path == "/events":
            self._send_json(405, {"error": "Method not allowed"})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        path = self.path.split("?")[0].rstrip("/")
        if path == "/health":
            self._drain_body()
            self._send_json(405, {"error": "Method not allowed"})
            return
        if path != "/events":
            self._drain_body()
            self._send_json(404, {"error": "Not found"})
            return

        # 1. Authentication check
        if not self._check_auth():
            self._drain_body()
            self._send_json(401, {"error": "Unauthorized"})
            return

        # 2. Content-Length check & 64 KB body size limit
        content_length_str = self.headers.get("Content-Length")
        if not content_length_str:
            self._send_json(400, {"error": "Missing Content-Length header"})
            return
        try:
            content_length = int(content_length_str)
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length header"})
            return

        if content_length < 0:
            self._send_json(400, {"error": "Negative Content-Length header"})
            return

        if content_length > MAX_BODY_SIZE:
            self._drain_body()
            self._send_json(413, {"error": "Payload too large (max 64 KB)"})
            return

        raw_body = self.rfile.read(content_length)
        if len(raw_body) > MAX_BODY_SIZE:
            self._send_json(413, {"error": "Payload too large (max 64 KB)"})
            return

        # 3. JSON parsing
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._send_json(400, {"error": f"Invalid JSON: {exc}"})
            return

        # 4. Ingest event(s) with thread lock and isolated store connection
        with self.server.lock:  # type: ignore[attr-defined]
            store = RecordStore(self.server.db_path)  # type: ignore[attr-defined]
            try:
                if isinstance(payload, dict):
                    result = ingest_event(payload, store)
                elif isinstance(payload, list):
                    result = [ingest_event(event_item, store) for event_item in payload]
                else:
                    self._send_json(400, {"error": "Event payload must be a JSON object or list"})
                    return
            except DuplicateEventError as exc:
                self._send_json(409, {"error": str(exc)})
                return
            except ValidationError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            except Exception as exc:
                self._send_json(500, {"error": f"Internal server error: {exc}"})
                return
            finally:
                store.close()

        self._send_json(200, result)

    def do_PUT(self) -> None:
        self._handle_other_method()

    def do_DELETE(self) -> None:
        self._handle_other_method()

    def do_PATCH(self) -> None:
        self._handle_other_method()

    def do_HEAD(self) -> None:
        self._handle_other_method()

    def _handle_other_method(self) -> None:
        self._drain_body()
        path = self.path.split("?")[0].rstrip("/")
        if path in ("/events", "/health"):
            self._send_json(405, {"error": "Method not allowed"})
        else:
            self._send_json(404, {"error": "Not found"})


class ReceiverServer(ThreadingHTTPServer):
    """Threading HTTP server carrying receiver configuration and synchronization lock."""

    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[BaseHTTPRequestHandler],
        db_path: str,
        api_key: str,
    ):
        self.db_path = db_path
        self.api_key = api_key
        self.lock = threading.Lock()
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        super().__init__(server_address, RequestHandlerClass)


def make_server(
    host: str = "127.0.0.1",
    port: int = 8001,
    db_path: str = "data/records.db",
    api_key: str | None = None,
) -> ReceiverServer:
    """Create a configured ReceiverServer instance. Refuses to start if api_key is missing."""
    if api_key is None:
        api_key = os.environ.get("SIDECAR_API_KEY")
    if not api_key:
        raise RuntimeError("SIDECAR_API_KEY environment variable is not set")
    return ReceiverServer((host, port), ReceiverHandler, db_path=db_path, api_key=api_key)


def main() -> None:
    parser = argparse.ArgumentParser(description="TraceLedger Sidecar Event Receiver")
    parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8001, help="Port (default: 8001)")
    parser.add_argument("--db", default="data/records.db", help="SQLite DB path (default: data/records.db)")
    args = parser.parse_args()

    api_key = os.environ.get("SIDECAR_API_KEY")
    if not api_key:
        sys.stderr.write("Error: SIDECAR_API_KEY environment variable is required\n")
        sys.exit(1)

    server = make_server(host=args.host, port=args.port, db_path=args.db, api_key=api_key)
    print(f"TraceLedger sidecar receiver listening on {args.host}:{args.port} (db: {args.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping receiver...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
