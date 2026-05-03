from __future__ import annotations

import os
import re
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

DEFAULT_ZIP_CODE = ""
DEFAULT_SEARCH_TERMS = ()
DEFAULT_DISTANCE_MILES = 15
MAX_DISTANCE_MILES = 25
DEFAULT_HOURS_OLD = 168
DEFAULT_RESULTS_PER_TERM = 30
DEFAULT_SITES = (
    "linkedin",
    "indeed",
    "zip_recruiter",
    "dice",
    "usajobs",
    "brassring",
    "disney_jobs",
    "paramount_jobs",
    "warner_bros_jobs",
    "universal_jobs",
    "sony_pictures_jobs",
    "netflix_jobs",
)
DEFAULT_PAY_MIN = 0
DEFAULT_PAY_MAX = 0
DEFAULT_PAY_INTERVAL = "any"
PAY_INTERVAL_OPTIONS = ("any", "hour", "day", "week", "month", "year")
JOBSPY_SITES = ("indeed", "zip_recruiter", "linkedin", "glassdoor")
DIRECT_SITES = (
    "dice",
    "usajobs",
    "brassring",
    "disney_jobs",
    "paramount_jobs",
    "warner_bros_jobs",
    "universal_jobs",
    "sony_pictures_jobs",
    "netflix_jobs",
)
SITE_DISPLAY_NAMES = {
    "indeed": "Indeed",
    "zip_recruiter": "ZipRecruiter",
    "linkedin": "LinkedIn",
    "glassdoor": "Glassdoor",
    "dice": "Dice",
    "usajobs": "USAJOBS",
    "brassring": "BrassRing",
    "disney_jobs": "Disney Jobs",
    "paramount_jobs": "Paramount Jobs",
    "warner_bros_jobs": "Warner Bros Jobs",
    "universal_jobs": "Universal Jobs",
    "sony_pictures_jobs": "Sony Pictures Jobs",
    "netflix_jobs": "Netflix Jobs",
}
DIRECT_SOURCE_CONFIG = {
    "dice": {
        "company": "Dice",
        "domains": ("dice.com",),
        "base_queries": ("{term} {location}", "{term} studio {location}"),
        "search_path": "jobs",
        "studio": False,
    },
    "usajobs": {
        "company": "USAJOBS",
        "domains": ("usajobs.gov",),
        "base_queries": ("{term} {location}", "{term} federal {location}"),
        "studio": False,
    },
    "brassring": {
        "company": "BrassRing",
        "domains": ("brassring.com", "sjobs.brassring.com", "jobs.brassring.com"),
        "base_queries": ("{term} {location}", "{term} careers {location}"),
        "studio": False,
    },
    "disney_jobs": {
        "company": "Disney",
        "domains": ("jobs.disneycareers.com",),
        "base_queries": ("{term} {location}", "{term} technology {location}", "{term} studio {location}"),
        "studio": True,
    },
    "paramount_jobs": {
        "company": "Paramount",
        "domains": ("careers.paramount.com",),
        "base_queries": ("{term} {location}", "{term} technology {location}", "{term} streaming {location}"),
        "studio": True,
    },
    "warner_bros_jobs": {
        "company": "Warner Bros. Discovery",
        "domains": ("careers.wbd.com",),
        "base_queries": ("{term} {location}", "{term} technology {location}", "{term} studio {location}"),
        "studio": True,
    },
    "universal_jobs": {
        "company": "Universal",
        "domains": ("jobs.universalparks.com", "jobs.nbcunicareers.com", "nbcunicareers.com"),
        "base_queries": ("{term} {location}", "{term} technology {location}", "{term} studios {location}"),
        "studio": True,
    },
    "sony_pictures_jobs": {
        "company": "Sony Pictures",
        "domains": ("sonypicturesjobs.com", "sonyjobs.com"),
        "base_queries": ("{term} {location}", "{term} technology {location}", "{term} pictures {location}"),
        "studio": True,
    },
    "netflix_jobs": {
        "company": "Netflix",
        "domains": ("jobs.netflix.com",),
        "base_queries": ("{term} {location}", "{term} technology {location}", "{term} studio {location}"),
        "studio": True,
    },
}
STUDIO_COMPANIES = {
    "disney",
    "paramount",
    "warner bros. discovery",
    "warner bros",
    "universal",
    "sony pictures",
    "netflix",
}
TERM_ALIASES = {
    "help desk": ("help desk", "service desk", "desktop support", "it support"),
    "support analyst": (
        "support analyst",
        "technical support analyst",
        "it support analyst",
        "desktop support analyst",
        "help desk analyst",
    ),
    "desktop support": ("desktop support", "endpoint support", "workstation support"),
    "media systems engineer": ("media systems engineer", "media engineer", "broadcast engineer", "production technology"),
}
ZIP_LOOKUP_URL = "https://api.zippopotam.us/us/{zip_code}"
ZIP_FALLBACKS = {
    "91607": {"city": "North Hollywood", "state": "CA"},
}
BING_SEARCH_URL = "https://www.bing.com/search"
PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
)
DIRECT_RESULT_LIMIT = 12
REQUEST_TIMEOUT = 12
ProgressCallback = Callable[[str], None]


