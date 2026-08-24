# LeetCode Submission History Exporter

Exports your **complete** LeetCode submission history — every attempt at every
status, with full source code — joined against problem difficulty and topic
tags, into a folder an LLM can analyse without further explanation.

Wrong Answers, TLEs and Runtime Errors are the point, not noise: they are what
shows which topics you actually struggle with, and *how* you struggle with them.

## Setup

Requires Python 3.10+. Two ways to run it:

**With uv (no venv needed)** — dependencies are declared inline in the script:

```bash
uv run leetcode_export.py --self-test
```

**With pip:**

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

One-time browser download for Playwright (skipped automatically if you already
have it):

```bash
python -m playwright install chromium
```

## Usage

```bash
uv run leetcode_export.py
```

First run opens a real browser window. **You** log in — password, Google,
GitHub, 2FA, CAPTCHA, whatever you use. The tool never sees your credentials.

The window stays open until LeetCode itself confirms the login, then closes on
its own. It does not simply wait for a session cookie to appear: a cookie can
show up part-way through an OAuth handshake, well before you have actually
finished signing in. The session is saved to
`leetcode_export/.browser_profile/`, so later runs open no window until it
expires.

Then it fetches the problem catalog, lists your submissions, downloads the code
for each one, and writes the analysis files.

| Flag | Effect |
|---|---|
| `--outdir PATH` | Export folder (default `./leetcode_export`) |
| `--full` | Re-list the entire history, ignoring the incremental cutoff |
| `--delay SECONDS` | Seconds between requests (default `1.75`, minimum `0.5`) |
| `--refresh-catalog` | Refetch the problem catalog even if it is fresh |
| `--retry-failed` | Re-attempt everything in `failed_submissions.json` |
| `--rebuild-analysis` | Regenerate the analysis files offline, no login |
| `--self-test` | Run offline assertions and exit |

## Signing in with a session cookie

If the browser login fails — Google and Cloudflare both flag automated
browsers as bots, and there is no way around that from inside one — hand the
tool a session directly instead. You log in normally in your **own** browser
and copy the cookie across; no browser is launched, and Playwright is not even
needed.

1. Log in to LeetCode in your normal browser.
2. Open DevTools → **Application** (Firefox: **Storage**) → Cookies →
   `https://leetcode.com`.
3. Copy the **value** of the `LEETCODE_SESSION` cookie.

```bash
export LEETCODE_SESSION='paste-the-value-here'
uv run leetcode_export.py
```

To keep it out of your shell history, put it in a file once and read from
there:

```bash
export LEETCODE_SESSION="$(cat ~/.leetcode_session)"
```

`LEETCODE_CSRFTOKEN` can be set the same way but is optional — this tool only
ever reads, and LeetCode does not require a CSRF token for that.

When `LEETCODE_SESSION` is set it takes precedence over the saved browser
profile, so unset it if you later want to go back to the browser login.

**Treat that value like a password.** It grants full access to your LeetCode
account for as long as it lives. Do not commit it or paste it anywhere. It
expires after a while; when it does the tool says so and you repeat the copy.

## Analysing the export

That is what this is for. Point an LLM at the folder and let it read your code:

```bash
cd leetcode_export && claude "read prompt.md and do the analysis"
```

`prompt.md` is regenerated on every run with your real numbers in it. You do
not need to explain anything else — it documents the schema, warns about the
traps, and lays out the job.

### It is a big job, done chunk by chunk

The point is not a summary of the statistics. It is that an LLM reads **every
solution you have ever submitted** — the accepted ones too, since passing code
still shows your habits — and reports the mistakes you repeat, the smells in
code that worked, and a portrait of how you write.

That is far more than fits in one context (~1.9M tokens of code here), so the
export is pre-split into **109 review bundles**, one per topic, each problem in
exactly one bundle. The model works through them a few at a time.

**Progress is tracked by which files exist.** A bundle is done when
`findings/<topic>.json` has been written. There is no state file to corrupt and
nothing to keep in sync.

To carry on in a fresh session:

```bash
cd leetcode_export && claude "read prompt.md and continue"
```

It compares `review/` against `findings/`, picks up the next unfinished bundle,
and keeps going. Repeat until every bundle has findings — then ask it to do the
reduce step, which reads all the findings files and writes `REPORT.md`: the
recurring mistakes ranked by frequency, your coding-style profile, weak and
strong topics with dates, and a prioritised practice plan.

If your LLM has subagents, it will fan several bundles out in parallel, since
bundles are fully independent.

### What the tool decides, and what the LLM decides

Every rate, median and count in `analysis_summary.json` is computed by the tool.
An LLM asked to average thousands of CSV rows gets some of it wrong quietly.
The tool supplies the facts; the LLM reads the code and supplies the diagnosis.

The tool also separates out the submissions that are not you solving a problem,
because counting them would flatter exactly the topics you are weakest at:

- **Post-solve submissions** — anything sent *after* a problem was already
  accepted. Re-runs, optimisation, measuring runtime. In this export that is
  3,011 of 5,212 submissions, and it is kept out of `status_breakdown`
  entirely. This is structural, not a guess: first-solve effort cannot happen
  after the problem is already solved.
- **Suspected pasted code** — editorial or LLM output pasted in and submitted.
  Flagged by timing and code similarity: a wholesale rewrite between two
  submissions a minute apart, or a Medium/Hard going straight to Accepted
  moments after the previous submission, leaving no window to have solved it.
  A heuristic, deliberately conservative, and `prompt.md` tells the model to
  discount rather than exclude. Compare `self_solve_rate` against `solve_rate`
  per topic to see where it matters.
- **Byte-identical resubmissions** — marked with `same_code_as` so the model
  skips re-reading the same text. 535 files here.

