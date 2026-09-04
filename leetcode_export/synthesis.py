#!/usr/bin/env python3
"""The cross-cutting synthesis: habits, not topics.

REPORT.md holds the written analysis of this export -- the ranked recurring
mistakes, the cross-cutting failure modes, the practice plan. It is the best
writing about this reader in the project and the book told people to open it in
an editor. This module carries that content as book pages instead.

The prose is authored, like course.py. Everything countable is joined: each
habit carries a `match` regex that build_book.py runs over findings/*.json, so
the number beside a habit is measured rather than typed, and stays true when the
analysis is rerun.

Habit dict:
    rank     position in REPORT.md section 3, which ranked by frequency
    title    the habit, named as a behaviour
    html     what it is and why it costs attempts
    match    regex over the diagnosis text, or None for habits that are not
             per-mistake facts (a submission-rate habit has nothing to join to)
    stat     an authored figure for those, quoted from the report
    lessons  slugs of the lessons that teach the fix
"""

from __future__ import annotations

from course import p, ul


# --------------------------------------------------------------------------
# Section 3 of REPORT.md: recurring mistakes, ranked by frequency.
# --------------------------------------------------------------------------

HABITS = [
{
 "rank": 1,
 "title": "Rewriting problems you have already solved",
 "stat": "57.8% of all submissions",
 "match": None,
 "html": (
  p("More than half of everything in this export was submitted to a problem "
    "that was already solved. That is not a mistake &mdash; deliberately "
    "re-implementing a solved problem a second way is one of the better "
    "practice habits there is, and it is why this export contains parallel "
    "implementations of the same problem in three languages.")
  + p("It is also where the damage concentrates. Nearly every paste flag in "
      "the export sits in a post-solve resubmission, and so do a large share "
      "of the regressions: a sentinel bug in <em>jump-game-viii</em> was fixed "
      "once and then reintroduced by a later cleanup pass; an accepted "
      "<em>implement-trie</em> solution was reformatted to a different brace "
      "style and lost the descent step inside <code>startsWith</code>.")
  + p("The counter-habit is one sentence long. <strong>A rewrite is new code, "
      "so run the checklist you would run on new code.</strong> The judge is "
      "not going to be more careful on your behalf just because the problem "
      "already has a green tick against it.")),
 "lessons": ["edit-hygiene", "wrong-name"],
},
{
 "rank": 2,
 "title": "Brute force first, optimise after the judge complains",
 "stat": "pervasive",
 "match": r"\bTLE\b|time limit exceeded|brute[- ]force|O\(n\^?2\)|"
          r"quadratic|too slow|nested[- ]loop scan|linear scan.{0,40}instead",
 "html": (
  p("The pattern is: write the direct solution, submit, read Time Limit "
    "Exceeded, then think about complexity. It works, in the sense that the "
    "problem gets solved. It costs an attempt every time, and it means the "
    "complexity analysis happens after the code exists, when you are "
    "attached to it.")
  + p("The report finds this across quicksort, range-minimum-maximum-query, "
      "trie and two-pointers. The smells list is fuller still: an O(n&sup2;) "
      "pairwise scan in <em>invalid-transactions</em> where a time-bucketed "
      "map was used in the rewrite minutes later, a fresh "
      "<code>freq[26]</code> rebuilt on every outer iteration of a sliding "
      "window, a full sort where a bucket pass would do.")
  + p("The fix is to spend thirty seconds on arithmetic before writing "
      "anything: read <code>n</code> from the constraints, and ask what "
      "complexity fits in a second. That is the whole of lesson 1, and it is "
      "first in the course for this reason.")),
 "lessons": ["complexity-budget"],
},
{
 "rank": 3,
 "title": "Boundaries and off-by-one",
 "stat": None,
 "match": r"off[- ]by[- ]one|\bbound(s|ary|aries)?\b|inclusive|exclusive|"
          r"`?<=?`? (instead of|where|should)|strict(ly)? (less|greater)|"
          r"out of bounds|index out of|one (too (many|few)|extra|short)",
 "html": (
  p("Two separate bundles, written independently, both call this "
    "&ldquo;the single most common failure mode&rdquo;. It dominates array, "
    "sorting, string, two-pointers, sliding-window, prefix-sum and "
    "binary-tree alike, which is what makes it worth treating as a skill "
    "rather than as a property of any topic.")
  + p("It has three distinguishable shapes and they need different habits. "
      "<strong>Comparison boundaries</strong> &mdash; <code>&lt;</code> where "
      "<code>&lt;=</code> was meant &mdash; are decided by whether the "
      "interval is closed or half-open, which the statement tells you and "
      "which belongs in a comment. <strong>Sizing</strong> &mdash; an array "
      "one slot short &mdash; comes from a bound that was guessed rather than "
      "derived. <strong>The end of the sequence</strong> &mdash; a final "
      "group, run or carry that no transition ever closes &mdash; is its own "
      "lesson.")),
 "lessons": ["bounds", "last-group", "binary-search"],
},
{
 "rank": 4,
 "title": "Getting the edge direction backwards",
 "stat": None,
 "match": r"edge direction|dependency direction|indegree|in-degree|reversed? (the )?edge|"
          r"a before b|prerequisite|topological",
 "html": (
  p("The topological-sort signature bug, and the report notes it recurring "
    "<em>verbatim months apart</em> &mdash; which is the tell that the "
    "instance got fixed and the invariant did not.")
  + p("Every course-schedule-shaped problem gives you pairs and a sentence "
      "about which comes first, and the sentence is ambiguous in English in a "
      "way it is not in the graph. <code>[a, b]</code> meaning &ldquo;to take "
      "a you must first take b&rdquo; is an edge from b to a, and it is "
      "<code>indegree[a]</code> that increments. Reverse it and the algorithm "
      "still runs, still terminates, and answers a different question.")
  + p("The counter-habit is mechanical: write the comment before the loop, "
      "not after the failure.")),
 "lessons": ["graph-traversal"],
},
{
 "rank": 5,
 "title": "Sentinels that collide with real values",
 "stat": None,
 "match": r"sentinel|MAX_VALUE|MIN_VALUE|magic (number|value)|"
          r"uninitiali[sz]ed|-1 (as|to mean)|in-band|placeholder value",
 "html": (
  p("A value chosen to mean &ldquo;nothing here yet&rdquo; that a real answer "
    "can also take. <em>jump-game-viii</em> used "
    "<code>Integer.MAX_VALUE</code> as the sentinel in a <code>long[]</code>, "
    "where it is an ordinary number rather than an extreme one. "
    "<em>validate-binary-search-tree</em> is the same class as a "
    "twenty-submission struggle.")
  + p("What makes this rank fifth rather than lower is the regression: the "
      "<em>jump-game-viii</em> sentinel was fixed, and then a later post-solve "
      "cleanup pass put it back. A sentinel is a claim about the range of your "
      "data, and cleanup passes do not re-check claims.")),
 "lessons": ["sentinels", "integer-width"],
},
{
 "rank": 6,
 "title": "Renames finished on one side only",
 "stat": "part of 242 compile errors",
 "match": r"rename|undeclared|does not exist|cannot find symbol|"
          r"name mismatch|declared as .{0,20}but|half-finished",
 "html": (
  p("<code>queries</code> renamed to <code>query</code> at the declaration "
    "and not at the call site. An undeclared <code>stats</code>. A helper "
    "whose signature changed on one side. Dozens of instances, every one "
    "costing a full attempt for code the compiler on your own machine would "
    "have rejected in under a second.")
  + p("This is the cheapest category in the entire export to eliminate, "
      "because it requires no thinking at all &mdash; only compiling before "
      "submitting.")),
 "lessons": ["edit-hygiene"],
},
{
 "rank": 7,
 "title": "A pasted loop that kept the old variable",
 "stat": None,
 "match": r"copy[- ]?pasted|copy/paste|pasted from|never had its .{0,20}renamed|"
          r"stale variable|reused the wrong|wrong loop variable",
 "html": (
  p("<em>3sum-closest</em> mixed <code>j&lt;n</code> and <code>k&lt;n</code>. "
    "A second prefix-scan loop was pasted from the first and never had its "
    "target array renamed, so it wrote <code>preMax[i]</code> twice and "
    "<code>postMin</code> never. In "
    "<em>lexicographically-smallest-generated-string</em> the identical "
    "wrong-loop-variable bug appears twice in one file &mdash; fixed at the "
    "first site, then written again at the second.")
  + p("These compile, run, and read a real element every time. Nothing about "
      "the failure points back at the line that caused it, which is why they "
      "take four or five submissions to find instead of one.")),
 "lessons": ["wrong-name"],
},
{
 "rank": 8,
 "title": "Union-find that merges the arguments instead of the roots",
 "stat": None,
 "match": r"union\(|\bDSU\b|disjoint set|find\(x\)|raw arg|parent\[x\] = y|"
          r"union.{0,40}(root|argument)",
 "html": (
  p("<code>union(x, y)</code> that checks connectivity with "
    "<code>find(x) == find(y)</code> and then merges <code>x</code> and "
    "<code>y</code> rather than their roots. The structure still looks like a "
    "forest and still answers most queries correctly, because on many inputs "
    "the arguments <em>are</em> roots.")
  + p("The report catches it twice in first-solve code, and once shipped "
      "unnoticed in a post-solve rewrite &mdash; that third one is in the "
      "book as a habit in accepted code, where the analysis notes it "
      "&ldquo;happens to pass only because of this problem's specific access "
      "pattern&rdquo;. The identical shape is a real Wrong Answer in "
      "<em>graph-valid-tree</em>.")),
 "lessons": ["union-find"],
},
{
 "rank": 9,
 "title": "Calling System.gc() before returning",
 "stat": "across 5 topics",
 "match": r"System\.gc",
 "html": (
  p("A distinctive habit, apparently aimed at the reported runtime or memory "
    "percentile, appearing across binary-search, bit-manipulation, "
    "simulation, sliding-window and union-find.")
  + p("It does not do what it appears to be for. <code>System.gc()</code> is "
      "a request, the judge measures peak usage rather than final usage, and "
      "the call itself costs time. It is harmless to the verdict and it is "
      "noise in code you may later want to read, or show someone. Worth "
      "naming here only because it is so consistent that it functions as a "
      "signature.")),
 "lessons": [],
},
{
 "rank": 10,
 "title": "Guessing a bigger constant instead of deriving the bound",
 "stat": None,
 "match": r"sized? .{0,30}(guess|ad[- ]hoc|arbitrar)|resiz|"
          r"new (int|long|boolean|char)\[\d{4,}\]|"
          r"bigger constant|10001|20001|100001|magic (size|bound)",
 "html": (
  p("<em>concatenate-non-zero-digits</em> resized one lookup table four times "
    "&mdash; 11, then 10001, then 20001, then 100001 &mdash; across four "
    "Runtime Errors. <em>partition-equal-subset-sum</em> did the same dance "
    "with a <code>boolean[]</code> across four post-solve resubmissions: "
    "20000, 10001, 20001, 10001 again.")
  + p("Each of those is one submission spent asking the judge a question you "
      "could answer yourself. The size of a counting array is "
      "<code>max(data) + 1</code> or a number the constraints hand you; both "
      "are derivable at the moment you declare it. When the constant is right "
      "it is right by luck, and the next problem's constraints are "
      "different.")),
 "lessons": ["counting-arrays", "bounds"],
},
{
 "rank": 11,
 "title": "Checking the bounds after the read instead of before",
 "stat": None,
 "match": r"bounds check|before (the )?(array )?access|short[- ]circuit|"
          r"&& .{0,30}(order|first)|guard.{0,25}(after|before) the",
 "html": (
  p("Recurring in grid and graph traversal code. The guard is present and "
    "correct; it is simply on the wrong side of the <code>&amp;&amp;</code>.")
  + p("Java's <code>&amp;&amp;</code> evaluates left to right and stops "
      "early, which means the left operand is the only thing protecting the "
      "right one. <code>grid[r][c] == 1 &amp;&amp; inBounds(r, c)</code> "
      "throws while the condition is still being evaluated, and the bounds "
      "test never runs. That ordering <em>is</em> the guard.")),
 "lessons": ["bounds", "graph-traversal"],
},
{
 "rank": 12,
 "title": "Solving around the technique the tag names",
 "stat": "16 topics",
 "match": None,
 "html": (
  p("A long list of topics where LeetCode's tag names a technique and the "
    "submitted code used something else: algorithm-x, boyer-moore, "
    "binary-lifting, bellman-ford, dancing-links, Floyd's cycle-finding, "
    "Kosaraju's, meet-in-the-middle, flow-network, Newton's method, "
    "rolling-hash, quicksort, sieve theory, Sprague-Grundy, tournament-sort, "
    "and even binary-indexed-tree and segment-tree themselves.")
  + p("This is not a bug, and most of those solutions were accepted. It is a "
      "map of the techniques you have solved <em>around</em> rather than "
      "<em>with</em> &mdash; which is exactly the list to work from when the "
      "goal is breadth rather than accuracy. Tags are LeetCode's "
      "categorisation, not a record of what you wrote, so treat this as a "
      "reading list rather than a scoreboard.")),
 "lessons": [],
},
]