class JobScannerError(RuntimeError):
    """Raised when the job search cannot be completed."""


@dataclass(slots=True)
class ResolvedLocation:
    zip_code: str
    city: str
    state: str

    @property
    def display_name(self) -> str:
        return f"{self.city}, {self.state}"

    @property
    def search_location(self) -> str:
        return self.display_name


@dataclass(slots=True)
class JobSearchConfig:
    zip_code: str = DEFAULT_ZIP_CODE
    city: str = ""
    state: str = ""
    custom_url: str = ""
    search_terms: tuple[str, ...] = DEFAULT_SEARCH_TERMS
    distance_miles: int = DEFAULT_DISTANCE_MILES
    hours_old: int = DEFAULT_HOURS_OLD
    results_per_term: int = DEFAULT_RESULTS_PER_TERM
    sites: tuple[str, ...] = DEFAULT_SITES
    remote_only: bool = False
    pay_min: int = DEFAULT_PAY_MIN
    pay_max: int = DEFAULT_PAY_MAX
    pay_interval: str = DEFAULT_PAY_INTERVAL


@dataclass(slots=True)
class JobListing:
    title: str
    company: str
    location: str
    site: str
    search_term: str
    date_posted: str
    salary_min: str
    salary_max: str
    job_type: str
    interval: str
    is_remote: str
    job_url: str
    company_url: str
    description: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class SearchCandidate:
    title: str
    url: str
    snippet: str
    source: str
    company: str


def resolve_location(zip_code: str, city: str = "", state: str = "", timeout: int = 10) -> ResolvedLocation:
    city = city.strip()
    state = state.strip().upper()
    if city and state:
        return ResolvedLocation(zip_code="", city=city, state=state)

    clean_zip = "".join(ch for ch in zip_code if ch.isdigit())
    if len(clean_zip) != 5:
        raise JobScannerError("Enter either a 5-digit ZIP code or a city and state.")

    try:
        with _without_proxy_env():
            session = _build_session()
            response = session.get(ZIP_LOOKUP_URL.format(zip_code=clean_zip), timeout=timeout)
            if response.ok:
                payload = response.json()
                places = payload.get("places") or []
                if places:
                    city = places[0].get("place name") or ""
                    state = places[0].get("state abbreviation") or ""
                    if city and state:
                        return ResolvedLocation(zip_code=clean_zip, city=city, state=state)
    except requests.RequestException:
        pass

    fallback = ZIP_FALLBACKS.get(clean_zip)
    if fallback:
        return ResolvedLocation(zip_code=clean_zip, city=fallback["city"], state=fallback["state"])

    raise JobScannerError(
        f"Could not resolve ZIP code {clean_zip}. Check your connection or try a nearby city and state."
    )


