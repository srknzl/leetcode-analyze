#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.32", "playwright>=1.48"]
# ///
"""Export a complete LeetCode submission history -- every attempt at every
status, with full source code -- into a folder an LLM can analyse unaided.

    uv run leetcode_export.py              # incremental (default)
    uv run leetcode_export.py --full       # re-list the whole history
    uv run leetcode_export.py --self-test  # offline assertions, no network

Uses LeetCode's undocumented internal endpoints. See README.md.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

BASE = "https://leetcode.com"
GRAPHQL_URL = f"{BASE}/graphql"
SUBMISSIONS_URL = f"{BASE}/api/submissions/"
LOGIN_URL = f"{BASE}/accounts/login/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

PAGE = 20                      # /api/submissions/ ignores limit > 20
CATALOG_PAGE = 100
CHECKPOINT_EVERY = 10
SESSION_CHECK_EVERY = 200
MAX_RETRIES = 5
MAX_BACKOFF = 300.0
CONSECUTIVE_FAILURE_LIMIT = 5
CATALOG_MAX_AGE = 30 * 86400
LOGIN_TIMEOUT = 600
HTTP_TIMEOUT = 30

CSV_COLUMNS = [
    "submission_id", "timestamp", "datetime_utc", "title", "titleSlug",
    "difficulty", "topic_tags", "status_display", "lang", "runtime", "memory",
    "runtime_percentile", "memory_percentile", "code_file_path",
]

EXT = {
    "python3": "py", "python": "py", "pypy3": "py", "java": "java",
    "cpp": "cpp", "c": "c", "csharp": "cs", "javascript": "js",
    "typescript": "ts", "golang": "go", "ruby": "rb", "swift": "swift",
    "kotlin": "kt", "rust": "rs", "php": "php", "scala": "scala",
    "elixir": "ex", "erlang": "erl", "racket": "rkt", "dart": "dart",
    "mysql": "sql", "postgresql": "sql", "mssql": "sql", "oraclesql": "sql",
}

Q_USER_STATUS = "query { userStatus { isSignedIn username } }"

Q_SUBMISSION_DETAILS = """
query submissionDetails($submissionId: Int!) {
  submissionDetails(submissionId: $submissionId) {
    code
    timestamp
    statusCode
    lang { name }
    question { questionId titleSlug title }
    runtime
    memory
    runtimePercentile
    memoryPercentile
  }
}
"""

Q_PROBLEM_LIST = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(categorySlug: $categorySlug, limit: $limit, skip: $skip, filters: $filters) {
    total: totalNum
    questions: data {
      difficulty
      frontendQuestionId: questionFrontendId
      title
      titleSlug
      topicTags { name slug }
    }
  }
}
"""

Q_USER_STATS = """
query userStats($username: String!) {
  matchedUser(username: $username) {
    submitStats {
      totalSubmissionNum { difficulty count submissions }
    }
  }
}
"""

Q_SINGLE_QUESTION = """
query singleQuestion($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionFrontendId
    title
    titleSlug
    difficulty
    topicTags { name slug }
  }
}
"""


class SessionExpired(Exception):
    """The LEETCODE_SESSION cookie is no longer valid."""


class FetchFailed(Exception):
    """One item failed after exhausting retries; the run continues."""


def log(msg: str = "") -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------
# Pure helpers (all covered by --self-test)
# --------------------------------------------------------------------------

def ext_for(lang: str) -> str:
    """File extension for a LeetCode language name, .txt for anything new."""
    return EXT.get((lang or "").strip().lower(), "txt")


def safe_component(value: str, fallback: str = "unknown") -> str:
    """Sanitise a network-supplied string for use as a single path component.

    Slugs come from LeetCode, so they are untrusted input on a filesystem
    path: strip anything that could traverse or escape the export folder.
    """
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "")).strip("._-")
    return cleaned or fallback


def code_filename(timestamp: int, status: str, lang: str, sub_id: int) -> str:
    """`<timestamp>_<Status>_<lang>_<id>.<ext>`.

    The submission id is part of the name because two submissions can share a
    timestamp; without it the second would silently overwrite the first.
    """
    return "{}_{}_{}_{}.{}".format(
        int(timestamp),
        safe_component(status, "Unknown"),
        safe_component(lang, "unknown"),
        int(sub_id),
        ext_for(lang),
    )


def backoff_delay(attempt: int, base: float, cap: float = MAX_BACKOFF) -> float:
    """Deterministic exponential backoff. Jitter is applied by the caller."""
    return min(base * (2 ** attempt), cap)


def retry_wait(retry_after: str | None, attempt: int, base: float) -> float:
    """Seconds to wait before a retry. Retry-After wins over our own backoff."""
    if retry_after:
        raw = str(retry_after).strip()
        try:
            return max(0.0, float(raw))
        except ValueError:
            pass
        try:  # Retry-After may also be an HTTP-date
            when = parsedate_to_datetime(raw)
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError):
            pass
    return backoff_delay(attempt, base) * random.uniform(1.0, 1.3)


def next_cutoff(state: dict) -> int:
    """The incremental cutoff for the *next* run.

    Only advances once the queue has fully drained on a complete listing.
    Advancing to "newest processed so far" would make the next run's listing
    stop above submissions still sitting unprocessed in the queue, silently
    orphaning them -- submissions are processed newest-first.
    """
    current = int(state.get("last_completed_timestamp") or 0)
    if state.get("pending") or state.get("list_cursor") or not state.get("list_complete"):
        return current
    return max(current, int(state.get("newest_listed_timestamp") or 0))


def history_enumerated(state: dict) -> bool:
    """Do we already hold at least as many submissions as LeetCode reports?

    A walk that was interrupted after covering everything still leaves us with
    the complete set; the count says so even when the completion flag does not.
    """
    reported = int(state.get("reported_total_submissions") or 0)
    if not reported:
        return False
    held = len(state.get("pending") or []) + len(state.get("processed_ids") or [])
    return held >= reported


def listing_cutoff(state: dict, full: bool = False) -> int:
    """How far back the listing must walk -- the *listing* frontier.

    Distinct from next_cutoff(), which tracks how far the *downloads* have got.
    Once the whole history has been enumerated, every submission at or below
    newest_listed_timestamp is already recorded (queued or processed), so a
    re-list only needs to look for submissions newer than that. Using the
    download frontier here would re-walk the entire history on every run until
    the queue drained, costing hundreds of requests to discover nothing.
    """
    if full:
        return 0
    if state.get("list_complete") or history_enumerated(state):
        return max(int(state.get("newest_listed_timestamp") or 0),
                   int(state.get("last_completed_timestamp") or 0))
    return int(state.get("last_completed_timestamp") or 0)


def month_key(timestamp: int) -> str:
    return datetime.fromtimestamp(int(timestamp), timezone.utc).strftime("%Y-%m")


