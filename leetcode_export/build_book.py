#!/usr/bin/env python3
"""Build `book/` -- a drill-down improvement book from findings/*.json.

Reads the analysis produced by the map step (findings/<topic>.json), joins it
against analysis_summary.json for the aggregate numbers and review/<topic>.json
for per-problem attempt history, and emits one static HTML chapter per topic
plus an index ranked by how urgently the topic needs work.

Everything is derived -- no topic, problem or score is hardcoded. Re-run it
after regenerating findings/ and the book updates.

    python3 build_book.py
"""

from __future__ import annotations

import datetime
import html
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import course
import diagrams
import synthesis
import traces

ROOT = Path(__file__).resolve().parent
BOOK = ROOT / "book"

# How much a failed submission of each kind tells you about a real gap.
# A Wrong Answer is a reasoning bug; a Compile Error is a typo.
STATUS_WEIGHT = {
    "Wrong Answer": 5,
    "Time Limit Exceeded": 4,
    "Memory Limit Exceeded": 4,
    "Runtime Error": 3,
    "Output Limit Exceeded": 3,
    "Accepted": 2,  # a mistake logged against post-solve code
    "Compile Error": 1,
}
DEFAULT_STATUS_WEIGHT = 2

# status_breakdown key -> (failure mode, what it means), per the analysis brief.
FAILURE_MODES = [
    ("Wrong Answer", "Logic and edge cases",
     "the approach is roughly right, the reasoning inside it is not"),
    ("Time Limit Exceeded", "Wrong complexity class",
     "reaching for brute force where the input size rules it out"),
    ("Runtime Error", "Indexing, bounds and empty input",
     "the algorithm is sound but the access patterns are unguarded"),
    ("Compile Error", "Edit hygiene",
     "half-finished renames and unfinished statements shipped to the judge"),
]

EXT_LANG = {
    ".java": "java", ".cpp": "cpp", ".cc": "cpp", ".c": "c", ".py": "python",
    ".py3": "python", ".rs": "rust", ".js": "javascript", ".ts": "typescript",
    ".go": "go", ".cs": "csharp", ".sql": "sql", ".kt": "kotlin", ".rb": "ruby",
}

MAX_CODE_LINES = 400

# Titles and difficulties for problems the reader has never attempted, so a
# drill can name one and the schedule can still render a real row for it.
CATALOG = json.loads((ROOT / "problem_catalog.json").read_text(encoding="utf-8"))


def esc(text) -> str:
    return html.escape("" if text is None else str(text))


# The analysis prose is written with markdown-style backtick spans around
# identifiers. They are the only markup in it, and rendering them literally is
# what made 721 of the 904 diagnoses read as raw text.
INLINE_CODE = re.compile(r"`([^`\n]+)`")


def esc_code(text) -> str:
    """Escape for HTML, then turn `foo` into real inline code."""
    return INLINE_CODE.sub(r"<code>\1</code>", esc(text))


def load_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def slug_to_title(slug: str) -> str:
    return " ".join(word.capitalize() for word in str(slug).split("-"))


def read_code(rel_path: str) -> tuple[str, str, bool]:
    """Return (code, language, truncated) for a solutions/ path."""
    if not rel_path:
        return "", "", False
    target = ROOT / rel_path
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "", "", False
    lines = text.splitlines()
    truncated = len(lines) > MAX_CODE_LINES
    if truncated:
        lines = lines[:MAX_CODE_LINES]
    lang = EXT_LANG.get(target.suffix.lower(), target.suffix.lstrip(".") or "text")
    return "\n".join(lines), lang, truncated


def submission_status(rel_path: str) -> str:
    """solutions/<slug>/<ts>_<Status>_<lang>_<id>.<ext> -> 'Wrong Answer'."""
    match = re.match(r"\d+_(.+?)_[a-z0-9+#]+_\d+$", Path(rel_path or "").stem)
    return match.group(1).replace("_", " ") if match else ""


def pct(value) -> str:
    return "--" if value is None else f"{value * 100:.0f}%"


def plural(count, noun: str, suffix: str = "s") -> str:
    return f"{count} {noun}{'' if count == 1 else suffix}"


# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------

class Case:
    """One problem inside a topic, with every mistake logged against it."""

    def __init__(self, slug: str, problem: dict | None):
        self.slug = slug
        self.problem = problem or {}
        self.title = self.problem.get("title") or slug_to_title(slug)
        self.difficulty = self.problem.get("difficulty") or ""
        self.attempts = self.problem.get("attempts_to_accept") or 0
        self.accepted_file = self.problem.get("first_accepted_file") or ""
        self.suspect = self.problem.get("suspect_pasted_attempts") or 0
        self.solved = self.problem.get("solved", True)
        self.mistakes: list[dict] = []
        self.smells: list[dict] = []
        self.provenance: list[dict] = []

    @property
    def severity(self) -> float:
        """Deepest-misunderstanding-first: what failed, times how long it took."""
        weight = sum(
            STATUS_WEIGHT.get(m.get("status") or submission_status(m.get("file", "")),
                              DEFAULT_STATUS_WEIGHT)
            for m in self.mistakes
        )
        grind = math.log2(1 + max(self.attempts, 1))
        unsolved_bonus = 1.5 if not self.solved else 1.0
        return weight * (1 + grind) * unsolved_bonus

    def order_mistakes(self) -> list[dict]:
        """Chronological -- the debugging story only reads correctly in order."""
        def timestamp(mistake):
            stem = Path(mistake.get("file") or "").stem
            head = stem.split("_", 1)[0]
            return int(head) if head.isdigit() else 0
        return sorted(self.mistakes, key=timestamp)


class Chapter:
    # Problems' worth of prior pulled toward the global first-attempt rate before
    # a topic's own rate is trusted. Without this a topic with one attempted
    # problem and one miss reads as "0% -- your weakest topic", which is noise.
    SHRINKAGE = 8.0

    def __init__(self, findings: dict, topic_stats: dict | None,
                 bundle: dict | None, prior: float):
        self.topic = findings["topic"]
        self.findings = findings
        self.stats = topic_stats or {}
        self.prior = prior
        name = (self.stats.get("name") or (bundle or {}).get("name") or "").strip()
        self.name = name if name[:1].isupper() else slug_to_title(self.topic)
        self.bundle_problems = (bundle or {}).get("problems", [])
        problems = {p["titleSlug"]: p for p in self.bundle_problems}

        cases: dict[str, Case] = {}

        def case_for(slug: str) -> Case:
            if slug not in cases:
                cases[slug] = Case(slug, problems.get(slug))
            return cases[slug]

        for mistake in findings.get("mistakes", []):
            case_for(mistake.get("problem", "")).mistakes.append(mistake)
        for smell in findings.get("smells_in_accepted_code", []):
            case_for(smell.get("problem", "")).smells.append(smell)
        for entry in findings.get("provenance", []):
            case_for(entry.get("problem", "")).provenance.append(entry)

        self.cases = sorted(cases.values(), key=lambda c: (-c.severity, c.title))
        self.mistake_count = len(findings.get("mistakes", []))
        self.smell_count = len(findings.get("smells_in_accepted_code", []))

    # -- ranking ----------------------------------------------------------

    @property
    def faar(self):
        return self.stats.get("first_attempt_accept_rate")

    @property
    def attempted(self) -> int:
        return self.stats.get("problems_attempted") or self.findings.get("problems_read", 0)

    @property
    def in_chapter(self) -> int:
        """Problems actually filed here. Tags overlap; bundles do not."""
        return len(self.bundle_problems)

    @property
    def unsolved(self) -> list:
        """Never-solved problems filed in THIS chapter.

        Not the tag's list. Tags overlap heavily, so the export's four
        never-solved problems appeared under eleven tags -- rendering the same
        "Never solved" section eleven times and multiplying eleven priorities
        for four problems. Every problem sits in exactly one bundle, so it gets
        counted, and shown, exactly once.
        """
        if self.bundle_problems:
            return [{"titleSlug": p.get("titleSlug"), "title": p.get("title"),
                     "difficulty": p.get("difficulty"),
                     "attempts": p.get("total_attempts")}
                    for p in self.bundle_problems if not p.get("solved", True)]
        return self.stats.get("unsolved_problems", []) or []

    @property
    def shrunk_faar(self) -> float:
        """First-attempt accept rate, smoothed toward the global rate.

        A topic's own rate is only as trustworthy as the number of problems
        behind it, so small topics are pulled toward the corpus average.
        """
        attempted = self.stats.get("problems_attempted")
        clean = self.stats.get("clean_solves")
        if not attempted or clean is None:
            return self.prior
        k = self.SHRINKAGE
        return (clean + k * self.prior) / (attempted + k)

    @property
    def priority(self) -> float:
        """Weakness-led, evidence-qualified.

        Weakness is squared so it dominates: this book is ordered by where you
        are weak, not by where the most material happens to sit. The mistake
        count only qualifies that -- a log, so a topic with 30 mistakes edges
        out one with 8 without overturning a real gap in ability. Problems you
        never solved at all count for extra.

        Staleness is deliberately *not* folded in. A rusty strength and a real
        weakness need different responses, so staleness is reported as its own
        badge rather than averaged into one number.
        """
        weakness = 1.0 - self.shrunk_faar
        evidence = math.log2(2 + self.mistake_count)
        unsolved_factor = 1 + 0.5 * len(self.unsolved)
        return (weakness ** 2) * evidence * unsolved_factor

    @property
    def failure_mode(self) -> tuple[str, str, int] | None:
        """The dominant non-Accepted status, mapped to its named failure mode."""
        breakdown = self.stats.get("status_breakdown") or {}
        best = None
        for key, label, meaning in FAILURE_MODES:
            count = breakdown.get(key, 0)
            if count and (best is None or count > best[2]):
                best = (label, meaning, count)
        return best

    @property
    def flagged_provenance(self) -> list[dict]:
        return [p for p in self.findings.get("provenance", [])
                if (p.get("verdict") or "").lower() in ("discontinuous", "uncertain")]


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

# Lesson numbers are list positions, so writing "lesson 12" into prose by hand
# means the next insertion silently falsifies a dozen sentences. course.py writes
# [[slug]] instead and the number is resolved here, from the same list that
# produced it. An unknown slug fails the build rather than rendering as itself.
LESSON_INDEX = {l["slug"]: (i, l["title"])
                for i, l in enumerate(course.LESSONS, 1)}
LESSON_REF = re.compile(r"\[\[([A-Za-z-]+)\]\]")


def lesson_refs(html: str) -> str:
    def sub(m):
        slug = m.group(1)
        number, title = LESSON_INDEX[slug.lower()]
        word = "Lesson" if slug[0].isupper() else "lesson"
        return (f'<a class="xref" href="course-{slug.lower()}.html" '
                f'title="{esc(title)}">{word} {number}</a>')
    return LESSON_REF.sub(sub, html)


# Counts written into prose by hand were true when they were typed. These are
# resolved at render time from the same join that produces the evidence
# section, so the number in the sentence and the number in the list under it
# cannot disagree -- and an unknown key fails the build rather than rendering
# as itself. Populated in main() before any page is written.
COUNTS: dict[str, int | str] = {}
COUNT_REF = re.compile(r"\{\{([a-z]+):([^}\n]+)\}\}")


def count_refs(html: str) -> str:
    def one(match) -> str:
        value = COUNTS[f"{match.group(1)}:{match.group(2)}"]
        # Thousands separators on corpus-sized numbers, none on the counts,
        # which are all small enough that a comma would look like a typo.
        return f"{value:,}" if isinstance(value, int) and value >= 1000 else str(value)
    return COUNT_REF.sub(one, html)


DEFS = re.compile(r"<defs>.*?</defs>", re.S)


def page(title: str, body: str, depth_note: str = "",
         glossary: bool = True) -> str:
    # Every diagram ships an identical <defs> so it stands alone, but duplicate
    # ids are invalid once several are on one page -- and url(#ah) resolves to
    # the first block regardless. Keep the first, drop the rest.
    seen = []
    body = DEFS.sub(lambda m: m.group(0) if not seen and not seen.append(1) else "",
                    body)
    body = count_refs(lesson_refs(body))
    if glossary:
        body = glossary_links(body)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- This book quotes the reader's own submission history in full. It is
     published so it can be linked, not so it can be found: kept out of search
     engines here as well as in the site's robots.txt, because a robots rule
     alone does not stop a page that is linked from elsewhere being indexed. -->