def search_jobs(
    config: JobSearchConfig,
    progress_callback: ProgressCallback | None = None,
) -> tuple[ResolvedLocation, list[JobListing]]:
    location = resolve_location(config.zip_code, config.city, config.state)
    scrape_jobs = _load_jobspy()
    distance_miles = min(max(int(config.distance_miles), 1), MAX_DISTANCE_MILES)
    pay_min = max(int(config.pay_min), 0)
    pay_max = max(int(config.pay_max), 0)
    if pay_max and pay_max < pay_min:
        pay_min, pay_max = pay_max, pay_min
    pay_interval = _normalize_interval(config.pay_interval)
    posted_cutoff = datetime.now(timezone.utc) - timedelta(hours=max(int(config.hours_old), 1))

    listings: list[JobListing] = []
    listings_by_key: dict[str, JobListing] = {}
    errors: list[str] = []
    session = _build_session()
    posted_cache: dict[str, str] = {}

    for term in config.search_terms:
        for site_name in config.sites:
            _progress(progress_callback, f"Searching {SITE_DISPLAY_NAMES.get(site_name, site_name)} for {term}...")
            if site_name in JOBSPY_SITES:
                site_results, site_errors = _search_jobspy_site(
                    scrape_jobs,
                    site_name,
                    term,
                    config,
                    location,
                )
            else:
                site_results, site_errors = _search_direct_site(session, site_name, term, location, config.results_per_term)

            errors.extend(site_errors)
            for listing in site_results:
                _fill_missing_posted_date(session, listing, posted_cache)
                if not _matches_search_term(listing, term):
                    continue
                if not _matches_posted_window(listing, posted_cutoff):
                    continue
                if not _matches_interval(listing, pay_interval):
                    continue
                if not _matches_pay_range(listing, pay_min, pay_max):
                    continue
                key = _dedupe_key(listing)
                existing = listings_by_key.get(key)
                if existing is None:
                    listings_by_key[key] = listing
                    continue
                existing.search_term = _merge_search_terms(existing.search_term, listing.search_term)

        if config.custom_url.strip():
            _progress(progress_callback, f"Searching custom URL for {term}...")
            site_results, site_errors = _search_custom_url(
                session,
                config.custom_url,
                term,
                location,
                config.results_per_term,
            )
            errors.extend(site_errors)
            for listing in site_results:
                _fill_missing_posted_date(session, listing, posted_cache)
                if not _matches_search_term(listing, term):
                    continue
                if not _matches_posted_window(listing, posted_cutoff):
                    continue
                if not _matches_interval(listing, pay_interval):
                    continue
                if not _matches_pay_range(listing, pay_min, pay_max):
                    continue
                key = _dedupe_key(listing)
                existing = listings_by_key.get(key)
                if existing is None:
                    listings_by_key[key] = listing
                    continue
                existing.search_term = _merge_search_terms(existing.search_term, listing.search_term)

    listings = list(listings_by_key.values())
    listings.sort(key=_listing_priority)
    if not listings and errors:
        joined = "\n".join(errors[:10])
        raise JobScannerError(f"No job listings could be loaded.\n\nSource errors:\n{joined}")
    return location, listings


def _search_jobspy_site(
    scrape_jobs: Callable[..., Any],
    site_name: str,
    term: str,
    config: JobSearchConfig,
    location: ResolvedLocation,
) -> tuple[list[JobListing], list[str]]:
    scrape_kwargs: dict[str, Any] = {
        "site_name": [site_name],
        "search_term": term,
        "location": location.search_location,
        "distance": min(max(int(config.distance_miles), 1), MAX_DISTANCE_MILES),
        "results_wanted": config.results_per_term,
        "hours_old": config.hours_old,
        "country_indeed": "USA",
        "linkedin_fetch_description": True,
        "verbose": 0,
    }
    if config.remote_only:
        scrape_kwargs["is_remote"] = True

    try:
        with _without_proxy_env():
            frame = scrape_jobs(**scrape_kwargs)
    except Exception as exc:
        message = str(exc)
        if site_name == "glassdoor" and (
            "status code 400" in message.casefold() or "location not parsed" in message.casefold()
        ):
            return [], [f"Glassdoor skipped for '{term}': request blocked or location not parsed."]
        return [], [f"{site_name} for '{term}': {exc}"]

    records = frame.to_dict("records") if hasattr(frame, "to_dict") else []
    listings = [_normalize_listing(record, term) for record in records]
    return listings, []