There is a third signal the tool cannot compute: code that was pasted after a
long pause. No timing or similarity check can see it — only the code can. So
`prompt.md` asks the LLM to judge that while it reads, under tight rules: it
compares against *your own* corpus rather than doing generic AI-detection,
only adjudicates clean Accepts on Medium and Hard where the answer changes
something, must give a concrete reason, and may never exclude anything on its
own judgement — it annotates and lowers confidence instead. `uncertain` is an
allowed verdict, and telling you that you didn't solve something you did is
treated as the worse error.

## Output

```
leetcode_export/                 (gitignored — holds a live login session)
├── prompt.md                    the LLM briefing; point Claude at this
├── analysis_summary.json        overview / by_topic / by_month (small: read whole)
├── review/                      per-problem detail, split into bundles
│   ├── <topic>.json             one bundle of problems + every attempt file
│   └── _index.json              titleSlug -> which bundle holds it
├── findings/                    written by the LLM; one file per finished bundle
├── REPORT.md                    written by the LLM at the end
├── submissions_all.csv          one row per submission, every status
├── problem_catalog.json         titleSlug -> difficulty, topic tags, number
├── failed_submissions.json      downloads that failed, for --retry-failed
├── state.json                   incremental bookkeeping
├── solutions/<titleSlug>/
│   ├── <timestamp>_<Status>_<lang>_<id>.<ext>
│   └── attempts_summary.json
└── .browser_profile/            saved Playwright login session
```

Every attempt is kept — failed ones sit beside the eventual accepted solution
in the same folder, which is what makes "what was I doing wrong" answerable.

Per-topic metrics worth knowing about:

- **`first_attempt_accept_rate`** — solved with zero failed attempts. Real
  mastery, as opposed to grinding it out.
- **`self_solve_rate`** — the same coverage, with attempts flagged as pasted
  removed. Where this sits well below `solve_rate`, the topic is weaker than it
  looks.
- **`review_files`** — which bundles under `review/` hold this topic's problems.
- **`median_attempts_to_accept`** — how expensive a solve is on this topic.
- **`status_breakdown`** — TLE-heavy means wrong complexity; Runtime-Error-heavy
  means edge cases and bounds; Wrong-Answer-heavy means logic.
- **`unsolved_problems`** — attempted, never accepted.
- **`days_since_last_practice`** — for spotting strengths that have gone stale.
- **`coverage_of_reported`** — how much of your history this export actually
  holds, measured against LeetCode's own submission count for the account. A
  shortfall becomes an explicit caveat in `prompt.md` so the analysis is not
  read as complete when it is not.

## Incremental and resumable

Re-run it whenever you like; it only fetches what is new.

- Submissions are listed newest-first and listing stops at the last completed
  run's cutoff.
- Once the full history has been enumerated, later runs only look for
  submissions *newer* than the last listing — a restart mid-download costs one
  request, not a re-walk of the whole history. `--full` still forces a
  complete re-walk.
- The listing itself is checkpointed and resumable. If LeetCode cuts it short —
  it refuses deep pagination once you are thousands of submissions in — the
  run keeps everything found so far, downloads that code, and resumes the
  listing from a saved cursor next time.
- The cutoff only advances once the download queue has fully drained, so an
  interrupted run can never silently skip submissions.
- Progress is checkpointed every 10 submissions with atomic writes, and rows
  are flushed to the CSV as they are downloaded.
- **Ctrl+C is safe at any point.** The next run picks up exactly where it
  stopped and re-downloads nothing.

`--full` re-lists your whole history but still skips anything already
downloaded — so it is safe to re-run after an interrupt. To genuinely start
over, delete the export folder.

## Rate limiting

Getting your account throttled would defeat the purpose, so the tool is
deliberately slow:

- **Sequential only.** No threads, no concurrency, ever.
- ~1.75s of jittered delay before **every** request.
- On HTTP 403, 429 or 5xx: exponential backoff capped at 5 minutes, 5 retries,
  and a `Retry-After` header is honoured exactly when present. LeetCode throttles
  with 403 as well as 429, so both are treated as "slow down", not "give up".
- 5 consecutive failures stops the run entirely rather than hammering a server
  that is clearly unhappy. Wait a while, then re-run.
- The session is re-checked every 200 requests; if it has expired the run stops
  cleanly with progress saved instead of burning retries against a dead cookie.

A first backfill of a few thousand submissions takes one to three hours. It
prints a live ETA, and stopping partway costs you nothing.

## Troubleshooting

**"Timed out waiting for a confirmed login"** — the window has a 10-minute
budget and closes only once LeetCode confirms you are signed in. Just re-run.

**Google sign-in, or a Cloudflare check, fails in the tool's browser** —
both classify Playwright-driven browsers as bots. Email/password or GitHub may
still work; if not, use the session-cookie method above, which sidesteps the
automated browser entirely.

**Session expires mid-run** — expected on long backfills. The run stops with
everything saved; re-run and it will open the browser for a fresh login.

**`Listing stopped early: HTTP 403`** — LeetCode throttled or refused deep
pagination. Nothing is lost: the submissions already found are downloaded and
the listing resumes from its cursor on the next run. If it keeps stopping at
the same offset, raise `--delay` (try `3`) and re-run.

**Lots of entries in `failed_submissions.json`** — run `--retry-failed` later.
These are downloads that failed, *not* problems you failed, and `prompt.md`
tells the LLM so explicitly.

## Caveat

This uses LeetCode's **undocumented internal endpoints** (`/api/submissions/`
and the GraphQL API that the website itself calls). They were verified working
on 2026-08-24, but LeetCode can change or remove them at any time without
notice. The problem-catalog query is the most likely thing to break first — a
newer variant of it already exists in the wild.

Everything runs locally against your own account, at a request rate far below
normal browsing.