# --------------------------------------------------------------------------
# Section 7: how the debugging loop itself behaves. Not bug classes -- the
# process around them, which is why none of these join to a mistake record.
# --------------------------------------------------------------------------

MODES = [
 ("The loop is fast and shallow",
  p("Submit, read the verdict, patch the nearest line, resubmit &mdash; "
    "sometimes within seconds. Instances get fixed quickly, which is genuinely "
    "a strength. The class underneath goes untouched, which is why the same "
    "bug shape reappears months later in unrelated code.")
  + p("The signature is visible in the timestamps: runs of four and five "
      "submissions minutes apart where each attempt moves a symptom. "
      "<em>top-k-frequent-elements</em> is the clearest &mdash; a null check "
      "added, then bucket-scan conditions adjusted, while the counting itself "
      "had been broken since the first line.")
  + p("<strong>The rule that breaks it:</strong> before the second patch on a "
      "problem, write down what the failing case actually is. Not the verdict "
      "&mdash; the input, and what your code does to it.")),

 ("Post-solve code is less trustworthy than first-solve code",
  p("Every discontinuous or pasted provenance flag in the export sits in a "
    "post-solve resubmission, and so do several of the regressions. The "
    "attention that goes into a first solve is not present in a rewrite, "
    "because the problem no longer feels open.")),

 ("Bugs get fixed; invariants do not get learned",
  p("The topological-sort edge direction and the union-find raw-argument bug "
    "are the two clearest cases: each occurrence is patched quickly and each "
    "resurfaces independently months later. A fix that is applied to a line "
    "rather than understood as a rule has a half-life.")
  + p("This is the reason the course exists in the shape it does &mdash; a "
      "lesson per invariant rather than a page per problem.")),

 ("A stable fingerprint, across six years and four languages",
  p("Terse loop variables next to descriptive domain names. Turkish comments "
    "during rapid exploratory rewrites. A recurrence sketched as pseudocode "
    "before it is implemented. The <code>System.gc()</code> habit. None of "
    "these are mistakes; they are what makes provenance judgements possible at "
    "all, and they are worth knowing about yourself.")),
]


