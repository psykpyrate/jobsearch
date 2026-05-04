from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from job_scanner import (
    DEFAULT_HOURS_OLD,
    DEFAULT_RESULTS_PER_TERM,
    DEFAULT_SITES,
    DEFAULT_ZIP_CODE,
    JobListing,
    JobScannerError,
    JobSearchConfig,
    SITE_DISPLAY_NAMES,
    search_jobs,
)

APP_DIR = Path(__file__).resolve().parent
HTML_DIR = APP_DIR / "html-app"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
MAX_BODY_BYTES = 64 * 1024
DEFAULT_API_CORS_ORIGIN = os.environ.get("JOB_SCANNER_CORS_ORIGIN", "*")
DISPLAY_TO_SITE = {label.casefold(): site for site, label in SITE_DISPLAY_NAMES.items()}


def parse_args() -> argparse.Namespace:
    env_port = parse_port(os.environ.get("PORT"), DEFAULT_PORT)
    env_host = "0.0.0.0" if os.environ.get("PORT") else DEFAULT_HOST
    parser = argparse.ArgumentParser(description="Serve the Job Scanner HTML app with a live Python API.")
    parser.add_argument("--host", default=env_host, help=f"Host interface to bind. Default: {env_host}")
    parser.add_argument("--port", type=int, default=env_port, help=f"Port to listen on. Default: {env_port}")
    return parser.parse_args()


def build_config(payload: dict[str, Any]) -> JobSearchConfig:
    search_terms = parse_search_terms(payload.get("searchTitles", ""))
    if not search_terms:
        raise JobScannerError("Enter one or more search titles.")

    sites = parse_sites(payload.get("selectedBoards"))
    zip_code = normalize_text(payload.get("zipCode", DEFAULT_ZIP_CODE))
    city = normalize_text(payload.get("city", ""))
    state = normalize_text(payload.get("state", "")).upper()

    return JobSearchConfig(
        zip_code=zip_code,
        city=city,
        state=state,
        custom_url=normalize_text(payload.get("customUrl", "")),
        search_terms=search_terms,
        distance_miles=parse_int(payload.get("distance"), 15),
        hours_old=parse_int(payload.get("hoursOld"), DEFAULT_HOURS_OLD),
        results_per_term=parse_int(payload.get("resultsPerTerm"), DEFAULT_RESULTS_PER_TERM),
        sites=sites,
        remote_only=bool(payload.get("remoteOnly", False)),
        pay_min=parse_int(payload.get("payMin"), 0),
        pay_max=parse_int(payload.get("payMax"), 0),
        pay_interval="any",
    )


def parse_search_terms(raw_text: str) -> tuple[str, ...]:
    parts = re.split(r"\s+\bOR\b\s+|[\r\n;,]+", raw_text or "", flags=re.IGNORECASE)
    cleaned = []
    seen: set[str] = set()
    for part in parts:
        term = " ".join(part.split())
        key = term.casefold()
        if not term or key in seen:
            continue
        seen.add(key)
        cleaned.append(term)
    return tuple(cleaned)


def parse_sites(raw_sites: Any) -> tuple[str, ...]:
    if not isinstance(raw_sites, list):
        return DEFAULT_SITES

    mapped: list[str] = []
    seen: set[str] = set()
    for raw_site in raw_sites:
        site = map_site_name(raw_site)
        if not site or site in seen:
            continue
        seen.add(site)
        mapped.append(site)
    return tuple(mapped) if mapped else DEFAULT_SITES


def map_site_name(value: Any) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    if text in SITE_DISPLAY_NAMES:
        return text
    return DISPLAY_TO_SITE.get(text.casefold(), "")


def parse_int(value: Any, default: int) -> int:
    text = normalize_text(value)
    if not text:
        return default
    try:
        return int(text)
    except (TypeError, ValueError):
        return default


def parse_port(value: Any, default: int) -> int:
    parsed = parse_int(value, default)
    return parsed if parsed > 0 else default


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def serialize_listing(listing: JobListing) -> dict[str, Any]:
    return {
        "id": listing_id(listing),
        "title": listing.title or "Untitled",
        "company": listing.company or "Unknown company",
        "location": listing.location or "Unknown location",
        "site": listing.site or "Unknown site",
        "pay": format_pay(listing),
        "posted": format_posted_display(listing.date_posted),
        "posted_raw": listing.date_posted or "",
        "term": listing.search_term or "",
        "description": listing.description or "",
        "job_url": listing.job_url or "",
        "company_url": listing.company_url or "",
        "job_type": listing.job_type or "",
        "interval": listing.interval or "",
        "remote": truthy_display(listing.is_remote),
        "salary_min": listing.salary_min or "",
        "salary_max": listing.salary_max or "",
    }