def _search_direct_site(
    session: requests.Session,
    site_name: str,
    term: str,
    location: ResolvedLocation,
    results_limit: int,
) -> tuple[list[JobListing], list[str]]:
    source_config = DIRECT_SOURCE_CONFIG.get(site_name)
    if source_config is None:
        return [], [f"Unknown source: {site_name}"]

    listings: list[JobListing] = []
    errors: list[str] = []
    seen_urls: set[str] = set()
    for query in _direct_queries(source_config, term, location):
        try:
            candidates = _search_bing(session, query, source_config["domains"])
        except requests.RequestException as exc:
            errors.append(f"{SITE_DISPLAY_NAMES.get(site_name, site_name)} for '{term}': {exc}")
            continue

        for candidate in candidates:
            if candidate.url in seen_urls:
                continue
            seen_urls.add(candidate.url)
            listings.append(_candidate_to_listing(candidate, term, location, site_name))
            if len(listings) >= results_limit:
                return listings, errors
    return listings, errors


def _candidate_to_listing(
    candidate: SearchCandidate,
    term: str,
    location: ResolvedLocation,
    site_name: str,
) -> JobListing:
    return JobListing(
        title=candidate.title or "Untitled",
        company=candidate.company or SITE_DISPLAY_NAMES.get(site_name, site_name),
        location=location.display_name,
        site=SITE_DISPLAY_NAMES.get(site_name, site_name),
        search_term=term,
        date_posted="",
        salary_min="",
        salary_max="",
        job_type="",
        interval="",
        is_remote="",
        job_url=candidate.url,
        company_url=_base_company_url(candidate.url),
        description=candidate.snippet,
    )


def _search_bing(session: requests.Session, query: str, allowed_domains: tuple[str, ...]) -> list[SearchCandidate]:
    with _without_proxy_env():
        response = session.get(
            BING_SEARCH_URL,
            params={"q": query, "count": str(DIRECT_RESULT_LIMIT)},
            timeout=REQUEST_TIMEOUT,
        )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results: list[SearchCandidate] = []
    for result in soup.select("li.b_algo"):
        anchor = result.select_one("h2 a")
        if anchor is None:
            continue
        url = (anchor.get("href") or "").strip()
        if not _allowed_result_domain(url, allowed_domains):
            continue
        title = " ".join(anchor.get_text(" ", strip=True).split())
        snippet_node = result.select_one(".b_caption p") or result.select_one("p")
        snippet = " ".join((snippet_node.get_text(" ", strip=True) if snippet_node else "").split())
        results.append(
            SearchCandidate(
                title=title,
                url=url,
                snippet=snippet,
                source="Bing",
                company=_company_from_title(title),
            )
        )
        if len(results) >= DIRECT_RESULT_LIMIT:
            break
    return results


def _search_custom_url(
    session: requests.Session,
    custom_url: str,
    term: str,
    location: ResolvedLocation,
    results_limit: int,
) -> tuple[list[JobListing], list[str]]:
    domain = _domain_key(custom_url)
    if not domain:
        return [], [f"Custom URL skipped for '{term}': invalid URL."]

    try:
        candidates = _search_bing(session, f"site:{domain} {term} {location.display_name}", (domain,))
    except requests.RequestException as exc:
        return [], [f"Custom URL for '{term}': {exc}"]

    listings: list[JobListing] = []
    seen_urls: set[str] = set()
    for candidate in candidates:
        if candidate.url in seen_urls:
            continue
        seen_urls.add(candidate.url)
        listings.append(
            JobListing(
                title=candidate.title or "Untitled",
                company=candidate.company or domain,
                location=location.display_name,
                site=domain,
                search_term=term,
                date_posted="",
                salary_min="",
                salary_max="",
                job_type="",
                interval="",
                is_remote="",
                job_url=candidate.url,
                company_url=_base_company_url(candidate.url),
                description=candidate.snippet,
            )
        )
        if len(listings) >= results_limit:
            break
    return listings, []