# --------------------------------------------------------------------------
# Section 8: the practice plan. Ordered by expected return, not by topic.
# --------------------------------------------------------------------------

PLAN = [
{
 "title": "Close the four problems that were never solved",
 "why": p("Each was abandoned mid-approach rather than exhausted. Three of the "
          "four are Easy or Medium, and the analysis already names the specific "
          "reason each attempt failed &mdash; which means the hard part is "
          "done and the remaining work is finishing a sentence."),
 "lessons": [],
 "link": ("unsolved.html", "The four unsolved problems"),
},
{
 "title": "Drill boundary reasoning as its own skill",
 "why": p("It dominates every topic regardless of algorithm family, which "
          "means it cannot be fixed by practising any particular topic. Write "
          "the inclusive/exclusive semantics down before writing the loop."),
 "lessons": ["bounds", "last-group", "binary-search"],
 "link": None,
},
{
 "title": "Turn the two cleanest named bugs into checklist items",
 "why": p("State the edge direction explicitly before any Kahn's BFS. Always "
          "union via <code>find(x)</code> and <code>find(y)</code>, never the "
          "raw arguments. Both recur months apart, and both are one sentence "
          "to check."),
 "lessons": ["graph-traversal", "union-find"],
 "link": None,
},
{
 "title": "Refresh what was strong and has gone cold",
 "why": p("Binary-search-tree sits at a 76% clean-solve rate &mdash; one of "
          "the highest in the export &mdash; and has not been touched in nine "
          "months. Linked-list, queue and binary-tree are in the same "
          "position. One problem each restores them; nothing else on this list "
          "is as cheap."),
 "lessons": ["linked-list"],
 "link": None,
},
{
 "title": "Practise recognising when a segment tree is needed",
 "why": p("The mechanics are not the gap. Segment-tree is the lowest "
          "self-solve rate of any substantial topic in the export, and the "
          "failures are about reaching for it, or not, rather than about "
          "building it once the decision is made."),
 "lessons": ["range-structures"],
 "link": None,
},
{
 "title": "Treat number theory, recursion and divide-and-conquer as one cluster",
 "why": p("The worst wrong-answer-to-accepted ratios in the export, with no "
          "single mechanical bug driving them. The gap is in formulating the "
          "recurrence up front, which is one skill wearing three topic names."),
 "lessons": ["number-theory", "recursion", "dynamic-programming"],
 "link": None,
},
{
 "title": "Rein in the zero-value churn, and keep the rest",
 "why": p("Byte-identical resubmissions cost attempts and teach nothing. "
          "Parallel implementations of a solved problem in a second language "
          "are among the best things in this export. The habit is worth "
          "keeping; the noise inside it is not."),
 "lessons": ["edit-hygiene"],
 "link": None,
},
]