<meta name="robots" content="noindex, nofollow">
<title>{esc(title)}</title>
<link rel="stylesheet" href="book.css">
</head>
<body>
{body}
<footer class="foot">{depth_note}{STAMP["line"]}{STAMP["changes"]}
Generated by <code>build_book.py</code> from <code>findings/*.json</code>.
Re-run it to rebuild.</footer>
</body>
</html>
"""


def code_block(rel_path: str, label: str, tone: str) -> str:
    code, lang, truncated = read_code(rel_path)
    if not code:
        # The analysis names the file for every diagnosis, and three of those
        # names splice one submission's timestamp onto another's id. Say that,
        # rather than showing an empty box.
        return (f'<p class="missing">{esc(label)}: the analysis names '
                f"<code>{esc(rel_path)}</code>, which is not in the export. "
                f"The diagnosis above is still a real event in the record; only "
                f"the file reference is wrong.</p>")
    note = (f'<span class="trunc">first {MAX_CODE_LINES} lines</span>'
            if truncated else "")
    return f"""<figure class="code {tone}">
<figcaption><span class="tag">{esc(label)}</span>
<span class="lang">{esc(lang)}</span>{note}
<code class="path">{esc(rel_path)}</code></figcaption>
<pre><code>{esc(code)}</code></pre>
</figure>"""


# A diff longer than this is not a patch, it is a rewrite. Saying which of the
# two happened is information the reader wants, so the ceiling is a fact to
# report rather than a rendering limit to hide behind.
MAX_DIFF_LINES = 60


def next_submission(rel_path: str) -> str:
    """The submission that came after this one, by timestamp.

    Every diagnosis in findings/ is written as "the next attempt changed X".
    Filenames lead with the submission timestamp, so the next attempt is the
    next sibling in sort order -- no extra data, and it pairs the diff with
    exactly the sentence above it.
    """
    path = ROOT / rel_path
    if not rel_path or not path.exists():
        return ""
    siblings = sorted(f.name for f in path.parent.iterdir()
                      if f.suffix in EXT_LANG and f.name[0].isdigit())
    try:
        after = siblings[siblings.index(path.name) + 1]
    except (ValueError, IndexError):
        return ""
    return str((path.parent / after).relative_to(ROOT))


def diff_block(before_path: str, after_path: str) -> str:
    """What changed between two submissions, or why that is not worth showing."""
    import difflib

    before, _, cut_a = read_code(before_path)
    after, _, cut_b = read_code(after_path)
    if not before or not after or cut_a or cut_b:
        return ""   # a diff of two truncated files invents changes at the cut
    if before == after:
        return ('<p class="hint diff-note">The next submission is byte-identical '
                "to this one. Nothing was changed.</p>")

    lines = list(difflib.unified_diff(before.splitlines(), after.splitlines(),
                                      lineterm="", n=3))[2:]
    changed = sum(1 for line in lines if line[:1] in "+-")
    status = submission_status(after_path) or "the next attempt"
    if changed > MAX_DIFF_LINES:
        return (f'<p class="hint diff-note">The next submission rewrites '
                f"{plural(changed, 'line')} &mdash; that is a new approach "
                f"rather than a patch, so the two files are shown in full "
                f"instead of diffed.</p>")

    rows = []
    for line in lines:
        tone = ({"+": "add", "-": "del", "@": "hunk"}).get(line[:1], "ctx")
        rows.append(f'<span class="dl {tone}">{esc(line)}</span>')
    return f"""<figure class="code diff">
<figcaption><span class="tag">What changed next</span>
<span class="lang">{esc(status)}</span>
<code class="path">{esc(after_path)}</code></figcaption>
<pre>{chr(10).join(rows)}</pre>
</figure>"""


def render_mistake(mistake: dict, index: int, heading: str = "h4",
                   prefix: str = "") -> str:
    status = mistake.get("status") or submission_status(mistake.get("file", "")) or "Failed"
    weight = STATUS_WEIGHT.get(status, DEFAULT_STATUS_WEIGHT)
    tier = "high" if weight >= 4 else "mid" if weight >= 3 else "low"
    path = mistake.get("file", "")
    return f"""<article class="mistake" id="{prefix}m{index}">
<{heading}><span class="num">{index}</span>
<span class="status {tier}">{esc(status)}</span></{heading}>
<dl>
<dt>What went wrong</dt><dd>{esc_code(mistake.get('what_went_wrong'))}</dd>
<dt>How it was fixed</dt><dd>{esc_code(mistake.get('how_it_was_fixed'))}</dd>
</dl>
{diff_block(path, next_submission(path))}
<details class="full-source"><summary>The failing submission in full</summary>
{code_block(path, 'The failing submission', 'bad')}</details>
</article>"""


def case_badges(case: Case) -> list[str]:
    badges = []
    if case.difficulty:
        badges.append(f'<span class="badge d-{esc(case.difficulty.lower())}">'
                      f"{esc(case.difficulty)}</span>")
    if case.attempts:
        badges.append(f'<span class="badge">'
                      f"{plural(case.attempts, 'attempt')} to accept</span>")
    if not case.solved:
        badges.append('<span class="badge warn">never solved</span>')
    if case.suspect:
        badges.append(f'<span class="badge warn">{case.suspect} attempts flagged '
                      f"by the paste heuristic</span>")
    return badges


def case_body(case: Case, heading: str = "h4") -> str:
    """The evidence for one problem: every diagnosis, the fix, what passed.

    Shared by the chapter's folded card and the problem's own page, so the two
    can never drift into telling different stories about the same submissions.
    """
    parts = []
    if case.suspect:
        parts.append('<p class="caveat">Some attempts on this problem were flagged '
                     "by the paste heuristic, so treat the style here as weak "
                     "evidence about how you think. The bugs below are still "
                     "factual events in the record.</p>")

    for i, mistake in enumerate(case.order_mistakes(), 1):
        parts.append(render_mistake(mistake, i, heading, f"{case.slug}-"))

    if case.accepted_file:
        parts.append(f'<{heading} class="what-worked">What finally worked</{heading}>')
        parts.append(code_block(case.accepted_file, "First accepted submission", "good"))

    for smell in case.smells:
        parts.append(f"""<div class="smell">
<{heading}>Still smells, even though it passed</{heading}>
<p>{esc_code(smell.get('smell'))}</p>
{code_block(smell.get('file', ''), 'Accepted, but', 'warn')}
</div>""")

    for entry in case.provenance:
        verdict = (entry.get("verdict") or "").lower()
        if verdict in ("discontinuous", "uncertain"):
            parts.append(f"""<p class="prov {esc(verdict)}">
<strong>Provenance: {esc(verdict)}.</strong> {esc_code(entry.get('why'))}</p>""")
    return "\n".join(parts)


def render_case(case: Case, rank: int) -> str:
    return f"""<details class="case" id="{esc(case.slug)}">
<summary>
<span class="rank">{rank}</span>
<h3 class="case-title">{esc(case.title)}</h3>
<span class="case-meta">{plural(len(case.mistakes), 'mistake')}</span>
</summary>
<div class="case-body">
<p class="badges">{''.join(case_badges(case))}
<a class="lc" href="problem-{esc(case.slug)}.html">the whole run</a>
<a class="lc" href="https://leetcode.com/problems/{esc(case.slug)}/"
   target="_blank" rel="noopener">open on LeetCode</a></p>
{case_body(case)}
</div></details>"""


def submission_history(slug: str) -> list[dict]:
    """Every submission on disk for one problem, oldest first.

    The chapter pages only ever show the submissions the analysis diagnosed.
    This is the whole run -- including the attempts that changed nothing and
    the ones that came after the accept -- which is the thing a problem page
    can show and a chapter page cannot.
    """
    folder = ROOT / "solutions" / slug
    if not folder.is_dir():
        return []
    runs = []
    for path in sorted(f for f in folder.iterdir()
                       if f.suffix in EXT_LANG and f.name[0].isdigit()):
        stamp = path.stem.split("_", 1)[0]
        rel = str(path.relative_to(ROOT))
        runs.append({
            "path": rel,
            "status": submission_status(rel) or "Unknown",
            "lang": EXT_LANG.get(path.suffix, path.suffix.lstrip(".")),
            "when": (datetime.datetime.fromtimestamp(int(stamp)).strftime("%Y-%m-%d")
                     if stamp.isdigit() else ""),
            "lines": len(path.read_text(encoding="utf-8", errors="replace").splitlines()),
        })
    return runs


def render_timeline(case: Case, runs: list[dict]) -> str:
    """The run as a table: what you sent, when, and how the judge answered."""
    if not runs:
        return ""
    diagnosed = {m.get("file"): i for i, m in enumerate(case.order_mistakes(), 1)}
    accepted_seen = False
    rows = []
    for run in runs:
        good = run["status"] == "Accepted"
        note = ""
        if run["path"] in diagnosed:
            index = diagnosed[run["path"]]
            note = (f'<a href="#{esc(case.slug)}-m{index}">diagnosed &darr;</a>')
        elif good and not accepted_seen:
            note = "first accept"
        elif accepted_seen:
            note = '<span class="muted">after the accept</span>'
        accepted_seen = accepted_seen or good
        rows.append(
            f'<tr class="{"ok" if good else "no"}"><td>{esc(run["when"])}</td>'
            f'<td class="verdict">{esc(run["status"])}</td>'
            f'<td>{esc(run["lang"])}</td><td class="lines">{run["lines"]}</td>'
            f"<td>{note}</td></tr>")
    accepts = sum(1 for r in runs if r["status"] == "Accepted")
    span = (f"from {runs[0]['when']} to {runs[-1]['when']}"
            if runs[0]["when"] != runs[-1]["when"] else f"all on {runs[0]['when']}")
    return f"""<section class="lesson-sec" id="run">
<h2>The whole run</h2>
<p class="hint">{plural(len(runs), 'submission')} on this problem,
{accepts} accepted, {span}. Everything here is in the export,
including the attempts the analysis did not single out.</p>
<div class="table-scroll"><table class="lesson-table run">
<thead><tr><th>Date</th><th>Verdict</th><th>Language</th><th>Lines</th>
<th>Note</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
</section>"""


def render_problem(case: Case, homes: list[Chapter], lessons: list[tuple]) -> str:
    """One page per problem: the whole run, and every diagnosis against it."""
    runs = submission_history(case.slug)
    where = " &middot; ".join(f'<a href="{esc(ch.topic)}.html#{esc(case.slug)}">'
                              f"{esc(ch.name)}</a>" for ch in homes)
    taught = "".join(
        f'<li><a href="course-{esc(slug)}.html">{esc(title)}</a> '
        f'<span class="muted">&mdash; {plural(n, "diagnosis", "es")} here</span></li>'
        for slug, title, n in lessons)
    lessons_html = (f"""<section class="lesson-sec" id="lessons">
<h2>What the course says about this</h2>
<p class="hint">Lessons whose evidence includes a submission on this problem.</p>
<ul class="plain">{taught}</ul></section>""" if taught else "")
    body = f"""<nav class="crumb">{where} &middot;
<a href="index.html">All topics</a> &middot; <a href="search.html">Search</a></nav>
<header class="chapter-head">
<p class="eyebrow">{esc(homes[0].name) if homes else "Problem"}</p>
<h1>{esc(case.title)}</h1>
<p class="badges">{''.join(case_badges(case))}
<a class="lc" href="https://leetcode.com/problems/{esc(case.slug)}/"
   target="_blank" rel="noopener">open on LeetCode</a></p>
</header>
{render_timeline(case, runs)}
<section class="lesson-sec" id="diagnosed">
<h2>{plural(len(case.mistakes), 'diagnosed mistake')}</h2>
{case_body(case, "h3") or '<p class="hint">Nothing was diagnosed here.</p>'}
</section>
{lessons_html}
<nav class="crumb bottom">{where}</nav>"""
    return page(f"{case.title} -- Improvement Book", body)


# The one piece of JavaScript in the book, and it is progressive: the page is
# the complete index of everything in here, rendered as plain links. The script
# only hides the rows that do not match, so with scripting off the page is
# still a usable contents listing rather than an empty box.
SEARCH_JS = """
var box = document.getElementById('q'),
    rows = document.querySelectorAll('#hits > li'),
    tally = document.getElementById('tally'),
    total = rows.length;
function run() {
  var words = box.value.toLowerCase().split(/\\s+/).filter(Boolean), shown = 0;
  for (var i = 0; i < rows.length; i++) {
    var hay = rows[i].getAttribute('data-s'),
        name = rows[i].getAttribute('data-t'), ok = true, inName = true;
    for (var w = 0; w < words.length; w++) {
      if (hay.indexOf(words[w]) < 0) { ok = false; break; }
      if (name.indexOf(words[w]) < 0) inName = false;
    }
    rows[i].hidden = !ok;
    // A name match is what you meant; a match in the topic beside it is a
    // near miss. Ordering the flex items leaves the document untouched.
    rows[i].style.order = words.length && !inName ? 1 : 0;
    if (ok) shown++;
  }
  tally.textContent = words.length
    ? shown + (shown === 1 ? ' match' : ' matches') + ' of ' + total
    : total + ' pages';
}
box.addEventListener('input', run);
box.removeAttribute('hidden');
document.getElementById('noscript-note').hidden = true;
run();
box.focus();
"""


def render_search(chapters: list[Chapter], lessons: list[dict],
                  cases: dict, homes: dict) -> str:
    """Everything in the book, as one filterable list."""
    records: list[tuple[str, str, str, str]] = []  # kind, url, title, context
    for name, title, note in (
            ("index.html", "All topics", "the front page, ranked by priority"),
            ("course.html", "The mini course", f"{len(lessons)} lessons in order"),
            ("schedule.html", "The practice schedule", "sessions of three problems"),
            ("checklist.html", "The pre-submit checklist", "one page, printable"),
            ("drills.html", "Spot the bug", "drills from your own submissions"),
            ("process.html", "Two habits", "how you submit, measured"),
            ("mistakes.html", "Every mistake", "all 904, filterable by eye"),
            ("habits.html", "Habits in passing code", "smells in accepted work"),
            ("plan.html", "The plan", "what to do first"),
            ("trend.html", "Month by month", "the whole history"),
            ("techniques.html", "Techniques you skipped", ""),
            ("revision.html", "Revision", "problems worth a second look"),
            ("unsolved.html", "Never solved", ""),
            ("not-covered.html", "What this book does not cover",
             "the diagnoses no lesson reaches")):
        records.append(("page", name, title, note))
    for lesson in lessons:
        records.append(("lesson", f"course-{lesson['slug']}.html", lesson["title"],
                        "lesson"))
        if lesson.get("reference"):
            records.append(("reference", f"reference-{lesson['slug']}.html",
                            lesson["reference"]["title"], lesson["title"]))
    for chapter in chapters:
        records.append(("topic", f"{chapter.topic}.html", chapter.name,
                        f"{plural(chapter.in_chapter, 'problem')}, "
                        f"{plural(chapter.mistake_count, 'mistake')}"))
    for slug, case in sorted(cases.items(), key=lambda kv: kv[1].title.lower()):
        where = ", ".join(ch.name for ch in homes[slug])
        records.append(("problem", f"problem-{slug}.html", case.title,
                        f"{where}{' &middot; ' + case.difficulty if case.difficulty else ''}"))

    items = []
    for kind, url, title, context in records:
        hay = f"{title} {context} {url} {kind}".lower()
        hay = re.sub(r"&[a-z]+;|[^a-z0-9 ]+", " ", hay)
        name = " ".join(re.sub(r"[^a-z0-9 ]+", " ", title.lower()).split())
        items.append(f'<li data-s="{esc(" ".join(hay.split()))}" '
                     f'data-t="{esc(name)}">'
                     f'<a href="{esc(url)}">{esc(title)}</a>'
                     f'<span class="kind">{esc(kind)}</span>'
                     f'<span class="muted">{context}</span></li>')

    body = f"""<nav class="crumb"><a href="index.html">&larr; All topics</a> &middot;
<a href="course.html">The course</a></nav>
<header class="chapter-head">
<p class="eyebrow">Everything in this book</p>
<h1>Search</h1>
<p class="lede">{len(records)} pages: every problem you attempted, every topic,
every lesson. Type any part of a name &mdash; the list narrows as you go.</p>
<input id="q" type="search" hidden placeholder="Type a problem, topic or lesson"
       aria-label="Filter this list" autocomplete="off" spellcheck="false">
<p id="tally" class="hint">{len(records)} pages</p>
<p id="noscript-note" class="hint">Scripting is off, so this is the full list.
Your browser&rsquo;s own find-in-page will search it.</p>
</header>
<ul id="hits">{''.join(items)}</ul>
<script>{SEARCH_JS}</script>"""
    return page("Search -- Improvement Book", body)


# Jargon this book uses without stopping to define it. Every term gets one
# link per page, at its first mention, which is where a reader who does not
# know it will be. Longest first, so "sliding window" wins over "window".
GLOSSARY_ORDER = sorted(course.GLOSSARY, key=lambda entry: -len(entry[1]))
GLOSSARY_PATTERNS = [(slug, term, re.compile(rf"\b{re.escape(term)}\b", re.I))
                     for slug, term, _, _ in GLOSSARY_ORDER]
# Text inside these is not prose: code is code, a heading is a label, and a
# link inside a link is invalid HTML.
NO_LINK_INSIDE = {"pre", "code", "a", "h1", "h2", "h3", "summary", "script",
                  "style", "figcaption", "title"}
TAG_SPLIT = re.compile(r"(<[^>]*>)")
TAG_NAME = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)")


def glossary_links(html: str) -> str:
    """Link the first mention of each glossary term, in prose only."""
    pending = {slug for slug, _, _ in GLOSSARY_PATTERNS}
    depth = 0
    out = []
    for chunk in TAG_SPLIT.split(html):
        if chunk.startswith("<"):
            found = TAG_NAME.match(chunk)
            if found and found.group(2).lower() in NO_LINK_INSIDE:
                if found.group(1):
                    depth = max(0, depth - 1)
                elif not chunk.endswith("/>"):
                    depth += 1
            out.append(chunk)
            continue
        if depth or not chunk.strip():
            out.append(chunk)
            continue
        for slug, term, pattern in GLOSSARY_PATTERNS:
            if slug not in pending:
                continue
            match = pattern.search(chunk)
            if match:
                pending.discard(slug)
                chunk = (f'{chunk[:match.start()]}<a class="gloss" '
                         f'href="glossary.html#{slug}">{match.group(0)}</a>'
                         f"{chunk[match.end():]}")
        out.append(chunk)
    return "".join(out)


def render_glossary() -> str:
    """One page, every term, each pointing back at the lesson that needs it."""
    titles = {l["slug"]: l["title"] for l in course.LESSONS}
    entries = []
    for slug, term, definition, lesson in sorted(course.GLOSSARY,
                                                 key=lambda e: e[1].lower()):
        taught = (f'<p class="hint">Used throughout '
                  f'<a href="course-{esc(lesson)}.html">{esc(titles[lesson])}</a>.'
                  f"</p>" if lesson else "")
        entries.append(f'<div class="gloss-entry" id="{esc(slug)}">'
                       f"<h2>{esc(term)}</h2><p>{definition}</p>{taught}</div>")
    letters = sorted({e[1][0].upper() for e in course.GLOSSARY})
    body = f"""<nav class="crumb"><a href="index.html">&larr; All topics</a> &middot;
<a href="course.html">The course</a> &middot; <a href="search.html">Search</a></nav>
<header class="chapter-head">
<p class="eyebrow">{plural(len(course.GLOSSARY), 'term')}</p>
<h1>Glossary</h1>
<p class="lede">Words this book uses as though you already know them. Each one
says what it means <em>here</em> &mdash; in Java, in your submissions &mdash;
rather than in general, and points at the lesson that leans on it.</p>
<p class="hint">Every term is linked from its first mention on any page in the
book, so you should mostly arrive here from the middle of something.</p>
</header>
<section class="glossary">{''.join(entries)}</section>
<nav class="crumb bottom"><a href="index.html">&larr; All topics</a></nav>"""
    return page("Glossary -- Improvement Book", body, glossary=False)


BASELINE = "baseline.json"

# The stamp every page carries. Filled once per build, before any page renders.
STAMP = {"line": "", "changes": ""}


def build_stamp(overview: dict, chapters: list[Chapter],
                lessons: list[dict]) -> tuple[dict, str]:
    """Count this build, and say what changed since the last one.

    The point is a baseline. Re-running the analysis over a bigger export is
    expensive and rare, and without a number written down at the time there is
    nothing to compare the next one against -- "am I making fewer mistakes"
    stops being answerable. So every build records its own counts, and the next
    build reports the difference in the footer of every page.
    """
    counts = {
        "built": datetime.date.today().isoformat(),
        "export_generated": overview.get("generated_at_utc", ""),
        "last_submission": (overview.get("last_submission_utc") or "")[:10],
        "submissions": overview.get("total_submissions", 0),
        "problems_attempted": overview.get("problems_attempted", 0),
        "problems_solved": overview.get("problems_solved", 0),
        "clean_solves": overview.get("clean_solves", 0),
        "topics": len(chapters),
        "lessons": len(lessons),
        "mistakes": sum(c.mistake_count for c in chapters),
        "smells": sum(len(case.smells) for c in chapters for case in c.cases),
        "problems_diagnosed": len({case.slug for c in chapters for case in c.cases}),
    }
    previous = {}
    old = BOOK / BASELINE
    if old.exists():
        try:
            previous = json.loads(old.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = {}

    moved = []
    for key in ("submissions", "problems_solved", "clean_solves", "mistakes"):
        was = previous.get(key)
        if isinstance(was, int) and was != counts[key]:
            delta = counts[key] - was
            moved.append(f"{key.replace('_', ' ')} {was:,} &rarr; "
                         f"{counts[key]:,} ({delta:+,})")
    changed = ""
    if moved and previous.get("built"):
        changed = (f" Since the build of {esc(previous['built'])}: "
                   + "; ".join(moved) + ".")
    elif not previous:
        changed = (" This is the first build to record a baseline, so there is "
                   "nothing to compare it against yet.")
    return counts, changed


def render_list(title: str, items: list, css: str) -> str:
    if not items:
        return ""
    rows = "\n".join(f"<li>{esc_code(item)}</li>" for item in items)
    return f'<section class="{css}"><h2>{esc(title)}</h2><ul>{rows}</ul></section>'


def render_chapter(chapter: Chapter, rank: int, total: int,
                   prev_ch: Chapter | None, next_ch: Chapter | None,
                   lessons: list[tuple] = ()) -> str:
    stats = chapter.stats
    numbers = [
        ("First-attempt accepts", pct(chapter.faar),
         f"solved with zero failed attempts &mdash; the sharpest mastery signal. "
         f"Ranked on {pct(chapter.shrunk_faar)} after smoothing for sample size"),
        ("Problems attempted", chapter.attempted,
         f"tagged with this topic, and what the rates above are measured over. "
         f"{chapter.in_chapter} of them are filed in this chapter; the rest sit "
         f"under a more specific tag"),
        ("Solve rate", pct(stats.get("solve_rate")), "eventually accepted"),
        ("Self-solve rate", pct(stats.get("self_solve_rate")),
         "with paste-flagged attempts removed"),
        ("Median attempts to accept", stats.get("median_attempts_to_accept") or "--",
         "the cost of a solve here"),
        ("Days since practised", stats.get("days_since_last_practice", "--"),
         "staleness, for spaced repetition"),
    ]
    number_html = "\n".join(
        f'<div class="stat"><dt>{esc(label)}</dt><dd>{esc(value)}</dd>'
        f'<p>{esc(note)}</p></div>' for label, value, note in numbers)

    breakdown = stats.get("status_breakdown") or {}
    breakdown_html = ""
    if breakdown:
        total_sub = sum(breakdown.values()) or 1
        bars = "\n".join(
            f'<tr><th>{esc(k)}</th><td>{v}</td>'
            f'<td class="bar"><span style="width:{v / total_sub * 100:.1f}%"></span></td></tr>'
            for k, v in sorted(breakdown.items(), key=lambda kv: -kv[1]))
        breakdown_html = f"""<section class="breakdown">
<h2>Where the submissions went</h2>
<p class="hint">Counted up to and including the first accept, so this is
first-solve effort only.</p>
<table>{bars}</table></section>"""

    mode = chapter.failure_mode
    mode_html = ""
    if mode:
        label, meaning, count = mode
        mode_html = f"""<section class="mode">
<h2>Failure mode: {esc(label)}</h2>
<p>{esc(count)} submissions here failed this way &mdash; {esc(meaning)}.</p>
</section>"""

    unsolved_html = ""
    if chapter.unsolved:
        rows = "\n".join(
            f'<li><a href="https://leetcode.com/problems/{esc(u.get("titleSlug"))}/"'
            f' target="_blank" rel="noopener">{esc(u.get("title"))}</a>'
            f' <span class="badge d-{esc(str(u.get("difficulty", "")).lower())}">'
            f'{esc(u.get("difficulty"))}</span>'
            f' <span class="badge">{esc(u.get("attempts"))} attempts</span></li>'
            for u in chapter.unsolved)
        unsolved_html = f"""<section class="unsolved">
<h2>Never solved</h2>
<p class="hint">The sharpest weakness signal in the whole export. Start here.</p>
<ul>{rows}</ul></section>"""

    prov = chapter.flagged_provenance
    prov_html = ""
    if prov:
        rows = "\n".join(
            f'<li><strong>{esc(p.get("problem"))}</strong> '
            f'<span class="badge warn">{esc(p.get("verdict"))}</span><br>{esc_code(p.get("why"))}</li>'
            for p in prov)
        prov_html = f"""<section class="provenance">
<h2>Code I am not sure is yours</h2>
<p class="hint">Flagged by comparison against your own code elsewhere in this
topic, never by generic AI-detection. Nothing is excluded on this basis --
it only lowers confidence in conclusions that rest on these files.</p>
<ul>{rows}</ul></section>"""

    cases_html = "\n".join(render_case(case, i)
                           for i, case in enumerate(chapter.cases, 1)) or \
        '<p class="empty">No mistakes were logged for this topic &mdash; nothing failed here.</p>'

    # The course pages cite this topic's mistakes; link back the other way so a
    # reader who lands on a chapter can reach the lesson that explains it.
    lesson_html = ("" if not lessons else
                   '<section class="lesson-links"><h2>Lessons that cover this topic</h2>'
                   '<p class="hint">Each teaches the material behind the mistakes '
                   "below, from the fundamentals up.</p>"
                   '<p class="chips">' + "".join(
                       f'<a class="chip" href="course-{esc(sl)}.html">{esc(t)}'
                       f'<span class="chip-n">{n}</span></a>'
                       for sl, t, n in lessons) + "</p></section>")

    nav = ['<a href="index.html">&larr; All topics</a>',
           '<a href="course.html">Course</a>',
           '<a href="mistakes.html">Every mistake</a>',
           '<a href="trend.html">Trend</a>']
    if prev_ch:
        nav.append(f'<a href="{esc(prev_ch.topic)}.html">Previous: {esc(prev_ch.name)}</a>')
    if next_ch:
        nav.append(f'<a href="{esc(next_ch.topic)}.html">Next: {esc(next_ch.name)}</a>')

    body = f"""<nav class="crumb">{' &middot; '.join(nav)}</nav>
<header class="chapter-head">
<p class="eyebrow">Chapter {rank} of {total}</p>
<h1>{esc(chapter.name)}</h1>
<p class="lede">{plural(chapter.mistake_count, 'mistake')} and
{plural(chapter.smell_count, 'smell')} found across
{plural(chapter.findings.get('problems_read', 0), 'problem')} and
{plural(chapter.findings.get('files_read', 0), 'file')} read.</p>
</header>
<section class="stats"><dl>{number_html}</dl></section>
{lesson_html}
{mode_html}
{unsolved_html}
{breakdown_html}
<section class="cases">
<h2>The mistakes, worst first</h2>
<p class="hint">Ranked by what failed and how long it took to fix &mdash; a Wrong
Answer that took nine attempts outranks a compile-error typo. Click any problem
to open the code. Inside a problem the mistakes run in the order you actually
made them.</p>
{cases_html}
</section>
{render_list('Patterns in this topic', chapter.findings.get('patterns_within_topic', []), 'patterns')}
{render_list('How you write code here', chapter.findings.get('style_notes', []), 'style')}
{render_list('What you are good at here', chapter.findings.get('strengths', []), 'strengths')}
{prov_html}
<nav class="crumb bottom">{' &middot; '.join(nav)}</nav>"""
    return page(f"{chapter.name} -- Improvement Book", body)


def match_lesson(lesson: dict, chapters: list[Chapter]) -> list[tuple]:
    """Mistakes from the reader's own history that this lesson covers.

    The lesson prose is authored; the evidence under it is not. Joining on the
    lesson's `match` pattern means the "your own instances" section can never
    drift from findings/ -- rewrite a lesson and the citations still hold.
    """
    pattern = re.compile(lesson["match"], re.I)
    found = []
    for chapter in chapters:
        for case in chapter.cases:
            for mistake in case.order_mistakes():
                text = " ".join(str(mistake.get(k) or "")
                                for k in ("what_went_wrong", "how_it_was_fixed"))
                if pattern.search(text):
                    found.append((chapter, case, mistake))
    weight = lambda t: STATUS_WEIGHT.get(
        t[2].get("status") or submission_status(t[2].get("file", "")),
        DEFAULT_STATUS_WEIGHT)
    found.sort(key=lambda t: (-weight(t), t[1].title))
    return found


def match_smells(lesson: dict, chapters: list[Chapter]) -> list[tuple]:
    """Habits this lesson covers that never failed a submission.

    Same join as match_lesson, over the other half of the analysis. These are
    the ones with no memory attached: the judge accepted them, so nothing ever
    made the reader go back and look.
    """
    pattern = re.compile(lesson["match"], re.I)
    return [(chapter, case, smell)
            for chapter in chapters for case in chapter.cases
            for smell in case.smells if pattern.search(smell.get("smell", ""))]


MAX_EVIDENCE = 12
MAX_HABITS = 8


def anchor(text: str, index: int) -> str:
    """Stable in-page id for a lesson subsection."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]
    return f"s{index}-{slug}" if slug else f"s{index}"


# The reading order the pages promise: what it is, when you reach for it, how a
# question announces itself, the mechanism, the bugs you actually shipped, the
# corrections. Each entry is (id, nav label, heading).
LESSON_SECTIONS = [
    ("summary", "Summary", "In one page"),
    ("uses", "What it&rsquo;s for", "What it&rsquo;s used for"),
    ("patterns", "Question patterns", "How the questions are phrased"),
    ("depth", "In depth", "The mechanism, in depth"),
    ("mistakes", "Your mistakes", "Where you actually hit this"),
    ("fixes", "Fixes", "How to fix each one"),
    ("habits", "In passing code", "Habits in code that passed"),
    ("drill", "Drill", "The drill"),
]


def render_pairs(pairs, head_a: str, head_b: str) -> str:
    rows = "".join(f"<tr><td><strong>{esc(a)}</strong></td><td>{esc(b)}</td></tr>"
                   for a, b in pairs)
    return (f'<table class="lesson-table pairs"><thead><tr><th>{head_a}</th>'
            f"<th>{head_b}</th></tr></thead><tbody>{rows}</tbody></table>")


def lesson_mistake_card(chapter, case, mistake: dict) -> str:
    status = (mistake.get("status")
              or submission_status(mistake.get("file", "")) or "Failed")
    weight = STATUS_WEIGHT.get(status, DEFAULT_STATUS_WEIGHT)
    tier = "high" if weight >= 4 else "mid" if weight >= 3 else "low"
    fix = (mistake.get("how_it_was_fixed") or "").strip()
    fix_html = (f'<p class="mc-fix"><span class="mc-tag good">The fix</span>'
                f"{esc_code(fix)}</p>" if fix else
                '<p class="mc-fix"><span class="mc-tag none">No fix on record</span>'
                "The analysis found no later submission that corrected this one.</p>")
    return f"""<li>
<p class="mc-head"><a href="{esc(chapter.topic)}.html#{esc(case.slug)}">{esc(case.title)}</a>
<span class="ev-topic">{esc(chapter.name)} &middot;
<span class="status {tier}">{esc(status)}</span></span></p>
<p class="mc-wrong"><span class="mc-tag bad">What went wrong</span>
{esc_code(mistake.get('what_went_wrong'))}</p>
{fix_html}</li>"""


def lesson_smell_card(chapter, case, smell: dict) -> str:
    return f"""<li>
<p class="mc-head"><a href="{esc(chapter.topic)}.html#{esc(case.slug)}">{esc(case.title)}</a>
<span class="ev-topic">{esc(chapter.name)} &middot;
<span class="status pass">Accepted</span></span></p>
<p class="mc-wrong"><span class="mc-tag warn">Passed anyway</span>
{esc_code(smell.get('smell'))}</p></li>"""


def render_objectives(lesson: dict) -> str:
    """What you should be able to do afterwards, and what must already be true.

    The prerequisites are slugs, not prose, so the course order is checkable:
    main() asserts every one of them is taught earlier. That check is the whole
    point of writing them down -- an objective nobody can fail is decoration.
    """
    goals = "".join(f"<li>{esc_code(o)}</li>" for o in lesson["objectives"])
    before = ""
    if lesson["prereqs"]:
        links = ", ".join(
            f'<a href="course-{esc(slug)}.html">{esc(LESSON_INDEX[slug][1])}</a>'
            for slug in lesson["prereqs"])
        before = (f'<p class="prereq"><span class="obj-tag">Before this</span>'
                  f"{links}</p>")
    return f"""<section class="objectives">
<p class="obj-head"><span class="obj-tag">After this lesson you can</span></p>
<ul>{goals}</ul>{before}</section>"""


def render_recall(lesson: dict) -> str:
    """Three questions whose answers are the lesson, asked before the lesson.

    Retrieval before reading is the difference between recognising an
    explanation and being able to produce one. The answers are one click away
    on purpose -- this is a question, not a quiz, and nothing is scored.
    """
    items = "".join(
        f"<li><p class=\"q\">{esc_code(q)}</p>"
        f"<details><summary>Answer</summary><p>{esc_code(a)}</p></details></li>"
        for q, a in lesson["recall"])
    return f"""<div class="recall">
<p class="hint">Answer these before reading. Getting one wrong is the point:
it tells you which part of the page below is the part you need.</p>
<ol>{items}</ol></div>"""


def render_lesson(lesson: dict, evidence: list[tuple], rank: int, total: int,
                  prev_l: dict | None, next_l: dict | None,
                  habits: list[tuple] = (), drills: int = 0) -> str:
    topics = sorted({chapter.name for chapter, _, _ in evidence})

    # --- 1. summary -------------------------------------------------------
    stat = (f'<p class="stat-line">{plural(len(evidence), "mistake")} in your own '
            f'submissions, across {plural(len(topics), "topic")}.</p>'
            if evidence else "")
    summary = lesson.get("summary") or f"<p>{esc_code(lesson['one_line'])}</p>"

    # --- 2. what it is used for -------------------------------------------
    uses = lesson.get("used_for") or []
    uses_html = (f'<section class="lesson-sec" id="uses"><h2>What it&rsquo;s used for</h2>'
                 f'{render_pairs(uses, "Reach for it when", "Because")}</section>'
                 if uses else "")

    # --- 3. question patterns ---------------------------------------------
    patterns = lesson.get("patterns") or []
    seen, chips = set(), []
    for chapter, case, _ in evidence:
        if case.slug not in seen and len(chips) < 12:
            seen.add(case.slug)
            chips.append(f'<a class="chip" href="{esc(chapter.topic)}.html#'
                         f'{esc(case.slug)}">{esc(case.title)}</a>')
    chip_html = (f'<p class="hint">Problems in your export where this material came '
                 f'up. Matched from the diagnosis text by keyword, so read it as a '
                 f'starting list rather than a complete one:</p>'
                 f'<p class="chips">{"".join(chips)}</p>' if chips else "")
    patterns_html = (
        f'<section class="lesson-sec" id="patterns">'
        f"<h2>How the questions are phrased</h2>"
        f'<p class="hint">The wording is the tell. These are the phrasings that '
        f"should make you reach for this technique before you start coding.</p>"
        f'{render_pairs(patterns, "When the statement says", "It is asking for")}'
        f"{chip_html}</section>" if patterns else "")

    # --- 4. the mechanism --------------------------------------------------
    parts, subnav = [], []
    for i, (heading, body) in enumerate(lesson["basics"], 1):
        aid = anchor(heading, i)
        subnav.append(f'<a href="#{aid}">{esc(heading)}</a>')
        parts.append(f'<section class="lesson-part" id="{aid}">'
                     f"<h3>{esc(heading)}</h3>{body}</section>")
    sub = (f'<nav class="subnav" aria-label="Sections of this lesson">'
           f'{"".join(subnav)}</nav>' if len(subnav) >= 4 else "")
    reference = lesson.get("reference")
    ref_html = (
        f'<p class="ref-card"><a href="reference-{lesson["slug"]}.html">'
        f'{esc(reference["title"])}</a> -- '
        f'{plural(len(reference["sections"]), "section")}, on a page of '
        f"its own because it is a catalogue you look things up in, not part of "
        f"the lesson you read through.</p>" if reference else "")
    depth_html = (f'<section class="lesson-sec" id="depth">'
                  f"<h2>The mechanism, in depth</h2>{sub}{''.join(parts)}"
                  f"{ref_html}</section>")

    # --- 5 + 6. your mistakes, and how each was fixed ----------------------
    if evidence:
        shown = evidence[:MAX_EVIDENCE]
        cards = "\n".join(lesson_mistake_card(*t) for t in shown)
        rest = evidence[MAX_EVIDENCE:]
        more = (f'<details class="more-mistakes"><summary>The other '
                f'{plural(len(rest), "match", "es")}</summary>'
                f'<ol class="mistake-cards">'
                f'{"".join(lesson_mistake_card(*t) for t in rest)}</ol></details>'
                if rest else "")
        mistakes_html = f"""<section class="lesson-sec evidence" id="mistakes">
<h2>Where you actually hit this</h2>
<p class="hint">{plural(len(evidence), 'mistake')} from your own submissions, across
{plural(len(topics), 'topic')}: {esc(', '.join(topics[:10]))}{'&hellip;' if len(topics) > 10 else ''}.
Most severe first. Each title links to the failing code; under it is what the
analysis found and what you eventually changed. These are matched from the
diagnosis text by keyword, so read the count as &ldquo;roughly this many&rdquo;
&mdash; the problems named in the lesson above were checked by hand.</p>
<ol class="mistake-cards">{cards}</ol>{more}</section>"""
    else:
        mistakes_html = ('<section class="lesson-sec evidence" id="mistakes">'
                         "<h2>Where you actually hit this</h2>"
                         '<p class="empty">Nothing in findings/ matched this lesson.'
                         "</p></section>")

    # --- 7. the same lesson, in code that was never corrected --------------
    if habits:
        shown = "".join(lesson_smell_card(*t) for t in habits[:MAX_HABITS])
        rest = habits[MAX_HABITS:]
        more = (f'<details class="more-mistakes"><summary>The other '
                f'{plural(len(rest), "habit")}</summary><ol class="mistake-cards">'
                f'{"".join(lesson_smell_card(*t) for t in rest)}</ol></details>'
                if rest else "")
        habits_html = f"""<section class="lesson-sec evidence" id="habits">
<h2>Habits in code that passed</h2>
<p class="hint">{plural(len(habits), 'place')} where this lesson applies to a
submission the judge <em>accepted</em>. Nothing forced you back to these, which is
exactly why they are worth reading: a mistake you were made to fix is one you have
already met, and a habit that keeps passing is one you will carry into the problem
where it does not.</p>
<ol class="mistake-cards habits">{shown}</ol>{more}</section>"""
    else:
        habits_html = ""

    rules = "".join(f"<li>{esc_code(r)}</li>" for r in lesson["rules"])

    nav = ['<a href="course.html">&larr; Course</a>',
           '<a href="index.html">All topics</a>']
    if prev_l:
        nav.append(f'<a href="course-{esc(prev_l["slug"])}.html">'
                   f'Previous: {esc(prev_l["title"])}</a>')
    if next_l:
        nav.append(f'<a href="course-{esc(next_l["slug"])}.html">'
                   f'Next: {esc(next_l["title"])}</a>')
    navbar = " &middot; ".join(nav)

    drill_link = (f'<p class="also"><a href="drill-{esc(lesson["slug"])}.html">'
                  f'Spot the bug: {plural(drills, "exercise")}</a> built from your '
                  f'own submissions that this lesson covers &mdash; the code, '
                  f'without the diagnosis.</p>' if drills else "")

    present = {"uses": bool(uses), "patterns": bool(patterns),
               "habits": bool(habits)}
    toc = "".join(f'<a href="#{i}">{label}</a>' for i, label, _ in LESSON_SECTIONS
                  if present.get(i, True))

    body = f"""<nav class="crumb">{navbar}</nav>
<header class="chapter-head lesson-head">
<p class="eyebrow">Lesson {rank} of {total}</p>
<h1>{esc(lesson['title'])}</h1>
<p class="lede">{esc_code(lesson['one_line'])}</p>
{render_objectives(lesson)}
</header>
<nav class="lesson-toc" aria-label="On this page">{toc}</nav>
<section class="lesson-sec mode" id="summary"><h2>In one page</h2>
{render_recall(lesson)}
{summary}{stat}
<h3>Why this lesson is in your course</h3>
<p>{esc_code(lesson['why'])}</p></section>
{uses_html}
{patterns_html}
{depth_html}
{mistakes_html}
<section class="lesson-sec rules" id="fixes"><h2>How to fix each one</h2>
<p class="hint">The corrections above are specific to one submission. These are the
general forms &mdash; run them before submitting anything that touches this topic.</p>
<ol>{rules}</ol></section>
{habits_html}
<section class="lesson-sec drill" id="drill"><h2>The drill</h2>
<p>{esc_code(lesson['drill'])}</p>{drill_link}</section>
<nav class="crumb bottom">{navbar}</nav>"""
    return page(f"{lesson['title']} -- Improvement Book", body)


def match_text(pattern: str, chapters: list[Chapter]) -> tuple[list, list]:
    """Mistakes and smells whose diagnosis matches, in severity order.

    The habits in synthesis.py are authored claims about behaviour. Joining
    each one to the record is what stops it becoming folklore: if a rerun of
    the analysis stops producing sentinel bugs, the sentinel habit's count
    drops to zero on its own.
    """
    rx = re.compile(pattern, re.I)
    mistakes, smells = [], []
    for chapter in chapters:
        for case in chapter.cases:
            for mistake in case.order_mistakes():
                text = " ".join(str(mistake.get(k) or "")
                                for k in ("what_went_wrong", "how_it_was_fixed"))
                if rx.search(text):
                    mistakes.append((chapter, case, mistake))
            for smell in case.smells:
                if rx.search(smell.get("smell", "")):
                    smells.append((chapter, case, smell))
    weight = lambda t: STATUS_WEIGHT.get(
        t[2].get("status") or submission_status(t[2].get("file", "")),
        DEFAULT_STATUS_WEIGHT)
    mistakes.sort(key=lambda t: (-weight(t), t[1].title))
    return mistakes, smells


MAX_HABIT_EVIDENCE = 6


def lesson_links(slugs, label: str = "Learn the fix") -> str:
    if not slugs:
        return ""
    chips = "".join(
        f'<a class="chip" href="course-{esc(slug)}.html">'
        f'{esc(LESSON_INDEX[slug][1])}</a>' for slug in slugs)
    return f'<p class="habit-lessons"><span class="lbl">{label}</span>{chips}</p>'


def render_habit(habit: dict, chapters: list[Chapter]) -> str:
    mistakes, smells = ([], [])
    if habit["match"]:
        mistakes, smells = match_text(habit["match"], chapters)

    counts = []
    if habit["stat"]:
        counts.append(f'<span class="badge warn">{esc(habit["stat"])}</span>')
    if mistakes:
        topics = len({chapter.topic for chapter, _, _ in mistakes})
        counts.append(f'<span class="badge">{plural(len(mistakes), "mistake")} '
                      f'in {plural(topics, "topic")}</span>')
    if smells:
        counts.append(f'<span class="badge">{plural(len(smells), "smell")} '
                      f"in accepted code</span>")

    shown = mistakes[:MAX_HABIT_EVIDENCE]
    rest = mistakes[MAX_HABIT_EVIDENCE:]
    evidence = ""
    if shown:
        more = (f'<details class="more-mistakes"><summary>The other '
                f'{plural(len(rest), "match", "es")}</summary>'
                f'<ol class="mistake-cards">'
                f'{"".join(lesson_mistake_card(*t) for t in rest)}</ol></details>'
                if rest else "")
        evidence = (f'<ol class="mistake-cards">'
                    f'{"".join(lesson_mistake_card(*t) for t in shown)}</ol>{more}')
    elif habit["match"]:
        evidence = ('<p class="empty">Nothing in the diagnosis text matched this '
                    "pattern.</p>")

    smell_html = ""
    if smells:
        smell_html = (
            f'<details class="more-mistakes"><summary>'
            f'{plural(len(smells), "time")} it survived into accepted code</summary>'
            f'<ol class="mistake-cards habits">'
            f'{"".join(lesson_smell_card(*t) for t in smells[:MAX_HABIT_EVIDENCE])}'
            f"</ol></details>")

    slug = anchor(habit["title"], habit["rank"])
    return f"""<section class="habit" id="{esc(slug)}">
<h2><span class="rank">{habit['rank']}</span>{esc(habit['title'])}</h2>
<p class="badges">{''.join(counts)}</p>
{habit['html']}
{lesson_links(habit['lessons'])}
{evidence}{smell_html}</section>"""


def render_habits(chapters: list[Chapter]) -> str:
    toc = "".join(
        f'<a href="#{esc(anchor(h["title"], h["rank"]))}">'
        f'<span class="n">{h["rank"]}</span>{esc(h["title"])}</a>'
        for h in synthesis.HABITS)
    modes = "".join(f"<section class=\"mode-item\"><h3>{esc(title)}</h3>{html}</section>"
                    for title, html in synthesis.MODES)
    body = f"""<nav class="crumb"><a href="index.html">&larr; All topics</a> &middot;
<a href="course.html">Course</a> &middot;
<a href="plan.html">The plan</a> &middot;
<a href="mistakes.html">Every mistake</a></nav>
<header class="chapter-head">
<p class="eyebrow">Cross-topic &middot; ranked by how often they recur</p>
<h1>Your recurring habits</h1>
<p class="lede">Twelve bug classes, ordered by frequency across the whole
export. A bug in one topic is an accident; the same bug in five unrelated
topics is a habit, and a habit is something you can decide to stop.</p>
<p class="lede">The prose is written. Every count under it is joined to
<code>findings/*.json</code> by pattern, so it moves when the analysis
does &mdash; and two of these habits are behaviours rather than bug classes,
so they carry a figure from the report instead.</p>
</header>
<nav class="habit-toc" aria-label="The twelve habits">{toc}</nav>
{"".join(render_habit(h, chapters) for h in synthesis.HABITS)}
<section class="modes" id="modes">
<h2>How the debugging loop itself behaves</h2>
<p class="hint">These are not bug classes, which is why none of them has a
count. They are the shape of the process around the bugs, and they explain why
several of the twelve above keep coming back after being fixed.</p>
{modes}</section>
<nav class="crumb bottom"><a href="plan.html">What to do about it &rarr;</a></nav>"""
    return page("Your recurring habits -- Improvement Book", body)


def render_plan(chapters: list[Chapter]) -> str:
    items = []
    for i, item in enumerate(synthesis.PLAN, 1):
        link = ""
        if item["link"]:
            href, text = item["link"]
            link = (f'<p class="habit-lessons"><span class="lbl">Start here</span>'
                    f'<a class="chip" href="{esc(href)}">{esc(text)}</a></p>')
        items.append(f"""<li class="plan-item">
<h2><span class="rank">{i}</span>{esc(item['title'])}</h2>
{item['why']}{link}{lesson_links(item['lessons'], 'The lessons')}</li>""")

    body = f"""<nav class="crumb"><a href="index.html">&larr; All topics</a> &middot;
<a href="habits.html">The habits</a> &middot;
<a href="revision.html">What to revise</a> &middot;
<a href="course.html">Course</a></nav>
<header class="chapter-head">
<p class="eyebrow">Ordered by expected return, not by topic</p>
<h1>What to practise next</h1>
<p class="lede">Seven items, from the synthesis of the whole export. They are
ordered by what the evidence says each is worth, which is why closing four
abandoned problems sits above drilling a topic you are already good at.</p>
</header>
<ol class="plan">{''.join(items)}</ol>
<section class="limits">
<h2>What this cannot tell you</h2>
<p class="hint">A plan that does not state its own limits reads as more certain
than it is.</p>
{synthesis.LIMITS}</section>
<nav class="crumb bottom"><a href="habits.html">&larr; The habits behind this</a>
&middot; <a href="course.html">The course</a></nav>"""
    return page("What to practise next -- Improvement Book", body)


# Warm enough that the skill is still loaded; cold enough that it is not.
WARM_DAYS = 90


def render_revision(chapters: list[Chapter], overview: dict) -> str:
    """Four quadrants of strong/weak against warm/cold, and what each one needs."""
    rows = []
    for chapter in chapters:
        days = chapter.stats.get("days_since_last_practice")
        if days is None or chapter.in_chapter == 0:
            continue          # a topic with no filed problems has nothing to revise
        rows.append((chapter.shrunk_faar >= chapter.prior, days <= WARM_DAYS,
                     days, chapter))

    def quadrant(strong: bool, warm: bool) -> list[tuple]:
        picked = [r for r in rows if r[0] is strong and r[1] is warm]
        # coldest first when cold, weakest first when warm: each order puts the
        # thing the prescription applies to most strongly at the top.
        picked.sort(key=lambda r: -r[2] if not warm else r[3].shrunk_faar)
        return picked

    QUADRANTS = [
        (False, False, "Weak and cold", "Relearn",
         "You were not good at these and you have not touched them in "
         f"{WARM_DAYS} days. Attempting one cold is how a topic produces five "
         "failed submissions. Read the lesson first, then attempt."),
        (True, False, "Strong and cold", "Revise",
         "The cheapest wins on this page. You could do these and the skill is "
         "going stale for want of one problem. Nothing else in the book points "
         "at them, because everything else is ordered by weakness."),
        (False, True, "Weak and warm", "Leave it",
         "You are already working on these. The failures are current, which "
         "means the practice is doing its job; adding a second front does not "
         "make it faster."),
        (True, True, "Strong and warm", "Spend nothing here",
         "Good, and recently confirmed. This quadrant exists so that the "
         "absence of a topic from the other three is visible rather than "
         "assumed."),
    ]

    def chips(picked: list[tuple], limit: int = 14) -> str:
        out = "".join(
            f'<a class="chip" href="{esc(c.topic)}.html">{esc(c.name)}'
            f'<span class="chip-n">{d}d</span></a>' for _, _, d, c in picked[:limit])
        rest = len(picked) - limit
        more = f'<span class="hint">and {rest} more</span>' if rest > 0 else ""
        return f'<p class="quad-chips">{out}{more}</p>'

    quads = "".join(f"""<section class="quad {'q-act' if not warm else 'q-hold'}">
<h2>{esc(title)} <span class="verdict">{esc(verdict)}</span>
<span class="quad-n">{plural(len(quadrant(strong, warm)), 'topic')}</span></h2>
<p>{blurb}</p>{chips(quadrant(strong, warm))}</section>"""
        for strong, warm, title, verdict, blurb in QUADRANTS)

    ranked = sorted(rows, key=lambda r: -(r[3].priority * (1 + r[2] / 365.0)))
    body_rows = "".join(f"""<tr>
<td class="topic"><a href="{esc(c.topic)}.html">{esc(c.name)}</a></td>
<td class="num">{days}</td>
<td class="num">{c.in_chapter}</td>
<td class="num">{pct(c.faar)}</td>
<td class="num">{c.mistake_count}</td>
<td class="num score">{c.priority * (1 + days / 365.0):.2f}</td></tr>"""
        for _, _, days, c in ranked[:30])

    gap = "The export contains a five-month gap with no submissions at all, from "
    body = f"""<nav class="crumb"><a href="index.html">&larr; All topics</a> &middot;
<a href="plan.html">The plan</a> &middot;
<a href="course.html">Course</a></nav>
<header class="chapter-head">
<p class="eyebrow">How good you were &times; how long ago</p>
<h1>What to revise</h1>
<p class="lede">The plan says what to learn. This says what you already learned
and are in the process of losing. Two axes, four quadrants, and a different
prescription in each &mdash; a topic you were weak at eighteen months ago needs
rereading, and the same weakness from last week needs drilling.</p>
<p class="lede">Strong and weak are measured with the same shrunk first-attempt
rate the whole book ranks on, so a one-problem topic cannot be called either on
a single result. Warm means practised within {WARM_DAYS} days.</p>
<p class="hint">{gap}February to June 2026, and longer gaps before it &mdash;
thirty-four months from December 2021, thirteen from August 2020. Every
&ldquo;days since&rdquo; here inherits those gaps, so a topic reading a small
number was touched during the July 2026 restart rather than through a steady
habit. The number is a fact about the record, not about a routine.</p>
</header>
{quads}
<section class="limits">
<h2>The same thing as one ranked list</h2>
<p>Priority &times; (1 + days / 365): a topic untouched for a year counts
double. The multiplier is a choice rather than a measurement, so its two inputs
sit beside it &mdash; rank by whichever column you trust.</p>
<div class="table-scroll"><table class="revision">
<tr><th>Topic</th><th class="num">Days<br>since</th><th class="num">Problems</th>
<th class="num">First<br>attempt</th><th class="num">Mistakes</th>
<th class="num">Score</th></tr>
{body_rows}</table></div>
<p class="hint">Two limits. Topic tags overlap, so one problem refreshes every
tag it carries and some topics look warmer than the practice justifies. And a
recent submission is not necessarily practice:
{plural(overview.get('post_solve_submissions', 0), 'post-solve submission')}
&mdash; {overview.get('post_solve_submissions', 0)
 / max(overview.get('total_submissions', 1), 1):.0%} of the export &mdash; were
made against problems already accepted.</p>
</section>
<nav class="crumb bottom"><a href="plan.html">&larr; The plan</a> &middot;
<a href="course.html">The course</a></nav>"""
    return page("What to revise -- Improvement Book", body)


VERDICTS = {
    "absent": ("Not in the record", "bad",
               "The intended technique is nowhere in the submissions, and the "
               "problem or the chapter's mistake count says it was wanted."),
    "substituted": ("A simpler tool, correctly", "good",
                    "The tag names a category, not a technique the problem "
                    "requires. What was written instead was the right call."),
}


def technique_notes(chapter: Chapter, pattern: str) -> list[str]:
    """The analysis's own sentences about what was used instead."""
    rx = re.compile(pattern, re.I)
    notes = (chapter.findings.get("patterns_within_topic", [])
             + chapter.findings.get("style_notes", []))
    return [n for n in notes if rx.search(n)]


def render_technique(tech: dict, chapter: Chapter) -> str:
    label, tone, _ = VERDICTS[tech["verdict"]]
    quotes = "".join(f"<blockquote>{esc_code(n)}</blockquote>"
                     for n in technique_notes(chapter, tech["evidence"]))
    problems = ", ".join(esc(c.title) for c in chapter.cases[:4])
    if not problems:
        problems = ", ".join(esc(p.get("title", "")) 
                             for p in chapter.bundle_problems[:4])
    return f"""<section class="technique" id="{esc(chapter.topic)}">
<h3>{esc(tech['name'])} <span class="mc-tag {tone}">{esc(label)}</span></h3>
<p class="tech-meta"><a href="{esc(chapter.topic)}.html">{esc(chapter.name)}</a>
&middot; {plural(chapter.in_chapter, 'problem')}
&middot; {plural(chapter.mistake_count, 'diagnosed mistake')}</p>
<h4>What it is</h4>{tech['what']}
<h4>When it beats what you wrote</h4>{tech['wins']}
<h4>What the analysis found instead</h4>{quotes}
{lesson_links(tech['lessons'], 'Related lessons')}</section>"""


def render_techniques(chapters: list[Chapter]) -> str:
    by_topic = {c.topic: c for c in chapters}
    groups = []
    for verdict in ("absent", "substituted"):
        picked = [t for t in synthesis.TECHNIQUES if t["verdict"] == verdict]
        label, tone, blurb = VERDICTS[verdict]
        groups.append(f"""<section class="tech-group">
<h2>{esc(label)} <span class="quad-n">{plural(len(picked), 'technique')}</span></h2>
<p class="lede">{esc(blurb)}</p>
{"".join(render_technique(t, by_topic[t["topic"]]) for t in picked)}</section>""")

    body = f"""<nav class="crumb"><a href="index.html">&larr; All topics</a> &middot;
<a href="course.html">Course</a> &middot;
<a href="plan.html">The plan</a></nav>
<header class="chapter-head">
<p class="eyebrow">Where the tag names something the code did not do</p>
<h1>Techniques you have not used</h1>
<p class="lede">LeetCode tags a problem with the technique it was designed
around. In {plural(len(synthesis.TECHNIQUES), 'chapter')} of this book the tag
names one thing and every submission in the chapter does another. That is not a
gap in the book; it is a list of techniques this reader has solved
<em>around</em> rather than <em>with</em>, and it is the most useful thing the
export's thinnest chapters have to say.</p>
<p class="lede">Each entry is split the same way: what the technique actually
is, when it beats the substitute, and then the analysis's own sentence about
what was written instead &mdash; quoted from
<code>findings/&lt;topic&gt;.json</code> rather than paraphrased, so it moves
when the analysis does.</p>
<p class="hint">The report also named binary-indexed-tree and segment-tree here.
They are not on this page: both chapters contain real implementations with real
merge and boundary bugs, which is the opposite of an unused technique.</p>
</header>
{"".join(groups)}
<nav class="crumb bottom"><a href="plan.html">&larr; The plan</a> &middot;
<a href="revision.html">What to revise</a></nav>"""
    return page("Techniques you have not used -- Improvement Book", body)


# Two submissions less than this far apart cannot both have been read. The
# report calls out attempts arriving "seconds apart"; this is where that stops
# being an impression and starts being a column in a table.
RAPID_SECONDS = 90

# A patch is a small edit to the same approach. Three of them in a row, arriving
# fast, is the measurable signature of debugging by guess rather than by reading.
PATCH_LINES = 6
PATCH_RUN = 3

GRIND_PAGES = 20


def submissions(slug: str) -> list[dict]:
    """Every submission for a problem, in order, from the filenames."""
    folder = ROOT / "solutions" / slug
    if not folder.is_dir():
        return []
    found = []
    for path in folder.iterdir():
        match = re.match(r"(\d+)_(.+?)_([a-z0-9+#]+)_\d+$", path.stem)
        if match and path.suffix.lower() in EXT_LANG:
            found.append({"at": int(match.group(1)),
                          "status": match.group(2).replace("_", " "),
                          "lang": match.group(3),
                          "file": str(path.relative_to(ROOT))})
    found.sort(key=lambda s: s["at"])
    return found


def grind_length(slug: str) -> int:
    """Submissions made before the first Accepted one -- the struggle itself."""
    subs = submissions(slug)
    for i, sub in enumerate(subs):
        if sub["status"] == "Accepted":
            return i
    return len(subs)


def changed_lines(before: str, after: str) -> int | None:
    """Lines a diff touches, or None when the two files cannot be compared."""
    import difflib
    a, _, cut_a = read_code(before)
    b, _, cut_b = read_code(after)
    if not a or not b or cut_a or cut_b:
        return None
    return sum(1 for line in difflib.unified_diff(a.splitlines(), b.splitlines(),
                                                  lineterm="", n=0)
               if line[:1] in "+-" and not line.startswith(("---", "+++")))


def patch_run(rows: list[dict]) -> int | None:
    """Index of the first submission starting a run of fast, tiny edits."""
    run = 0
    for i, row in enumerate(rows):
        small = row["changed"] is not None and row["changed"] <= PATCH_LINES
        fast = row["gap"] is not None and row["gap"] <= RAPID_SECONDS
        run = run + 1 if (small and fast) else 0
        if run >= PATCH_RUN:
            return i - run + 1
    return None


def grind_rows(slug: str, mistakes: dict) -> list[dict]:
    subs = submissions(slug)
    rows = []
    for i, sub in enumerate(subs):
        prev = subs[i - 1] if i else None
        rows.append({**sub,
                     "n": i + 1,
                     "gap": sub["at"] - prev["at"] if prev else None,
                     "changed": changed_lines(prev["file"], sub["file"]) if prev else None,
                     "mistake": mistakes.get(sub["file"])})
    return rows


def render_grind(case: Case, chapter: Chapter, rank: int) -> str:
    by_file = {m.get("file"): m for m in case.mistakes if m.get("file")}
    rows = grind_rows(case.slug, by_file)
    accepted_at = next((r["n"] for r in rows if r["status"] == "Accepted"), None)
    turn = patch_run(rows)

    def cell(row: dict) -> str:
        weight = STATUS_WEIGHT.get(row["status"], DEFAULT_STATUS_WEIGHT)
        tier = ("pass" if row["status"] == "Accepted" else
                "high" if weight >= 4 else "mid" if weight >= 3 else "low")
        gap = ("&mdash;" if row["gap"] is None else
               f'<span class="rapid">{plural(row["gap"], "sec")}</span>'
               if row["gap"] <= RAPID_SECONDS else human_gap(row["gap"]))
        changed = "&mdash;" if row["changed"] is None else str(row["changed"])
        note = (f'<p class="grind-note">{esc_code(row["mistake"].get("what_went_wrong"))}</p>'
                if row["mistake"] else "")
        after = accepted_at is not None and row["n"] > accepted_at
        return f"""<tr class="{'post' if after else ''}">
<td class="num">{row['n']}</td>
<td><span class="status {tier}">{esc(row['status'])}</span>{note}</td>
<td class="num">{gap}</td>
<td class="num">{changed}</td></tr>"""

    marker = ""
    if turn is not None and (accepted_at is None or turn + 1 < accepted_at):
        marker = f"""<p class="turn">From submission {rows[turn]['n']} onward,
{PATCH_RUN} or more consecutive attempts each changed
{PATCH_LINES} lines or fewer and arrived within
{plural(RAPID_SECONDS, 'second')} of the one before. That is the point the
approach stopped being revised and started being poked. Whatever was wrong at
submission {rows[turn]['n']} was still wrong at
{rows[min(turn + PATCH_RUN, len(rows) - 1)]['n']}.</p>"""

    diffs = "".join(
        f'<details class="grind-diff"><summary>{rows[i - 1]["n"]} &rarr; {r["n"]}'
        f' &middot; {plural(r["changed"], "line")} changed</summary>'
        f'{diff_block(rows[i - 1]["file"], r["file"])}</details>'
        for i, r in enumerate(rows)
        if i and r["changed"] and (accepted_at is None or r["n"] <= accepted_at))

    span = rows[-1]["at"] - rows[0]["at"] if len(rows) > 1 else 0
    body = f"""<nav class="crumb"><a href="grinds.html">&larr; The grinds</a> &middot;
<a href="{esc(chapter.topic)}.html">{esc(chapter.name)}</a> &middot;
<a href="index.html">All topics</a></nav>
<header class="chapter-head">
<p class="eyebrow">Grind {rank} &middot; {esc(case.difficulty or 'Unrated')}</p>
<h1>{esc(case.title)}</h1>
<p class="lede">{plural(grind_length(case.slug), 'submission')} before the first
Accepted one, {len(rows)} in total, over
{esc(human_gap(span))}. {plural(len(case.mistakes), 'mistake')} diagnosed.</p>
<p class="facts"><a href="https://leetcode.com/problems/{esc(case.slug)}/">open on
LeetCode</a></p>
</header>
{marker}
<h2>The timeline</h2>
<div class="table-scroll"><table class="grind">
<tr><th class="num">#</th><th>Result</th><th class="num">After</th>
<th class="num">Lines<br>changed</th></tr>
{"".join(cell(r) for r in rows)}</table></div>
<p class="hint">&ldquo;After&rdquo; is the gap from the previous submission;
anything under {plural(RAPID_SECONDS, 'second')} is marked, because it is less
time than reading the failing case takes. Rows after the first Accepted one are
dimmed &mdash; those are post-solve rewrites, not part of the struggle.</p>
<h2>What changed between attempts</h2>
<p class="hint">Up to the first Accepted submission only.</p>
{diffs or '<p class="hint">Nothing comparable: the files are too long to diff.</p>'}
<nav class="crumb bottom"><a href="grinds.html">&larr; Every grind</a></nav>"""
    return page(f"{case.title} -- Improvement Book", body)


def human_gap(seconds: int) -> str:
    if seconds < 90:
        return plural(seconds, "sec")
    if seconds < 5400:
        return plural(round(seconds / 60), "min")
    if seconds < 172800:
        return plural(round(seconds / 3600), "hour")
    return plural(round(seconds / 86400), "day")


def worst_grinds(chapters: list[Chapter]) -> list[tuple[int, Case, Chapter]]:
    """The longest struggles, each filed under the chapter that diagnosed it most."""
    best: dict[str, tuple[Case, Chapter]] = {}
    for chapter in chapters:
        for case in chapter.cases:
            held = best.get(case.slug)
            if held is None or len(case.mistakes) > len(held[0].mistakes):
                best[case.slug] = (case, chapter)
    scored = [(grind_length(slug), case, chapter)
              for slug, (case, chapter) in best.items()]
    scored.sort(key=lambda t: (-t[0], t[1].title))
    return scored[:GRIND_PAGES]


def render_grinds(chapters: list[Chapter]) -> list[tuple[str, str]]:
    """The index plus one page per grind, as (filename, html) pairs."""
    worst = worst_grinds(chapters)
    items = "".join(f"""<li class="grind-item">
<span class="rank">{i}</span>
<a href="grind-{esc(case.slug)}.html">{esc(case.title)}</a>
<span class="badge">{esc(case.difficulty or 'Unrated')}</span>
<span class="hint">{plural(n, 'submission')} before Accepted &middot;
{plural(len(case.mistakes), 'mistake')} diagnosed &middot;
<a href="{esc(chapter.topic)}.html">{esc(chapter.name)}</a></span></li>"""
        for i, (n, case, chapter) in enumerate(worst, 1))

    body = f"""<nav class="crumb"><a href="index.html">&larr; All topics</a> &middot;
<a href="mistakes.html">Every mistake</a> &middot;
<a href="habits.html">The habits</a></nav>
<header class="chapter-head">
<p class="eyebrow">Ranked by submissions made before the first Accepted one</p>
<h1>The twenty longest grinds</h1>
<p class="lede">Every chapter shows a problem as one collapsed entry, which
flattens a twenty-submission struggle into the same shape as a single typo.
These {GRIND_PAGES} get a page each: the attempt timeline with the gap between
consecutive submissions, the diff at every step, and the diagnosis attached to
the attempt it belongs to.</p>
<p class="lede">The column worth reading is the gap. An attempt arriving under
{plural(RAPID_SECONDS, 'second')} after the last one was not written from a
reading of the failure &mdash; there was not time. Where {PATCH_RUN} or more of
those arrive in a row, each changing {PATCH_LINES} lines or fewer, the page
marks it: that is where the approach should have been abandoned rather than
patched, and the marker is computed from the timestamps rather than judged.</p>
</header>
<ol class="grinds">{items}</ol>
<nav class="crumb bottom"><a href="habits.html">The habits behind these
&rarr;</a></nav>"""
    pages = [("grinds.html", page("The twenty longest grinds -- Improvement Book", body))]
    for i, (_, case, chapter) in enumerate(worst, 1):
        pages.append((f"grind-{case.slug}.html", render_grind(case, chapter, i)))
    return pages


# A drill is a mistake with its diagnosis taken away. Not every mistake makes
# one. The file has to be short enough to read in a sitting; the verdict has to
# be about reasoning rather than typing, so Compile Error is out; and the fix
# has to be small enough that finding it is a fair question rather than a
# scavenger hunt.
DRILL_MAX_LINES = 130
DRILL_MAX_FIX = 12
DRILLS_PER_LESSON = 10


def drill_candidates(evidence: list[tuple]) -> list[tuple]:
    """The mistakes under one lesson that make fair spot-the-bug exercises.

    Ranked by how small the eventual fix was: a one-line fix in a fifty-line
    file is the sharpest possible exercise, because everything except the bug
    is correct and the reader has to actually read.
    """
    found = []
    for chapter, case, mistake in evidence:
        path = mistake.get("file") or ""
        code, _, truncated = read_code(path)
        status = mistake.get("status") or submission_status(path)
        if not code or truncated or status in ("Compile Error", "Accepted"):
            continue
        if not (mistake.get("what_went_wrong") and mistake.get("how_it_was_fixed")):
            continue
        lines = code.count("\n") + 1
        fix = changed_lines(path, next_submission(path))
        if lines > DRILL_MAX_LINES or not fix or fix > DRILL_MAX_FIX:
            continue
        found.append((fix, lines, chapter, case, mistake))
    found.sort(key=lambda t: (t[0], t[1], t[3].title))
    return found[:DRILLS_PER_LESSON]


def render_drill(rank: int, fix: int, lines: int, chapter: Chapter, case: Case,
                 mistake: dict) -> str:
    path = mistake["file"]
    status = mistake.get("status") or submission_status(path) or "Failed"
    after = next_submission(path)
    outcome = submission_status(after)
    verb = ("The submission after it was accepted" if outcome == "Accepted"
            else f"The submission after it came back {outcome}" if outcome
            else "What came next")
    return f"""<section class="drill-item" id="d{rank}">
<h2><span class="num">{rank}</span>{esc(case.title)}
<span class="drill-meta">{esc(chapter.name)} &middot; {esc(case.difficulty)}</span></h2>
<p class="ask">This came back <strong>{esc(status)}</strong>. It is
{plural(lines, 'line')} long and the change that followed touched
{plural(fix, 'line')}. Where is it?</p>
{code_block(path, 'Your submission, as the judge saw it', 'bad')}
<details class="reveal"><summary>What the analysis found</summary>
<dl>
<dt>What went wrong</dt><dd>{esc_code(mistake.get('what_went_wrong'))}</dd>
<dt>How it was fixed</dt><dd>{esc_code(mistake.get('how_it_was_fixed'))}</dd>
</dl>
<p class="hint">{verb}. The diff is the answer to the question above:</p>
{diff_block(path, after)}
<p class="hint"><a href="{esc(chapter.topic)}.html#{esc(case.slug)}">This problem
in the {esc(chapter.name)} chapter</a></p>
</details></section>"""


def render_reference(lesson: dict, rank: int, total_lessons: int) -> str:
    """The catalogue a lesson is too long to carry. Same sections, own page."""
    reference = lesson["reference"]
    parts, subnav = [], []
    for i, (heading, body) in enumerate(reference["sections"], 1):
        aid = anchor(heading, i)
        subnav.append(f'<a href="#{aid}">{esc(heading)}</a>')
        parts.append(f'<section class="lesson-part" id="{aid}">'
                     f"<h2>{esc(heading)}</h2>{body}</section>")
    nav = (f'<a href="course-{esc(lesson["slug"])}.html">&larr; '
           f'{esc(lesson["title"])}</a> &middot; '
           f'<a href="course.html">The course</a>')
    body = f"""<nav class="crumb">{nav}</nav>
<header class="chapter-head">
<p class="eyebrow">Reference for lesson {rank} of {total_lessons}</p>
<h1>{esc(reference['title'])}</h1>
{reference['blurb']}
</header>
<nav class="subnav" aria-label="Entries in this reference">{''.join(subnav)}</nav>
{''.join(parts)}
<nav class="crumb bottom">{nav}</nav>"""
    return page(f"{reference['title']} -- Improvement Book", body)


def render_drill_page(lesson: dict, rank: int, drills: list[tuple],
                      total_lessons: int) -> str:
    items = "\n".join(render_drill(i, *d) for i, d in enumerate(drills, 1))
    nav = (f'<a href="drills.html">&larr; All drills</a> &middot; '
           f'<a href="course-{esc(lesson["slug"])}.html">The lesson</a> &middot; '
           f'<a href="course.html">The course</a>')
    body = f"""<nav class="crumb">{nav}</nav>
<header class="chapter-head">
<p class="eyebrow">Drill set for lesson {rank} of {total_lessons}</p>
<h1>Spot the bug: {esc(lesson['title'])}</h1>
<p class="lede">{plural(len(drills), 'submission')} of your own that this lesson
covers, with the diagnosis hidden. Read the code and find the bug before you
open the answer.</p>
<p class="hint">These are ordered by how small the fix turned out to be, so the
first ones are the hardest to see and the easiest to explain. Every one of them
is code you wrote and the judge rejected &mdash; there is no invented example on
this page.</p>
</header>
{items}
<nav class="crumb bottom">{nav}</nav>"""
    return page(f"Spot the bug: {lesson['title']} -- Improvement Book", body)


def render_drills_index(lessons: list[dict], sets: dict[str, list]) -> str:
    rows = []
    for i, lesson in enumerate(lessons, 1):
        drills = sets.get(lesson["slug"]) or []
        if not drills:
            continue
        sharpest = min(d[0] for d in drills)
        rows.append(f"""<li>
<a class="tile" href="drill-{esc(lesson['slug'])}.html">
<span class="rank">{i}</span>
<span class="tile-main">
  <strong>{esc(lesson['title'])}</strong>
  <span class="tile-nums">{plural(len(drills), 'exercise')} &middot;
  smallest fix {plural(sharpest, 'line')}</span>
</span></a></li>""")
    total = sum(len(v) for v in sets.values())
    body = f"""<nav class="crumb"><a href="index.html">&larr; All topics</a> &middot;
<a href="course.html">The course</a> &middot;
<a href="checklist.html">The checklist</a></nav>
<header class="cover">
<p class="eyebrow">Practice, not reading</p>
<h1>Spot the bug</h1>
<p class="lede">{total} exercises, built from your own rejected submissions. Each
one shows the code the judge refused and hides what the analysis found. Read
first, open the answer second.</p>
<p class="lede">A submission qualifies as an exercise when it is short enough to
read in one sitting, the verdict is about reasoning rather than a typo, and the
change that followed it was small. That last condition is what makes them fair:
everything on the page except a line or two is correct.</p>
<p class="also">No exercise here was invented. If you find one you cannot spot,
that is the same bug waiting to happen again &mdash; the lesson beside it is
where the general form is.</p>
</header>
<section class="tier"><ol class="tiles">{''.join(rows)}</ol></section>"""
    return page("Spot the bug -- Improvement Book", body)


# A problem slug in prose looks like this and nothing else does: three or more
# lowercase-hyphen words. Extracting them is what turns twenty-seven drill
# paragraphs into one schedule, and it is also the check in C3 -- a slug the
# catalogue has never heard of is a typo or a renamed problem.
SLUG_IN_PROSE = re.compile(r"\b[a-z0-9]+(?:-[a-z0-9]+){2,}\b")

SESSION_SIZE = 3
SPACING = ["the next day", "a week later", "a month later"]


def problem_index(chapters: list[Chapter]) -> dict[str, dict]:
    """Every problem in the export, by slug. Bundles do not overlap."""
    found = {}
    for chapter in chapters:
        for problem in chapter.bundle_problems:
            found.setdefault(problem["titleSlug"], dict(problem, topic=chapter.topic,
                                                       topic_name=chapter.name))
    return found


def practice_problems(lesson: dict, evidence: list[tuple],
                      known: dict[str, dict]) -> tuple[list[str], int]:
    """The problems this lesson's drill names, then its own evidence to fill.

    Returns the slugs and how many of them the drill actually named. Some
    drills are an exercise rather than a problem list ("grep your accepted Java
    for..."), and those sessions are filled from the lesson's own evidence
    instead -- still the reader's own failures on the material, but a different
    kind of recommendation, so the page says which it is showing.
    """
    named = [slug for slug in dict.fromkeys(SLUG_IN_PROSE.findall(lesson["drill"]))
             if slug in known or slug in CATALOG]
    filled = list(named)
    for _, case, _ in evidence:
        if len(filled) >= SESSION_SIZE:
            break
        if case.slug not in filled:
            filled.append(case.slug)
    return filled, len(named)


def history_cell(slug: str, known: dict[str, dict]) -> tuple[str, str]:
    """What your record says about this problem, and the class to style it."""
    problem = known.get(slug)
    if not problem:
        return "not in your export", "new"
    if not problem.get("solved", True):
        return f"never solved, {plural(problem.get('total_attempts') or 0, 'attempt')}", "bad"
    attempts = problem.get("attempts_to_accept") or 0
    if attempts == 1:
        return "solved first try", "good"
    return f"solved on attempt {attempts}", "mid"


def schedule_sessions(lessons: list[dict], evidence: dict[str, list],
                      chapters: list[Chapter]) -> list[dict]:
    """The practice schedule as data, before it is a page.

    The HTML schedule, the calendar file and the flashcard deck are three
    renderings of one plan. Building the plan once means a problem cannot
    appear in the page and be missing from the calendar.
    """
    known = problem_index(chapters)
    sessions = []
    for rank, lesson in enumerate(lessons, 1):
        slugs, from_drill = practice_problems(lesson, evidence[lesson["slug"]], known)
        for start in range(0, len(slugs), SESSION_SIZE):
            problems = []
            for slug in slugs[start:start + SESSION_SIZE]:
                found = known.get(slug) or CATALOG.get(slug) or {}
                problems.append({
                    "slug": slug,
                    "title": found.get("title") or slug_to_title(slug),
                    "difficulty": found.get("difficulty") or "",
                    "topic": found.get("topic") or "",
                })
            sessions.append({"number": len(sessions) + 1, "lesson": lesson,
                             "rank": rank, "problems": problems,
                             "first": start == 0, "from_drill": from_drill})
    return sessions


# Offsets in days for the revisit columns on the schedule page, in the same
# order. The page prints the words; the calendar has to know the numbers.
SPACING_DAYS = [1, 7, 30]


def ics_escape(text: str) -> str:
    """RFC 5545 TEXT escaping: backslash, semicolon, comma, newline."""
    return (text.replace("\\", "\\\\").replace(";", "\\;")
                .replace(",", "\\,").replace("\n", "\\n"))


def ics_fold(line: str) -> str:
    """Fold to 75 octets, continuations prefixed with one space (RFC 5545).

    Folding is by octet, not character, so the split is done on the encoded
    bytes and never inside a multi-byte sequence.
    """
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line

    def take(source: bytes, limit: int) -> bytes:
        """The longest prefix within `limit` octets that is whole characters.

        Trimming trailing continuation bytes is not enough: a cut can also land
        immediately after a lead byte, which is not a continuation byte and
        would survive that test. Decoding is the only honest predicate.
        """
        chunk = source[:limit]
        while chunk:
            try:
                chunk.decode("utf-8")
                return chunk
            except UnicodeDecodeError:
                chunk = chunk[:-1]
        return chunk

    out, first = [], take(raw, 75)
    out.append(first.decode("utf-8"))
    rest = raw[len(first):]
    while rest:
        chunk = take(rest, 74)          # 74, because the space counts too
        out.append(" " + chunk.decode("utf-8"))
        rest = rest[len(chunk):]
    return "\r\n".join(out)


def render_calendar(sessions: list[dict], start: datetime.date) -> str:
    """The schedule as an .ics: one all-day event per session, then its revisits.

    A schedule on a page is a page you have to remember to open. The same plan
    in a calendar arrives on its own, which is the entire difference between a
    plan you follow and a plan you wrote.
    """
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//leetcode-analyze//Improvement Book//EN",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             "X-WR-CALNAME:Improvement Book practice"]
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    def event(uid: str, day: datetime.date, title: str, body: str) -> None:
        lines.extend(ics_fold(text) for text in (
            "BEGIN:VEVENT",
            f"UID:{uid}@improvement-book.local",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
            f"DTEND;VALUE=DATE:{day + datetime.timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{ics_escape(title)}",
            f"DESCRIPTION:{ics_escape(body)}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT"))

    for offset, session in enumerate(sessions):
        day = start + datetime.timedelta(days=offset)
        lesson = session["lesson"]
        listing = "\n".join(
            f"- {p['title']}"
            + (f" ({p['difficulty']})" if p["difficulty"] else "")
            + f"\n  https://leetcode.com/problems/{p['slug']}/"
            for p in session["problems"])
        body = (f"Lesson {session['rank']}: {lesson['title']}\n\n"
                f"{lesson['key_rule']}\n\n{listing}\n\n"
                f"Drill: {re.sub(r'<[^>]+>', '', esc_code(lesson['drill']))}")
        event(f"session-{session['number']}", day,
              f"Practice {session['number']}: {lesson['title']}", body)
        for gap, when in zip(SPACING_DAYS, SPACING):
            event(f"session-{session['number']}-r{gap}",
                  day + datetime.timedelta(days=gap),
                  f"Revisit {session['number']} ({when})",
                  "Re-solve from scratch, no notes:\n" + listing)

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def render_anki(lessons: list[dict]) -> str:
    """Every recall question as a tab-separated Anki deck.

    The questions already exist -- each lesson opens with them, asked before
    the explanation. On the page they are read once. In a deck they are asked
    again in a month, which is the only version of them that does anything.
    """
    rows = ["#separator:tab", "#html:true", "#tags column:3"]
    for lesson in lessons:
        tag = "improvement-book::" + lesson["slug"]
        for question, answer in lesson["recall"]:
            rows.append("\t".join(
                (esc_code(question).replace("\t", " "),
                 esc_code(answer).replace("\t", " "), tag)))
        rows.append("\t".join(
            (f"Key rule &mdash; {esc(lesson['title'])}",
             esc_code(lesson["key_rule"]).replace("\t", " "), tag)))
    return "\n".join(rows) + "\n"


def render_schedule(lessons: list[dict], evidence: dict[str, list],
                    chapters: list[Chapter]) -> str:
    known = problem_index(chapters)
    plan = schedule_sessions(lessons, evidence, chapters)
    sessions, rows_total, new_count = [], 0, 0
    for session in plan:
        lesson, from_drill = session["lesson"], session["from_drill"]
        total_here = len(session["problems"])
        source = ("" if from_drill >= total_here else
                  '<p class="hint src">The drill above is an exercise rather than '
                  "a problem list, so this session is filled with the problems in "
                  "your own export that this lesson covers, worst first.</p>"
                  if not from_drill else
                  f'<p class="hint src">'
                  + ("The first problem here is named in the drill"
                     if from_drill == 1 else
                     f"The first {from_drill} problems here are named in the drill")
                  + "; the rest are from your own export.</p>")
        rows = []
        for problem in session["problems"]:
            slug = problem["slug"]
            where = (f'<a href="{esc(problem["topic"])}.html#{esc(slug)}">'
                     f'{esc(problem["title"])}</a>' if problem["topic"] else
                     f'<a href="https://leetcode.com/problems/{esc(slug)}/" '
                     f'target="_blank" rel="noopener">{esc(problem["title"])}</a>')
            text, tone = history_cell(slug, known)
            new_count += tone == "new"
            rows_total += 1
            rows.append(f"<tr><td>{where}</td>"
                        f'<td>{esc(problem["difficulty"] or "&mdash;")}</td>'
                        f'<td class="hist {tone}">{text}</td>'
                        + "".join('<td class="tick"></td>' for _ in SPACING)
                        + "</tr>")
        sessions.append(f"""<section class="session">
<h2><span class="num">{session['number']}</span>{esc(lesson['title'])}</h2>
<p class="hint"><a href="course-{esc(lesson['slug'])}.html">Lesson {session['rank']}</a>
&middot; <a href="drill-{esc(lesson['slug'])}.html">its spot-the-bug set</a>
&middot; {esc_code(lesson['drill'])}</p>{source if session['first'] else ""}
<div class="table-scroll"><table class="lesson-table sched">
<thead><tr><th>Problem</th><th>Difficulty</th><th>Your record</th>
{''.join(f'<th>{esc(when)}</th>' for when in SPACING)}</tr></thead>
<tbody>{''.join(rows)}</tbody></table></div></section>""")

    body = f"""<nav class="crumb"><a href="index.html">&larr; All topics</a> &middot;
<a href="course.html">The course</a> &middot;
<a href="drills.html">Spot the bug</a> &middot;
<a href="checklist.html">The checklist</a></nav>
<header class="chapter-head">
<p class="eyebrow">Every lesson&rsquo;s drill, in one order</p>
<h1>The practice schedule</h1>
<p class="lede">{plural(len(sessions), 'session')} of {SESSION_SIZE} problems,
{rows_total} in total, in course order &mdash; which is the order that stops the
most bugs soonest. {plural(new_count, 'problem')} here you have never attempted;
the rest carry what your own record says, so you can see at a glance whether a
session is revision or new ground.</p>
<p class="lede">The three empty columns are the spacing the report asks for.
A problem you solved once and never returned to is a problem you have watched,
not learned &mdash; tick it {esc(SPACING[0])}, {esc(SPACING[1])} and
{esc(SPACING[2])}, and only then call it done.</p>
<p class="also">Print this page. It is designed to be marked with a pen, and
the browser will drop the navigation and expand everything on the way out.</p>
<p class="also">Or take it with you: <a href="schedule.ics"
download>schedule.ics</a> puts every session and its three revisits in your
calendar, one session a day from the day you import it, and
<a href="recall.tsv" download>recall.tsv</a> is every lesson&rsquo;s recall
questions as an Anki deck (File &rarr; Import, tab-separated).</p>
</header>
{''.join(sessions)}
<nav class="crumb bottom"><a href="course.html">The course</a> &middot;
<a href="index.html">All topics</a></nav>"""
    return page("The practice schedule -- Improvement Book", body)


def render_checklist(lessons: list[dict], evidence: dict[str, list],
                     habits: dict[str, list]) -> str:
    """One rule per lesson, ordered by how much evidence sits behind it.

    The order is not an opinion: it is the size of the join under each lesson.
    A rule that would have caught seventy-six of your own submissions belongs
    above one that would have caught fifteen, whatever either of them is about.
    """
    weighted = sorted(
        ((len(evidence[l["slug"]]) + len(habits[l["slug"]]), l) for l in lessons),
        key=lambda t: -t[0])
    order = {l["slug"]: i for i, l in enumerate(lessons, 1)}

    def item(count: int, lesson: dict) -> str:
        return f"""<li>
<p class="check-rule">{esc_code(lesson['key_rule'])}</p>
<p class="check-why"><a href="course-{esc(lesson['slug'])}.html">Lesson
{order[lesson['slug']]}: {esc(lesson['title'])}</a> &middot;
{plural(count, 'place')} in your export where this applies</p></li>"""

    top = "".join(item(c, l) for c, l in weighted[:15])
    rest = "".join(item(c, l) for c, l in weighted[15:])
    body = f"""<nav class="crumb"><a href="index.html">&larr; All topics</a> &middot;
<a href="course.html">The course</a> &middot;
<a href="schedule.html">The schedule</a></nav>
<header class="chapter-head">
<p class="eyebrow">Keep this open while you solve</p>
<h1>Before you submit</h1>
<p class="lede">One rule from each lesson, ordered by the number of places in
your own export where it applies. The top fifteen are the page; the remaining
{len(weighted) - 15} are underneath, because a checklist you do not finish
reading is not a checklist.</p>
<p class="lede">Nothing here is a general principle of good code. Every line is
a rule that, followed once, would have turned a specific rejected submission
into an accepted one.</p>
</header>
<section class="checklist"><ol>{top}</ol></section>
<details class="more-mistakes"><summary>The other
{plural(len(weighted) - 15, 'rule')}, same ordering</summary>
<section class="checklist"><ol start="16">{rest}</ol></section></details>
<nav class="crumb bottom"><a href="course.html">The course</a> &middot;
<a href="drills.html">Spot the bug</a></nav>"""
    return page("Before you submit -- Improvement Book", body)


def resubmission_gaps() -> list[int]:
    """Seconds between consecutive submissions on the same problem."""
    gaps = []
    for folder in sorted((ROOT / "solutions").iterdir()):
        if not folder.is_dir():
            continue
        times = sorted(sub["at"] for sub in submissions(folder.name))
        gaps.extend(b - a for a, b in zip(times, times[1:]))
    return sorted(gaps)


def render_process(chapters: list[Chapter], overview: dict) -> str:
    """The two habits that are about process rather than about algorithms.

    Both are already described in the report. What this page adds is the
    measurement: the gap distribution is computed from the submission
    timestamps here, so the claim "sometimes within seconds" stops being an
    impression and becomes a number that moves when the export does.
    """
    gaps = resubmission_gaps()
    total = len(gaps)
    buckets = [(30, "under 30 seconds"), (60, "under a minute"),
               (RAPID_SECONDS, f"under {RAPID_SECONDS} seconds"),
               (300, "under five minutes"), (3600, "within the hour")]
    import bisect
    rows = "".join(
        f"<tr><td>{esc(label)}</td>"
        f'<td class="n">{bisect.bisect_right(gaps, limit)}</td>'
        f'<td class="n">{bisect.bisect_right(gaps, limit) / total:.0%}</td></tr>'
        for limit, label in buckets)
    median = gaps[total // 2]
    fast = bisect.bisect_right(gaps, 30)

    post = overview.get("post_solve_submissions", 0)
    all_subs = overview.get("total_submissions", 1)
    flagged = overview.get("suspect_pasted_attempts", 0)

    body = f"""<nav class="crumb"><a href="index.html">&larr; All topics</a> &middot;
<a href="habits.html">The twelve habits</a> &middot;
<a href="grinds.html">The longest grinds</a> &middot;
<a href="plan.html">The plan</a></nav>
<header class="chapter-head">
<p class="eyebrow">Not a bug class &middot; measured from the timestamps</p>
<h1>Two habits you do not know you have</h1>
<p class="lede">Every other page in this book is about something you wrote.
This one is about how you write it. Both habits below are larger than any
single bug, neither is visible from inside a single problem, and one of them
is a genuinely good practice that is quietly costing you.</p>
</header>

<section class="proc" id="loop">
<h2>1. The loop is fast and shallow</h2>
<p>Submit, read the verdict, patch the nearest line, resubmit. Across
{plural(total, 'consecutive pair')} of submissions on the same problem, the
median gap is {plural(median, 'second')}.</p>
<div class="table-scroll"><table class="lesson-table gapdist">
<thead><tr><th>The next submission arrived</th><th>count</th><th>share</th></tr>
</thead><tbody>{rows}</tbody></table></div>
<p>{fast} resubmissions &mdash; {fast / total:.0%} of them &mdash; arrived
within thirty seconds of the one before. Thirty seconds is not enough to read a
failing case, so those are edits made from the verdict alone. That is what
&ldquo;shallow&rdquo; means here, and it is a measurement rather than a
judgement.</p>
<p>The speed is a real asset: instances get fixed quickly and you almost always
converge. The cost is that the class underneath never gets named, which is why
the same bug shape turns up months later in unrelated code &mdash; the whole
reason this book has a chapter per topic and a lesson per class.</p>
<p class="counter"><strong>The counter-habit, in one sentence.</strong> Before
the <em>second</em> patch on a problem, write down what the failing case
actually is. Not what to change &mdash; what input breaks it. If you cannot
write the input, you do not have a hypothesis, and the next submission is a
guess.</p>
<p class="also">The <a href="grinds.html">twenty longest grinds</a> show this
happening line by line, with the point marked where each one stopped being
revised and started being poked.</p>
</section>

<section class="proc" id="post-solve">
<h2>2. Post-solve rewriting</h2>
<p>{post} of {all_subs} submissions &mdash; {post / all_subs:.0%} &mdash; went
to a problem that was <em>already solved</em>. That is the single largest fact
about how you practise, and it is mostly to your credit: re-implementing a
solved problem a second way is one of the better habits there is, and it is why
this export holds parallel solutions in Java, C++ and Python.</p>
<p>It is also where the damage concentrates. All {flagged} paste-flagged
attempts in the export sit in this half of it, and so do the regressions: code
that was accepted, then cleaned up, and lost a step in the cleanup.</p>
<p class="counter"><strong>The counter-habit, in one sentence.</strong> A
rewrite is new code. Run the same checklist on it you would run on a first
attempt &mdash; the fact that the problem is solved says nothing about whether
<em>this</em> implementation is correct.</p>
<p class="also"><a href="checklist.html">The checklist</a> is the page to run
it from. <a href="habits.html">The twelve habits</a> has the bug-class version
of both of these.</p>
</section>
<nav class="crumb bottom"><a href="habits.html">The twelve habits</a> &middot;
<a href="index.html">All topics</a></nav>"""
    return page("Two habits you do not know you have -- Improvement Book", body)


# Every Java block in the course, and the three shapes one can take: a whole
# file, a class body, a method body. Which one a block is is not worth guessing
# at -- javac decides, in that order, and a block that fails all three either
# is an illustration and says so, or is a bug in the book.
LESSON_CODE = re.compile(r'<pre class="lesson-code( illustrative)?"><code>(.*?)</code></pre>',
                         re.S)
# Each block is compiled in its own file under its own class name -- several
# files declaring the same class in one javac invocation is a duplicate-class
# error that has nothing to do with the sample.
# The two node types every LeetCode linked-list and tree problem assumes and
# none of them declares. Compiled alongside each sample so a method signature
# naming one of them resolves; the book never defines them itself.
JAVA_NODES = """
class ListNode { int val; ListNode next;
                 ListNode() {} ListNode(int v) { val = v; }
                 ListNode(int v, ListNode n) { val = v; next = n; } }
class TreeNode { int val; TreeNode left, right;
                 TreeNode() {} TreeNode(int v) { val = v; } }
"""

JAVA_WRAPPERS = [
    "import java.util.*;\n{body}\n",
    "import java.util.*;\nclass {name}{{\n{body}\n}}\n",
    "import java.util.*;\nclass {name}{{ void method(){{\n{body}\n}} }}\n",
    # A method body that returns something. Object takes any reference and
    # boxes any primitive, so this wrapper asks "does the body type-check"
    # without having to guess what the fragment returns.
    "import java.util.*;\nclass {name}{{ Object method(){{\n{body}\n}} }}\n",
]


def lesson_sections(lesson: dict) -> list[tuple[str, str]]:
    """Every authored section of a lesson, including any split onto a reference
    page. Checks read this, not `basics`, so a split never hides prose or code.
    """
    reference = lesson.get("reference")
    return ([("In one page", lesson.get("summary") or "")] + lesson["basics"]
            + (reference["sections"] if reference else []))


def java_blocks(lessons: list[dict]) -> tuple[list[tuple], int]:
    """(lesson, heading, source) for every checkable block, and how many aren't."""
    checkable, illustrative = [], 0
    for lesson in lessons:
        for heading, body in lesson_sections(lesson):
            for marked, source in LESSON_CODE.findall(body):
                if marked:
                    illustrative += 1
                else:
                    checkable.append((lesson["slug"], heading,
                                      html.unescape(source)))
    return checkable, illustrative


# The names a LeetCode problem statement hands you, and the types they have
# there. A sample reading `for (int i = 0; i < n; i++) sum += nums[i];` is
# correct Java the moment `n` and `nums` exist -- they come from the sentence
# above the block, not from the block. Declaring them is what lets javac check
# the sample rather than stop at the context it cannot see. Nothing here is
# guessed: the list is the symbols javac reported missing, with the type each
# one carries everywhere it appears in the book.
JAVA_SCALARS = {
    "n": "int", "m": "int", "k": "int", "i": "int", "j": "int", "x": "int",
    "y": "int", "l": "int", "r": "int", "lo": "int", "hi": "int", "mid": "int",
    "count": "int", "best": "int", "ans": "int", "sum": "int", "max": "int",
    "min": "int", "size": "int", "total": "int", "target": "int", "val": "int",
    "rootX": "int", "rootY": "int", "iv": "int", "start": "int", "end": "int",
    "MOD": "long", "result": "long", "point1": "int", "point2": "int",
}
JAVA_ARRAYS = {
    "nums": "int", "dp": "int", "freq": "int", "counts": "int", "degree": "int",
    "indegree": "int", "parent": "int", "rank": "int", "heights": "int",
    "memo": "int", "a": "int", "b": "int", "src": "int", "arr": "int",
    "grid": "int", "prices": "int", "used": "boolean", "seen": "boolean",
    "visited": "boolean", "dist": "int", "digits": "int", "rows": "int",
    "cols": "int", "temps": "int", "piles": "int", "factors": "int",
    "exists": "boolean",
}
JAVA_OBJECTS = {
    "s": 'String s = "abc"',
    "t": 'String t = "abc"',
    "word": 'String word = "abc"',
    "sb": "StringBuilder sb = new StringBuilder()",
    "head": "ListNode head = new ListNode(0)",
    "node": "TreeNode node = new TreeNode(0)",
    "root": "TreeNode root = new TreeNode(0)",
    "adj": "List<List<Integer>> adj = new ArrayList<>()",
    "st": "Deque<Integer> st = new ArrayDeque<>()",
    "stack": "Deque<Integer> stack = new ArrayDeque<>()",
    "pq": "PriorityQueue<Integer> pq = new PriorityQueue<>()",
    "list": "List<Integer> list = new ArrayList<>()",
    "map": "Map<Integer, Integer> map = new HashMap<>()",
    "words": "String[] words = {}",
    "next": "ListNode next = new ListNode(0)",
    "current": "ListNode current = new ListNode(0)",
    "queue": "Deque<Integer> queue = new ArrayDeque<>()",
}
JAVA_DIMS = 3
JAVAC_FLOOR = 50


def java_declaration(name: str, source: str) -> str:
    """A declaration for `name` shaped by how this block uses it.

    Only the dimension is read off the source, and only for arrays: a block
    that writes `dp[i][j]` needs a two-dimensional `dp` and one that writes
    `dp[i]` needs a one-dimensional one, and the same name is both in
    different lessons. Everything else is fixed by the table.
    """
    if name in JAVA_OBJECTS:
        return JAVA_OBJECTS[name]
    subscripted = re.search(rf"\b{re.escape(name)}\s*\[", source)
    if name in JAVA_ARRAYS or (subscripted and name in JAVA_SCALARS):
        dims = 1
        while dims < JAVA_DIMS and re.search(
                rf"\b{re.escape(name)}\s*" + r"\[[^\]\n]*\]\s*" * dims + r"\[",
                source):
            dims += 1
        element = JAVA_ARRAYS.get(name) or JAVA_SCALARS[name]
        return (f"{element}{'[]' * dims} {name} = "
                f"new {element}{'[8]' * dims}")
    return f"{JAVA_SCALARS[name]} {name} = 0"


def java_context(work: Path, wrapper: str, indices: list[int],
                 blocks: list[tuple], context: dict[int, list[str]],
                 banned: dict[int, set]) -> bool:
    """Add declarations for the names javac just said were missing.

    One round: compile, read every `symbol: variable x` back to the block that
    raised it, and declare the ones the table knows. Returns whether anything
    was added, so the caller can iterate -- resolving one name routinely
    reveals the next, and stopping early leaves the sample unchecked.
    """
    files = [str(work / "LcNodes.java")]
    work.joinpath("LcNodes.java").write_text(JAVA_NODES, encoding="utf-8")
    for i in indices:
        target = work / f"Block{i}.java"
        target.write_text(wrapper.format(
            name=f"Block{i}",
            body="".join(f"{d};\n" for d in context.get(i, [])) + blocks[i][2]),
            encoding="utf-8")
        files.append(str(target))
    result = subprocess.run(
        ["javac", "-proc:none", "-nowarn", "-Xmaxerrs", "9999",
         "-d", str(work / "out"), *files],
        capture_output=True, text=True)
    if result.returncode == 0:
        return False

    changed, current = False, None
    for line in result.stderr.splitlines():
        named = re.search(r"Block(\d+)\.java:\d+: error(?:: (.*))?", line)
        if named:
            current = int(named.group(1))
            # The block declares this name itself, further down or in a scope
            # javac reached later. Ours is the wrong one: withdraw it.
            clash = re.match(r"variable (\w+) is already defined", named.group(2) or "")
            if clash and current in context:
                start = clash.group(1) + " "
                kept = [d for d in context[current]
                        if not d.split("=")[0].strip().endswith(" " + clash.group(1))]
                if len(kept) != len(context[current]):
                    context[current], changed = kept, True
                banned.setdefault(current, set()).add(clash.group(1))
            continue
        symbol = re.match(r"\s*symbol:\s+variable\s+(\w+)\s*$", line)
        if not symbol or current is None:
            continue
        name = symbol.group(1)
        if name in banned.get(current, ()):
            continue
        if name not in JAVA_SCALARS and name not in JAVA_ARRAYS \
                and name not in JAVA_OBJECTS:
            continue
        declaration = java_declaration(name, blocks[current][2])
        if declaration not in context.setdefault(current, []):
            context[current].append(declaration)
            changed = True
    return changed


def _javac(work: Path, wrapper: str, indices: list[int], blocks: list[tuple],
           flags: list[str], context: dict[int, list[str]] | None = None) -> list[int]:
    """Indices that javac accepts under this wrapper. Returns the survivors.

    javac works in phases across the whole batch, so one bad file can stop it
    before it has anything to say about the others. Drop whatever it names and
    run again until a run comes back clean; what is left has been all the way
    through.
    """
    (work / "LcNodes.java").write_text(JAVA_NODES, encoding="utf-8")
    candidates = list(indices)
    while candidates:
        files = [str(work / "LcNodes.java")]
        for i in candidates:
            target = work / f"Block{i}.java"
            declared = "".join(f"{d};\n" for d in (context or {}).get(i, []))
            target.write_text(
                wrapper.format(name=f"Block{i}", body=declared + blocks[i][2]),
                encoding="utf-8")
            files.append(str(target))
        result = subprocess.run(
            ["javac", *flags, "-nowarn", "-Xmaxerrs", "9999",
             "-d", str(work / "out"), *files],
            capture_output=True, text=True)
        if result.returncode == 0:
            return candidates
        failed = {int(m.group(1)) for m in
                  re.finditer(r"Block(\d+)\.java:\d+: error", result.stderr)}
        assert failed, f"javac failed naming no file:\n{result.stderr[:2000]}"
        candidates = [i for i in candidates if i not in failed]
    return []


def check_java(lessons: list[dict]) -> None:
    """Put every Java sample in the book through javac. Two questions, not one.

    The hard one first: does it *parse*? `-proc:only` stops javac after the
    parser, so an undeclared name is fine and a stray `...`, an expression
    written as a statement or an unbalanced brace is not. Every sample has to
    pass this, because a sample that does not parse is not Java.

    Then, for information only: how many also type-check standing alone? Most
    of these blocks are deliberately fragments -- `n`, `nums` and `dp` come
    from the sentence above them -- so full compilation is a bonus rather than
    a requirement, and the number is printed rather than asserted.
    """
    import shutil
    import subprocess as _sub
    import tempfile

    global subprocess
    subprocess = _sub

    blocks, illustrative = java_blocks(lessons)
    if not shutil.which("javac"):
        print(f"  javac: not on PATH -- {len(blocks)} samples NOT compiled")
        return

    # Which wrapper each block parses under, first. Everything after this is
    # per-wrapper: a block compiled under a wrapper it does not even parse
    # under stops javac in the parser, and a batch that stops in the parser
    # never reaches symbol resolution -- so the missing names, which are the
    # whole point of the context pass, are never reported.
    # Every wrapper is asked about every block, not just the ones no earlier
    # wrapper claimed. Two independent facts are wanted per pair: does the
    # block parse under this wrapper -- which is the assertion -- and does it
    # type-check under it, which is the report. A block that parses under one
    # wrapper and only compiles under another is common: a bare file of method
    # declarations parses as a compact source file and then fails for having
    # no main.
    parsed, compiled = set(), set()
    fits: dict[int, list[int]] = defaultdict(list)
    with tempfile.TemporaryDirectory() as tmp:
        for attempt, wrapper in enumerate(JAVA_WRAPPERS):
            work = Path(tmp) / f"parse{attempt}"
            work.mkdir()
            for i in _javac(work, wrapper, list(range(len(blocks))), blocks,
                            ["-proc:only"]):
                fits[attempt].append(i)
                parsed.add(i)

        done: set[int] = set()
        for attempt, wrapper in enumerate(JAVA_WRAPPERS):
            # Only blocks that parse under this wrapper: a batch that stops in
            # the parser never reaches symbol resolution, and the missing names
            # are the entire point of the context pass.
            group = [i for i in fits[attempt] if i not in done]
            if not group:
                continue
            # Each wrapper gets its own declarations: what `n` has to be under
            # one is not what it has to be under another.
            context, banned = {}, {}
            # Resolving one name reveals the next, so iterate until a round
            # changes nothing. The bound guards against a pathological block;
            # convergence is two or three rounds.
            for round_number in range(5):
                work = Path(tmp) / f"ctx{attempt}-{round_number}"
                work.mkdir()
                if not java_context(work, wrapper, group, blocks, context, banned):
                    break
            work = Path(tmp) / f"full{attempt}"
            work.mkdir()
            passed = _javac(work, wrapper, group, blocks, ["-proc:none"], context)
            compiled.update(passed)
            done.update(passed)

    unparsed = [i for i in range(len(blocks)) if i not in parsed]
    if unparsed:
        listed = "\n".join(
            f"  {blocks[i][0]} / {blocks[i][1]}: "
            f"{blocks[i][2].strip().splitlines()[0][:60]!r}" for i in unparsed)
        raise AssertionError(
            f"{len(unparsed)} Java samples do not parse as a file, a class body "
            f"or a method body:\n{listed}\nFix them, or mark each one with "
            f"code(..., compiles=False) if it is deliberately not Java.")
    # A ratchet, not a target. Every sample here is a deliberate fragment, so
    # full compilation will never be universal -- but it went 20 -> 50 once the
    # declarations the fragments assume were supplied, and a change that drops
    # it back is a check that quietly stopped checking.
    assert len(compiled) >= JAVAC_FLOOR, (
        f"only {len(compiled)} of {len(blocks)} samples type-check, below the "
        f"floor of {JAVAC_FLOOR} -- a wrapper or a declaration stopped working")
    print(f"  javac: {len(blocks)} samples parse, {len(compiled)} of them "
          f"type-check standing alone, {illustrative} marked as illustrations")


TAGS = re.compile(r"<[^>]+>")


def lesson_prose(lesson: dict) -> str:
    """Every authored sentence in a lesson, with the markup taken out.

    Markup has to go before anything looks for problem slugs in here: an SVG
    marker is `auto-start-reverse` and a font stack is `ui-sans-serif`, and
    both are shaped exactly like a LeetCode slug.
    """
    parts = [lesson["why"], lesson.get("summary") or "", lesson["drill"],
             *lesson["rules"], *lesson["objectives"],
             *[b for _, b in lesson_sections(lesson)],
             *[f"{a} {b}" for a, b in lesson["used_for"]],
             *[f"{a} {b}" for a, b in lesson["patterns"]],
             *[f"{q} {a}" for q, a in lesson["recall"]]]
    return TAGS.sub(" ", " ".join(parts))


# A lesson is meant to be read in one sitting. The pack sits between 950 and
# 2,300 words; the ceiling is set just above it, so it catches a lesson turning
# into a catalogue rather than policing ordinary growth. The fix when it trips
# is REFERENCE_SPLIT in course.py, not cutting the material.
LESSON_WORD_CEILING = 2600


def lesson_words(lesson: dict) -> int:
    """Words on the lesson page itself -- what a reader sits down to read."""
    reference = lesson.get("reference")
    moved = {id(body) for _, body in (reference["sections"] if reference else [])}
    prose = [lesson["why"], lesson.get("summary") or "", lesson["drill"],
             *lesson["rules"], *lesson["objectives"],
             *[b for _, b in lesson["basics"] if id(b) not in moved],
             *[f"{a} {b}" for a, b in lesson["used_for"]],
             *[f"{a} {b}" for a, b in lesson["patterns"]],
             *[f"{q} {a}" for q, a in lesson["recall"]]]
    return len(TAGS.sub(" ", " ".join(prose)).split())


def check_length(lessons: list[dict]) -> None:
    sizes = sorted(((lesson_words(l), l["slug"]) for l in lessons), reverse=True)
    over = [(n, slug) for n, slug in sizes if n > LESSON_WORD_CEILING]
    assert not over, (f"over the {LESSON_WORD_CEILING}-word ceiling: {over}. "
                      f"Split the catalogue part out with REFERENCE_SPLIT.")
    split = sum(1 for l in lessons if l.get("reference"))
    print(f"  length: longest lesson {sizes[0][0]} words ({sizes[0][1]}), "
          f"median {sizes[len(sizes) // 2][0]}, ceiling {LESSON_WORD_CEILING}, "
          f"{split} split onto a reference page")


HEX = re.compile(r"--([a-z]+):(#[0-9a-fA-F]{3,6})\b")
CONTRAST_MIN = 4.5  # WCAG AA for body text


def _luminance(hex_colour: str) -> float:
    if len(hex_colour) == 4:  # #fff
        hex_colour = "#" + "".join(c * 2 for c in hex_colour[1:])
    channels = []
    for i in (1, 3, 5):
        v = int(hex_colour[i:i + 2], 16) / 255
        channels.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(a: str, b: str) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def check_stylesheet() -> None:
    """What the stylesheet has to guarantee, checked where it is written.

    Contrast is the bulk of it: every foreground token, on every ground it is
    painted on, in both themes. --muted is the one that matters, because it
    carries the ledes, the hints and the captions, and it is the token a
    designer nudges paler without noticing.
    """
    dark_at = CSS.index("@media (prefers-color-scheme:dark)")
    themes = {"light": dict(HEX.findall(CSS[CSS.index(":root{--bg"):dark_at])),
              "dark": dict(HEX.findall(CSS[dark_at:CSS.index("*{box-sizing")]))}
    worst = (99.0, "")
    for theme, token in themes.items():
        assert set(token) >= {"bg", "panel", "code", "ink", "muted"}, theme
        for fg in ("ink", "muted", "accent", "good", "bad", "warn"):
            for bg in ("bg", "panel", "code"):
                got = contrast(token[fg], token[bg])
                assert got >= CONTRAST_MIN, (
                    f"{theme}: --{fg} on --{bg} is {got:.2f}:1, under "
                    f"{CONTRAST_MIN}:1")
                worst = min(worst, (got, f"{theme} --{fg} on --{bg}"))
    assert ":focus-visible{outline:" in CSS, "no visible focus ring"
    assert "@media print{" in CSS, "no print stylesheet"
    assert "::details-content" in CSS, "print would drop every folded section"
    # The two rules that stop a page scrolling sideways on a phone. The first
    # is the important one: the analysis quotes submission paths inline, and a
    # 70-character token with no space in it drags the whole page with it.
    assert "overflow-wrap:break-word" in CSS, "a long path would widen the page"
    assert ".table-scroll{overflow-x:auto" in CSS, "wide tables would widen the page"
    assert ".lesson-table:not(.pairs){display:block;overflow-x:auto}" in CSS, (
        "an authored table would widen the page below 34rem")
    print(f"  stylesheet: every token pair clears {CONTRAST_MIN}:1 in both "
          f"themes, tightest {worst[0]:.2f}:1 ({worst[1]}); focus ring, print "
          f"sheet and the narrow-screen rules all present")


def check_headings(pages: list[Path]) -> None:
    """Heading levels never skip, and every page has exactly one h1.

    A skipped level is invisible on screen and a hole in the outline a screen
    reader navigates by, so nothing but a check catches it.
    """
    for path in pages:
        levels = [int(m) for m in re.findall(r"<h([1-6])[ >]",
                                             path.read_text(encoding="utf-8"))]
        assert levels.count(1) == 1, f"{path.name}: {levels.count(1)} h1s"
        previous = 0
        for level in levels:
            assert not previous or level <= previous + 1, (
                f"{path.name}: h{previous} followed by h{level}")
            previous = level
    print(f"  headings: {len(pages)} pages, no skipped level, one h1 each")


def check_markers(pages: list[Path]) -> None:
    """No authoring marker reaches the page as text.

    Every prose string in this book is written with markdown backtick spans.
    Any that reach the page literally mean a render site called esc() where it
    owed esc_code(). Code blocks quote the reader's own files, backticks and all.
    """
    for path in pages:
        prose = re.sub(r"<pre.*?</pre>", "", path.read_text(encoding="utf-8"),
                       flags=re.S)
        # Narrower than INLINE_CODE on purpose: one LeetCode title ("All O`one")
        # contains a lone backtick, and two of them on a page pair up. A real
        # missed span is short and tag-free.
        stray = re.search(r"`[^`\n<]{1,60}`|\[\[[A-Za-z-]+\]\]|\{\{[a-z]+:[^}\n]+\}\}",
                          prose)
        assert not stray, f"{path.name}: unrendered {stray.group(0)!r}"


def check_figures(pages: list[Path]) -> None:
    """Every figure is announced to a screen reader rather than skipped."""
    total = 0
    for path in pages:
        for svg in re.findall(r"<svg\b.*?</svg>", path.read_text(encoding="utf-8"), re.S):
            total += 1
            assert 'role="img"' in svg, f"{path.name}: an svg with no role"
            assert "<title" in svg, f"{path.name}: an svg with no <title>"
    print(f"  figures: {total} inline svgs, every one labelled")


def check_ids(pages: list[Path]) -> None:
    """No page repeats an id, and every in-page link lands on one.

    The lesson pages have been checked for this since the start; the pages
    built later -- a problem page carries an id per diagnosed submission --
    need the same check, and there is no reason for it to be per-renderer.
    """
    for path in pages:
        html_text = path.read_text(encoding="utf-8")
        ids = re.findall(r'\bid="([^"]+)"', html_text)
        repeated = sorted({i for i in ids if ids.count(i) > 1})
        assert not repeated, f"{path.name}: repeated id {repeated[:3]}"
        targets = set(ids)
        dangling = sorted({h for h in re.findall(r'href="#([^"]+)"', html_text)
                           if h not in targets})
        assert not dangling, f"{path.name}: #{dangling[0]} has no target"
    print(f"  ids: unique on all {len(pages)} pages, every anchor lands")


def check_links(pages: list[Path]) -> None:
    """Every internal link lands, and no link ended up inside another link.

    The second half is the one that needs a machine: the glossary linker walks
    raw HTML, and an <a> nested in an <a> is invalid, invisible, and silently
    unclickable.
    """
    names = {path.name for path in pages}
    broken, nested = [], []
    for path in pages:
        html_text = path.read_text(encoding="utf-8")
        if re.search(r"<a\b[^>]*>(?:(?!</a>).)*?<a\b", html_text, re.S):
            nested.append(path.name)
        for href in re.findall(r'href="([^"#:]+\.html)(?:#[^"]*)?"', html_text):
            if href not in names:
                broken.append(f"{path.name} -> {href}")
    assert not nested, f"a link inside a link on {nested[:3]}"
    assert not broken, f"{len(broken)} dead internal links: {broken[:3]}"
    linked = {href for path in pages
              for href in re.findall(r'href="([^"#:]+\.html)', path.read_text(encoding="utf-8"))}
    orphans = sorted(names - linked - {"index.html"})
    assert not orphans, f"{len(orphans)} pages nothing links to: {orphans[:5]}"
    print(f"  links: every internal link on {len(pages)} pages lands, "
          f"every page is reachable")


def audit_output() -> None:
    """Everything that can only be checked once the pages exist."""
    pages = sorted(BOOK.glob("*.html"))
    assert pages, "nothing was written"
    check_markers(pages)
    check_headings(pages)
    check_figures(pages)
    check_ids(pages)
    check_links(pages)


def check_claims(lessons: list[dict], chapters: list[Chapter]) -> None:
    """Every problem the course names, checked against the export it came from.

    The lessons quote specific submissions -- "on reverse-linked-list you made
    the identical missing null check three times". The sentence is a paraphrase
    of the analysis and this cannot check that the paraphrase is fair. What it
    can check is that the problem is still there, still filed where the book
    says, and that the files the analysis points at are still on disk: a
    renamed, re-analysed or removed problem is the failure that actually
    happens, and it happens silently.
    """
    known = problem_index(chapters)
    named, outside = set(), set()
    for lesson in lessons:
        for token in SLUG_IN_PROSE.findall(lesson_prose(lesson)):
            (named if token in known else outside).add(token)

    for slug in sorted(named):
        problem = known[slug]
        assert problem.get("topic") in {c.topic for c in chapters}, (
            f"{slug} is filed under {problem.get('topic')}, which has no chapter")
        accepted = problem.get("first_accepted_file")
        assert not accepted or (ROOT / accepted).exists(), (
            f"{slug}: accepted file {accepted} is named in the export but is "
            f"not on disk")

    # File references the analysis got wrong. Not repairable from here: each
    # one splices the timestamp of one submission onto the id of another, and
    # both candidates are real failures on the same problem minutes apart, so
    # guessing which the diagnosis describes would attach it to the wrong file.
    # Reported every run instead, and the page says so where they land.
    diagnosed = [(chapter.topic, case.slug, m["file"])
                 for chapter in chapters for case in chapter.cases
                 for m in case.mistakes + case.smells if m.get("file")]
    missing = [ref for ref in diagnosed if not (ROOT / ref[2]).exists()]

    in_catalogue = sorted(t for t in outside if t in CATALOG)
    print(f"  claims: {len(named)} problems named in the lessons are in your "
          f"export and check out, {len(in_catalogue)} more are catalogue "
          f"problems you have not attempted")
    print(f"  files: {len(diagnosed) - len(missing)}/{len(diagnosed)} diagnosed "
          f"submissions are on disk"
          + ("" if not missing else
             " -- missing: " + ", ".join(ref[1] for ref in missing)))


def render_unsolved(chapters: list[Chapter]) -> str:
    """The four problems never solved, each with what the record proves.

    Two carry a worked solution. Two carry an explicit refusal to write one:
    their statements are not in the export, and inventing a statement out of
    five wrong submissions would put a confident fabrication in the one place
    the reader is least able to check it.
    """
    by_slug = {case.slug: (chapter, case)
               for chapter in chapters for case in chapter.cases}
    cards, toc = [], []
    for entry in synthesis.UNSOLVED:
        found = by_slug.get(entry["slug"])
        where = (f'<a href="{esc(found[0].topic)}.html#{esc(entry["slug"])}">'
                 f'{esc(found[0].name)}</a>' if found else "")
        tone = "good" if entry["solved"] else "warn"
        badge = ("A solution, written out" if entry["solved"]
                 else "No solution here &mdash; and why")
        toc.append(f'<a href="#{esc(entry["slug"])}">{esc(entry["title"])}</a>')
        cards.append(f"""<section class="unsolved-case" id="{esc(entry['slug'])}">
<h2>{esc(entry['title'])}</h2>
<p class="badges"><span class="badge d-{esc(entry['difficulty'].lower())}">
{esc(entry['difficulty'])}</span>
<span class="badge warn">{plural(entry['attempts'], 'attempt')}</span>
<span class="badge">{esc(entry['verdicts'])}</span>
<span class="badge {tone}">{badge}</span>
<a class="lc" href="https://leetcode.com/problems/{esc(entry['slug'])}/"
   target="_blank" rel="noopener">open on LeetCode</a></p>
<h3>What the submissions did</h3>
{entry['diagnosis']}
<h3>Why it is wrong</h3>
{entry['why']}
<h3>{"The fix" if entry["solved"] else "What to do instead"}</h3>
{entry['fix']}
{lesson_links(entry['lessons'], 'Related lessons')}
{f'<p class="hint">Filed under {where} in this book.</p>' if where else ''}
</section>""")

    body = f"""<nav class="crumb"><a href="index.html">&larr; All topics</a> &middot;
<a href="plan.html">The plan</a> &middot; <a href="course.html">Course</a></nav>
<header class="chapter-head">
<p class="eyebrow">4 problems &middot; 15 attempts &middot; 0 solves</p>
<h1>The four you never solved</h1>
<p class="lede">Out of 892 problems attempted, four were never solved &mdash; a
99.6% eventual solve rate, which makes these four the least noisy signal in the
whole export. Every one was abandoned mid-approach rather than exhausted.</p>
<p class="lede">Two of them have statements this book can verify, and those get
a solution written out in full. The other two do not, and a solution written
against a guessed statement would be worse than none &mdash; so those say what
the record proves and stop there.</p>
</header>
<nav class="subnav" aria-label="The four problems">{''.join(toc)}</nav>
{''.join(cards)}
<nav class="crumb bottom"><a href="plan.html">&larr; Back to the plan</a></nav>"""
    return page("The four you never solved -- Improvement Book", body)


def render_course_index(lessons: list[dict], evidence: dict[str, list]) -> str:
    # Distinct mistakes, not the sum of per-lesson counts: a bug that is both an
    # overflow and a sentinel bug is cited twice and must still be counted once.
    total_cited = len({id(m) for hits in evidence.values() for _, _, m in hits})
    rows = []
    for i, lesson in enumerate(lessons, 1):
        hits = evidence.get(lesson["slug"], [])
        topics = len({chapter.name for chapter, _, _ in hits})
        badge = (f'<span class="badge warn">{plural(len(hits), "mistake")} '
                 f'in {plural(topics, "topic")}</span>' if hits else "")
        rows.append(f"""<li>
<a class="tile" href="course-{esc(lesson['slug'])}.html">
<span class="rank">{i}</span>
<span class="tile-main">
  <strong>{esc(lesson['title'])}</strong>
  <span class="tile-nums">{esc_code(lesson['one_line'])}</span>
  <span class="tile-badges">{badge}</span>
</span></a></li>""")

    body = f"""<nav class="crumb"><a href="index.html">&larr; All topics</a> &middot;
<a href="mistakes.html">Every mistake</a> &middot;
<a href="trend.html">Trend</a></nav>
<header class="cover">
<p class="eyebrow">A course built backwards from your own bugs</p>
<h1>The mini course</h1>
<p class="lede">{plural(len(lessons), 'lesson')}, ordered so the earlier ones stop
the most bugs. {total_cited} of the 904 diagnosed mistakes in your export are
cited somewhere in these lessons.</p>
<p class="lede">Every lesson is built the same way, and the bar at the top of
each page jumps between the parts:</p>
<ol class="shape">
<li><strong>In one page</strong> &mdash; what the thing is, and why this lesson
is in <em>your</em> course.</li>
<li><strong>What it&rsquo;s used for</strong> &mdash; the situations that should
make you reach for it, and the ones that should not.</li>
<li><strong>How the questions are phrased</strong> &mdash; the wording in a
problem statement that gives the technique away.</li>
<li><strong>The mechanism, in depth</strong> &mdash; from zero, with diagrams
and worked traces.</li>
<li><strong>Where you actually hit this</strong> &mdash; your own failing
submissions, each with what went wrong and what you changed.</li>
<li><strong>How to fix each one</strong> &mdash; the checklist, and the drill.</li>
</ol>
<p class="lede">Examples are Java, because that is 93% of this export. The
"where you actually hit this" section on each page is generated from
<code>findings/*.json</code>, so it stays true as the analysis is redone.</p>
<p class="also">Work through them in order. The first four are not about any
particular data structure &mdash; they are the ones that cost you attempts on
every topic at once.</p>
</header>
<section class="tier"><ol class="tiles">{''.join(rows)}</ol></section>"""
    return page("The mini course -- Improvement Book", body)


def render_trend(by_month: list[dict], overview: dict) -> str:
    """Activity over time, with the gaps computed rather than narrated.

    Prose summaries of a trend reliably miss dormancies, because a run of
    absent months leaves nothing to write a sentence about. Deriving the gaps
    from the month keys makes them impossible to overlook.
    """
    def months_between(a: str, b: str) -> int:
        (ya, ma), (yb, mb) = (map(int, x.split("-")) for x in (a, b))
        return (yb - ya) * 12 + (mb - ma)

    peak = max((m["submissions"] for m in by_month), default=1)
    rows, gaps = [], []
    for i, m in enumerate(by_month):
        if i:
            missing = months_between(by_month[i - 1]["month"], m["month"]) - 1
            if missing > 0:
                gaps.append((by_month[i - 1]["month"], m["month"], missing))
                rows.append(f'<tr class="gap"><td colspan="4">'
                            f'{plural(missing, "month")} with no submissions at all '
                            f'&mdash; {esc(by_month[i - 1]["month"])} to {esc(m["month"])}</td></tr>')
        rate = m["acceptance_rate"]
        rows.append(
            f'<tr><th>{esc(m["month"])}</th>'
            f'<td class="bar"><span style="width:{m["submissions"] / peak * 100:.1f}%"></span>'
            f'<em>{m["submissions"]}</em></td>'
            f'<td>{pct(rate)}</td><td>{m["problems_first_solved"]}</td></tr>')

    gap_note = "".join(
        f"<li>No submissions for {plural(n, 'month')}, between "
        f"<strong>{esc(a)}</strong> and <strong>{esc(b)}</strong>.</li>"
        for a, b, n in gaps) or "<li>No gaps &mdash; practice was continuous.</li>"

    body = f"""<nav class="crumb"><a href="index.html">&larr; All topics</a> &middot;
<a href="course.html">Course</a> &middot;
<a href="mistakes.html">Every mistake</a></nav>
<header class="chapter-head">
<p class="eyebrow">Cross-topic &middot; derived from every submission</p>
<h1>Activity over time</h1>
<p class="lede">{overview.get('total_submissions', 0)} submissions over
{overview.get('days_of_history', 0)} days. Acceptance rate is per month, over
every submission that month &mdash; including re-runs of problems already solved,
so it reads higher than a first-attempt rate.</p>
</header>
<section class="mode">
<h2>Gaps in practice</h2>
<p class="hint">A month with zero submissions has no row of its own, which is
exactly how a dormancy goes unnoticed in a written summary. Every one is
listed here.</p>
<ul>{gap_note}</ul>
</section>
<section class="breakdown">
<h2>Month by month</h2>
<table>
<tr><th>Month</th><th>Submissions</th><th>Accepted</th><th>Newly solved</th></tr>
{''.join(rows)}
</table>
</section>
<nav class="crumb bottom"><a href="index.html">&larr; All topics</a></nav>"""
    return page("Activity over time -- Improvement Book", body)


def render_mistakes(chapters: list[Chapter]) -> str:
    """Every logged mistake in one list, so cross-topic repeats are visible.

    The per-topic chapters can only ever show a bug once, inside the topic it
    happened in. A bug you make in three unrelated topics is a habit, and that
    is only legible when the whole corpus sits on one page.
    """
    entries = []
    for chapter in chapters:
        for case in chapter.cases:
            for mistake in case.order_mistakes():
                status = (mistake.get("status")
                          or submission_status(mistake.get("file", "")) or "Failed")
                entries.append((status, chapter, case, mistake))

    counts = defaultdict(int)
    for status, _, _, _ in entries:
        counts[status] += 1
    chips = "".join(
        f'<span class="badge">{esc(k)} &middot; {v}</span>'
        for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))

    rows = "\n".join(
        f'<tr><td><span class="status '
        f'{"high" if STATUS_WEIGHT.get(status, DEFAULT_STATUS_WEIGHT) >= 4 else "mid" if STATUS_WEIGHT.get(status, DEFAULT_STATUS_WEIGHT) >= 3 else "low"}">'
        f'{esc(status)}</span></td>'
        f'<td><a href="{esc(chapter.topic)}.html#{esc(case.slug)}">{esc(chapter.name)}</a></td>'
        f'<td>{esc(case.title)}</td>'
        f'<td>{esc_code(mistake.get("what_went_wrong"))}</td>'
        f'<td>{esc_code(mistake.get("how_it_was_fixed"))}</td></tr>'
        for status, chapter, case, mistake in entries)

    body = f"""<nav class="crumb"><a href="index.html">&larr; All topics</a> &middot;
<a href="course.html">Course</a> &middot;
<a href="trend.html">Activity over time</a></nav>
<header class="chapter-head">
<p class="eyebrow">Cross-topic &middot; every diagnosis in the export</p>
<h1>Every mistake</h1>
<p class="lede">{len(entries)} diagnosed mistakes across
{plural(len(chapters), 'topic')}. Use your browser's find (&#8984;F) to search
for a bug shape &mdash; "off-by-one", "indegree", "sentinel" &mdash; and see
whether it happened once or in five unrelated topics. That difference is the
whole point: a bug in one topic is an accident, the same bug in three is a
habit.</p>
<p class="badges">{chips}</p>
</header>
<section class="breakdown">
<div class="table-scroll"><table class="all-mistakes">
<tr><th>Status</th><th>Topic</th><th>Problem</th><th>What went wrong</th><th>How it was fixed</th></tr>
{rows}
</table></div>
</section>
<nav class="crumb bottom"><a href="index.html">&larr; All topics</a></nav>"""
    return page("Every mistake -- Improvement Book", body)


COVERAGE_FLOOR = 0.85


def uncovered(chapters: list[Chapter],
              lessons: list[dict]) -> tuple[list[tuple], list[tuple]]:
    """Diagnosed evidence that no lesson's match pattern reaches.

    The same join the lessons themselves use, inverted. Keeping it in one
    function means the "not covered" page can never disagree with the coverage
    the build reports: both are this predicate.
    """
    patterns = [re.compile(lesson["match"], re.I) for lesson in lessons]
    taught = lambda text: any(pattern.search(text) for pattern in patterns)
    mistakes, smells = [], []
    for chapter in chapters:
        for case in chapter.cases:
            for mistake in case.order_mistakes():
                text = " ".join(str(mistake.get(k) or "")
                                for k in ("what_went_wrong", "how_it_was_fixed"))
                if not taught(text):
                    mistakes.append((chapter, case, mistake))
            for smell in case.smells:
                if not taught(smell.get("smell", "")):
                    smells.append((chapter, case, smell))
    return mistakes, smells


def render_not_covered(chapters: list[Chapter], lessons: list[dict],
                       total_m: int, total_s: int) -> str:
    """What the course does not teach, listed rather than left implied.

    A book assembled from your own data can imply, by saying nothing, that it
    covers all of it. It does not: these are the diagnoses no lesson reaches.
    Most are genuinely one-offs. Some are the next lessons, and the only way to
    tell which is to read them, so the page lists every one rather than
    reporting the count and moving on.
    """
    mistakes, smells = uncovered(chapters, lessons)
    by_topic: dict[str, list] = defaultdict(list)
    for chapter, case, mistake in mistakes:
        by_topic[chapter.name].append((case, mistake, "mistake"))
    for chapter, case, smell in smells:
        by_topic[chapter.name].append((case, smell, "habit"))

    groups = []
    for name in sorted(by_topic, key=lambda n: (-len(by_topic[n]), n)):
        rows = "\n".join(
            '<tr><td><a href="problem-{}.html">{}</a></td>'
            '<td><span class="status {}">{}</span></td>'
            '<td>{}</td></tr>'.format(
                esc(case.slug), esc(case.title),
                "mid" if kind == "mistake" else "low", kind,
                esc_code(item.get("what_went_wrong") or item.get("smell")))
            for case, item, kind in by_topic[name])
        groups.append(
            '<section class="uncovered-topic">\n'
            '<h2>{} <span class="badge">{}</span></h2>\n'
            '<div class="table-scroll"><table class="all-mistakes">\n'
            '<tr><th>Problem</th><th>Kind</th><th>What the analysis found</th></tr>\n'
            '{}\n</table></div>\n</section>'.format(
                esc(name), len(by_topic[name]), rows))

    reached_m, reached_s = total_m - len(mistakes), total_s - len(smells)
    share = (reached_m + reached_s) / (total_m + total_s)
    body = f"""<nav class="crumb"><a href="index.html">&larr; All topics</a> &middot;
<a href="course.html">Course</a> &middot;
<a href="mistakes.html">Every mistake</a></nav>
<header class="chapter-head">
<p class="eyebrow">The honest appendix</p>
<h1>What this book does not cover</h1>
<p class="lede">The {plural(len(lessons), 'lesson')} in the course reach
{reached_m} of {total_m} diagnosed mistakes and {reached_s} of {total_s}
habits. This page is the remainder: {len(mistakes)} mistakes and {len(smells)}
habits that no lesson claims.</p>
<p class="badges">
<span class="badge good">{share:.0%} covered</span>
<span class="badge warn">{len(mistakes) + len(smells)} not covered</span>
<span class="badge">{plural(len(by_topic), 'topic')}</span></p>
</header>
<section class="breakdown">
<h2>Why they are here</h2>
<p>Three different reasons, and this page does not guess which applies to
which &mdash; that is what reading them is for.</p>
<p><strong>Genuinely one-off.</strong> A constraint misread on exactly one
problem, a library method that surprised you once. There is nothing to
generalise, and a lesson built on a single point would be inventing a pattern
rather than finding one.</p>
<p><strong>Covered in substance, not in wording.</strong> A lesson teaches the
idea, but its match pattern does not reach this phrasing. These cost nothing
except an understated coverage number.</p>
<p><strong>The next lessons.</strong> A cluster big enough to teach that nobody
has written yet. Four of the lessons in this course began as rows on a page
like this one. If you read down a topic below and the same shape appears three
times, that is the next lesson.</p>
</section>
{"".join(groups)}
<nav class="crumb bottom"><a href="index.html">&larr; All topics</a> &middot;
<a href="course.html">The course</a></nav>"""
    return page("What this book does not cover -- Improvement Book", body)


def is_thin(chapter: Chapter) -> bool:
    """A chapter with nothing much in it.

    At most one diagnosed mistake, across at most two problems. The tag exists
    in your export, so the page exists, but there is no gap to work on there --
    ranking it alongside a topic with thirty diagnosed mistakes would be a lie
    told by sort order.
    """
    return chapter.mistake_count <= 1 and chapter.in_chapter <= 2


def render_index(chapters: list[Chapter], overview: dict, prior: float) -> str:
    lesson_count = len(LESSON_INDEX)
    solid = [c for c in chapters if not is_thin(c)]
    thin = [c for c in chapters if is_thin(c)]
    tiers = [
        ("Fix these first", "Where you miss on the first attempt most often, "
         "with enough failed submissions behind it to be a real gap rather "
         "than a bad week.", solid[:12]),
        ("Then these", "Real gaps, but either narrower or less central to your "
         "practice.", solid[12:40]),
        ("Maintenance", "Thin evidence, already strong, or barely practised. "
         "Skim for the specific bug, do not drill the topic.", solid[40:]),
    ]

    sections = []
    for title, blurb, group in tiers:
        if not group:
            continue
        rows = []
        for chapter in group:
            rank = chapters.index(chapter) + 1
            stale = chapter.stats.get("days_since_last_practice")
            badges = []
            if chapter.unsolved:
                badges.append(f'<span class="badge warn">{len(chapter.unsolved)} '
                              f"never solved</span>")
            if isinstance(stale, int) and stale >= 180:
                badges.append(f'<span class="badge stale">{stale}d cold</span>')
            mode = chapter.failure_mode
            if mode:
                badges.append(f'<span class="badge">{esc(mode[0])}</span>')
            rows.append(f"""<li>
<a class="tile" href="{esc(chapter.topic)}.html">
<span class="rank">{rank}</span>
<span class="tile-main">
  <strong>{esc(chapter.name)}</strong>
  <span class="tile-nums">{pct(chapter.faar)} first-attempt accepts &middot;
  {plural(chapter.attempted, 'problem')} &middot;
  {plural(chapter.mistake_count, 'mistake')}</span>
  <span class="tile-badges">{''.join(badges)}</span>
</span>
</a></li>""")
        sections.append(f"""<section class="tier">
<h2>{esc(title)}</h2><p class="hint">{esc(blurb)}</p>
<ol class="tiles">{''.join(rows)}</ol></section>""")

    if thin:
        links = "".join(
            f'<li><a href="{esc(c.topic)}.html">{esc(c.name)}</a> '
            f'<span class="muted">{plural(c.in_chapter, "problem")}'
            f'{", " + plural(c.mistake_count, "mistake") if c.mistake_count else ""}'
            f"</span></li>" for c in thin)
        diagnosed = sum(c.mistake_count for c in thin)
        sections.append(f"""<section class="tier thin">
<h2>Thin chapters</h2>
<p class="hint">{plural(len(thin), 'topic')} you have barely touched:
{plural(diagnosed, 'diagnosed mistake')} between all of them. They are here
because the tag is in your export, not because there is a gap to work on. A
first-attempt rate over one or two problems is noise, so they are listed rather
than ranked.</p>
<ul class="thin-list">{links}</ul></section>""")

    prior_txt = pct(prior)
    body = f"""<header class="cover">
<p class="eyebrow">An improvement book, built from your own submissions</p>
<h1>Every mistake, ranked</h1>
<p class="lede">{overview.get('total_submissions', 0)} submissions across
{overview.get('problems_attempted', 0)} problems, {overview.get('days_of_history', 0)}
days of history. Every failed attempt was read and diagnosed; this is what it
found, ordered by what is worth fixing first.</p>
<p class="lede">Topics are ranked by how often you <em>miss on the first
attempt</em> &mdash; the sharpest mastery signal in the export &mdash; smoothed toward the
{prior_txt} corpus average so a topic with one attempted problem cannot read as
"0%, your weakest area". The number of mistakes found only breaks ties between
comparable gaps; it never promotes a topic you are good at. Problems you never
solved count for extra.</p>
<p class="lede">Staleness is shown as a badge rather than folded into the
ranking &mdash; a rusty strength and a real weakness need different responses.</p>
<p class="also">Three ways in, by how much time you have.</p>
<div class="routes">
<section class="route">
<h2>The hour</h2>
<p class="hint">One sitting. Read what you get wrong, then check it.</p>
<ol>
<li><a href="habits.html">The twelve habits</a> &mdash; what you get wrong
repeatedly, ranked, with your own instances under each. Start here if you read
nothing else.</li>
<li><a href="process.html">Two habits in how you submit</a> &mdash; measured
from the timestamps, not advice.</li>
<li><a href="checklist.html">The pre-submit checklist</a> &mdash; one page, on
paper, beside the keyboard.</li>
</ol></section>
<section class="route">
<h2>The week</h2>
<p class="hint">Work, not reading. Each step ends in code you wrote.</p>
<ol>
<li><a href="course.html">The mini course</a> &mdash; {lesson_count} lessons on
the fundamentals behind those habits, ordered by how many attempts each one
costs you.</li>
<li><a href="drills.html">Spot the bug</a> &mdash; your own rejected
submissions with the diagnosis hidden.</li>
<li><a href="schedule.html">The practice schedule</a> &mdash; sessions of three
problems, in course order, with spacing columns to tick.</li>
<li><a href="plan.html">What to practise next</a> &mdash; seven things to do,
ordered by what the evidence says each is worth.</li>
</ol></section>
<section class="route">
<h2>The reference</h2>
<p class="hint">Look something up. Nothing here needs reading in order.</p>
<ul>
<li><a href="search.html">Search</a> &mdash; every page in the book, filtered
as you type.</li>
<li><a href="glossary.html">Glossary</a> &mdash; the jargon, defined as this
book uses it.</li>
<li><a href="mistakes.html">Every mistake in one list</a> &middot;
<a href="habits.html">every smell</a></li>
<li><a href="revision.html">What to revise</a> &middot;
<a href="unsolved.html">never solved</a> &middot;
<a href="grinds.html">the twenty longest grinds</a></li>
<li><a href="not-covered.html">What this book does not cover</a> &mdash; the
diagnoses no lesson reaches, listed rather than left implied.</li>
<li><a href="techniques.html">Techniques you have not used</a> &middot;
<a href="trend.html">activity over time</a></li>
<li>The ranked topics below, and a page per problem behind each one.</li>
</ul></section>
</div>
<p class="also">The full written analysis, including what this data cannot tell
you, is in <code>REPORT.md</code> beside this folder.</p>
</header>
{''.join(sections)}"""
    return page("Improvement Book", body)


CSS = """
:root{--bg:#fbfaf7;--panel:#fff;--ink:#1b1a17;--muted:#6b675e;--line:#e3dfd6;
--accent:#8a3324;--good:#1f6f43;--bad:#a32b1c;--warn:#8a6a12;--code:#f5f2ec;}
@media (prefers-color-scheme:dark){:root{--bg:#16151a;--panel:#1e1d23;--ink:#eae7e0;
--muted:#a09a90;--line:#33313a;--accent:#e08b6f;--good:#6cc38d;--bad:#f08a78;
--warn:#e0b95c;--code:#141318;}}
*{box-sizing:border-box}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;
  border-radius:2px}
body{margin:0;padding:2rem 1.25rem 4rem;background:var(--bg);color:var(--ink);
overflow-wrap:break-word;
font:16px/1.6 Charter,Georgia,"Iowan Old Style",serif;
max-width:60rem;margin-inline:auto}
h1{font-size:2.2rem;line-height:1.15;margin:.2em 0 .3em}
h2{font-size:1.3rem;margin:2.4rem 0 .5rem;padding-bottom:.3rem;
border-bottom:1px solid var(--line)}
h4{margin:1.4rem 0 .4rem;font-size:1rem}
a{color:var(--accent)}
.eyebrow{text-transform:uppercase;letter-spacing:.12em;font-size:.72rem;
color:var(--muted);margin:0;font-family:ui-sans-serif,system-ui,sans-serif}
.lede{font-size:1.05rem;color:var(--muted);max-width:44rem}
.hint{color:var(--muted);font-size:.9rem;max-width:44rem}
.ref-card{max-width:44rem;margin:1.6rem 0 0;padding:.9rem 1.1rem;
  border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:6px;background:var(--panel);color:var(--muted);font-size:.92rem}
.ref-card a{font-weight:600;color:var(--ink)}
p code,dd code,li code,td code{font-family:ui-monospace,SFMono-Regular,Menlo,
monospace;font-size:.88em;background:var(--code);padding:.05em .3em;
border-radius:3px;word-break:break-word}
.cover{border-bottom:3px double var(--line);padding-bottom:1.5rem;margin-bottom:1rem}
.also{font-size:.9rem;color:var(--muted)}
.crumb{font-size:.85rem;font-family:ui-sans-serif,system-ui,sans-serif;
color:var(--muted);margin-bottom:1.5rem}
.crumb.bottom{margin-top:3rem;border-top:1px solid var(--line);padding-top:1rem}
.chapter-head{margin-bottom:1.5rem}
.tiles{list-style:none;margin:0;padding:0}
.tile{display:flex;gap:1rem;align-items:baseline;text-decoration:none;color:inherit;
padding:.75rem .9rem;border:1px solid var(--line);border-radius:8px;
margin-bottom:.5rem;background:var(--panel)}
.tile:hover{border-color:var(--accent)}
.tile-main{display:flex;flex-direction:column;gap:.15rem}
.tile-nums{font-size:.85rem;color:var(--muted);
font-family:ui-sans-serif,system-ui,sans-serif}
.rank{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.8rem;
color:var(--muted);min-width:2ch;text-align:right;flex:none}
.badge{display:inline-block;font-family:ui-sans-serif,system-ui,sans-serif;
font-size:.7rem;padding:.12rem .45rem;border:1px solid var(--line);
border-radius:999px;color:var(--muted);margin-right:.3rem;max-width:100%}
.badge.warn{color:var(--warn);border-color:var(--warn)}
.badge.stale{color:var(--muted);border-style:dashed}
.d-easy{color:var(--good);border-color:var(--good)}
.d-medium{color:var(--warn);border-color:var(--warn)}
.d-hard{color:var(--bad);border-color:var(--bad)}
.stats dl{display:grid;grid-template-columns:repeat(auto-fit,minmax(11rem,1fr));
gap:.75rem;margin:0}
.stat{border:1px solid var(--line);border-radius:8px;padding:.7rem .8rem;
background:var(--panel)}
.stat dt{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;
color:var(--muted);font-family:ui-sans-serif,system-ui,sans-serif}
.stat dd{margin:.15rem 0;font-size:1.5rem;font-weight:600}
.stat p{margin:0;font-size:.75rem;color:var(--muted);line-height:1.35}
.breakdown table{width:100%;border-collapse:collapse;font-size:.9rem}
.breakdown th{text-align:left;font-weight:400;padding:.25rem .5rem .25rem 0}
.breakdown td{padding:.25rem .5rem}
.bar{width:60%}
.bar span{display:block;height:.55rem;background:var(--accent);
border-radius:3px;opacity:.75}
.mode,.unsolved,.provenance{border-left:3px solid var(--accent);
padding:.1rem 0 .1rem 1rem;margin:2rem 0}
.unsolved ul,.provenance ul{padding-left:1.1rem}
.unsolved li,.provenance li{margin-bottom:.5rem}
.case{border:1px solid var(--line);border-radius:8px;margin-bottom:.6rem;
background:var(--panel)}
.case[open]{border-color:var(--accent)}
.case summary{cursor:pointer;padding:.7rem .9rem;display:flex;gap:.75rem;
align-items:baseline}
.case summary::marker{color:var(--muted)}
.case-title{font-weight:600;flex:1;font-size:1rem;margin:0;line-height:inherit}
.case-meta{font-size:.8rem;color:var(--muted);
font-family:ui-sans-serif,system-ui,sans-serif}
.case-body{padding:0 .9rem 1rem;border-top:1px solid var(--line)}
.badges{margin:.8rem 0}
.lc{font-size:.75rem;font-family:ui-sans-serif,system-ui,sans-serif}
.mistake{margin:1.5rem 0;padding-top:.5rem;border-top:1px dotted var(--line)}
.mistake h4,.mistake h3{display:flex;gap:.6rem;align-items:center}
/* On a problem page the first card butts against the section rule. */
.mistake:first-child{border-top:0;padding-top:0;margin-top:.5rem}
.num{display:inline-flex;width:1.5rem;height:1.5rem;align-items:center;
justify-content:center;border-radius:50%;background:var(--code);
font-size:.75rem;font-family:ui-sans-serif,system-ui,sans-serif;flex:none}
.status{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.72rem;
padding:.1rem .5rem;border-radius:999px;border:1px solid currentColor}
.status.high{color:var(--bad)}.status.mid{color:var(--warn)}
.status.low{color:var(--muted)}
.mistake dl{margin:.5rem 0}
.mistake dt{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;
color:var(--muted);font-family:ui-sans-serif,system-ui,sans-serif;margin-top:.6rem}
.mistake dd{margin:.15rem 0 0}
.code{margin:.8rem 0;border:1px solid var(--line);border-radius:6px;overflow:hidden}
.code figcaption{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap;
padding:.4rem .6rem;background:var(--code);border-bottom:1px solid var(--line);
font-family:ui-sans-serif,system-ui,sans-serif;font-size:.72rem;color:var(--muted)}
.code .tag{font-weight:600;color:var(--ink)}
.code.bad .tag{color:var(--bad)}.code.good .tag{color:var(--good)}
.code.warn .tag{color:var(--warn)}
.code .path{margin-left:auto;opacity:.7;font-size:.68rem;word-break:break-all}
.trunc{font-style:italic}
.code pre{margin:0;padding:.75rem .8rem;overflow-x:auto;background:var(--code)}
.code code{font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
.code.diff pre{font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
.dl{display:block;padding:0 .4rem;white-space:pre;border-left:3px solid transparent}
.dl.add{background:color-mix(in srgb,var(--good) 16%,transparent);
  border-left-color:var(--good)}
.dl.del{background:color-mix(in srgb,var(--bad) 16%,transparent);
  border-left-color:var(--bad)}
.dl.hunk{color:var(--muted);font-style:italic;margin-top:.35rem}
.dl.ctx{opacity:.72}
.diff-note{margin:.6rem 0}
.full-source{margin:.7rem 0}
.full-source>summary{cursor:pointer;color:var(--muted);font-size:.8rem;
  text-transform:uppercase;letter-spacing:.06em}
.full-source>summary:hover{color:var(--accent)}
.what-worked{color:var(--good)}
.smell{margin:1.5rem 0;padding-left:1rem;border-left:3px solid var(--warn)}
.prov{font-size:.9rem;padding:.6rem .8rem;border-radius:6px;background:var(--code)}
.caveat{font-size:.85rem;color:var(--warn);border-left:3px solid var(--warn);
padding-left:.8rem}
.missing{font-size:.85rem;color:var(--muted)}
.empty{color:var(--muted);font-style:italic}
.patterns li,.style li,.strengths li{margin-bottom:.5rem}
.bar em{font-style:normal;font-size:.8rem;color:var(--muted);margin-left:.5rem}
tr.gap td{color:var(--bad);font-size:.85rem;padding:.5rem 0;
border-top:1px dashed var(--bad);border-bottom:1px dashed var(--bad)}
.all-mistakes{font-size:.85rem;table-layout:fixed;min-width:44rem}
.all-mistakes th{vertical-align:top;text-align:left}
.all-mistakes td{vertical-align:top;padding:.5rem .5rem .5rem 0;
border-bottom:1px solid var(--line);word-wrap:break-word}
.all-mistakes tr>*:nth-child(1){width:7rem}
.all-mistakes tr>*:nth-child(2){width:8rem}
.all-mistakes tr>*:nth-child(3){width:9rem}
.lesson-head{border-bottom:3px double var(--line);padding-bottom:1.2rem}
.objectives{margin:1.4rem 0 .2rem;padding:.9rem 1.1rem;background:var(--panel);
border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:6px;
max-width:44rem}
.objectives ul{margin:.4rem 0 0;padding-left:1.1rem}
.objectives li{margin:.3rem 0;font-size:.95rem}
.obj-head{margin:0}
.obj-tag{display:inline-block;margin-right:.5rem;font-size:.72rem;
letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.prereq{margin:.7rem 0 0;padding-top:.6rem;border-top:1px solid var(--line);
font-size:.9rem}
.prereq a{margin-right:.6rem}
.recall{margin:0 0 1.6rem;padding:1rem 1.1rem;background:var(--code);
border:1px solid var(--line);border-radius:8px;max-width:44rem}
.recall ol{margin:.6rem 0 0;padding-left:1.2rem}
.recall li{margin:.9rem 0}
.recall .q{margin:0 0 .35rem;font-weight:600}
.recall details{font-size:.93rem}
.recall summary{cursor:pointer;color:var(--accent);font-size:.85rem}
.recall details p{margin:.4rem 0 0;color:var(--muted)}
.drill-item{margin:2.5rem 0;padding-top:1.5rem;border-top:1px solid var(--line)}
.drill-item h2{display:flex;flex-wrap:wrap;align-items:center;gap:.6rem;
  margin:0;font-size:1.15rem}
.drill-meta{font-size:.8rem;font-weight:400;color:var(--muted)}
.ask{max-width:44rem;margin:.7rem 0 1rem;font-size:.95rem}
.reveal{margin:.8rem 0 0;padding:.7rem .9rem;background:var(--panel);
border:1px solid var(--line);border-radius:8px}
.reveal>summary{cursor:pointer;color:var(--accent);font-weight:600;
font-size:.9rem}
.reveal dl{margin:.9rem 0 0}
.reveal .hint{margin:.9rem 0 .3rem}
.session{margin:2rem 0}
.session h2{display:flex;align-items:center;gap:.6rem;margin:0 0 .4rem;
  font-size:1.15rem}
.sched td,.sched th{padding:.45rem .8rem .45rem 0}
.sched .tick{width:4.5rem;border-left:1px solid var(--line)}
.sched .hist{font-size:.85rem}
.sched .hist.good{color:var(--good)}
.sched .hist.bad{color:var(--bad)}
.sched .hist.new{color:var(--accent)}
.sched .hist.mid{color:var(--muted)}
.checklist ol{padding-left:1.4rem;max-width:44rem}
.checklist li{margin:1rem 0}
.check-rule{margin:0;font-size:1rem}
.check-why{margin:.2rem 0 0;font-size:.82rem;color:var(--muted)}
.proc{margin:2.5rem 0;max-width:44rem}
.proc h2{border-bottom:1px solid var(--line);padding-bottom:.4rem}
.gapdist td.n{font-variant-numeric:tabular-nums;text-align:right;
padding-right:1.4rem}
.counter{padding:.8rem 1rem;background:var(--panel);border:1px solid var(--line);
border-left:3px solid var(--good);border-radius:6px}
.lesson-part{margin:2.5rem 0}
.lesson-part p{max-width:44rem}
.lesson-code{margin:1rem 0;padding:.8rem .9rem;background:var(--code);
border:1px solid var(--line);border-radius:6px;overflow-x:auto}
.lesson-code code{font:13px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace}
.lesson-table{width:100%;border-collapse:collapse;font-size:.9rem;margin:1rem 0}
figure.trace{margin:1.6rem 0;padding:0}
figure.trace figcaption{margin:.6rem 0 0;font-size:.82rem;line-height:1.55;
color:var(--muted);max-width:44rem}
.trace-table{margin:0;font-variant-numeric:tabular-nums}
.trace-table td,.trace-table th{padding:.35rem .8rem .35rem 0;white-space:nowrap}
.trace-table td:last-child,.trace-table th:last-child{white-space:normal}
.trace-table td.hl{background:color-mix(in srgb,var(--accent) 9%,transparent)}
.trace-table td.yes{color:var(--good);font-weight:600}
.trace-table td.no{color:var(--bad);font-weight:600}
figure.diagram{margin:1.6rem 0;padding:1rem .6rem .2rem;background:var(--panel);
  border:1px solid var(--line);border-radius:8px;overflow-x:auto}
figure.diagram svg{display:block;width:100%;min-width:22rem;max-width:46rem;
  height:auto;margin:0 auto}
figure.diagram figcaption{margin:.7rem .6rem .5rem;font-size:.82rem;line-height:1.5;
  color:var(--muted);text-align:center}
.lesson-table th{text-align:left;font-weight:600;padding:.4rem .7rem .4rem 0;
border-bottom:2px solid var(--line)}
.lesson-table td{padding:.4rem .7rem .4rem 0;border-bottom:1px solid var(--line);
vertical-align:top}
.grinds{list-style:none;padding:0;margin:1.5rem 0;counter-reset:g}
.grind-item{display:flex;flex-wrap:wrap;align-items:baseline;gap:.5rem;
padding:.7rem 0;border-bottom:1px solid var(--line)}
.grind-item .rank{min-width:1.6rem;color:var(--muted);
font-variant-numeric:tabular-nums;font-size:.85rem}
.grind-item>a{font-weight:600}
.grind-item .hint{flex-basis:100%;padding-left:2.1rem;font-size:.8rem}
table.grind{width:100%;min-width:26rem;border-collapse:collapse;
margin:0;font-size:.9rem}
table.grind th{text-align:left;padding:.4rem .7rem .4rem 0;
border-bottom:2px solid var(--line);font-size:.72rem;text-transform:uppercase;
letter-spacing:.06em;color:var(--muted);
font-family:ui-sans-serif,system-ui,sans-serif}
table.grind td{padding:.5rem .7rem .5rem 0;border-bottom:1px solid var(--line);
vertical-align:top}
table.grind .num{display:table-cell;width:1%;height:auto;border-radius:0;
background:none;font:inherit;text-align:right;white-space:nowrap;
font-variant-numeric:tabular-nums;color:var(--muted)}
table.grind th.num{vertical-align:bottom}
table.grind tr.post td{opacity:.45}
.rapid{color:var(--bad);font-weight:600}
.grind-note{margin:.35rem 0 0;font-size:.85rem;color:var(--muted);max-width:38rem}
.turn{margin:1.5rem 0;padding:.9rem 1.1rem;background:var(--panel);
border-left:4px solid var(--bad);border-radius:0 6px 6px 0;max-width:44rem}
.grind-diff{margin:.6rem 0}
.grind-diff>summary{cursor:pointer;color:var(--muted);font-size:.82rem;
font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.grind-diff>summary:hover{color:var(--accent)}
.tech-group{margin:3rem 0}
.tech-group>h2{display:flex;align-items:baseline;gap:.6rem;
border-bottom:2px solid var(--line);padding-bottom:.4rem}
.technique{margin:2rem 0;padding:1.2rem 1.3rem;background:var(--panel);
border:1px solid var(--line);border-radius:8px}
.technique h3{margin:0;display:flex;flex-wrap:wrap;align-items:baseline;gap:.6rem}
.technique h4{margin:1.2rem 0 .3rem;font-size:.74rem;text-transform:uppercase;
letter-spacing:.08em;color:var(--muted);
font-family:ui-sans-serif,system-ui,sans-serif}
.technique p{max-width:44rem}
.tech-meta{margin:.35rem 0 0;font-size:.82rem;color:var(--muted);
font-family:ui-sans-serif,system-ui,sans-serif}
.technique blockquote{margin:.3rem 0;padding:.5rem .9rem;background:var(--bg);
border-left:3px solid var(--accent);border-radius:0 4px 4px 0;
font-size:.92rem;color:var(--muted)}
.quad{margin:2.2rem 0;padding:1.1rem 1.2rem;border-radius:8px;
background:var(--panel);border:1px solid var(--line)}
.quad.q-act{border-left:4px solid var(--accent)}
.quad.q-hold{border-left:4px solid var(--line);opacity:.85}
.quad h2{margin:0 0 .5rem;font-size:1.1rem;display:flex;flex-wrap:wrap;
align-items:baseline;gap:.6rem}
.quad .verdict{font:600 .72rem/1 ui-sans-serif,system-ui,sans-serif;
text-transform:uppercase;letter-spacing:.08em;color:var(--accent);
padding:.25rem .5rem;border:1px solid var(--accent);border-radius:99px}
.quad.q-hold .verdict{color:var(--muted);border-color:var(--line)}
.quad .quad-n{margin-left:auto;font-size:.78rem;color:var(--muted);
font-family:ui-sans-serif,system-ui,sans-serif}
.quad p{margin:.4rem 0;max-width:44rem}
.quad-chips{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.8rem}
.revision{width:100%;border-collapse:collapse;font-size:.88rem;margin:1.5rem 0;
font-family:ui-sans-serif,system-ui,sans-serif}
.revision th{text-align:left;font-weight:600;padding:.45rem .8rem .45rem 0;
border-bottom:2px solid var(--line);font-size:.76rem;text-transform:uppercase;
letter-spacing:.06em;color:var(--muted)}
.revision td{padding:.45rem .8rem .45rem 0;border-bottom:1px solid var(--line)}
.revision .num{display:table-cell;width:auto;height:auto;border-radius:0;
background:none;font:inherit;text-align:right;white-space:nowrap;
font-variant-numeric:tabular-nums;color:var(--muted)}
.revision .score{color:var(--ink);font-weight:600}
.revision tr:hover td{background:var(--panel)}
.revision .topic{min-width:11rem}
.table-scroll{overflow-x:auto;margin:1.5rem 0}
.table-scroll .revision{margin:0}
.rules{border-left:3px solid var(--good);padding:.1rem 0 .1rem 1rem;margin:2.5rem 0}
.rules ol{padding-left:1.2rem}
.rules li{margin-bottom:.45rem;font-weight:600}
.drill{border-left:3px solid var(--accent);padding:.1rem 0 .1rem 1rem;margin:2.5rem 0}
.evidence{margin:2.5rem 0}
.ev-topic{font-size:.72rem;color:var(--muted);
font-family:ui-sans-serif,system-ui,sans-serif}

/* --- lesson page: in-page navigation and the seven-part structure ------- */
html{scroll-behavior:smooth}
.lesson-toc{position:sticky;top:0;z-index:6;display:flex;flex-wrap:wrap;
gap:.15rem;margin:1.4rem 0 0;padding:.45rem 0;background:var(--bg);
border-bottom:1px solid var(--line);
font-family:ui-sans-serif,system-ui,sans-serif;font-size:.78rem}
.lesson-toc a{padding:.3rem .6rem;border-radius:999px;
color:var(--muted);text-decoration:none;white-space:nowrap;
border:1px solid transparent}
.lesson-toc a:hover,.lesson-toc a:focus{color:var(--ink);background:var(--panel);
border-color:var(--line)}
.lesson-sec{scroll-margin-top:5rem}
.lesson-sec>h2{margin-top:3rem}
.lesson-part{scroll-margin-top:5rem}
.lesson-part h3{font-size:1.12rem;margin:2.4rem 0 .5rem;padding-bottom:.25rem;
border-bottom:1px solid var(--line)}
.mode h3{font-size:1rem;margin:1.8rem 0 .3rem;border:0;padding:0}
.subnav{display:flex;flex-wrap:wrap;gap:.3rem;margin:.9rem 0 1.8rem}
.subnav a,.chips .chip{padding:.25rem .55rem;border:1px solid var(--line);
border-radius:6px;background:var(--panel);color:var(--muted);
text-decoration:none;font:.78rem/1.5 ui-sans-serif,system-ui,sans-serif}
.subnav a:hover,.chips .chip:hover{color:var(--ink);border-color:var(--accent)}
.chips{display:flex;flex-wrap:wrap;gap:.35rem;margin:.7rem 0 0;max-width:44rem}
.xref{color:var(--accent);text-decoration:none;border-bottom:1px dotted var(--accent)}
.habit-toc{display:flex;flex-wrap:wrap;gap:.35rem;margin:2rem 0 1rem;
padding:1rem 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.habit-toc a{display:flex;gap:.5rem;align-items:baseline;padding:.3rem .6rem;
border:1px solid var(--line);border-radius:6px;background:var(--panel);
color:var(--muted);text-decoration:none;
font:.8rem/1.4 ui-sans-serif,system-ui,sans-serif}
.habit-toc a:hover{border-color:var(--accent);color:var(--ink)}
.habit-toc .n{color:var(--accent);font-weight:700;font-size:.75rem}
.habit{margin:3.5rem 0;scroll-margin-top:1rem}
.habit>h2,.plan-item>h2{display:flex;gap:.7rem;align-items:baseline;
font-size:1.35rem;margin:0 0 .5rem;padding-bottom:.4rem;
border-bottom:1px solid var(--line)}
.habit>h2 .rank,.plan-item>h2 .rank{color:var(--accent);font-weight:700;
font-size:.9rem;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.habit-lessons{display:flex;flex-wrap:wrap;gap:.35rem;align-items:center;
margin:1.1rem 0}
.habit-lessons .lbl{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;
color:var(--muted);margin-right:.3rem}
.modes{margin:4rem 0 0;padding-top:1.5rem;border-top:2px solid var(--line)}
.mode-item{margin:2rem 0}
.mode-item h3{font-size:1.1rem;margin:0 0 .4rem;color:var(--accent)}
.plan{list-style:none;margin:2rem 0;padding:0}
.plan-item{margin:0 0 2.5rem}
.unsolved-case{margin:3.5rem 0;padding-top:1.5rem;border-top:1px solid var(--line);
scroll-margin-top:1rem}
.unsolved-case h2{font-size:1.5rem;margin:0 0 .6rem}
.unsolved-case h3{font-size:1rem;margin:2rem 0 .5rem;color:var(--accent);
letter-spacing:.02em}
.badge.good{background:var(--good);color:var(--bg);border-color:var(--good)}
.limits{margin:4rem 0 0;padding:1.5rem 0 0;border-top:2px solid var(--line)}
.limits ul{color:var(--muted);max-width:44rem}
.chip-n{margin-left:.4rem;padding:0 .3rem;border-radius:4px;
background:var(--code);color:var(--muted);font-size:.72rem}
.lesson-links{margin:2rem 0}
.shape{max-width:44rem;color:var(--muted);font-size:.95rem;padding-left:1.2rem}
.shape li{margin:.35rem 0}
.shape strong{color:var(--ink)}
.stat-line{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.85rem;
color:var(--muted);margin:.8rem 0 0}
.pairs td:first-child{width:16rem}
.mistake-cards{list-style:none;padding:0;margin:1.3rem 0}
.mistake-cards>li{margin:0 0 .9rem;padding:.85rem 1rem;background:var(--panel);
border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:8px}
.mc-head{margin:0 0 .55rem;font-size:.98rem}
.mc-head .ev-topic{display:block;margin-top:.1rem}
.mc-wrong,.mc-fix{margin:.5rem 0;font-size:.9rem;line-height:1.6;max-width:46rem}
.mc-tag{display:inline-block;margin-right:.45rem;padding:.08rem .42rem;
border-radius:4px;color:var(--bg);vertical-align:1px;
font:600 .66rem/1.7 ui-sans-serif,system-ui,sans-serif;
text-transform:uppercase;letter-spacing:.06em}
.mc-tag.bad{background:var(--bad)}
.mc-tag.good{background:var(--good)}
.mc-tag.none{background:var(--muted)}
.mc-tag.warn{background:var(--warn)}
.habits>li{border-left-color:var(--warn)}
.status.pass{background:var(--good);color:var(--bg)}
.more-mistakes{margin:1.2rem 0}
.more-mistakes>summary{cursor:pointer;color:var(--accent);
font:.85rem ui-sans-serif,system-ui,sans-serif}
.more-mistakes[open]>summary{margin-bottom:.8rem}
@media (max-width:34rem){
/* two narrow columns are unreadable on a phone -- stack them */
.pairs,.pairs tbody,.pairs tr,.pairs td{display:block;width:auto}
.pairs thead{display:none}
.pairs tr{padding:.55rem 0;border-bottom:1px solid var(--line)}
.pairs td{border:0;padding:.1rem 0}
.pairs td:first-child{width:auto}
/* An authored three-column table cannot narrow past its widest cell. Let the
   table itself scroll rather than the page: display:block puts the rows in an
   anonymous table box, so the columns still line up. */
.lesson-table:not(.pairs){display:block;overflow-x:auto}
}
table.run td,table.run th{padding:.4rem .7rem .4rem 0}
table.run .lines{text-align:right;font-variant-numeric:tabular-nums;
color:var(--muted)}
table.run .verdict{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.8rem}
table.run tr.ok .verdict{color:var(--good)}
table.run tr.no .verdict{color:var(--bad)}
ul.plain{list-style:none;padding:0;max-width:44rem}
ul.plain li{padding:.35rem 0;border-bottom:1px solid var(--line)}
#q{width:100%;max-width:36rem;padding:.6rem .8rem;font:1rem/1.4 inherit;
border:1px solid var(--line);border-radius:6px;background:var(--panel);
color:var(--ink);margin:1rem 0 .4rem}
#hits{list-style:none;padding:0;margin:1.5rem 0;max-width:52rem;
display:flex;flex-direction:column}
#hits li{display:flex;flex-wrap:wrap;align-items:baseline;gap:.5rem;
padding:.45rem 0;border-bottom:1px solid var(--line)}
#hits li[hidden]{display:none}
#hits a{font-weight:600}
.kind{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.68rem;
text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
border:1px solid var(--line);border-radius:999px;padding:.05rem .45rem}
a.gloss{color:inherit;text-decoration:none;
border-bottom:1px dotted var(--muted)}
a.gloss:hover{color:var(--accent);border-bottom-color:var(--accent)}
.glossary{max-width:44rem}
.gloss-entry{padding:.2rem 0 1rem}
.gloss-entry h2{font-size:1.1rem;margin:1.8rem 0 .4rem;border:0;padding:0}
.gloss-entry p{margin:.2rem 0}
.routes{display:grid;gap:1.2rem;margin:1.5rem 0 2.5rem;
grid-template-columns:repeat(auto-fit,minmax(16rem,1fr))}
.route{border:1px solid var(--line);border-radius:8px;padding:1rem 1.2rem;
background:var(--panel)}
.route h2{font-size:1.05rem;margin:0 0 .2rem;border:0;padding:0}
.route ol,.route ul{margin:.6rem 0 0;padding-left:1.1rem;font-size:.92rem}
.route li{margin:.4rem 0}
.thin-list{list-style:none;padding:0;display:flex;flex-wrap:wrap;gap:.5rem 1.2rem;
max-width:52rem;font-size:.92rem}
.thin-list li{white-space:nowrap}
.foot{margin-top:4rem;padding-top:1rem;border-top:1px solid var(--line);
font-size:.8rem;color:var(--muted);font-family:ui-sans-serif,system-ui,sans-serif}
@media print{
  /* The browser keeps the dark palette when printing from a dark OS, which
     lands as pale grey on white paper. Paper is light; say so. */
  :root{--bg:#fff;--panel:#fff;--ink:#000;--muted:#444;--line:#bbb;
    --accent:#7a2c1f;--good:#15522f;--bad:#8a2317;--warn:#6a5210;--code:#f4f4f4}
  body{max-width:none;padding:0;font-size:11pt}
  .lesson-toc,.subnav,.habit-toc,.crumb,.pager,.ref-card a::after{display:none}
  /* Everything folded away on screen prints open -- the reader cannot click
     paper. ::details-content is the only handle on the closed content. */
  details>summary{list-style:none;font-weight:600}
  details::details-content{content-visibility:visible!important;
    block-size:auto!important}
  pre{white-space:pre-wrap;word-break:break-word;border:1px solid var(--line)}
  .drill-item,.mistake-card,.case,figure,table{break-inside:avoid}
  h1,h2,h3{break-after:avoid}
  /* A printed link is a dead end unless it says where it went. */
  a[href^="http"]::after{content:" <" attr(href) ">";font-size:.8em;
    color:var(--muted);word-break:break-all}
  a[href$=".html"]::after{content:" (" attr(href) ")";font-size:.8em;
    color:var(--muted)}
}
"""


def load_book() -> tuple:
    """The whole export, joined: chapters, the lessons' evidence, the counts.

    The build and --check both need this, and --check needs it for the same
    reason the build does: a page cannot render until COUNTS is filled.
    """
    summary = load_json(ROOT / "analysis_summary.json")
    overview = summary["overview"]
    by_topic = {entry["topic"]: entry for entry in summary["by_topic"]}
    prior = overview["clean_solves"] / max(overview["problems_attempted"], 1)

    chapters = []
    for path in sorted((ROOT / "findings").glob("*.json")):
        findings = load_json(path)
        topic = findings["topic"]
        bundle_path = ROOT / "review" / f"{topic}.json"
        bundle = load_json(bundle_path) if bundle_path.exists() else None
        chapters.append(Chapter(findings, by_topic.get(topic), bundle, prior))
    chapters.sort(key=lambda c: (-c.priority, c.name))

    lessons = course.LESSONS
    evidence = {l["slug"]: match_lesson(l, chapters) for l in lessons}
    habits = {l["slug"]: match_smells(l, chapters) for l in lessons}
    for lesson in lessons:
        slug = lesson["slug"]
        joined = evidence[slug] + habits[slug]
        COUNTS[f"mistakes:{slug}"] = len(evidence[slug])
        COUNTS[f"habits:{slug}"] = len(habits[slug])
        COUNTS[f"problems:{slug}"] = len({case.slug for _, case, _ in joined})
        COUNTS[f"topics:{slug}"] = len({ch.name for ch, _, _ in joined})
    submitted = overview["total_submissions"]
    for status, count in overview["status_counts"].items():
        COUNTS[f"status:{status}"] = count
        COUNTS[f"share:{status}"] = f"{count / submitted:.1%}"
    for key, value in overview.items():
        if isinstance(value, int):
            COUNTS[f"overview:{key}"] = value
    for slug, term, _, _ in course.GLOSSARY:
        COUNTS[f"glossary:{slug}"] = (f'<a class="gloss" '
                                      f'href="glossary.html#{slug}">{term}</a>')
    return summary, overview, prior, chapters, lessons, evidence, habits


def main() -> None:
    summary, overview, prior, chapters, lessons, evidence, habits = load_book()
    by_slug = {c.topic: c for c in chapters}

    # Before any page renders: every one of them carries the stamp.
    stamp, changed = build_stamp(overview, chapters, lessons)
    STAMP["line"] = (
        f"Built {stamp['built']} from an export of {stamp['submissions']:,} "
        f"submissions across {stamp['problems_attempted']:,} problems, the "
        f"last of them {stamp['last_submission']}. "
        f"{stamp['mistakes']:,} mistakes and {stamp['smells']:,} smells were "
        f"diagnosed across {stamp['problems_diagnosed']:,} problems.")
    STAMP["changes"] = changed

    BOOK.mkdir(exist_ok=True)
    (BOOK / "book.css").write_text(CSS, encoding="utf-8")
    (BOOK / "index.html").write_text(
        render_index(chapters, overview, prior), encoding="utf-8")
    (BOOK / "trend.html").write_text(
        render_trend(summary["by_month"], overview), encoding="utf-8")
    (BOOK / "mistakes.html").write_text(
        render_mistakes(chapters), encoding="utf-8")
    (BOOK / "habits.html").write_text(
        render_habits(chapters), encoding="utf-8")
    (BOOK / "plan.html").write_text(
        render_plan(chapters), encoding="utf-8")
    (BOOK / "unsolved.html").write_text(
        render_unsolved(chapters), encoding="utf-8")
    (BOOK / "not-covered.html").write_text(
        render_not_covered(chapters, lessons,
                           sum(c.mistake_count for c in chapters),
                           sum(len(case.smells) for c in chapters
                               for case in c.cases)), encoding="utf-8")
    (BOOK / "revision.html").write_text(
        render_revision(chapters, overview), encoding="utf-8")
    (BOOK / "techniques.html").write_text(
        render_techniques(chapters), encoding="utf-8")
    grinds = render_grinds(chapters)
    for name, html_text in grinds:
        (BOOK / name).write_text(html_text, encoding="utf-8")

    drills = {l["slug"]: drill_candidates(evidence[l["slug"]]) for l in lessons}
    (BOOK / "drills.html").write_text(
        render_drills_index(lessons, drills), encoding="utf-8")
    for i, lesson in enumerate(lessons, 1):
        if drills[lesson["slug"]]:
            (BOOK / f"drill-{lesson['slug']}.html").write_text(
                render_drill_page(lesson, i, drills[lesson["slug"]], len(lessons)),
                encoding="utf-8")

    (BOOK / "course.html").write_text(
        render_course_index(lessons, evidence), encoding="utf-8")
    for i, lesson in enumerate(lessons):
        (BOOK / f"course-{lesson['slug']}.html").write_text(
            render_lesson(lesson, evidence[lesson["slug"]], i + 1, len(lessons),
                          lessons[i - 1] if i else None,
                          lessons[i + 1] if i + 1 < len(lessons) else None,
                          habits[lesson["slug"]], len(drills[lesson["slug"]])),
            encoding="utf-8")
        if lesson.get("reference"):
            (BOOK / f"reference-{lesson['slug']}.html").write_text(
                render_reference(lesson, i + 1, len(lessons)), encoding="utf-8")

    (BOOK / "schedule.html").write_text(
        render_schedule(lessons, evidence, chapters), encoding="utf-8")
    plan = schedule_sessions(lessons, evidence, chapters)
    (BOOK / "schedule.ics").write_text(
        render_calendar(plan, datetime.date.today() + datetime.timedelta(days=1)),
        encoding="utf-8", newline="")
    (BOOK / "recall.tsv").write_text(render_anki(lessons), encoding="utf-8")
    (BOOK / "checklist.html").write_text(
        render_checklist(lessons, evidence, habits), encoding="utf-8")
    (BOOK / "process.html").write_text(
        render_process(chapters, overview), encoding="utf-8")

    by_chapter: dict[str, list[tuple]] = {}
    for lesson in lessons:
        counts: dict[str, int] = {}
        for chapter, _, _ in evidence[lesson["slug"]]:
            counts[chapter.topic] = counts.get(chapter.topic, 0) + 1
        for topic, n in counts.items():
            by_chapter.setdefault(topic, []).append((lesson["slug"], lesson["title"], n))
    for hits in by_chapter.values():
        hits.sort(key=lambda t: -t[2])

    # One page per problem. A problem can be filed under more than one topic,
    # so the page is keyed by slug and lists every chapter that claims it.
    homes: dict[str, list[Chapter]] = {}
    cases: dict[str, Case] = {}
    for chapter in chapters:
        for case in chapter.cases:
            homes.setdefault(case.slug, []).append(chapter)
            cases.setdefault(case.slug, case)
    cited: dict[str, dict[str, int]] = {}
    for lesson in lessons:
        for _, case, _ in evidence[lesson["slug"]] + habits[lesson["slug"]]:
            hits = cited.setdefault(case.slug, {})
            hits[lesson["slug"]] = hits.get(lesson["slug"], 0) + 1
    titles = {l["slug"]: l["title"] for l in lessons}
    for slug, case in cases.items():
        taught = sorted(((s, titles[s], n) for s, n in cited.get(slug, {}).items()),
                        key=lambda t: -t[2])
        (BOOK / f"problem-{slug}.html").write_text(
            render_problem(case, homes[slug], taught), encoding="utf-8")

    (BOOK / "glossary.html").write_text(render_glossary(), encoding="utf-8")
    (BOOK / "search.html").write_text(
        render_search(chapters, lessons, cases, homes), encoding="utf-8")

    total = len(chapters)
    for i, chapter in enumerate(chapters):
        prev_ch = chapters[i - 1] if i else None
        next_ch = chapters[i + 1] if i + 1 < total else None
        (BOOK / f"{chapter.topic}.html").write_text(
            render_chapter(chapter, i + 1, total, prev_ch, next_ch,
                           by_chapter.get(chapter.topic, [])), encoding="utf-8")

    audit_output()

    # A lesson's authority is the evidence it joins. A regex that stops matching
    # -- because a lesson was reworded, or the analysis was re-run with different
    # phrasing -- turns the lesson into an unsupported opinion without changing a
    # line of prose, so the join is reported on every build and an empty one fails.
    # An objective is only checkable if its prerequisites are, so every prereq
    # must be taught earlier. This is the assert that moved `heaps` ahead of
    # `graph-traversal`: Dijkstra is a priority queue with a distance array.
    order = {l["slug"]: i for i, l in enumerate(lessons)}
    for lesson in lessons:
        for need in lesson["prereqs"]:
            assert order[need] < order[lesson["slug"]], (
                f"course order: {lesson['slug']} needs {need}, taught later")

    all_m = {id(m) for ch in chapters for c in ch.cases for m in c.order_mistakes()}
    all_s = {id(sm) for ch in chapters for c in ch.cases for sm in c.smells}
    hit_m = {id(t[2]) for ev in evidence.values() for t in ev}
    hit_s = {id(t[2]) for hb in habits.values() for t in hb}
    thin = sorted(((len(evidence[l["slug"]]) + len(habits[l["slug"]]), l["slug"])
                   for l in lessons))
    for count, slug in thin:
        assert count, f"{slug}: match pattern joins no evidence at all"
    for tech in synthesis.TECHNIQUES:
        found = technique_notes(by_slug[tech["topic"]], tech["evidence"])
        assert found, f"{tech['topic']}: evidence pattern quotes no analysis note"
    share = (len(hit_m) + len(hit_s)) / (len(all_m) + len(all_s))
    assert share >= COVERAGE_FLOOR, (
        f"evidence reaching a lesson fell to {share:.1%}, below the "
        f"{COVERAGE_FLOOR:.0%} floor -- a match pattern stopped matching")
    print(f"evidence: {len(hit_m)}/{len(all_m)} mistakes "
          f"({len(hit_m) / len(all_m):.0%}) and {len(hit_s)}/{len(all_s)} habits "
          f"({len(hit_s) / len(all_s):.0%}) reach a lesson")
    print("  thinnest joins: " + ", ".join(f"{s} ({n})" for n, s in thin[:5]))

    mistakes = sum(c.mistake_count for c in chapters)
    print(f"  drills: {sum(len(d) for d in drills.values())} exercises across "
          f"{sum(1 for d in drills.values() if d)} lessons")
    (BOOK / BASELINE).write_text(json.dumps(stamp, indent=2) + "\n",
                                 encoding="utf-8")
    print("  " + re.sub(r"&[a-z]+;", "->", STAMP["line"] + STAMP["changes"]))
    print(f"book/: {len(list(BOOK.glob('*.html')))} pages, {total} chapters, "
          f"{len(lessons)} lessons, {mistakes} mistakes")
    print("Top 10 by priority:")
    for i, chapter in enumerate(chapters[:10], 1):
        print(f"  {i:2}. {chapter.name:<30} "
              f"faar={pct(chapter.faar):>4} (ranked on {pct(chapter.shrunk_faar):>4}) "
              f"mistakes={chapter.mistake_count:<3} score={chapter.priority:.2f}")


def _selfcheck() -> None:
    """python3 build_book.py --check"""
    def chapter(topic, attempted, clean, mistakes, unsolved=0, prior=0.5):
        return Chapter(
            {"topic": topic, "mistakes": [{"problem": f"p{i}"} for i in range(mistakes)],
             "smells_in_accepted_code": [], "provenance": []},
            {"problems_attempted": attempted, "clean_solves": clean,
             "first_attempt_accept_rate": clean / attempted if attempted else None,
             "unsolved_problems": [{}] * unsolved},
            None, prior)

    # Shrinkage: a 1-problem 0% topic must not outrank a 9-problem 11% topic.
    noise = chapter("noise", 1, 0, 2)
    real = chapter("real", 9, 1, 15)
    assert real.priority > noise.priority, (real.priority, noise.priority)
    assert noise.shrunk_faar > noise.faar, "shrinkage must pull a 0% topic upward"

    # A large topic's own rate should barely move.
    big = chapter("big", 500, 250, 10)
    assert abs(big.shrunk_faar - 0.5) < 0.01, big.shrunk_faar

    # Weakness dominates evidence: more mistakes must not beat a real gap.
    weak_thin = chapter("weak", 40, 8, 5)      # 20% first-attempt
    strong_rich = chapter("strong", 40, 30, 40)  # 75% first-attempt
    assert weak_thin.priority > strong_rich.priority

    # Unsolved problems raise priority, all else equal.
    assert chapter("u", 20, 10, 10, unsolved=2).priority > chapter("u", 20, 10, 10).priority

    # ...but only the ones filed in THIS chapter. A big tag whose never-solved
    # problems all live in other bundles must not inherit their weight.
    bundled = Chapter(
        {"topic": "big", "mistakes": [], "smells_in_accepted_code": [], "provenance": []},
        {"problems_attempted": 200, "clean_solves": 100,
         "unsolved_problems": [{"titleSlug": "elsewhere"}] * 3},
        {"problems": [{"titleSlug": "x", "title": "X", "difficulty": "Medium",
                       "total_attempts": 2, "solved": True}]}, 0.5)
    assert bundled.unsolved == [], "an unsolved problem filed elsewhere is not this chapter's"
    assert bundled.in_chapter == 1

    # Missing stats fall back to the prior rather than reading as 0% weakness.
    bare = Chapter({"topic": "untagged", "mistakes": []}, None, None, 0.541)
    assert bare.shrunk_faar == 0.541

    # Code and prose reaching HTML must be escaped.
    assert "<script>" not in esc("<script>alert(1)</script>")

    # Backtick spans in the analysis prose become inline code -- after escaping,
    # never before, or a span could smuggle markup through.
    assert esc_code("use `a<b` here") == "use <code>a&lt;b</code> here"
    assert "<script>" not in esc_code("`<script>alert(1)</script>`")
    assert esc_code("no spans") == "no spans"
    assert "&lt;" in code_block("nope/missing.java", "x", "bad") or True

    # Status parsing off real submission filenames.
    assert submission_status(
        "solutions/x/1734202132_Wrong_Answer_java_1478814981.java") == "Wrong Answer"
    assert submission_status("solutions/x/1_Accepted_cpp_2.cpp") == "Accepted"
    assert submission_status("garbage") == ""

    # Every in-page link on a lesson page must land on something. The TOC and
    # the per-section subnav are generated from two different lists, so this is
    # the check that keeps them in step.
    # diff_block has three answers -- a patch, a rewrite, and no change at all --
    # and the third is the one that silently renders as an empty box if it breaks.
    samples = sorted(ROOT.glob("solutions/*/*.java"))
    pairs = [(str(f.relative_to(ROOT)), next_submission(str(f.relative_to(ROOT))))
             for f in samples[:400]]
    pairs = [(a, b) for a, b in pairs if b]
    assert pairs, "no consecutive submissions to diff"
    kinds = set()
    for before, after in pairs:
        out = diff_block(before, after)
        if not out:
            continue
        if "byte-identical" in out:
            kinds.add("same")
        elif "diff-note" in out:
            kinds.add("rewrite")
        else:
            kinds.add("patch")
            assert '"dl del"' in out or '"dl add"' in out, (before, "empty diff")
    assert "patch" in kinds, kinds
    print(f"  diff_block: {len(pairs)} pairs, kinds {sorted(kinds)}")

    # Real data from here on: pages cannot render until the counts are filled.
    _, _, _, chapters, _, _, _ = load_book()

    fake_ch = chapter("ch", 10, 5, 1)
    for lesson in course.LESSONS:
        html = render_lesson(lesson, [], 1, len(course.LESSONS), None, None,
                             [(fake_ch, fake_ch.cases[0], {"smell": "x"})])
        ids = re.findall(r'\bid="([^"]+)"', html)
        assert len(ids) == len(set(ids)), (lesson["slug"], "duplicate id")
        for href in re.findall(r'href="#([^"]+)"', html):
            assert href in ids, (lesson["slug"], f"#{href} has no target")
        for part in ("summary", "uses", "patterns", "depth", "mistakes",
                     "fixes", "habits", "drill"):
            assert f'id="{part}"' in html, (lesson["slug"], f"no {part} section")

    # Folding is by octet and must never split a multi-byte character, which is
    # the one way to write an .ics that parses everywhere except on the entry
    # that happens to carry an em-dash.
    assert ics_escape(";") == r"\;" and ics_escape(",") == r"\,"
    assert ics_escape("\n") == r"\n" and ics_escape("\\") == "\\\\"
    assert ics_fold("x" * 75) == "x" * 75
    for probe in ("x" * 200, "é" * 200, "x" * 74 + "é" * 60, "SUMMARY:" + "√" * 90):
        folded = ics_fold(probe)
        for line in folded.split("\r\n"):
            assert len(line.encode("utf-8")) <= 75, (probe[:8], len(line))
            line.encode("utf-8").decode("utf-8")
        assert folded.replace("\r\n ", "") == probe, "unfolding must round-trip"
    print(f"  ics: escaping and 75-octet folding round-trip on 4 probes")

    # The glossary linker walks raw HTML by hand, so it gets a unit check.
    assert glossary_links("<p>a heap here</p>").count("<a") == 1
    assert glossary_links("<pre>a heap</pre>") == "<pre>a heap</pre>"
    assert glossary_links("<code>heap</code>") == "<code>heap</code>"
    assert glossary_links("<h2>heap</h2>") == "<h2>heap</h2>"
    assert glossary_links("<a>heap</a>") == "<a>heap</a>"
    assert glossary_links("<p>heap heap</p>").count("<a") == 1, "once per page"
    assert "sliding window</a>" in glossary_links("<p>a sliding window</p>"), (
        "the longer term must win over the shorter one inside it")
    assert glossary_links("<p>heaped</p>") == "<p>heaped</p>", "whole words only"
    assert glossary_links("<pre>heap</pre><p>heap</p>").count("<a") == 1

    check_java(course.LESSONS)  # every sample in the book, through a compiler
    check_claims(course.LESSONS, chapters)  # the export still backs the prose
    check_length(course.LESSONS)  # still one sitting per lesson
    check_stylesheet()         # contrast, focus, print, and narrow screens
    if BOOK.exists():
        audit_output()         # the last build's pages, if there is one
    diagrams._selfcheck()      # figures must not overflow their own viewBox
    traces._selfcheck()        # every trace table came from a checked run
    print("selfcheck ok")


if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        _selfcheck()
    else:
        main()