def listing_id(listing: JobListing) -> str:
    if listing.job_url.strip():
        return listing.job_url.strip().lower()
    fallback = "|".join(part.strip().casefold() for part in (listing.title, listing.company, listing.location, listing.site))
    return fallback or f"listing-{abs(hash(listing.title + listing.company))}"


def truthy_display(value: str) -> str:
    clean = normalize_text(value).casefold()
    if clean in {"true", "1", "yes"}:
        return "Yes"
    if clean in {"false", "0", "no"}:
        return "No"
    return normalize_text(value)


def format_pay(listing: JobListing) -> str:
    low = format_currency(listing.salary_min)
    high = format_currency(listing.salary_max)
    interval = normalize_text(listing.interval).casefold()
    if interval.endswith("ly"):
        interval = interval[:-2]
    suffix = f" / {interval}" if interval else ""
    if low and high:
        return f"{low} - {high}{suffix}"
    if low:
        return f"{low}{suffix}"
    if high:
        return f"{high}{suffix}"
    return "Not listed"


def format_currency(value: str) -> str:
    digits = "".join(ch for ch in normalize_text(value) if ch.isdigit())
    if not digits:
        return ""
    return f"${int(digits):,}"


def format_posted_display(value: str) -> str:
    posted = parse_posted_datetime(value)
    if posted is None:
        clean = normalize_text(value)
        return clean or "Unknown"

    now = datetime.now(timezone.utc)
    delta = now - posted
    if delta.total_seconds() < 0:
        delta = posted - now
    if delta.total_seconds() < 86400:
        hours = max(int(delta.total_seconds() // 3600), 1)
        unit = "hour" if hours == 1 else "hours"
        return f"{hours} {unit} ago"
    return posted.astimezone().strftime("%Y-%m-%d")


def parse_posted_datetime(value: str) -> datetime | None:
    clean = normalize_text(value)
    if not clean:
        return None

    candidates = (
        clean,
        clean.replace("Z", "+00:00"),
        clean.replace(" UTC", "+00:00"),
        clean.replace(" ", "T", 1) if " " in clean and "T" not in clean else clean,
    )
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(clean, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


class JobScannerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, directory: str | None = None, **kwargs: Any) -> None:
        super().__init__(*args, directory=directory or str(HTML_DIR), **kwargs)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/api/health":
            self.send_json({"ok": True, "service": "job-scanner-web-api"})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path.rstrip("/") == "/api/search":
            self.handle_search()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", DEFAULT_API_CORS_ORIGIN)
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")

    def handle_search(self) -> None:
        try:
            payload = self.read_json_body()
            config = build_config(payload)
            location, listings = search_jobs(config)
        except JobScannerError as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except Exception as exc:  # pragma: no cover - defensive API boundary
            self.send_json({"ok": False, "error": f"Unexpected server error: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        rows = [serialize_listing(listing) for listing in listings]
        self.send_json(
            {
                "ok": True,
                "location": {
                    "zip_code": location.zip_code,
                    "city": location.city,
                    "state": location.state,
                    "display_name": location.display_name,
                },
                "results": rows,
            }
        )

    def read_json_body(self) -> dict[str, Any]:
        length_text = self.headers.get("Content-Length", "0")
        try:
            length = int(length_text)
        except ValueError as exc:
            raise JobScannerError("Invalid request body length.") from exc
        if length <= 0:
            return {}
        if length > MAX_BODY_BYTES:
            raise JobScannerError("Request body is too large.")
        raw_body = self.rfile.read(length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise JobScannerError("Request body must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise JobScannerError("Request body must be a JSON object.")
        return payload

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(host: str, port: int) -> None:
    if not HTML_DIR.exists():
        raise SystemExit(f"HTML app folder not found: {HTML_DIR}")

    handler = partial(JobScannerHandler, directory=str(HTML_DIR))
    with ThreadingHTTPServer((host, port), handler) as server:
        print(f"Job Scanner web app running at http://{host}:{port}")
        print("Press Ctrl+C to stop.")
        server.serve_forever()


def main() -> None:
    args = parse_args()
    run_server(args.host, args.port)


if __name__ == "__main__":
    main()