# --------------------------------------------------------------------------
# Section 9: what the data cannot say. Printed under the plan, because a plan
# that does not state its own limits reads as more certain than it is.
# --------------------------------------------------------------------------

LIMITS = ul(
 "The findings are a representative sample, not a census -- some bundles "
 "reviewed fewer problems than the topic's true attempted count.",
 "Provenance verdicts are style judgements, not ground truth. Several were "
 "left explicitly uncertain rather than resolved.",
 "Topic tags are LeetCode's categorisation, not a record of the technique you "
 "actually used.",
 "Timing and code are visible; understanding is not. A fast clean solve is "
 "strong evidence of recognition. A slow grind's eventual correctness does not "
 "say whether it came from reasoning or from a half-remembered technique "
 "landing right.",
 "Two dormancies -- three years to late 2024, then five months to July 2026 -- "
 "have no explanation in this data, and every 'days since practice' number "
 "inherits the second one.",
 "Nothing here speaks to production code, system design, or working with other "
 "people.",
)


# --------------------------------------------------------------------------
# The four problems that were never solved. The chapter pages call these "the
# sharpest weakness signal in the whole export" and then print a title, so
# this is where the sentence gets finished.
#
# Two of them have statements this book can verify, and those get a worked
# solution. Two do not, and reconstructing a problem statement out of failing
# code would be guessing -- so those pages stop at what the record proves.
# --------------------------------------------------------------------------

from course import code

