# LeetCode practice history -- analysis brief

You are reading a complete export of my LeetCode submission history. Analyse
it and tell me where I am weak, where I am strong, and what to practise next.
Work through it as described below; everything you need is in this folder.

## 1. What this dataset is

Exported by `leetcode_export.py` on 2026-09-04 17:42:56 UTC. It contains
**every submission I made, at every status** -- not only the accepted ones.
The failed attempts are deliberately included and are the most useful signal
in here.

- **Window:** 2020-02-13 09:41:55 to 2026-08-24 12:32:11 UTC (2384 days)
- **5212 submissions** across **892 distinct problems**
- **888 problems solved** (100% of those attempted); 483 on the first attempt
- Submission-level acceptance rate: 55%
- Status mix: Accepted 2882, Wrong Answer 1515, Runtime Error 324, Compile Error 242, Time Limit Exceeded 233, Memory Limit Exceeded 14, Unknown 1, Output Limit Exceeded 1
- Languages: java, cpp, rust, javascript, python3, mysql, python, c, golang, csharp, typescript, pythondata
- 5212 code files on disk under `solutions/`
- Coverage: **5212 of the 5208 submissions LeetCode reports for this account** (100%)

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
roughly 1,878K tokens across 109 bundles. So it is built to be
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
4. Write `findings/<topic>.json` before moving on, so the work survives.
   Every `file` you cite must be copied exactly from the bundle -- a single
   wrong digit still looks like a real submission and points at nothing. When
   the bundle is written, run

   ```
   python3 leetcode_export.py --check-findings
   ```

   and fix anything it reports before starting the next one. The JSON shape is:

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
