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
import hashlib
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

PASTE_GAP_SECONDS = 120       # nobody reads, thinks and types a Medium in two minutes
REWRITE_SIMILARITY = 0.5      # below this, consecutive attempts are a rewrite, not a fix
BENCHMARK_SIMILARITY = 0.9    # above this, it is the same code submitted again


def _read_solution(outdir: Path | None, rel_path: str) -> tuple[set[str] | None, str | None]:
    """One solution file, as (line set, content hash).

    The line set is a cheap stand-in for a real diff -- order and whitespace
    churn do not matter for *similarity*, content does. The hash is over the
    raw text, because it answers a different question: `same_code_as` tells the
    reader a file is safe to skip unread, so it must mean genuinely identical.
    Hashing the line set instead marked reordered code -- including Wrong
    Answer/Accepted pairs -- as duplicates and hid the very diff worth reading.
    """
    if not outdir or not rel_path:
        return None, None
    try:
        text = (outdir / rel_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, None
    lines = {ln.strip() for ln in text.splitlines() if ln.strip()}
    return lines or None, hashlib.md5(text.encode()).hexdigest()[:12]


def _jaccard(a: set[str] | None, b: set[str] | None) -> float | None:
    if not a or not b:
        return None
    return round(len(a & b) / len(a | b), 3)


def annotate_rows(rows: list[dict], outdir: Path | None = None) -> list[dict]:
    """Tag each row with the timing and code-similarity facts that separate my
    own problem solving from pasted code and from runtime benchmarking.

    The timing figure is a genuine upper bound and nothing more: if the previous
    submission landed 40 seconds ago, this problem got at most 40 seconds of my
    attention. A long gap proves nothing in either direction.
    """
    ordered = sorted(rows, key=lambda r: r["timestamp"])
    prev_ts: int | None = None
    prev_on_problem: dict[str, tuple[int, set[str] | None]] = {}

    for row in ordered:
        ts, slug = row["timestamp"], row.get("titleSlug", "")
        lines, digest = _read_solution(outdir, row.get("code_file_path", ""))
        last = prev_on_problem.get(slug)

        row["gap_before"] = None if prev_ts is None else ts - prev_ts
        row["gap_on_problem"] = None if last is None else ts - last[0]
        row["similarity_to_previous"] = _jaccard(lines, last[1]) if last else None
        row["code_hash"] = digest

        prev_ts, prev_on_problem[slug] = ts, (ts, lines)
    return ordered


def classify_attempt(row: dict, is_first_attempt: bool) -> str:
    """`own`, `pasted` or `resubmission`. A heuristic, deliberately conservative:
    anything it cannot argue for is left as `own`."""
    sim, gap = row.get("similarity_to_previous"), row.get("gap_on_problem")
    if sim is not None and gap is not None and gap <= PASTE_GAP_SECONDS:
        if sim >= BENCHMARK_SIMILARITY:
            return "resubmission"      # same code again -- a runtime measurement
        if sim < REWRITE_SIMILARITY:
            return "pasted"            # wholesale replacement, not a fix
    if (is_first_attempt and row.get("status_display") == "Accepted"
            and row.get("difficulty") != "Easy"):
        # Straight to Accepted on a Medium/Hard, minutes after the previous
        # submission: there was no window in which to solve it.
        gap_before = row.get("gap_before")
        if gap_before is not None and gap_before <= PASTE_GAP_SECONDS:
            return "pasted"
    return "own"


def summarize_attempts(problem_rows: list[dict], catalog: dict | None = None) -> dict:
    """Roll up every attempt at one problem. Used for attempts_summary.json
    and for the flat `problems` index in analysis_summary.json."""
    catalog = catalog or {}
    rows = sorted(problem_rows, key=lambda r: r["timestamp"])
    first, last = rows[0], rows[-1]
    slug = first.get("titleSlug", "")

    accepted_at = next((i for i, r in enumerate(rows)
                        if r.get("status_display") == "Accepted"), None)
    solved = accepted_at is not None
    attempts_to_accept = accepted_at + 1 if solved else None
    first_accepted = rows[accepted_at]["timestamp"] if solved else None
    tags = [t for t in (first.get("topic_tags") or "").split(";") if t]

    # Everything after the first Accept is revisiting, optimising or measuring
    # runtime -- never first-solve effort. Keeping it out of the diagnostic
    # counts is structural, not a guess.
    solve_window = rows[:accepted_at + 1] if solved else rows
    post_solve = rows[accepted_at + 1:] if solved else []
    statuses = Counter(r.get("status_display") or "Unknown" for r in solve_window)
    provenance = Counter(classify_attempt(r, i == 0) for i, r in enumerate(rows))

    attempt_files, seen_hash = [], {}
    for i, r in enumerate(rows):
        path = r.get("code_file_path")
        if not path:
            continue
        digest = r.get("code_hash")
        attempt_files.append({
            "path": path,
            "status": r.get("status_display"),
            "utc": iso_utc(r["timestamp"]),
            "phase": "solve" if i < len(solve_window) else "post_solve",
            "same_code_as": seen_hash.get(digest) if digest else None,
        })
        if digest and digest not in seen_hash:
            seen_hash[digest] = path
    pasted_in_solve = sum(1 for i, r in enumerate(rows[:len(solve_window)])
                          if classify_attempt(r, i == 0) == "pasted")

    return {
        "titleSlug": slug,
        "title": first.get("title") or slug,
        "difficulty": first.get("difficulty") or "Unknown",
        "frontend_id": (catalog.get(slug) or {}).get("frontendQuestionId"),
        "topic_tags": tags,
        "total_attempts": len(rows),
        "solve_attempts": len(solve_window),
        "status_breakdown": dict(statuses.most_common()),
        "post_solve_submissions": len(post_solve),
        "post_solve_status_breakdown": dict(Counter(
            r.get("status_display") or "Unknown" for r in post_solve).most_common()),
        "languages_used": sorted({r.get("lang") for r in rows if r.get("lang")}),
        "solved": solved,
        "attempts_to_accept": attempts_to_accept,
        "clean_solve": attempts_to_accept == 1 if solved else False,
        "suspect_pasted_attempts": provenance.get("pasted", 0),
        "resubmissions": provenance.get("resubmission", 0),
        "self_solved": solved and pasted_in_solve == 0,
        # The read-these-first pointers: the first Accept is the code I actually
        # arrived at, the failures before it are the mistakes worth reading.
        "first_accepted_file": (rows[accepted_at].get("code_file_path") if solved
                                else None),
        "failed_attempt_files": [r.get("code_file_path") for r in solve_window
                                 if r.get("status_display") != "Accepted"
                                 and r.get("code_file_path")],
        # Every attempt, in order, for a full read. `same_code_as` marks a file
        # whose contents are identical to an earlier attempt -- skipping those
        # loses nothing, they are the same text.
        "attempt_files": attempt_files,
        "max_seconds_before_first_accept": (rows[accepted_at].get("gap_before")
                                            if solved else None),
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

    if rows and "gap_before" not in rows[0]:
        rows = annotate_rows(rows)      # timing only; similarity needs the files

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
        self_solved = [p for p in tagged if p["self_solved"]]
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
            "problems_self_solved": len(self_solved),
            "self_solve_rate": round(len(self_solved) / len(tagged), 3),
            "clean_solves": len(clean),
            "first_attempt_accept_rate": round(len(clean) / len(tagged), 3),
            "median_attempts_to_accept": (round(statistics.median(attempts), 2)
                                          if attempts else None),
            "total_submissions": sum(breakdown.values()),
            "status_breakdown": dict(breakdown.most_common()),
            "post_solve_submissions": sum(p["post_solve_submissions"] for p in tagged),
            "suspect_pasted_attempts": sum(p["suspect_pasted_attempts"] for p in tagged),
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
        "problems_self_solved": sum(1 for p in plist if p["self_solved"]),
        "post_solve_submissions": sum(p["post_solve_submissions"] for p in plist),
        "suspect_pasted_attempts": sum(p["suspect_pasted_attempts"] for p in plist),
        "resubmissions": sum(p["resubmissions"] for p in plist),
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
| `review_bundles` (in `overview`) | how many bundles the per-problem detail was split into -- see `review/` |

Key fields inside `by_topic`:

| Field | Meaning |
|---|---|
| `problems_attempted` / `problems_solved` / `solve_rate` | coverage and outcome |
| `clean_solves` / `first_attempt_accept_rate` | solved with **zero** failed attempts -- the sharpest mastery signal |
| `problems_self_solved` / `self_solve_rate` | solved with no attempt flagged as pasted -- mastery, with the copy-paste removed |
| `post_solve_submissions` | submissions made *after* the problem was already solved -- re-runs and runtime measurement, excluded from `status_breakdown` |
| `suspect_pasted_attempts` | attempts the paste heuristic flagged (see section 2b) |
| `median_attempts_to_accept` | how much grinding a solve costs on this topic (solved problems only) |
| `status_breakdown` | counts of Accepted / Wrong Answer / ... **up to and including the first Accept only** |
| `unsolved_problems` | attempted but never accepted -- the sharpest weakness signal |
| `days_since_last_practice` | staleness, for spaced repetition |
| `by_difficulty` | the same coverage numbers split Easy / Medium / Hard |
| `review_files` | which `review/*.json` bundles hold this topic's problems |

### `review/` -- the per-problem detail, split so it fits

The per-problem entries are far too large to sit in one file, so they are split
into bundles: `review/<topic>.json`, each problem in **exactly one** bundle,
filed under its most specific tag. Every bundle holds the full entries --
including `failed_attempt_files` and `first_accepted_file` -- for its problems,
sorted with the most-failed problems first.

`review/_index.json` maps every `titleSlug` to the bundle holding it, for when
you need one specific problem.

### `submissions_all.csv` -- one row per SUBMISSION (not per problem)

`submission_id`, `timestamp` (UTC epoch seconds), `datetime_utc`, `title`,
`titleSlug`, `difficulty`, `topic_tags` (semicolon-joined slugs),
`status_display`, `lang`, `runtime`, `memory`, `runtime_percentile`,
`memory_percentile`, `code_file_path` (relative to this folder).

### `solutions/<titleSlug>/` -- the actual code

One file per attempt, named `<timestamp>_<Status>_<lang>_<id>.<ext>`, so the
failed attempts and the eventual accepted one sit side by side in the same
folder. Each folder also has an `attempts_summary.json` rollup.

**Do not go hunting through these folders.** Every problem entry in
`analysis_summary.json` names the two files worth opening directly:

| Field | What it points at |
|---|---|
| `first_accepted_file` | the *first* passing solution -- the code I actually arrived at, before any later tidying or optimising |
| `failed_attempt_files` | every Wrong Answer / TLE / Runtime Error that came before it, in order -- the mistakes themselves |

Read those two together and the diagnosis falls out: what I got wrong, and what
I changed to fix it. Later Accepted files on the same problem are re-runs and
say nothing about how I think.

## 2b. Pasted code, and why some numbers are split

Some submissions are not my own problem solving. They are editorial or
LLM-generated code, pasted in and submitted -- often just to see the runtime.
Counting those as solves would overstate my ability on exactly the topics I am
weakest at, so they are separated three ways: two the tool computes, and one
that is yours to make while you read.

**Structural, and certain:** anything submitted *after* a problem was first
Accepted is a revisit, not first-solve effort. It is counted in
`post_solve_submissions` and kept out of `status_breakdown`. No guesswork --
first-solve effort simply cannot happen after the problem is already solved.

**Heuristic, and fallible:** `suspect_pasted_attempts` counts attempts flagged
by timing and code similarity -- a wholesale rewrite between two submissions
made a minute apart, or a Medium/Hard going straight to Accepted moments after
the previous submission, leaving no window in which to have solved it.

Treat the heuristic as a reason to *discount*, never as proof. It cannot see
pasted code submitted after a long pause, and it will occasionally flag a
genuine fast solve. When a topic's `self_solve_rate` sits well below its
`solve_rate`, say so and lean on the lower number -- but say which one you used.

**Stylistic, and yours to judge.** The two signals above are both blind to the
commonest case: I open a problem, think for twenty minutes, give up, and paste
the editorial. Long gap, no earlier attempt to compare against, so nothing
mechanical fires. Only the code shows it -- so while you are reading, judge it.

Do it as a **comparison against my own code, never as generic AI-detection**.
"This does not look like the other forty solutions this person wrote" is a claim
you can support. "This looks AI-generated" is not -- that judgement is
unreliable in the absolute, and you would be guessing. You have my whole corpus;
use it as the baseline. What earns a flag is *discontinuity*: idioms, naming,
comment style, error handling or a level of sophistication that appears here and
nowhere else in my work on this topic.

Five rules, because the errors here are asymmetric -- telling me I did not solve
something I did solve is worse than missing a paste:

1. **Only adjudicate where it changes something.** A problem with six Wrong
   Answers before the Accept is obviously mine. Judge the clean or near-clean
   Accepts on Medium and Hard; skip the rest.
2. **Never exclude anything on your own judgement.** Annotate it and lower your
   confidence in the conclusions that rest on it. Exclusion is reserved for
   `post_solve`, which is certain.
3. **Always give the reason, concretely.** "Uses `functools.cache` and type
   hints; neither appears anywhere else in this bundle" is evidence. "Feels
   generated" is not, and should not be written down.
4. **Judge before you conclude.** Form the provenance view while reading the
   code, not after you have decided which topics are weak -- otherwise you will
   find pasted code exactly where your thesis needs it.
5. **Allow for me changing.** The export spans years and more than one language.
   Learning an idiom looks exactly like a different author. If a "new" style
   then recurs in later problems, it was me learning something; if it appears
   once and never again, that is the suspicious shape.

Where you cannot tell, say so. `uncertain` is a genuinely useful answer here and
a confident wrong one is not. And note the limit of the whole exercise: whether
I *understood* code I typed myself is not visible in the artefact at all.

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
- **`total_attempts` and `status_breakdown` no longer match.** The breakdown
  stops at the first Accept; `post_solve_submissions` holds the rest. That gap
  is intentional, not a bug.
- Timestamps are UTC epoch seconds. `status_display` values are LeetCode's own
  raw strings.

## 3. The job: read every file, one bundle at a time

> **Resuming?** If `findings/` already has files in it, this job is part-done.
> Do not start over. Skip to "Each chunk" below, take the next bundle with no
> findings file, and carry on. "Continue" is all the instruction you need.

I want the mistakes and the habits in my actual code found and named. Not a
summary of the statistics -- the statistics only tell you where to look. Read
the accepted solutions too: a solution that passed can still be quadratic, or
unreadable, or lucky, and those patterns matter as much as the failures.

**This is a large job and it will not fit in one context.** All the code runs to
roughly __CODE_TOKENS__ tokens across __BUNDLES__ bundles. So it is built to be
done in chunks, across as many sessions as it takes.

### How progress is tracked

**A bundle is done when `findings/<topic>.json` exists.** That is the entire
mechanism -- there is no state file to update and nothing to corrupt. Any
session can pick up where the last one stopped.

### Each chunk

1. List `review/*.json` and `findings/*.json`. The difference is the work left.
   If `findings/` does not exist yet, create it.
2. Take the next unfinished bundle. If you have subagents, run several in
   parallel -- bundles are fully independent. Otherwise do them one at a time
   and drop the code from context between bundles.
3. For that bundle: read `review/<topic>.json`, then read **every** file listed
   in each problem's `attempt_files` -- accepted and failed alike.
   - Skip any entry whose `same_code_as` is set. It is byte-identical to the
     file it names; reading it again tells you nothing.
   - Entries with `"phase": "post_solve"` came after the problem was already
     solved. Still read them -- they show how I optimise -- but never count
     them as first-solve effort.
   - Ignore problems with a non-zero `suspect_pasted_attempts` when judging how
     I think: that code may not be mine.
4. Write `findings/<topic>.json` before moving on, so the work survives:

   ```json
   {
     "topic": "<slug>",
     "problems_read": 0,
     "files_read": 0,
     "mistakes": [{"problem": "<slug>", "file": "<path>", "status": "Wrong Answer",
                   "what_went_wrong": "off-by-one in the binary-search upper bound",
                   "how_it_was_fixed": "changed hi = n-1 to hi = n"}],
     "smells_in_accepted_code": [{"problem": "<slug>", "file": "<path>",
                                  "smell": "O(n^2) scan where a prefix sum was enough"}],
     "provenance": [{"problem": "<slug>", "file": "<path>",
                     "verdict": "mine | uncertain | discontinuous",
                     "why": "uses functools.cache and type hints; neither appears anywhere else in this bundle"}],
     "style_notes": ["reaches for dict-of-lists before defaultdict",
                     "names loop variables i/j/k even in nested logic",
                     "writes the recursion first, converts to iterative only after TLE"],
     "patterns_within_topic": ["..."],
     "strengths": ["..."]
   }
   ```

   Be specific. "Off-by-one in the binary-search upper bound" is worth
   something; "logic error" is not.

   `provenance` only needs entries for clean or near-clean Accepts on Medium and
   Hard, per rule 1 in section 2b. Most problems will not need one at all, and
   `mine` is the correct verdict for the overwhelming majority.

   `style_notes` is about **how I write**, not whether it passed: naming,
   structure, which constructs I reach for, whether I comment, how I handle
   edge cases, whether I decompose or write one long function. Note it from the
   accepted code as much as the failed code -- a solution that passed still
   shows my habits.
5. When you run low on context, stop cleanly. Say which bundles are done and
   how many remain, and tell me to start a fresh session and point it back at
   this file. Do not try to finish everything in one go.

### The reduce step, once every bundle has findings

Read all of `findings/*.json` -- they are small -- and write `REPORT.md`
covering section 4 below. The point of this step is what repeats **across**
topics: a mistake I make in three unrelated topics is a habit, and worth more
than any single-topic statistic. Group the findings into named recurring
errors, each with its count and the specific problems as evidence.

Never bulk-read `solutions/` directly. Go bundle by bundle.

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
**Provenance, stated once and honestly.** How many problems you marked
`discontinuous` or `uncertain`, and what that does to the rest of the report.
If it is a small number, say the analysis stands. If a weak topic's evidence
turns out to rest largely on code you doubt is mine, that is the single most
important thing in the report -- say it first, because it means the real
weakness is worse than the statistics show.

**How I write code.** A characterisation drawn from the whole corpus, not one
sample: the constructs I reach for, how I name and structure things, my default
approach to a new problem, what I do when the first attempt fails, and how my
style changed over the years the export covers. Be blunt and specific -- this
should read as a recognisable portrait of me as a programmer, backed by files
you actually read.

**Recurring mistakes, ranked by how often they actually occur.** The other
main deliverable. For each: a name, what it is, how many times it happened,
which problems and files, and what to do differently. Order by frequency, not
by how interesting they are.

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
    body = PROMPT_SCHEMA.replace(
        "__CODE_TOKENS__", f"{round(o.get('code_bytes', 0) / 3800):,}K").replace(
        "__BUNDLES__", str(o.get("review_bundles", 0)))
    return header + body


def review_buckets(problems: list[dict]) -> dict[str, list[dict]]:
    """Split the problems into one bundle per topic, each problem in exactly one
    bundle. The rarest tag wins: `monotonic-stack` says far more about a problem
    than `array` does, and assigning to a single bundle means each solution file
    gets read once instead of once per tag.
    """
    freq = Counter(tag for p in problems for tag in p["topic_tags"])
    buckets: dict[str, list[dict]] = defaultdict(list)
    for problem in problems:
        tags = problem["topic_tags"]
        key = min(tags, key=lambda t: (freq[t], t)) if tags else "untagged"
        buckets[key].append(problem)
    for entries in buckets.values():
        # Richest material first, so a reader working top-down hits the
        # problems with the most failures before running out of room.
        entries.sort(key=lambda p: (-len(p["failed_attempt_files"]), p["titleSlug"]))
    return dict(buckets)


def write_review_bundles(outdir: Path, problems: list[dict], by_topic: list[dict],
                         tag_names: dict) -> dict:
    """Write review/<topic>.json and point every topic at the bundles holding
    its problems. Returns the index."""
    review = outdir / "review"
    review.mkdir(parents=True, exist_ok=True)

    buckets = review_buckets(problems)
    index, files_for_tag, written = {}, defaultdict(set), set()
    for topic, entries in buckets.items():
        name = f"{safe_component(topic)}.json"
        written.add(name)
        failing = [p for p in entries if p["failed_attempt_files"]]
        save_json(review / name, {
            "topic": topic,
            "name": tag_names.get(topic, topic),
            "problems_in_bundle": len(entries),
            "problems_with_failures": len(failing),
            "failed_attempts": sum(len(p["failed_attempt_files"]) for p in failing),
            "read_these_first": [p["titleSlug"] for p in failing[:20]],
            "problems": entries,
        })
        for problem in entries:
            index[problem["titleSlug"]] = f"review/{name}"
            for tag in problem["topic_tags"]:
                files_for_tag[tag].add(f"review/{name}")

    for topic in by_topic:
        topic["review_files"] = sorted(files_for_tag.get(topic["topic"], []))
    save_json(review / "_index.json", index)

    # Prune only afterwards. Every bundle is rewritten in place via save_json's
    # atomic replace, so an analysis session part-way down the list never sees a
    # bundle briefly missing.
    for stale in review.glob("*.json"):
        if stale.name not in written and stale.name != "_index.json":
            stale.unlink()
    return index


def rebuild(outdir: Path, state: dict | None = None, catalog: dict | None = None) -> None:
    """Regenerate every derived artefact from the CSV. Pure local computation."""
    rows = read_rows(outdir / "submissions_all.csv")
    if not rows:
        log("  No submissions on disk yet -- nothing to summarise.")
        return
    rows = annotate_rows(rows, outdir)   # reads the code files: paste detection
    if state is None:
        state = load_json(outdir / "state.json", new_state())
    if catalog is None:
        catalog = load_json(outdir / "problem_catalog.json", {})
    failed = load_json(outdir / "failed_submissions.json", [])

    csv_path = outdir / "submissions_all.csv"
    with csv_path.open(newline="", encoding="utf-8") as fh:
        raw_count = sum(1 for _ in csv.reader(fh)) - 1
    if raw_count > len(rows):
        # The CSV is the durable ledger, so never truncate it in place: write a
        # sibling and swap it in atomically. And if a fetch is appending to it
        # right now, leave it alone entirely -- a tidier file is worth nothing
        # next to the rows we would drop.
        tmp = csv_path.with_suffix(".csv.tmp")
        with tmp.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        with csv_path.open(newline="", encoding="utf-8") as fh:
            grew = sum(1 for _ in csv.reader(fh)) - 1 != raw_count
        if grew:
            tmp.unlink(missing_ok=True)
            log("  CSV is being written by another run -- skipping duplicate cleanup")
        else:
            os.replace(tmp, csv_path)
            log(f"  Removed {raw_count - len(rows)} duplicate rows from the CSV")

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

    # The per-problem detail is ~90% of the analysis and does not fit in one
    # context alongside anything else. It lives in review/ so it can be read a
    # bundle at a time; analysis_summary.json stays small enough to read whole.
    problems = analysis.pop("problems")
    tag_names = {t.get("slug"): t.get("name")
                 for entry in catalog.values() for t in (entry.get("topicTags") or [])}
    write_review_bundles(outdir, problems, analysis["by_topic"], tag_names)
    analysis["overview"]["review_bundles"] = len(list((outdir / "review").glob("*.json"))) - 1

    solutions = outdir / "solutions"
    code = [f for f in solutions.rglob("*")
            if f.is_file() and f.name != "attempts_summary.json"] if solutions.is_dir() else []
    code_files = len(code)
    analysis["overview"]["code_bytes"] = sum(f.stat().st_size for f in code)
    save_json(outdir / "analysis_summary.json", analysis)
    (outdir / "prompt.md").write_text(render_prompt(analysis, code_files), encoding="utf-8")

    log(f"  {len(rows)} submissions | {len(by_slug)} problems | "
        f"{len(analysis['by_topic'])} topics | "
        f"{analysis['overview']['review_bundles']} review bundles")
    log(f"  Wrote analysis_summary.json, review/ and prompt.md")


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

    # --- attempts after the first Accept are not first-solve effort ---------
    summary_d = summarize_attempts([r for r in rows if r["titleSlug"] == "d"])
    assert summary_d["status_breakdown"] == {"Accepted": 1}, summary_d["status_breakdown"]
    assert summary_d["post_solve_submissions"] == 1
    assert summary_d["post_solve_status_breakdown"] == {"Wrong Answer": 1}
    assert summary_d["total_attempts"] == 2, "the raw total still counts everything"

    # --- dive-in pointers: the mistakes, and the code they led to -----------
    def coded(sid, ts, status, path):
        return dict(row(sid, ts, "e", status), code_file_path=path)

    pointed = summarize_attempts([
        coded(10, 1700000000, "Wrong Answer", "solutions/e/wa.py"),
        coded(11, 1700000600, "Time Limit Exceeded", "solutions/e/tle.py"),
        coded(12, 1700001200, "Accepted", "solutions/e/ok.py"),
        coded(13, 1700001800, "Accepted", "solutions/e/later.py"),
    ])
    assert pointed["first_accepted_file"] == "solutions/e/ok.py", "must be the FIRST accept"
    assert pointed["failed_attempt_files"] == ["solutions/e/wa.py", "solutions/e/tle.py"]
    assert pointed["post_solve_submissions"] == 1

    # --- timing/similarity facts -------------------------------------------
    annotated = annotate_rows([row(20, 1700000000, "f", "Wrong Answer"),
                               row(21, 1700000030, "g", "Accepted"),
                               row(22, 1700000100, "f", "Accepted")])
    assert annotated[0]["gap_before"] is None and annotated[0]["gap_on_problem"] is None
    assert annotated[1]["gap_before"] == 30, "gap_before spans problems"
    assert annotated[2]["gap_before"] == 70 and annotated[2]["gap_on_problem"] == 100
    assert _jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert _jaccard({"a", "b"}, {"c"}) == 0.0
    assert _jaccard(set(), {"a"}) is None, "an unreadable file must not be a verdict"

    # Regression: `same_code_as` means "skip this file, you have read it".
    # Hashing a *set* of lines made reordered code -- including Wrong Answer /
    # Accepted pairs -- collide, so the analysis was told to skip the one diff
    # worth reading. The hash must be over the content, not the line set.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "s").mkdir()
        (root / "s" / "wa.py").write_text("if a > b:\n    return a\nreturn b\n")
        (root / "s" / "ok.py").write_text("return b\nif a > b:\n    return a\n")
        lines_wa, hash_wa = _read_solution(root, "s/wa.py")
        lines_ok, hash_ok = _read_solution(root, "s/ok.py")
        assert lines_wa == lines_ok, "reordering does not change the line set"
        assert hash_wa != hash_ok, "reordered code is NOT the same file"
        assert _read_solution(root, "s/missing.py") == (None, None)

    # --- the paste heuristic, and its deliberate blind spots ----------------
    def att(**kw):
        return {"status_display": "Accepted", "difficulty": "Medium", **kw}

    assert classify_attempt(att(similarity_to_previous=0.95, gap_on_problem=20),
                            False) == "resubmission", "same code again = a runtime measurement"
    assert classify_attempt(att(similarity_to_previous=0.2, gap_on_problem=20),
                            False) == "pasted", "a full rewrite in 20s was not typed"
    assert classify_attempt(att(similarity_to_previous=0.85, gap_on_problem=20),
                            False) == "own", "a small fix is genuine work"
    assert classify_attempt(att(similarity_to_previous=0.2, gap_on_problem=3600),
                            False) == "own", "a rewrite after an hour proves nothing"
    assert classify_attempt(att(gap_before=40), True) == "pasted", \
        "straight to Accepted on a Medium with no window to solve it"
    assert classify_attempt(att(gap_before=40, difficulty="Easy"), True) == "own", \
        "a fast Easy is plausible"
    assert classify_attempt(att(gap_before=40, status_display="Wrong Answer"),
                            True) == "own", "a fast failure is not a paste"
    assert classify_attempt(att(gap_before=9000), True) == "own"
    assert classify_attempt(att(), True) == "own", "no evidence means no accusation"

    suspect = summarize_attempts([dict(row(30, 1700000000, "h", "Accepted"),
                                       gap_before=15)])
    assert suspect["solved"] and suspect["self_solved"] is False
    assert suspect["suspect_pasted_attempts"] == 1
    honest = summarize_attempts([dict(row(31, 1700000000, "i", "Accepted"),
                                      gap_before=9000)])
    assert honest["self_solved"] is True and honest["max_seconds_before_first_accept"] == 9000

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