UNSOLVED = [
{
 "slug": "excel-sheet-column-title",
 "title": "Excel Sheet Column Title",
 "difficulty": "Easy",
 "attempts": 3,
 "verdicts": "3 x Wrong Answer, over one sitting",
 "solved": True,
 "diagnosis": (
  p("All three attempts are the same six lines with the <code>-1</code> in a "
    "different place:")
  + code("""
// attempt 1
sb.append((char)((int)'A' + (columnNumber % 26)));
// attempt 2
sb.append((char)((int)'A' + (columnNumber % 26) - 1));
// attempt 3
sb.append((char)((int)'A' + (columnNumber % 26 - 1)));
""")
  + p("Attempts 2 and 3 are the same expression. Java applies "
      "<code>%</code> before binary <code>-</code>, so the parentheses in "
      "attempt 3 change nothing at all &mdash; two submissions were spent "
      "moving a bracket. That is the shallow debugging loop in its purest "
      "form: the edit was to the line the output pointed at, not to the "
      "thing the output meant.")),
 "why": (
  p("<strong>Spreadsheet columns are not base 26.</strong> They are "
    "<em>bijective</em> base 26, which is a different numbering system: the "
    "digits are 1..26 (A..Z) and there is no digit zero.")
  + p("Ordinary base 26 has digits 0..25, so 26 is written <code>10</code> "
      "&mdash; a one and a nothing. Bijective base 26 has no nothing, so 26 "
      "is written <code>Z</code> and 27 is the first two-digit number, "
      "<code>AA</code>. Every place where ordinary base-26 would emit a zero "
      "digit, this system instead borrows from the column to its left.")
  + p("That is exactly what breaks in the submitted code. When "
      "<code>columnNumber % 26 == 0</code> &mdash; which is every multiple of "
      "26, the Z column &mdash; attempt 2 computes <code>'A' + 0 - 1</code> "
      "and appends the character before <code>A</code>. Column 26 comes out "
      "as <code>&quot;A@&quot;</code>. The <code>@</code> is the missing "
      "digit zero, rendered.")),
 "fix": (
  p("Borrow the one <em>before</em> taking the remainder, so the digits run "
    "0..25 internally while reading as 1..26. It is one statement, and it has "
    "to be the first statement in the loop:")
  + code("""
public String convertToTitle(int columnNumber) {
    StringBuilder sb = new StringBuilder();
    while (columnNumber > 0) {
        columnNumber--;                                  // no digit zero: borrow first
        sb.append((char) ('A' + columnNumber % 26));     // now 0..25 maps onto A..Z
        columnNumber /= 26;                              // and the borrow is already paid
    }
    return sb.reverse().toString();
}
""")
  + p("Check it against the boundaries rather than the middle: 1 is "
      "<code>A</code>, 26 is <code>Z</code>, 27 is <code>AA</code>, 52 is "
      "<code>AZ</code>, 702 is <code>ZZ</code> and 703 is <code>AAA</code>. "
      "The multiples of 26 are the whole test &mdash; every failing input in "
      "this export is one of them, and no other input distinguishes the two "
      "versions.")
  + p("The generalisation is worth more than the problem. Any numbering with "
      "no zero digit &mdash; column letters, 1-indexed levels of a complete "
      "tree, ranks that start at one &mdash; wants a decrement before the "
      "division. It is the same <code>+1</code> and <code>-1</code> tension "
      "as sizing a counting array, from the other side.")),
 "lessons": ["bounds", "counting-arrays", "number-theory"],
},
{
 "slug": "remove-duplicates-from-sorted-list",
 "title": "Remove Duplicates from Sorted List",
 "difficulty": "Easy",
 "attempts": 1,
 "verdicts": "1 x Wrong Answer, never revisited",
 "solved": True,
 "diagnosis": (
  p("One submission, one bug, and the shortest fix in this book. The pointer "
    "advances whether or not a node was just removed:")
  + code("""
ListNode current = head;
while (current != null && current.next != null) {
    if (current.next.val == current.val) {
        current.next = current.next.next;    // unlinked one duplicate
    }
    current = current.next;                  // ...and stepped past the next one
}
return head;
""")
  + p("On <code>[1,2,3]</code> it is correct. On <code>[1,1,2]</code> it is "
      "correct. It only fails on a run of <strong>three or more</strong> "
      "equal values, and the sample cases in the problem statement do not "
      "contain one. <code>[1,1,1,2]</code> comes back as "
      "<code>[1,1,2]</code>; <code>[1,1,1,1]</code> comes back as "
      "<code>[1,1]</code>.")),
 "why": (
  p("Deleting from a linked list moves the list under the pointer. After "
    "<code>current.next = current.next.next</code>, the node at "
    "<code>current.next</code> is a <em>new, unexamined</em> node &mdash; the "
    "loop has not looked at it yet. Advancing skips it.")
  + p("<strong>The invariant, said properly:</strong> <code>current</code> "
      "advances only when the node in front of it has been confirmed "
      "different. A removal confirms nothing, because it puts something new "
      "there.")),
 "fix": (
  p("Move the advance into the <code>else</code>. That is the entire change:")
  + code("""
public ListNode deleteDuplicates(ListNode head) {
    ListNode current = head;
    while (current != null && current.next != null) {
        if (current.next.val == current.val) current.next = current.next.next;
        else current = current.next;          // advance ONLY when nothing was removed
    }
    return head;
}
""")
  + p("The linked-list lesson already carries this as a rule &mdash; "
      "<em>after unlinking a node, do not advance</em> &mdash; which is worth "
      "sitting with. The rule was in the book before this page was written, "
      "and the submission is from before the book existed. This is what it "
      "looks like when a checklist item earns its place.")
  + p("Worth doing immediately afterwards: "
      "<em>remove-duplicates-from-sorted-list-ii</em>, which deletes every "
      "copy of a duplicated value rather than keeping one. It needs a dummy "
      "head, because the first node can now disappear, and it is the natural "
      "second half of this fifteen-minute exercise.")),
 "lessons": ["linked-list", "bounds"],
},
{
 "slug": "two-letter-card-game",
 "title": "Two-Letter Card Game",
 "difficulty": "Medium",
 "attempts": 5,
 "verdicts": "5 x Wrong Answer, across two separate days",
 "solved": False,
 "diagnosis": (
  p("Five attempts, and the analysis is clear about what happened between "
    "them. The first attempt categorised cards by which side the special "
    "letter <code>x</code> sat on and paired same-category cards, never "
    "considering the cross-pairing the scoring rule allows. It was then "
    "abandoned for a frequency-array approach, which was also wrong.")
  + p("The final attempt reduces every card to one of three counters &mdash; "
      "<code>left</code> for <code>x?</code>, <code>right</code> for "
      "<code>?x</code>, <code>middle</code> for <code>xx</code> &mdash; and "
      "greedily spends the <code>xx</code> cards against the other two. It "
      "has a specific, provable hole:")
  + code("""
while (middle > 0) {
    if (left % 2 == 1)       { left--;  middle--; ans++; }
    else if (right % 2 == 1) { right--; middle--; ans++; }
    else if (left > 0)       { left--;  middle--; ans++; }
    else if (right > 0)      { right--; middle--; ans++; }
    else break;               // <-- two xx cards left, and they pair with each other
}
ans += left / 2 + right / 2;  // xx pairs are never counted here either
""")
  + p("When <code>left</code> and <code>right</code> both reach zero with "
      "<code>middle</code> still positive, the loop breaks and the remaining "
      "<code>xx</code> cards score nothing &mdash; even though two "
      "<code>xx</code> cards are a valid pair on their own. The missing line "
      "is <code>ans += middle / 2</code>, and it is missing because the "
      "<code>xx</code> card was modelled as a wildcard that needs a partner "
      "rather than as a card in its own right.")),
 "why": (
  p("<strong>This page stops here, deliberately.</strong> The problem "
    "statement is not in the export, and the letters other than "
    "<code>x</code> are discarded before the counting starts &mdash; so the "
    "code cannot tell us what the real pairing rule is, only what this "
    "attempt assumed it was. Reconstructing the rule from five wrong "
    "solutions and writing a confident answer would be guessing, which is "
    "worse than saying so.")
  + p("What the record does establish is worth having, and it is most of the "
      "way to a solve:")
  + ul("The <code>xx</code> case is under-modelled, and "
       "<code>ans += middle / 2</code> is missing whatever else is wrong.",
       "The first attempt's diagnosis names the actual scoring rule as "
       "allowing a first-letter card to pair with a differently-lettered "
       "second-letter card that shares the other letter -- which the final "
       "attempt's three counters cannot express at all, because it throws "
       "the other letters away.",
       "All five attempts iterate on the counter model. None goes back to "
       "the statement.")),
 "fix": (
  p("The instruction here is not code, it is a procedure &mdash; and it is "
    "the same one that would have saved the six attempts on the segment-tree "
    "problem below.")
  + ul("Open the statement and write the scoring rule out as a sentence, in "
       "your own words, before writing anything else.",
       "Write down what a card is allowed to pair with. If the model you are "
       "about to build cannot represent that sentence, stop -- that is the "
       "bug, and no amount of adjusting the greedy will reach it.",
       "Only then decide whether the answer is counting, greedy or matching.")
  + p("The measurable signal that this was needed: five submissions, no "
      "change of model. Two failed patches on one problem is the point to "
      "stop editing, and this problem passed that point on day one.")),
 "lessons": ["complexity-budget", "edit-hygiene"],
},
{
 "slug": "minimum-stability-factor-of-array",
 "title": "Minimum Stability Factor of Array",
 "difficulty": "Hard",
 "attempts": 6,
 "verdicts": "6 x Wrong Answer, inside about sixteen minutes",
 "solved": False,
 "diagnosis": (
  p("Six attempts in sixteen minutes, all on one heuristic: find maximal "
    "gcd-stable runs, then repeatedly halve the largest one with a max-heap "
    "until the operation budget runs out.")
  + p("The analysis is blunt about it &mdash; splitting a run in half is not "
      "the operation that minimises the resulting stability factor, so the "
      "heuristic is not an approximation of the right answer, it is a "
      "different computation. The run-merging condition was also inconsistent "
      "between attempts: <code>nums[r+1] % div == 0 || div % nums[r+1] == 0</code> "
      "in some, a real running gcd in others.")
  + p("What the six attempts changed: the split formula, then the "
      "divisibility check swapped for an explicit <code>gcd()</code> helper, "
      "then the direction of the array. What none of them changed: the "
      "halving.")),
 "why": (
  p("<strong>This page stops here too</strong>, for the same reason &mdash; "
    "the statement is not in the export, and this is a Hard problem whose "
    "correct approach depends on the exact definition of the stability "
    "factor and of the permitted operation. A solution written from an "
    "assumed statement would be worth nothing.")
  + p("The transferable finding does not need the statement. Sixteen minutes "
      "and six submissions with the core model untouched is the shallow "
      "debugging loop at its most expensive: each edit was local, each "
      "verdict was the same, and the sixth attempt was no closer than the "
      "first.")
  + p("There is also a complexity-budget tell here. A greedy that "
      "&ldquo;repeatedly halves the largest thing&rdquo; is a plausible "
      "shape, and plausible shapes are exactly what a max-heap makes easy to "
      "write. Reaching for the structure before proving the greedy is the "
      "habit; the structure then makes the wrong idea comfortable to keep.")),
 "fix": (
  p("Two things to do, in order, and neither is a keystroke of Java.")
  + ul("Re-read the statement and write down what one operation actually "
       "does to the stability factor. If you cannot state that in a "
       "sentence, no greedy is safe.",
       "Prove the greedy before writing it, with an exchange argument -- the "
       "same one-line proof the intervals lesson uses for earliest-finish. "
       "A greedy you cannot justify in a sentence is a guess with a heap "
       "attached to it.")
  + p("If the exchange argument does not go through, the answer is almost "
      "certainly binary search on the answer: guess a stability factor, ask "
      "whether it is achievable within the operation budget, and let "
      "monotonicity do the rest. That is the standard escape from "
      "&ldquo;minimise the maximum&rdquo; and it is a lesson you already "
      "have.")),
 "lessons": ["binary-search", "complexity-budget", "number-theory"],
},
]