def iso_utc(timestamp: int) -> str:
    return datetime.fromtimestamp(int(timestamp), timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def fmt_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 90:
        return f"{seconds}s"
    if seconds < 5400:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h {(seconds % 3600) // 60}m"


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------

def save_json(path: Path, data) -> None:
    """Atomic write -- a Ctrl+C mid-write must not corrupt state."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def new_state() -> dict:
    return {
        "version": 1,
        "username": None,
        "last_completed_timestamp": 0,
        "newest_listed_timestamp": 0,
        "list_complete": False,
        "catalog_fetched_at": 0,
        "processed_ids": [],
        "pending": [],
        "list_cursor": {},
        "reported_total_submissions": 0,
        "reported_problems_attempted": 0,
    }


def read_rows(csv_path: Path) -> list[dict]:
    """Read submissions_all.csv back with numeric columns coerced."""
    if not csv_path.exists():
        return []
    rows, seen = [], set()
    with csv_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                row["timestamp"] = int(row.get("timestamp") or 0)
                row["submission_id"] = int(row.get("submission_id") or 0)
            except ValueError:
                continue
            if row["submission_id"] in seen:
                continue    # a crash between checkpoints can duplicate rows
            seen.add(row["submission_id"])
            rows.append(row)
    return rows


# --------------------------------------------------------------------------
# HTTP: every request to LeetCode goes through Client.request
# --------------------------------------------------------------------------

class Client:
    def __init__(self, cookies: dict, delay: float):
        import requests

        self.delay = delay
        self.requests_made = 0
        self._session_checks = 0
        self.username = None
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": USER_AGENT,
            "Referer": f"{BASE}/",
            "x-csrftoken": cookies.get("csrftoken", ""),
            "Accept": "application/json",
        })
        # Carry the whole jar across: the session may lean on more than the
        # two cookies we care about by name.
        for name, value in cookies.items():
            self.s.cookies.set(name, value, domain=".leetcode.com")

    def request(self, method: str, url: str, **kwargs):
        import requests

        for attempt in range(MAX_RETRIES + 1):
            # Sequential and paced: this is the whole rate-limit strategy.
            time.sleep(self.delay * random.uniform(0.85, 1.25))
            try:
                resp = self.s.request(method, url, timeout=HTTP_TIMEOUT, **kwargs)
            except requests.RequestException as exc:
                if attempt >= MAX_RETRIES:
                    raise FetchFailed(f"network error: {exc}") from exc
                wait = backoff_delay(attempt, self.delay) * random.uniform(1.0, 1.3)
                log(f"    network error ({exc.__class__.__name__}); retry in {fmt_duration(wait)}")
                time.sleep(wait)
                continue

            self.requests_made += 1
            if resp.status_code == 401:
                raise SessionExpired("LeetCode returned 401")
            if resp.status_code in (403, 429) or resp.status_code >= 500:
                if attempt >= MAX_RETRIES:
                    raise FetchFailed(f"HTTP {resp.status_code} after {MAX_RETRIES} "
                                      f"retries: {resp.text[:200]!r}")
                wait = retry_wait(resp.headers.get("Retry-After"), attempt, self.delay)
                label = ("rate limited" if resp.status_code in (403, 429)
                         else f"HTTP {resp.status_code}")
                log(f"    {label}; backing off {fmt_duration(wait)} "
                    f"(retry {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait)
                continue
            if resp.status_code >= 400:
                raise FetchFailed(f"HTTP {resp.status_code}: {resp.text[:200]!r}")
            return resp
        raise FetchFailed("retries exhausted")

    def graphql(self, query: str, variables: dict | None = None) -> dict:
        resp = self.request("POST", GRAPHQL_URL,
                            json={"query": query, "variables": variables or {}})
        try:
            payload = resp.json()
        except ValueError as exc:
            raise FetchFailed("GraphQL response was not JSON") from exc
        if payload.get("errors"):
            raise FetchFailed(f"GraphQL error: {payload['errors'][0].get('message', '?')}")
        return payload.get("data") or {}

    def signed_in_as(self) -> str | None:
        try:
            status = (self.graphql(Q_USER_STATUS).get("userStatus") or {})
        except (FetchFailed, SessionExpired):
            return None
        return status.get("username") if status.get("isSignedIn") else None

    def periodic_session_check(self) -> None:
        """Cheap insurance against burning retries on a dead session."""
        due = self.requests_made // SESSION_CHECK_EVERY
        if due > self._session_checks:
            self._session_checks = due
            if not self.signed_in_as():
                raise SessionExpired("session went stale mid-run")


# --------------------------------------------------------------------------
# Auth: a real browser window, driven by the user. We never see credentials.
# --------------------------------------------------------------------------

def _leetcode_cookies(context) -> dict:
    return {
        c["name"]: c["value"]
        for c in context.cookies()
        if "leetcode.com" in (c.get("domain") or "")
    }


def clean_cookie_value(raw: str, name: str = "LEETCODE_SESSION") -> str:
    """Strip quotes and a leading `NAME=` from a pasted cookie value."""
    value = (raw or "").strip().strip('"').strip("'").strip()
    if value.lower().startswith(f"{name.lower()}="):
        value = value.split("=", 1)[1].strip()
    return value.rstrip(";").strip()


def cookies_from_env() -> dict:
    """Session handed over directly, skipping the browser entirely."""
    token = clean_cookie_value(os.environ.get("LEETCODE_SESSION", ""))
    if not token:
        return {}
    cookies = {"LEETCODE_SESSION": token}
    csrf = clean_cookie_value(os.environ.get("LEETCODE_CSRFTOKEN", ""), "csrftoken")
    if csrf:
        cookies["csrftoken"] = csrf
    return cookies


def confirm_signed_in(context) -> str | None:
    """Who does LeetCode think we are, asked through the browser's cookie jar?"""
    from playwright.sync_api import Error as PlaywrightError

    try:
        resp = context.request.post(
            GRAPHQL_URL,
            data={"query": Q_USER_STATUS, "variables": {}},
            headers={"Content-Type": "application/json", "Referer": f"{BASE}/"},
            timeout=15000,
        )
        if not resp.ok:
            return None
        status = ((resp.json().get("data") or {}).get("userStatus") or {})
    except (PlaywrightError, ValueError, KeyError):
        return None
    return status.get("username") if status.get("isSignedIn") else None


def read_profile_cookies(profile_dir: Path) -> dict:
    """Fast path: read cookies from the saved profile without showing a window."""
    if not profile_dir.exists():
        return {}
    try:
        from playwright.sync_api import Error as PlaywrightError, sync_playwright
    except ImportError:
        return {}
    try:
        with sync_playwright() as pw:
            context = pw.chromium.launch_persistent_context(str(profile_dir), headless=True)
            try:
                return _leetcode_cookies(context)
            finally:
                context.close()
    except PlaywrightError as exc:
        log(f"  could not read saved session ({exc.__class__.__name__}); will ask you to log in")
        return {}


def interactive_login(profile_dir: Path) -> tuple[dict, str]:
    """Open a visible browser and wait until LeetCode confirms we are signed in.

    Waiting for a LEETCODE_SESSION cookie to appear is not enough -- a cookie
    can show up part-way through an OAuth handshake, well before the login has
    actually completed. So we ask LeetCode who we are and only accept a real
    username, and we keep the window open until we get one.
    """
    try:
        from playwright.sync_api import Error as PlaywrightError, sync_playwright
    except ImportError:
        raise SystemExit(
            "  Playwright is not installed, so the browser login is unavailable.\n"
            "  Either install it, or set LEETCODE_SESSION in your environment\n"
            "  (see README: 'Signing in with a session cookie').")

    profile_dir.mkdir(parents=True, exist_ok=True)
    log("\n  Opening a browser window -- log in to LeetCode yourself.")
    log("  Any method works (password, Google, GitHub, 2FA). This tool never")
    log("  sees your credentials; it only reads the session cookie afterwards.")
    log("  The window stays open until LeetCode confirms the login, then closes")
    log(f"  on its own. Waiting up to {LOGIN_TIMEOUT // 60} minutes...\n")

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            str(profile_dir), headless=False, viewport=None)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(LOGIN_URL)

            deadline = time.time() + LOGIN_TIMEOUT
            checked_token, last_check, username = None, 0.0, None
            announced = False
            while time.time() < deadline:
                try:
                    cookies = _leetcode_cookies(context)
                except PlaywrightError:
                    raise SystemExit("  Browser closed before login completed. Nothing saved.")

                token = cookies.get("LEETCODE_SESSION")
                if token and not announced:
                    log("  Session cookie appeared; confirming with LeetCode...")
                    announced = True
                # Re-confirm whenever the session cookie changes (logging in
                # rotates it), plus a slow heartbeat as a safety net.
                if token and (token != checked_token or time.time() - last_check > 10):
                    checked_token, last_check = token, time.time()
                    username = confirm_signed_in(context)
                    if username:
                        break
                time.sleep(2)
            else:
                raise SystemExit(
                    "  Timed out waiting for a confirmed login.\n"
                    "  If Google sign-in would not load, try email/password or GitHub\n"
                    "  instead -- Google sometimes blocks automated browsers.")

            log(f"  Confirmed: signed in as {username}.")
            cookies = _leetcode_cookies(context)
            if not cookies.get("csrftoken"):
                page.goto(f"{BASE}/")
                time.sleep(2)
                cookies = _leetcode_cookies(context)
            return cookies, username
        finally:
            try:
                context.close()
            except PlaywrightError:
                pass


def authenticate(profile_dir: Path, delay: float) -> Client:
    env_cookies = cookies_from_env()
    if env_cookies:
        log("  Using LEETCODE_SESSION from the environment (no browser needed).")
        client = Client(env_cookies, delay)
        username = client.signed_in_as()
        if not username:
            raise SystemExit(
                "  LeetCode rejected the LEETCODE_SESSION value in your environment.\n"
                "  It has most likely expired -- copy a fresh one from a browser\n"
                "  where you are logged in (see README: 'Signing in with a session\n"
                "  cookie'). Make sure you copied the cookie's value, not its name.")
        log(f"  Signed in as {username}.")
        client.username = username
        return client

    cookies = read_profile_cookies(profile_dir)
    if cookies.get("LEETCODE_SESSION"):
        client = Client(cookies, delay)
        username = client.signed_in_as()
        if username:
            log(f"  Signed in as {username} (saved session).")
            client.username = username
            return client
        log("  Saved session has expired.")

    cookies, username = interactive_login(profile_dir)
    client = Client(cookies, delay)
    if not client.signed_in_as():
        # The browser was signed in, so the login worked; the cookie handoff
        # into requests did not. Say which, rather than blaming the login.
        raise SystemExit(
            f"  Logged in as {username} in the browser, but the exported cookies\n"
            f"  were rejected outside it. Cookies carried over: "
            f"{', '.join(sorted(cookies)) or 'none'}.\n"
            f"  Please report this -- it is a bug in the cookie handoff.")
    log(f"  Signed in as {username}.")
    client.username = username
    return client


# --------------------------------------------------------------------------
# Phase 2: problem catalog (difficulty + topic tags)
# --------------------------------------------------------------------------

def fetch_catalog(client: Client) -> dict:
    catalog: dict = {}
    skip, total = 0, None
    while total is None or skip < total:
        data = client.graphql(Q_PROBLEM_LIST, {
            "categorySlug": "", "skip": skip, "limit": CATALOG_PAGE, "filters": {}})
        block = data.get("problemsetQuestionList") or {}
        questions = block.get("questions") or []
        if total is None:
            total = int(block.get("total") or 0)
            log(f"  {total} problems in the catalog")
        if not questions:
            break
        for q in questions:
            slug = q.get("titleSlug")
            if slug:
                catalog[slug] = {
                    "title": q.get("title"),
                    "difficulty": q.get("difficulty"),
                    "frontendQuestionId": q.get("frontendQuestionId"),
                    "topicTags": q.get("topicTags") or [],
                }
        skip += CATALOG_PAGE
        log(f"  catalog {min(skip, total)}/{total}")
    return catalog


def ensure_catalog(client: Client, outdir: Path, state: dict, force: bool) -> dict:
    path = outdir / "problem_catalog.json"
    catalog = load_json(path, {})
    age = time.time() - float(state.get("catalog_fetched_at") or 0)
    if catalog and not force and age < CATALOG_MAX_AGE:
        log(f"  Catalog: {len(catalog)} problems (cached, {int(age // 86400)}d old)")
        return catalog
    log("  Fetching problem catalog...")
    catalog = fetch_catalog(client) or catalog
    save_json(path, catalog)
    state["catalog_fetched_at"] = int(time.time())
    return catalog


def lookup_problem(client: Client, catalog: dict, slug: str) -> dict:
    """Catalog hit, else one extra query (premium/renamed/delisted problems)."""
    if slug in catalog:
        return catalog[slug]
    try:
        question = (client.graphql(Q_SINGLE_QUESTION, {"titleSlug": slug}) or {}).get("question")
    except FetchFailed:      # a dead session must propagate, not degrade silently
        question = None
    entry = {
        "title": (question or {}).get("title"),
        "difficulty": (question or {}).get("difficulty") or "Unknown",
        "frontendQuestionId": (question or {}).get("questionFrontendId"),
        "topicTags": (question or {}).get("topicTags") or [],
    }
    catalog[slug] = entry
    return entry


# --------------------------------------------------------------------------
# Phase 3: list submissions (cheap; builds the work queue)
# --------------------------------------------------------------------------

def fetch_account_totals(client: Client, username: str) -> tuple[int, int]:
    """LeetCode's own (submissions, problems attempted) count for this account.

    Gives the listing phase a denominator, and gives the analysis an honest
    completeness check against what LeetCode says exists.
    """
    try:
        data = client.graphql(Q_USER_STATS, {"username": username})
    except FetchFailed:
        return 0, 0
    stats = (((data.get("matchedUser") or {}).get("submitStats") or {})
             .get("totalSubmissionNum") or [])
    for entry in stats:
        if entry.get("difficulty") == "All":
            return int(entry.get("submissions") or 0), int(entry.get("count") or 0)
    return 0, 0


def list_record(raw: dict) -> dict:
    return {
        "id": int(raw["id"]),
        "timestamp": int(raw.get("timestamp") or 0),
        "title": raw.get("title") or "",
        "status_display": raw.get("status_display") or "Unknown",
        "lang": raw.get("lang") or "",
        "runtime": raw.get("runtime") or "",
        "memory": raw.get("memory") or "",
    }


def list_submissions(client: Client, state: dict, full: bool, outdir: Path) -> None:
    """Walk the submission list newest-first, checkpointing as we go.

    Deep offset pagination gets refused eventually, so we also pass the
    `last_key` cursor the API hands back. If the walk is cut short we keep
    everything found so far and record where to resume -- a long listing is
    too expensive to throw away on one bad response.
    """
    cutoff = listing_cutoff(state, full)

    known = set(state["processed_ids"]) | {p["id"] for p in state["pending"]}
    newest = int(state.get("newest_listed_timestamp") or 0)

    enumerated = bool(state.get("list_complete")) or history_enumerated(state)
    cursor = {} if (full or enumerated) else dict(state.get("list_cursor") or {})
    offset = int(cursor.get("offset") or 0)
    last_key = cursor.get("last_key") or ""

    reported = int(state.get("reported_total_submissions") or 0)
    if not reported and state.get("username"):
        reported, problems = fetch_account_totals(client, state["username"])
        if reported:
            state["reported_total_submissions"] = reported
            state["reported_problems_attempted"] = problems
            log(f"  LeetCode reports {reported} submissions across {problems} problems")

    if offset:
        log(f"  Resuming the listing from offset {offset}")
    elif enumerated:
        queued = len(state["pending"])
        log(f"  Full history already listed{f' ({queued} still queued)' if queued else ''}; "
            f"checking only for submissions newer than {iso_utc(cutoff)} UTC")
    elif cutoff:
        log(f"  Incremental: listing submissions newer than {iso_utc(cutoff)} UTC")
    else:
        log("  Listing the full submission history")

    found, seen, complete = 0, offset, False
    try:
        while True:
            params = {"offset": offset, "limit": PAGE}
            if last_key:
                params["lastkey"] = last_key
            resp = client.request("GET", SUBMISSIONS_URL, params=params)
            try:
                payload = resp.json()
            except ValueError as exc:
                raise FetchFailed("submission list was not JSON") from exc

            dump = payload.get("submissions_dump") or []
            if not dump:
                complete = True
                break

            reached_cutoff = False
            for raw in dump:
                seen += 1
                ts = int(raw.get("timestamp") or 0)
                newest = max(newest, ts)
                if cutoff and ts <= cutoff:
                    reached_cutoff = True
                    break
                sid = int(raw["id"])
                if sid in known:
                    continue
                known.add(sid)
                state["pending"].append(list_record(raw))
                found += 1

            offset += PAGE
            last_key = payload.get("last_key") or ""
            state["list_cursor"] = {"offset": offset, "last_key": last_key}
            state["newest_listed_timestamp"] = newest
            if reported:
                log(f"  listed {min(seen, reported)}/{reported} submissions "
                    f"({min(100, seen * 100 // reported)}%), {found} new")
            else:
                log(f"  listed {seen} submissions, {found} new")

            if reached_cutoff or not payload.get("has_next"):
                complete = True
                break
            if (offset // PAGE) % 10 == 0:     # keep the walk crash-proof
                save_state(outdir, state)
    except FetchFailed as exc:
        log(f"\n  Listing stopped early: {exc}")
        log(f"  Keeping the {found} submissions found so far. Their code will be")
        log(f"  downloaded now, and the next run resumes the listing from offset {offset}.")

    state["pending"].sort(key=lambda r: r["timestamp"], reverse=True)
    state["newest_listed_timestamp"] = newest
    state["list_complete"] = complete
    if complete:
        state["list_cursor"] = {}
    save_state(outdir, state)


# --------------------------------------------------------------------------
# Phase 4: download code (the long phase)
# --------------------------------------------------------------------------

def write_submission(outdir: Path, item: dict, detail: dict, meta: dict) -> dict:
    """Save one code file, return the CSV row."""
    question = detail.get("question") or {}
    slug = safe_component(question.get("titleSlug") or item["title"] or "unknown")
    lang = (detail.get("lang") or {}).get("name") or item["lang"]

    folder = outdir / "solutions" / slug
    folder.mkdir(parents=True, exist_ok=True)
    filename = code_filename(item["timestamp"], item["status_display"], lang, item["id"])
    (folder / filename).write_text(detail.get("code") or "", encoding="utf-8")

    tags = ";".join(t.get("slug", "") for t in (meta.get("topicTags") or []))
    return {
        "submission_id": item["id"],
        "timestamp": item["timestamp"],
        "datetime_utc": iso_utc(item["timestamp"]),
        "title": question.get("title") or item["title"],
        "titleSlug": slug,
        "difficulty": meta.get("difficulty") or "Unknown",
        "topic_tags": tags,
        "status_display": item["status_display"],
        "lang": lang,
        "runtime": item["runtime"],
        "memory": item["memory"],
        "runtime_percentile": _round(detail.get("runtimePercentile")),
        "memory_percentile": _round(detail.get("memoryPercentile")),
        "code_file_path": f"solutions/{slug}/{filename}",
    }


def _round(value):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return ""


def fetch_codes(client: Client, state: dict, catalog: dict, outdir: Path,
                items: list[dict], failed: dict, is_retry: bool) -> int:
    """Download code for every queued submission. Resumable at any point."""
    total = len(items)
    if not total:
        log("  Nothing to download.")
        return 0

    per_request = client.delay * 1.05 + 0.4
    log(f"\n  Queue: {total} submissions | est. {fmt_duration(total * per_request)} "
        f"at ~{per_request:.1f}s each")
    log("  Safe to stop with Ctrl+C at any time -- the next run resumes here.\n")

    csv_path = outdir / "submissions_all.csv"
    fresh = not csv_path.exists() or csv_path.stat().st_size == 0
    run_started = time.monotonic()
    consecutive_failures = 0
    saved = 0

    catalog_size = len(catalog)

    def checkpoint(index: int) -> None:
        nonlocal catalog_size
        if not is_retry:
            state["pending"] = items[index:]
        save_state(outdir, state)
        save_json(outdir / "failed_submissions.json", list(failed.values()))
        if len(catalog) != catalog_size:   # only when the fallback added entries
            save_json(outdir / "problem_catalog.json", catalog)
            catalog_size = len(catalog)

    handle = csv_path.open("a", newline="", encoding="utf-8")
    writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    if fresh:
        writer.writeheader()
    settled = 0          # items that have left the queue, one way or the other
    try:
        for index, item in enumerate(items, start=1):
            remaining = total - index
            # Pace over the whole run, not a rolling window: backoffs are part of
            # the real cost, but one 60s stall should nudge the estimate, not own
            # it for the next 20 lines.
            done = index - 1
            pace = (time.monotonic() - run_started) / done if done else per_request
            eta = fmt_duration(remaining * pace)
            log(f"  [{index}/{total}] {item['title']} ({item['status_display']}) | {eta} left")

            try:
                client.periodic_session_check()
                data = client.graphql(Q_SUBMISSION_DETAILS, {"submissionId": item["id"]})
                detail = data.get("submissionDetails")
                if not detail:
                    # null is ambiguous: dead session, or an unreachable
                    # submission. Ask who we are before assuming.
                    if not client.signed_in_as():
                        raise SessionExpired("submissionDetails returned null and we are signed out")
                    raise FetchFailed("submissionDetails returned null")

                slug = ((detail.get("question") or {}).get("titleSlug")
                        or safe_component(item["title"]))
                meta = lookup_problem(client, catalog, slug)
                writer.writerow(write_submission(outdir, item, detail, meta))
                handle.flush()

                state["processed_ids"].append(item["id"])
                failed.pop(item["id"], None)
                consecutive_failures = 0
                saved += 1
            except SessionExpired:
                raise
            except Exception as exc:  # noqa: BLE001 - one bad item must not end the run
                consecutive_failures += 1
                log(f"    FAILED: {exc}")
                record = dict(item)
                record["error"] = str(exc)
                record["failed_attempts"] = int(failed.get(item["id"], {}).get("failed_attempts", 0)) + 1
                failed[item["id"]] = record
                if consecutive_failures >= CONSECUTIVE_FAILURE_LIMIT:
                    checkpoint(index)
                    log(f"\n  {consecutive_failures} failures in a row -- stopping so we "
                        f"do not hammer LeetCode.")
                    log("  Wait an hour or so, then re-run. Progress is saved.")
                    raise SystemExit(2)

            settled = index
            if index % CHECKPOINT_EVERY == 0:
                checkpoint(index)
        checkpoint(total)
    except KeyboardInterrupt:
        checkpoint(settled)   # do not re-download what already landed
        raise
    finally:
        handle.close()
    return saved


def save_state(outdir: Path, state: dict) -> None:
    state["processed_ids"] = sorted(set(state["processed_ids"]))
    state["last_completed_timestamp"] = next_cutoff(state)
    save_json(outdir / "state.json", state)


# --------------------------------------------------------------------------
# Phase 5: rollup + deterministic statistics + the LLM briefing
# --------------------------------------------------------------------------

def summarize_attempts(problem_rows: list[dict], catalog: dict | None = None) -> dict:
    """Roll up every attempt at one problem. Used for attempts_summary.json
    and for the flat `problems` index in analysis_summary.json."""
    catalog = catalog or {}
    rows = sorted(problem_rows, key=lambda r: r["timestamp"])
    first, last = rows[0], rows[-1]
    slug = first.get("titleSlug", "")
    statuses = Counter(r.get("status_display") or "Unknown" for r in rows)

    accepted_at = next((i for i, r in enumerate(rows)
                        if r.get("status_display") == "Accepted"), None)
    solved = accepted_at is not None
    attempts_to_accept = accepted_at + 1 if solved else None
    first_accepted = rows[accepted_at]["timestamp"] if solved else None
    tags = [t for t in (first.get("topic_tags") or "").split(";") if t]

    return {
        "titleSlug": slug,
        "title": first.get("title") or slug,
        "difficulty": first.get("difficulty") or "Unknown",
        "frontend_id": (catalog.get(slug) or {}).get("frontendQuestionId"),
        "topic_tags": tags,
        "total_attempts": len(rows),
        "status_breakdown": dict(statuses.most_common()),
        "languages_used": sorted({r.get("lang") for r in rows if r.get("lang")}),
        "solved": solved,
        "attempts_to_accept": attempts_to_accept,
        "clean_solve": attempts_to_accept == 1 if solved else False,
        "first_attempt_timestamp": first["timestamp"],
        "first_attempt_utc": iso_utc(first["timestamp"]),
        "last_attempt_timestamp": last["timestamp"],
        "last_attempt_utc": iso_utc(last["timestamp"]),
        "first_accepted_timestamp": first_accepted,
        "first_accepted_utc": iso_utc(first_accepted) if solved else None,
        "days_to_solve": (round((first_accepted - first["timestamp"]) / 86400.0, 2)
                          if solved else None),
    }


def _difficulty_slice(problems: list[dict], difficulty: str) -> dict:
    subset = [p for p in problems if p["difficulty"] == difficulty]
    if not subset:
        return {}
    solved = [p for p in subset if p["solved"]]
    return {
        "problems_attempted": len(subset),
        "problems_solved": len(solved),
        "solve_rate": round(len(solved) / len(subset), 3),
        "clean_solves": sum(1 for p in solved if p["clean_solve"]),
        "total_submissions": sum(p["total_attempts"] for p in subset),
    }


def build_analysis(rows: list[dict], catalog: dict | None = None, failed_count: int = 0,
                   backfill_complete: bool = True, generated_at: int | None = None,
                   reported_total: int = 0) -> dict:
    """Every number an LLM would otherwise have to compute by eye over
    thousands of CSV rows -- and get quietly wrong."""
    catalog = catalog or {}
    now = int(generated_at if generated_at is not None else time.time())

    by_slug: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_slug[row.get("titleSlug", "")].append(row)
    problems = {slug: summarize_attempts(rs, catalog) for slug, rs in by_slug.items() if rs}
    plist = list(problems.values())

    topics: dict[str, list[dict]] = defaultdict(list)
    for problem in plist:
        for tag in problem["topic_tags"]:
            topics[tag].append(problem)

    tag_names = {t.get("slug"): t.get("name")
                 for entry in catalog.values() for t in (entry.get("topicTags") or [])}

    by_topic = []
    for tag, tagged in topics.items():
        solved = [p for p in tagged if p["solved"]]
        clean = [p for p in solved if p["clean_solve"]]
        attempts = [p["attempts_to_accept"] for p in solved]
        breakdown: Counter = Counter()
        for p in tagged:
            breakdown.update(p["status_breakdown"])
        last_practiced = max(p["last_attempt_timestamp"] for p in tagged)
        by_topic.append({
            "topic": tag,
            "name": tag_names.get(tag, tag),
            "problems_attempted": len(tagged),
            "problems_solved": len(solved),
            "solve_rate": round(len(solved) / len(tagged), 3),
            "clean_solves": len(clean),
            "first_attempt_accept_rate": round(len(clean) / len(tagged), 3),
            "median_attempts_to_accept": (round(statistics.median(attempts), 2)
                                          if attempts else None),
            "total_submissions": sum(breakdown.values()),
            "status_breakdown": dict(breakdown.most_common()),
            "unsolved_problems": sorted(
                ({"titleSlug": p["titleSlug"], "title": p["title"],
                  "difficulty": p["difficulty"], "attempts": p["total_attempts"],
                  "last_attempt_utc": p["last_attempt_utc"]}
                 for p in tagged if not p["solved"]),
                key=lambda p: -p["attempts"]),
            "first_practiced": iso_utc(min(p["first_attempt_timestamp"] for p in tagged)),
            "last_practiced": iso_utc(last_practiced),
            "days_since_last_practice": int((now - last_practiced) // 86400),
            "by_difficulty": {d: s for d in ("Easy", "Medium", "Hard")
                              if (s := _difficulty_slice(tagged, d))},
        })
    by_topic.sort(key=lambda t: -t["total_submissions"])

    months: dict[str, dict] = {}
    for row in rows:
        bucket = months.setdefault(month_key(row["timestamp"]), {
            "submissions": 0, "accepted": 0, "_problems": set(), "_topics": set()})
        bucket["submissions"] += 1
        if row.get("status_display") == "Accepted":
            bucket["accepted"] += 1
        bucket["_problems"].add(row.get("titleSlug"))
        bucket["_topics"].update(t for t in (row.get("topic_tags") or "").split(";") if t)
    newly_solved = Counter(month_key(p["first_accepted_timestamp"])
                           for p in plist if p["solved"])
    by_month = []
    for key in sorted(months):
        bucket = months[key]
        by_month.append({
            "month": key,
            "submissions": bucket["submissions"],
            "accepted": bucket["accepted"],
            "acceptance_rate": round(bucket["accepted"] / bucket["submissions"], 3),
            "distinct_problems_attempted": len(bucket["_problems"]),
            "problems_first_solved": newly_solved.get(key, 0),
            "topics_touched": sorted(bucket["_topics"]),
        })

    solved_all = [p for p in plist if p["solved"]]
    timestamps = [r["timestamp"] for r in rows] or [now]
    statuses: Counter = Counter(r.get("status_display") or "Unknown" for r in rows)
    overview = {
        "generated_at_utc": iso_utc(now),
        "first_submission_utc": iso_utc(min(timestamps)),
        "last_submission_utc": iso_utc(max(timestamps)),
        "days_of_history": int((max(timestamps) - min(timestamps)) // 86400),
        "total_submissions": len(rows),
        "problems_attempted": len(plist),
        "problems_solved": len(solved_all),
        "problem_solve_rate": round(len(solved_all) / len(plist), 3) if plist else 0.0,
        "submission_acceptance_rate": (round(statuses.get("Accepted", 0) / len(rows), 3)
                                       if rows else 0.0),
        "clean_solves": sum(1 for p in solved_all if p["clean_solve"]),
        "status_counts": dict(statuses.most_common()),
        "by_difficulty": {d: s for d in ("Easy", "Medium", "Hard")
                          if (s := _difficulty_slice(plist, d))},
        "languages": dict(Counter(r.get("lang") for r in rows if r.get("lang")).most_common()),
        "backfill_complete": bool(backfill_complete),
        "failed_fetch_count": int(failed_count),
        # What LeetCode itself says the account has, so coverage is checkable
        # rather than assumed.
        "reported_total_submissions": int(reported_total),
        "coverage_of_reported": (round(len(rows) / reported_total, 3)
                                 if reported_total else None),
    }

    return {
        "overview": overview,
        "by_topic": by_topic,
        "by_month": by_month,
        "problems": sorted(plist, key=lambda p: -p["last_attempt_timestamp"]),
    }


PROMPT_SCHEMA = """
## 2. The files, and what is in them

### `analysis_summary.json` -- start here, all the arithmetic is already done

| Section | Contents |
|---|---|
| `overview` | totals, date range, status counts, per-difficulty counts, completeness flags |
| `by_topic` | one entry per topic tag, sorted by how much I have practised it |
| `by_month` | per-calendar-month activity: the trajectory |
| `problems` | flat list, one entry per problem, most recently attempted first |

Key fields inside `by_topic`:

| Field | Meaning |
|---|---|
| `problems_attempted` / `problems_solved` / `solve_rate` | coverage and outcome |
| `clean_solves` / `first_attempt_accept_rate` | solved with **zero** failed attempts -- the sharpest mastery signal |
| `median_attempts_to_accept` | how much grinding a solve costs on this topic (solved problems only) |
| `status_breakdown` | counts of Accepted / Wrong Answer / Time Limit Exceeded / Runtime Error / ... |
| `unsolved_problems` | attempted but never accepted -- the sharpest weakness signal |
| `days_since_last_practice` | staleness, for spaced repetition |
| `by_difficulty` | the same coverage numbers split Easy / Medium / Hard |

### `submissions_all.csv` -- one row per SUBMISSION (not per problem)

`submission_id`, `timestamp` (UTC epoch seconds), `datetime_utc`, `title`,
`titleSlug`, `difficulty`, `topic_tags` (semicolon-joined slugs),
`status_display`, `lang`, `runtime`, `memory`, `runtime_percentile`,
`memory_percentile`, `code_file_path` (relative to this folder).

### `solutions/<titleSlug>/` -- the actual code

One file per attempt, named `<timestamp>_<Status>_<lang>_<id>.<ext>`, so the
failed attempts and the eventual accepted one sit side by side in the same
folder. Each folder also has an `attempts_summary.json` rollup.

### `problem_catalog.json`

`titleSlug` -> difficulty, topic tags, problem number. The source of the
topic labels.

### `failed_submissions.json`

Submissions whose **download** failed. `state.json` is internal bookkeeping --
ignore it.

### Traps that will corrupt the analysis if you miss them

- **One row per attempt, not per problem.** A problem I struggled with appears
  many times. Never count CSV rows as "problems".
- **`failed_submissions.json` means data we failed to fetch, not problems I
  failed.** These are gaps in the record. Never read them as weaknesses.
- **Topic totals overlap.** Most problems carry several tags, so per-topic
  counts deliberately do not sum to the overall total.
- Timestamps are UTC epoch seconds. `status_display` values are LeetCode's own
  raw strings.

## 3. How to work through this efficiently

1. **Read `analysis_summary.json` first.** Every rate, median and count in it
   was computed deterministically. Use those numbers rather than recomputing
   them from the CSV -- that is what they are for.
2. **Do not bulk-read `solutions/`.** It holds thousands of files.
3. **Then drill, selectively.** Take the 3-5 weakest topics. For each, open
   2-3 *failed* attempts plus the accepted solution for the same problem and
   compare the approaches. This is the step that turns statistics into a
   diagnosis -- "the DP failures are consistently wrong state definitions, not
   implementation bugs" is worth far more than "DP solve rate is 46%".
4. Fall back to the CSV only for ordering or detail the summary does not cover.

## 4. The analysis I want

### Weak areas, ranked
For each, give the numbers that justify the ranking **and** name the failure
mode. The status breakdown tells you which:

- **Wrong Answer heavy** -> logic and edge cases in an approach that is roughly right
- **Time Limit Exceeded heavy** -> wrong complexity class; reaching for brute force
- **Runtime Error heavy** -> indexing, bounds, null and empty-input handling
- **Low `first_attempt_accept_rate` but eventually solved** -> I can grind it out but do not *see* the approach
- **Entries in `unsolved_problems`** -> I never got there at all

### Strong areas
Separate genuine mastery (high `first_attempt_accept_rate`) from grind (solved,
but a high `median_attempts_to_accept`). They are different skills and need
different follow-up -- say which is which.

### Trend over time
From `by_month`: improving, plateaued, or dormant? Call out gaps in activity
and any month where the acceptance rate moved sharply.

### Stale strengths
Topics with good numbers but a large `days_since_last_practice`. These are the
ones most likely to have quietly decayed.

### Recurring failure modes
Patterns that cut across topics, drawn from the code you actually read.

## 5. The practice plan

Prioritised and specific, in the order I should do it:

- Named problems from `unsolved_problems` worth another attempt, hardest-earned first
- Named problems I *did* solve that are worth re-attempting cold, to test retention
- Topics to drill, with what specifically to focus on within each
- Roughly how to split my time across them

**Cite the numbers behind every recommendation** so I can check the reasoning
rather than take it on faith.

## What this data cannot tell you

Say so when it matters, and qualify conclusions accordingly:

- Practice done anywhere other than LeetCode
- Contest performance
- Problems I read and thought about but never submitted
- Time actually spent per problem -- only submission timestamps exist
- **Whether I looked at the editorial or a solution before submitting.** A
  clean accept does not always mean I found it myself.
"""


def render_prompt(analysis: dict, files_on_disk: int) -> str:
    o = analysis["overview"]
    header = f"""# LeetCode practice history -- analysis brief

You are reading a complete export of my LeetCode submission history. Analyse
it and tell me where I am weak, where I am strong, and what to practise next.
Work through it as described below; everything you need is in this folder.

## 1. What this dataset is

Exported by `leetcode_export.py` on {o['generated_at_utc']} UTC. It contains
**every submission I made, at every status** -- not only the accepted ones.
The failed attempts are deliberately included and are the most useful signal
in here.

- **Window:** {o['first_submission_utc']} to {o['last_submission_utc']} UTC ({o['days_of_history']} days)
- **{o['total_submissions']} submissions** across **{o['problems_attempted']} distinct problems**
- **{o['problems_solved']} problems solved** ({o['problem_solve_rate']:.0%} of those attempted); {o['clean_solves']} on the first attempt
- Submission-level acceptance rate: {o['submission_acceptance_rate']:.0%}
- Status mix: {', '.join(f"{k} {v}" for k, v in o['status_counts'].items())}
- Languages: {', '.join(o['languages']) or 'n/a'}
- {files_on_disk} code files on disk under `solutions/`
"""
    reported = o.get("reported_total_submissions") or 0
    if reported:
        header += (f"- Coverage: **{o['total_submissions']} of the {reported} submissions "
                   f"LeetCode reports for this account** "
                   f"({o['coverage_of_reported']:.0%})\n")
    caveats = []
    if reported and o["total_submissions"] < reported * 0.99:
        missing = reported - o["total_submissions"]
        caveats.append(
            f"- **{missing} submissions are missing** relative to the {reported} LeetCode\n"
            f"  reports for this account. The export is still in progress or was cut\n"
            f"  short. Weight conclusions accordingly, especially for older history.")
    if not o["backfill_complete"]:
        caveats.append(
            "- **The backfill is INCOMPLETE.** Some older submissions have not been\n"
            "  downloaded yet, so treat this as a recent-history sample, not my full\n"
            "  record, and say so in your conclusions.")
    if o["failed_fetch_count"]:
        caveats.append(
            f"- {o['failed_fetch_count']} submissions failed to download and are missing "
            f"from the data\n  (listed in `failed_submissions.json`). They are gaps in the "
            f"record, **not** problems I failed.")
    if caveats:
        header += "\n### Coverage caveats\n\n" + "\n".join(caveats) + "\n"
    return header + PROMPT_SCHEMA


def rebuild(outdir: Path, state: dict | None = None, catalog: dict | None = None) -> None:
    """Regenerate every derived artefact from the CSV. Pure local computation."""
    rows = read_rows(outdir / "submissions_all.csv")
    if not rows:
        log("  No submissions on disk yet -- nothing to summarise.")
        return
    if state is None:
        state = load_json(outdir / "state.json", new_state())
    if catalog is None:
        catalog = load_json(outdir / "problem_catalog.json", {})
    failed = load_json(outdir / "failed_submissions.json", [])

    csv_path = outdir / "submissions_all.csv"
    with csv_path.open(newline="", encoding="utf-8") as fh:
        raw_count = sum(1 for _ in csv.reader(fh)) - 1
    if raw_count > len(rows):
        log(f"  Removing {raw_count - len(rows)} duplicate rows from the CSV")
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    by_slug: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_slug[row.get("titleSlug", "")].append(row)
    for slug, problem_rows in by_slug.items():
        folder = outdir / "solutions" / safe_component(slug)
        folder.mkdir(parents=True, exist_ok=True)
        save_json(folder / "attempts_summary.json",
                  summarize_attempts(problem_rows, catalog))

    complete = bool(state.get("list_complete")) and not state.get("pending")
    analysis = build_analysis(rows, catalog, len(failed), complete,
                              reported_total=int(state.get("reported_total_submissions") or 0))
    save_json(outdir / "analysis_summary.json", analysis)

    solutions = outdir / "solutions"
    code_files = sum(1 for f in solutions.rglob("*")
                     if f.is_file() and f.name != "attempts_summary.json"
                     ) if solutions.is_dir() else 0
    (outdir / "prompt.md").write_text(render_prompt(analysis, code_files), encoding="utf-8")

    log(f"  {len(rows)} submissions | {len(by_slug)} problems | "
        f"{len(analysis['by_topic'])} topics")
    log(f"  Wrote analysis_summary.json and prompt.md")


# --------------------------------------------------------------------------
# Offline self-check
# --------------------------------------------------------------------------

def self_test() -> None:
    assert ext_for("python3") == "py" and ext_for("Python3") == "py"
    assert ext_for("mysql") == "sql" and ext_for("golang") == "go"
    assert ext_for("some-new-language") == "txt", "unknown languages must not crash"

    # Path components come off the network: they must not escape the folder.
    assert "/" not in safe_component("../../etc/passwd")
    assert ".." not in safe_component("../../etc/passwd")
    assert safe_component("") == "unknown"

    # Same problem, same second, same language -> still two distinct files.
    a = code_filename(1700000000, "Wrong Answer", "python3", 111)
    b = code_filename(1700000000, "Wrong Answer", "python3", 222)
    assert a != b and a.endswith(".py") and " " not in a, (a, b)

    # Cookie values get pasted by hand; tolerate the usual debris.
    assert clean_cookie_value("abc123") == "abc123"
    assert clean_cookie_value('  "abc123"  ') == "abc123"
    assert clean_cookie_value("LEETCODE_SESSION=abc123") == "abc123"
    assert clean_cookie_value("leetcode_session=abc123;") == "abc123"
    assert clean_cookie_value("") == "" and clean_cookie_value(None) == ""
    # A JWT-shaped value must survive intact -- it contains '=' padding.
    jwt = "eyJhbGciOi.eyJfYXV0aA==.sig-value"
    assert clean_cookie_value(f"LEETCODE_SESSION={jwt}") == jwt, clean_cookie_value(jwt)
    assert clean_cookie_value(jwt) == jwt

    env = dict(os.environ)
    try:
        os.environ.pop("LEETCODE_SESSION", None)
        os.environ.pop("LEETCODE_CSRFTOKEN", None)
        assert cookies_from_env() == {}
        os.environ["LEETCODE_SESSION"] = ' "tok" '
        assert cookies_from_env() == {"LEETCODE_SESSION": "tok"}
        os.environ["LEETCODE_CSRFTOKEN"] = "csrftoken=xyz"
        assert cookies_from_env() == {"LEETCODE_SESSION": "tok", "csrftoken": "xyz"}
    finally:
        os.environ.clear()
        os.environ.update(env)

    assert backoff_delay(0, 2.0) == 2.0
    assert backoff_delay(3, 2.0) == 16.0
    assert backoff_delay(20, 2.0) == MAX_BACKOFF, "backoff must be capped"
    assert retry_wait("30", 0, 1.75) == 30.0, "Retry-After must win over our backoff"
    assert retry_wait(None, 2, 1.0) >= 4.0

    # The cutoff must not advance while work is still queued.
    # The listing frontier is NOT the download frontier: a queue still full of
    # work must not force a re-walk of the whole history.
    listed = {"list_complete": True, "newest_listed_timestamp": 900,
              "last_completed_timestamp": 0, "pending": [{"id": 1}] * 3000}
    assert listing_cutoff(listed) == 900, "re-listed the whole history for nothing"
    assert listing_cutoff(listed, full=True) == 0, "--full must walk everything"
    mid_walk = dict(listed, list_complete=False, last_completed_timestamp=500)
    assert listing_cutoff(mid_walk) == 500, "an interrupted walk must keep going down"
    assert listing_cutoff({}) == 0

    # Regression: a finished listing must survive a later interrupted run.
    # list_submissions used to blank list_complete on entry, so an interrupt
    # threw the completion away and the next run re-walked the whole history.
    interrupted = {"list_complete": True, "newest_listed_timestamp": 900,
                   "last_completed_timestamp": 0, "pending": [{"id": 1}] * 10,
                   "list_cursor": {"offset": 400, "last_key": ""}}
    assert listing_cutoff(interrupted) == 900, "a finished listing was thrown away"

    # The count check rescues a state whose completion flag was already lost.
    lost = {"list_complete": False, "newest_listed_timestamp": 900,
            "last_completed_timestamp": 0, "list_cursor": {"offset": 400},
            "pending": [{"id": i} for i in range(80)],
            "processed_ids": list(range(1000, 1020)), "reported_total_submissions": 100}
    assert history_enumerated(lost) is True, "80 + 20 >= 100"
    assert listing_cutoff(lost) == 900, "re-walked a history we already hold"
    assert history_enumerated(dict(lost, reported_total_submissions=0)) is False
    assert history_enumerated(dict(lost, pending=[])) is False, "20 < 100"

    # A mid-walk cursor must block the download cutoff from advancing.
    assert next_cutoff({"list_complete": True, "pending": [],
                        "list_cursor": {"offset": 40},
                        "last_completed_timestamp": 100,
                        "newest_listed_timestamp": 900}) == 100

    busy = {"pending": [{"id": 1}], "list_complete": True,
            "last_completed_timestamp": 100, "newest_listed_timestamp": 900}
    assert next_cutoff(busy) == 100, "cutoff advanced with a non-empty queue"
    drained = dict(busy, pending=[])
    assert next_cutoff(drained) == 900
    assert next_cutoff(dict(drained, list_complete=False)) == 100

    def row(sid, ts, slug, status, diff="Medium", tags="dp", title=None):
        return {"submission_id": sid, "timestamp": ts, "titleSlug": slug,
                "title": title or slug, "difficulty": diff, "topic_tags": tags,
                "status_display": status, "lang": "python3"}

    rows = [
        row(1, 1700000000, "a", "Wrong Answer"),
        row(2, 1700000100, "a", "Accepted"),
        row(3, 1700000200, "b", "Accepted", diff="Easy"),
        row(4, 1700000300, "c", "Wrong Answer", diff="Hard"),
        row(5, 1700000400, "c", "Time Limit Exceeded", diff="Hard"),
        row(6, 1704063600, "d", "Accepted", tags="math"),   # 2023-12-31 23:00Z
        row(7, 1704067200, "d", "Wrong Answer", tags="math"),  # 2024-01-01 00:00Z
    ]

    summary_a = summarize_attempts([r for r in rows if r["titleSlug"] == "a"])
    assert summary_a["solved"] and summary_a["attempts_to_accept"] == 2
    assert summary_a["clean_solve"] is False
    assert summary_a["status_breakdown"] == {"Wrong Answer": 1, "Accepted": 1}
    summary_c = summarize_attempts([r for r in rows if r["titleSlug"] == "c"])
    assert not summary_c["solved"] and summary_c["attempts_to_accept"] is None

    analysis = build_analysis(rows, generated_at=1704067200)
    dp = next(t for t in analysis["by_topic"] if t["topic"] == "dp")
    assert dp["problems_attempted"] == 3 and dp["problems_solved"] == 2
    assert dp["clean_solves"] == 1, "only a zero-failure solve is a clean solve"
    assert dp["first_attempt_accept_rate"] == 0.333, dp["first_attempt_accept_rate"]
    assert dp["median_attempts_to_accept"] == 1.5, "unsolved problems must not skew the median"
    assert [p["titleSlug"] for p in dp["unsolved_problems"]] == ["c"]
    assert dp["status_breakdown"]["Wrong Answer"] == 2

    months = {m["month"] for m in analysis["by_month"]}
    assert {"2023-12", "2024-01"} <= months, f"month bucketing crossed years wrong: {months}"
    assert analysis["overview"]["problems_attempted"] == 4
    assert analysis["overview"]["problems_solved"] == 3

    # The brief must carry the real numbers, not a placeholder.
    text = render_prompt(analysis, files_on_disk=7)
    assert "7 submissions" in text and "4 distinct problems" in text
    assert "analysis_summary.json" in text and "cannot tell you" in text

    log("All self-tests passed.")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export your complete LeetCode submission history for LLM analysis.")
    parser.add_argument("--outdir", type=Path,
                        default=Path(__file__).resolve().parent / "leetcode_export",
                        help="export folder (default: ./leetcode_export)")
    parser.add_argument("--full", action="store_true",
                        help="re-list the entire history, ignoring the incremental "
                             "cutoff. Already-downloaded submissions are still skipped; "
                             "delete the export folder to truly start over.")
    parser.add_argument("--delay", type=float, default=1.75,
                        help="seconds between requests (default: 1.75)")
    parser.add_argument("--refresh-catalog", action="store_true",
                        help="refetch the problem catalog even if it is fresh")
    parser.add_argument("--retry-failed", action="store_true",
                        help="re-attempt everything in failed_submissions.json")
    parser.add_argument("--rebuild-analysis", action="store_true",
                        help="regenerate analysis_summary.json and prompt.md offline")
    parser.add_argument("--self-test", action="store_true",
                        help="run offline assertions and exit")
    args = parser.parse_args(argv)

    if args.self_test:
        self_test()
        return 0

    outdir = args.outdir.expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    if args.rebuild_analysis:
        log(f"Rebuilding analysis in {outdir}")
        rebuild(outdir)
        return 0

    if args.delay < 0.5:
        log("Refusing a delay below 0.5s -- that is how accounts get rate-limited.")
        return 2

    stored = load_json(outdir / "state.json", {})
    state = new_state() | (stored if isinstance(stored, dict) else {})
    failed = {int(r["id"]): r
              for r in load_json(outdir / "failed_submissions.json", []) if r.get("id")}

    log(f"Export folder: {outdir}")
    log("\n[1/5] Signing in")
    client = authenticate(outdir / ".browser_profile", args.delay)
    state["username"] = getattr(client, "username", None)

    try:
        log("\n[2/5] Problem catalog")
        catalog = ensure_catalog(client, outdir, state, args.refresh_catalog)
        save_state(outdir, state)

        if args.retry_failed:
            items = sorted(failed.values(), key=lambda r: -int(r.get("timestamp") or 0))
            log(f"\n[3/5] Retrying {len(items)} previously failed submissions")
        else:
            log("\n[3/5] Listing submissions")
            list_submissions(client, state, args.full, outdir)
            items = list(state["pending"])

        log("\n[4/5] Downloading code")
        saved = fetch_codes(client, state, catalog, outdir, items, failed, args.retry_failed)
        log(f"\n  Saved {saved} new submissions ({client.requests_made} requests this run).")

        log("\n[5/5] Building analysis")
        rebuild(outdir, state, catalog)
    except KeyboardInterrupt:
        save_state(outdir, state)
        save_json(outdir / "failed_submissions.json", list(failed.values()))
        log("\n\nStopped. Progress is saved -- re-run to pick up exactly here.")
        return 130
    except SessionExpired as exc:
        save_state(outdir, state)
        save_json(outdir / "failed_submissions.json", list(failed.values()))
        log(f"\n\nLeetCode session expired ({exc}). Progress is saved.")
        log("Re-run the tool -- it will open a browser so you can log in again.")
        return 3

    if failed:
        log(f"\n  {len(failed)} submissions failed to download. "
            f"Retry later with --retry-failed")
    log(f"\nDone. To analyse it:\n\n  cd {outdir} && claude \"read prompt.md and do the analysis\"\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