def _fill_missing_posted_date(session: requests.Session, listing: JobListing, posted_cache: dict[str, str]) -> None:
    if listing.date_posted or not listing.job_url:
        return
    cached = posted_cache.get(listing.job_url)
    if cached is not None:
        listing.date_posted = cached
        return
    inferred = _infer_posted_date_from_job_page(session, listing.job_url)
    posted_cache[listing.job_url] = inferred
    listing.date_posted = inferred


def _infer_posted_date_from_job_page(session: requests.Session, job_url: str) -> str:
    try:
        with _without_proxy_env():
            response = session.get(job_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException:
        return ""

    text = BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True)
    relative_patterns = (
        r"\b(\d+)\s+hours?\s+ago\b",
        r"\b(\d+)\s+days?\s+ago\b",
        r"\b(\d+)\s+weeks?\s+ago\b",
    )
    now = datetime.now(timezone.utc)
    for pattern in relative_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        amount = int(match.group(1))
        lowered = match.group(0).casefold()
        if "hour" in lowered:
            return (now - timedelta(hours=amount)).isoformat(timespec="minutes")
        if "day" in lowered:
            return (now - timedelta(days=amount)).isoformat(timespec="minutes")
        if "week" in lowered:
            return (now - timedelta(weeks=amount)).isoformat(timespec="minutes")
    return ""


def _direct_queries(source_config: dict[str, Any], term: str, location: ResolvedLocation) -> tuple[str, ...]:
    queries = []
    for template in source_config["base_queries"]:
        for domain in source_config["domains"]:
            queries.append(f'site:{domain} {template.format(term=term, location=location.display_name)}')
    return tuple(dict.fromkeys(" ".join(query.split()) for query in queries))


def _allowed_result_domain(url: str, allowed_domains: tuple[str, ...]) -> bool:
    domain = _domain_key(url)
    return any(domain == allowed or domain.endswith(f".{allowed}") for allowed in allowed_domains)


def _base_company_url(url: str) -> str:
    match = re.match(r"^(https?://[^/]+)", url.strip())
    return match.group(1) if match else url


def _company_from_title(title: str) -> str:
    clean = " ".join(title.split())
    if not clean:
        return ""
    if " at " in clean.lower():
        return clean.rsplit(" at ", 1)[-1].strip()
    parts = re.split(r"\s+[|\-]\s+", clean)
    return parts[-1].strip() if len(parts) > 1 else clean


def _load_jobspy():
    try:
        from jobspy import scrape_jobs  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise JobScannerError(
            "Missing dependency: install python-jobspy before running the job scanner."
        ) from exc
    return scrape_jobs


def _normalize_listing(record: dict[str, Any], search_term: str) -> JobListing:
    return JobListing(
        title=_stringify(record.get("title")),
        company=_stringify(record.get("company")),
        location=_stringify(record.get("location")),
        site=_stringify(record.get("site")),
        search_term=search_term,
        date_posted=_format_date(record.get("date_posted")),
        salary_min=_stringify(record.get("min_amount")),
        salary_max=_stringify(record.get("max_amount")),
        job_type=_stringify(record.get("job_type")),
        interval=_stringify(record.get("interval")),
        is_remote=_stringify(record.get("is_remote")),
        job_url=_stringify(record.get("job_url")),
        company_url=_stringify(record.get("company_url")),
        description=_stringify(record.get("description")),
    )