# --------------------------------------------------------------------------
# Section 3 item 12 of REPORT.md: topics whose tag names a technique the
# submitted code did not use.
#
# The report listed these as a failing. Reading the bundles, they are two
# different things: places where a simpler tool was correct and the tag is
# merely category metadata, and places where the intended technique is genuinely
# absent from the record. `verdict` says which, and `evidence` is a regex that
# selects the analysis's own sentence out of findings/<topic>.json, so nothing
# on the page is a paraphrase of the data by hand.
#
# Two topics the report named -- binary-indexed-tree and segment-tree -- are not
# here. Their bundles contain real implementations with real merge and boundary
# bugs, which is the opposite of an unused technique.
#
# Technique dict:
#     topic     findings/<topic>.json, and the chapter page it links to
#     name      the technique, not the tag
#     verdict   "substituted" (the simpler tool was right) or "absent"
#     what      three sentences: what the technique actually is
#     wins      when it beats what was written instead
#     evidence  regex selecting the analysis note that says what was used
#     lessons   slugs worth reading alongside it
# --------------------------------------------------------------------------

TECHNIQUES = [
{
 "topic": "meet-in-the-middle",
 "name": "Meet in the middle",
 "verdict": "absent",
 "what": p("Split the input in half, enumerate every subset of each half "
           "separately, and combine the two halves by sorting one and searching "
           "it for each element of the other. It turns 2<sup>n</sup> into "
           "2<sup>n/2</sup> log 2<sup>n/2</sup>, which is the difference between "
           "a million operations and a trillion. The technique is entirely "
           "about the combining step: the two halves are easy, and the whole "
           "art is choosing a key that lets a partial answer from one half find "
           "its partner in the other."),
 "wins": p("Whenever a constraint reads <code>n &le; 40</code> and the obvious "
           "solution is exponential. <em>Tallest Billboard</em> has "
           "<code>rods.length &le; 20</code>, which is the constraint author "
           "writing &ldquo;2<sup>10</sup> &times; 2<sup>10</sup>&rdquo; on the "
           "page in plain sight. A DP over the sum dimension also passes here, "
           "which is why the substitute went unnoticed &mdash; but the bound was "
           "not chosen for the DP."),
 "evidence": r"meet-in-the-middle",
 "lessons": ["complexity-budget", "dynamic-programming"],
},
{
 "topic": "binary-lifting",
 "name": "Binary lifting",
 "verdict": "absent",
 "what": p("Precompute, for every node, its 2<sup>k</sup>-th ancestor for every "
           "k up to log n, giving an n log n table. Any ancestor query then "
           "becomes a walk over the set bits of the jump distance, in log n "
           "steps rather than one step per level. The same table answers "
           "lowest-common-ancestor queries by lifting both nodes to equal depth "
           "and then jumping them upward together while their ancestors differ."),
 "wins": p("When ancestor or LCA queries are asked repeatedly on a fixed tree. "
           "One query is cheaper to answer by walking; a thousand queries on a "
           "deep tree is where the table pays for itself. All five problems in "
           "this chapter were solved with per-query ascent, and the chapter "
           "carries eight diagnosed mistakes &mdash; the most of any technique "
           "on this page &mdash; several of them in exactly the hand-rolled "
           "pointer-synchronised walking the table would replace."),
 "evidence": r"binary lifting|sparse ancestor",
 "lessons": ["graph-traversal", "recursion"],
},
{
 "topic": "flow-network",
 "name": "Network flow and bipartite matching",
 "verdict": "absent",
 "what": p("Model the problem as a graph with capacities on the edges and push "
           "as much flow as possible from a source to a sink; the maximum flow "
           "equals the minimum cut, and an assignment problem becomes a flow "
           "problem by giving every worker and every job a unit-capacity edge. "
           "Min-cost max-flow extends this to the cheapest such assignment. The "
           "whole family reduces optimisation problems that look combinatorial "
           "to a graph algorithm with a known bound."),
 "wins": p("When the problem is &ldquo;pair these up optimally&rdquo; and the "
           "sizes are too large for a bitmask. <em>Campus Bikes II</em> is small "
           "enough that bitmask DP is the right answer and the analysis notes "
           "that the reader arrived at that formulation unprompted, after a "
           "brute force had already passed. Flow is what the same problem needs "
           "one order of magnitude up."),
 "evidence": r"bipartite matching",
 "lessons": ["graph-traversal", "dynamic-programming"],
},
{
 "topic": "floyds-cycle-finding-algorithm",
 "name": "Tortoise and hare",
 "verdict": "absent",
 "what": p("Advance one pointer by a single step and another by two; if there is "
           "a cycle they meet inside it, and if there is not, the fast pointer "
           "runs off the end. Resetting the slow pointer to the head and then "
           "advancing both by one step lands them together on the cycle's first "
           "node, which is the fact that makes the technique useful rather than "
           "merely cute. It uses constant memory, which is the entire reason to "
           "prefer it over a visited set."),
 "wins": p("Any time a cycle must be detected in a structure you cannot annotate "
           "&mdash; a linked list you do not own, a functional graph, a digit "
           "process like <em>Happy Number</em>. This chapter's failures are not "
           "in the idea: they cluster in empty and single-node guards and in "
           "<code>&amp;&amp;</code>-versus-<code>||</code> short-circuit logic, "
           "which is [[degenerate-inputs]] rather than this technique."),
 "evidence": r"tortoise|two-pointer technique first|iteration-count heuristic",
 "lessons": ["degenerate-inputs", "linked-list"],
},
{
 "topic": "kosarajus-algorithm",
 "name": "Kosaraju's strongly connected components",
 "verdict": "substituted",
 "what": p("Run a depth-first search over the graph and push each node onto a "
           "stack as it finishes, then run a second search on the reversed graph "
           "in stack order; each tree of that second pass is one strongly "
           "connected component. Two linear passes give the full decomposition, "
           "and contracting each component yields a directed acyclic graph you "
           "can then process in topological order. Tarjan's algorithm computes "
           "the same thing in one pass with low-link numbers."),
 "wins": p("When you need the components themselves &mdash; their sizes, the "
           "condensed graph, or which of them are sinks. All three problems here "
           "only need to know whether a node lies on or leads to a cycle, which "
           "three-colour DFS answers directly. The substitution is correct; "
           "the tag is not evidence either way."),
 "evidence": r"Kosaraju|two-pass reverse-graph",
 "lessons": ["graph-traversal"],
},
{
 "topic": "rolling-hash",
 "name": "Rolling hash",
 "verdict": "substituted",
 "what": p("Treat a string window as a number in some base modulo a large prime, "
           "so sliding the window one character right costs a multiply, an add "
           "and a subtract rather than a rescan. Comparing two substrings then "
           "costs one integer comparison, with a collision probability you "
           "control by the choice of modulus. Precomputing prefix hashes makes "
           "any substring's hash an O(1) lookup."),
 "wins": p("When you need to compare many arbitrary substring pairs, not find "
           "one pattern &mdash; deduplicating windows, binary-searching the "
           "longest repeated substring, matching many patterns at once. Both "
           "problems here are single-pattern matching, where Z and KMP are "
           "exact rather than probabilistic, and both were solved clean on the "
           "first attempt. Preferring the algorithm you know cold is the right "
           "call under time pressure."),
 "evidence": r"rolling hash",
 "lessons": ["strings"],
},
{
 "topic": "boyer-moore-string-search-algorithm",
 "name": "Boyer-Moore string search",
 "verdict": "substituted",
 "what": p("Align the pattern against the text and compare from the pattern's "
           "right end leftward; on a mismatch, use precomputed bad-character and "
           "good-suffix tables to skip the alignment forward by as much as the "
           "pattern's whole length. Unlike KMP it can be sublinear, because "
           "characters absent from the pattern let it jump past them entirely. "
           "It is the algorithm behind most real-world <code>grep</code>-like "
           "searching."),
 "wins": p("On long texts with long patterns over a large alphabet, where the "
           "skips are big. <em>Find the Index of the First Occurrence</em> has "
           "tiny inputs, and the three implementations in the record &mdash; "
           "brute force in 2021, KMP in 2021, the Z-function in 2025 &mdash; are "
           "each fine for it. This chapter's twelve diagnosed mistakes are about "
           "resetting the pattern pointer on a mismatch, which is "
           "[[mutable-state]]."),
 "evidence": r"Boyer-Moore",
 "lessons": ["strings", "mutable-state"],
},
{
 "topic": "algorithm-x",
 "name": "Algorithm X",
 "verdict": "substituted",
 "what": p("Express the problem as an exact cover &mdash; a matrix of "
           "constraints and choices where you must pick a set of rows covering "
           "every column exactly once &mdash; and search it by repeatedly "
           "choosing the column with the fewest remaining options. That "
           "least-options-first rule is the whole power of the method: it fails "
           "fast on the most constrained part of the search. Dancing Links is "
           "the data structure that makes covering and uncovering a column O(1) "
           "and reversible."),
 "wins": p("When the constraints are numerous and heterogeneous, so that "
           "choosing where to branch matters more than the branching itself. "
           "N-Queens has one constraint shape and a natural row-by-row order, "
           "which is why plain backtracking is the correct tool and both "
           "solutions used it."),
 "evidence": r"Algorithm X|DLX",
 "lessons": ["recursion"],
},
{
 "topic": "dancing-links",
 "name": "Dancing Links",
 "verdict": "substituted",
 "what": p("Store the exact-cover matrix as a doubly linked list in two "
           "dimensions, so that removing a row or column is four pointer writes "
           "and restoring it is four more. Because the removed node keeps its own "
           "links, undoing a cover is exactly the reverse assignment &mdash; no "
           "copying, no allocation, no bookkeeping. It is the canonical example "
           "of a structure designed so that backtracking is free."),
 "wins": p("On exact-cover problems where the search tree is deep and wide "
           "enough that copying state at each node dominates. <em>Sudoku "
           "Solver</em> was accepted first try in 27 minutes with "
           "constraint-propagation backtracking, which is the pragmatic answer; "
           "the note is that the record contains no cover/uncover operations "
           "anywhere, so nothing here demonstrates the technique."),
 "evidence": r"Dancing Links|toroidal|cover/uncover",
 "lessons": ["recursion", "mutable-state"],
},
{
 "topic": "bellman-ford-algorithm",
 "name": "Bellman-Ford",
 "verdict": "substituted",
 "what": p("Relax every edge in the graph n-1 times; after pass k, every "
           "shortest path using at most k edges is correct, so after n-1 passes "
           "all of them are. A further pass that still improves something proves "
           "a negative cycle exists. It is slower than Dijkstra and it is the "
           "only one of the two that survives negative weights."),
 "wins": p("Negative edge weights, or a bound on the number of edges in the path "
           "&mdash; the k-stops variant of the cheapest-flight problem is "
           "Bellman-Ford with the loop count as the answer. <em>Evaluate "
           "Division</em> has multiplicative positive weights and was solved with "
           "BFS, which is correct. See [[graph-traversal]] for when Dijkstra's "
           "assumption breaks."),
 "evidence": r"Bellman-Ford",
 "lessons": ["graph-traversal"],
},
{
 "topic": "sieve-theory",
 "name": "The sieve of Eratosthenes",
 "verdict": "substituted",
 "what": p("Mark the multiples of each prime up to the square root of the limit; "
           "what survives is every prime below the limit, in roughly n log log n "
           "time. Storing the smallest prime factor rather than a boolean turns "
           "the same table into an O(log n) factoriser for any number in range. "
           "The cost is paid once for the whole range instead of per query."),
 "wins": p("When many numbers must be tested or factorised and they share a "
           "bounded range. <em>Four Divisors</em> was solved by trial division "
           "up to the square root of each element, which the analysis notes is "
           "simply fast enough at these bounds. Reach for the sieve when the "
           "per-element cost multiplied by the element count crosses your budget "
           "&mdash; see [[complexity-budget]] and [[number-theory]]."),
 "evidence": r"sieve",
 "lessons": ["number-theory", "complexity-budget"],
},
{
 "topic": "sprague-grundy-theorem",
 "name": "Sprague-Grundy",
 "verdict": "substituted",
 "what": p("Give every position of an impartial game a Grundy number: the "
           "smallest non-negative integer not among the Grundy numbers of its "
           "moves. A position is losing exactly when its Grundy number is zero, "
           "and the Grundy number of several independent games played at once is "
           "the XOR of theirs. That XOR is the entire reason the theory exists."),
 "wins": p("When a position decomposes into independent sub-games &mdash; piles, "
           "disconnected components, separate rows. <em>Stone Game IV</em> is a "
           "single non-decomposable game, so a plain win/lose boolean DP is not "
           "a shortcut but the correct tool, and the analysis says as much. "
           "Nothing is missing here except an occasion to use the XOR."),
 "evidence": r"Grundy",
 "lessons": ["dynamic-programming"],
},
{
 "topic": "newtons-method",
 "name": "Newton's method",
 "verdict": "substituted",
 "what": p("To solve f(x) = 0, repeatedly replace your guess with the point "
           "where the tangent at that guess crosses zero. For an integer square "
           "root this is <code>x = (x + n / x) / 2</code>, which doubles the "
           "number of correct digits per iteration and converges in a handful of "
           "steps from any sane start. Binary search on the answer solves the "
           "same problem in log n steps and is far harder to get wrong."),
 "wins": p("Rarely, in this setting: it matters when the function is expensive "
           "and smooth, or precision must be pushed far. <em>Sqrt(x)</em> was "
           "solved with a single <code>Math.sqrt</code> call, which the analysis "
           "records as optimising for the shortest correct submission over "
           "practising the nominal technique. That is a defensible choice for "
           "credit and a poor one for the drill the problem was set as."),
 "evidence": r"Newton",
 "lessons": ["binary-search"],
},
{
 "topic": "quicksort",
 "name": "Quickselect and partitioning",
 "verdict": "substituted",
 "what": p("Partition an array around a pivot so that everything smaller sits "
           "left of it and everything larger sits right; the pivot is then in "
           "its final sorted position. Recursing into both sides sorts; recursing "
           "into only the side containing the index you want selects, in linear "
           "expected time. Selection, not sorting, is what this is worth knowing "
           "for."),
 "wins": p("Finding a k-th largest element, or a top-k set, where sorting the "
           "whole array is n log n and partitioning is n. Both problems in this "
           "chapter are &ldquo;sort once, then one linear pass&rdquo;, where the "
           "library sort is the right answer. Where this would have paid is "
           "elsewhere in the export &mdash; the "
           "<em>top-k-frequent-elements</em> grind is a partitioning problem, and "
           "its failures were partition comparisons toggled between "
           "<code>&lt;</code> and <code>&lt;=</code> across three submissions."),
 "evidence": r"quicksort/partition|manual quicksort",
 "lessons": ["comparators", "case-analysis"],
},
{
 "topic": "tournament-sort",
 "name": "Tournament merge",
 "verdict": "substituted",
 "what": p("Merge k sorted sequences by pairing them up and merging each pair, "
           "then pairing the results, until one remains &mdash; log k rounds over "
           "n total elements. A heap of the k current heads reaches the same "
           "n log k bound while touching each element once. The pairwise form "
           "needs no auxiliary structure and parallelises; the heap form is "
           "shorter to write."),
 "wins": p("When merging is external or parallel, or when a heap's constant "
           "factor is the problem. <em>Merge k Sorted Lists</em> was solved with "
           "a priority queue, which is optimal and idiomatic; the pairwise "
           "version was written afterwards as post-solve exploration, once the "
           "problem was already passed. Both are in the record, which makes this "
           "the one entry on the page where the named technique does exist."),
 "evidence": r"tournament|pairwise",
 "lessons": ["heaps"],
},
]