def _dedupe_key(listing: JobListing) -> str:
    url = listing.job_url.strip().lower()
    if url:
        return url
    return "|".join(
        part.strip().lower()
        for part in (listing.title, listing.company, listing.location, listing.search_term, listing.site)
    )


def _listing_priority(listing: JobListing) -> tuple[int, float, str]:
    studio_rank = 0 if _is_studio_listing(listing) else 1
    return (studio_rank, -_timestamp_value(listing.date_posted), listing.title.casefold())


def _is_studio_listing(listing: JobListing) -> bool:
    company = listing.company.casefold()
    site = listing.site.casefold()
    return any(name in company for name in STUDIO_COMPANIES) or "jobs" in site and any(
        studio.split()[0] in site for studio in STUDIO_COMPANIES
    )


def _timestamp_value(value: str) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _format_date(value: Any) -> str:
    if value in (None, "", "NaT"):
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="minutes")
    return _stringify(value)


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if text == "nan":
        return ""
    return text.strip()


def _matches_search_term(listing: JobListing, search_term: str) -> bool:
    title = _normalize_text(listing.title)
    aliases = TERM_ALIASES.get(search_term.casefold(), (search_term,))
    normalized_aliases = tuple(_normalize_text(alias) for alias in aliases)

    if any(alias and alias in title for alias in normalized_aliases):
        return True

    tokens = [token for token in _normalize_text(search_term).split() if token]
    if tokens and all(token in title for token in tokens):
        return True

    return False


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().replace("/", " ").replace("-", " ").split())


def _matches_pay_range(listing: JobListing, pay_min: int, pay_max: int) -> bool:
    if pay_min == 0 and pay_max == 0:
        return True

    min_amount = _parse_amount(listing.salary_min)
    max_amount = _parse_amount(listing.salary_max)
    if min_amount is None and max_amount is None:
        return False

    low = min_amount if min_amount is not None else max_amount
    high = max_amount if max_amount is not None else min_amount
    if low is None or high is None:
        return False

    if pay_min and high < pay_min:
        return False
    if pay_max and low > pay_max:
        return False
    return True


def _matches_interval(listing: JobListing, pay_interval: str) -> bool:
    if pay_interval == DEFAULT_PAY_INTERVAL:
        return True
    return _normalize_interval(listing.interval) == pay_interval


def _matches_posted_window(listing: JobListing, cutoff: datetime) -> bool:
    posted = _parse_posted_datetime(listing.date_posted)
    if posted is None:
        return True
    return posted >= cutoff


def _parse_amount(value: str) -> int | None:
    digits = "".join(ch for ch in value if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _normalize_interval(value: str) -> str:
    interval = _normalize_text(value)
    if interval.endswith("ly"):
        interval = interval[:-2]
    if interval in {"annual", "annum"}:
        return "year"
    if interval in PAY_INTERVAL_OPTIONS:
        return interval
    return DEFAULT_PAY_INTERVAL if not interval else interval


def _parse_posted_datetime(value: str) -> datetime | None:
    clean = value.strip()
    if not clean:
        return None

    candidates = (
        clean,
        clean.replace("Z", "+00:00"),
        clean.replace(" UTC", "+00:00"),
    )
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            continue

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            parsed = datetime.strptime(clean, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def _merge_search_terms(existing: str, incoming: str) -> str:
    merged: list[str] = []
    for value in (existing, incoming):
        for part in value.split(" | "):
            term = part.strip()
            if term and term not in merged:
                merged.append(term)
    return " | ".join(merged)


def _domain_key(url: str) -> str:
    match = re.match(r"^https?://([^/:]+)", url.strip(), re.IGNORECASE)
    if not match:
        return ""
    domain = match.group(1).casefold()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _build_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return session


def _progress(callback: ProgressCallback | None, message: str) -> None:
    if callback is not None:
        callback(message)


@contextmanager
def _without_proxy_env():
    saved = {key: os.environ.get(key) for key in PROXY_ENV_KEYS}
    try:
        for key in PROXY_ENV_KEYS:
            os.environ.pop(key, None)
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
