#!/usr/bin/env python3
"""Course content for the improvement book.

The lessons here are authored -- prose and worked examples cannot be derived
from submission data. Everything *about* you is derived: each lesson carries a
`match` pattern, and build_book.py joins it against findings/*.json so the
"your own instances" section is pulled from mistakes you actually made, with
counts and file paths. Rewrite a lesson freely; the evidence stays honest.

Examples are Java because 4,824 of 5,212 submissions in this export are Java.

Lesson dict:
    slug      file name, course-<slug>.html
    title     lesson heading
    one_line  index blurb
    why       why this lesson exists for *this* reader, in one paragraph
    summary   html -- what the thing is, before any of the detail
    used_for  [(situation, why)] -- when you reach for it
    patterns  [(phrasing in the statement, what it is asking for)]
    match     regex over "what_went_wrong" + "how_it_was_fixed", case-insensitive
    basics    [(heading, html)] -- the from-zero explanation
    rules     [str] -- the checklist to run before submitting
    drill     what to practise, concretely
"""

from __future__ import annotations

import diagrams
import traces

# --------------------------------------------------------------------------
# Small helpers for writing the lesson bodies without drowning in markup.
# --------------------------------------------------------------------------

def p(text: str) -> str:
    return f"<p>{text}</p>"


def code(java: str, compiles: bool = True) -> str:
    """A Java block. `compiles=False` marks an illustration, not a program.

    build_book.py --check puts every other block through javac, wrapped as a
    file, a class body or a method body -- whichever one it needs. A block that
    cannot compile under any of them has to say so here, so the exception is a
    decision in the source rather than a hole in the check. The eight that do
    are pseudo-code: `{ ... }` placeholders, `...` in a signature, an ASCII
    picture, catalogues of expressions that are not statements -- and one that
    demonstrates a compile error on purpose, which javac is right to reject.
    """
    from html import escape
    kind = "lesson-code" if compiles else "lesson-code illustrative"
    return f'<pre class="{kind}"><code>{escape(java.strip())}</code></pre>'


def ul(*items: str) -> str:
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="lesson-table"><tr>{head}</tr>{body}</table>'


# --------------------------------------------------------------------------
# The lessons, in the order they should be worked through.
# --------------------------------------------------------------------------

LESSONS = [
# ==========================================================================
{
 "slug": "complexity-budget",
 "title": "Read the constraints, then choose the algorithm",
 "one_line": "The input size tells you the complexity you are allowed. Pick it before you write a line.",
 "why": "76 Time Limit Exceeded verdicts, spread over 35 topics. The pattern in your "
        "history is consistent: you write the direct simulation, submit it, and only "
        "reach for the right structure once the judge refuses it. That works, but it "
        "costs you the first attempt on nearly every hard problem, and it is the "
        "single biggest reason your first-attempt accept rate sits at 54%.",
 "summary": (
  p('Before any data structure, you pick a complexity class. The constraint '
     'line in the problem statement is not decoration — it is the '
     'specification of which algorithms are allowed, and it is written '
     'before you read the examples.') +
  p('Reading it first turns “which algorithm?” from a guess into a lookup. '
     'n ≤ 20 means exponential is fine. n ≤ 10⁵ means you have O(n log n) '
     'and nothing worse. There is no third option where you write the '
     'quadratic one and optimise the inner loop.')
 ),
 "used_for": [
  ('You have read the statement but written nothing yet',
   'The constraint line narrows a dozen candidate approaches to two or '
    'three, before you have invested in any of them.'),
  ('A submission came back Time Limit Exceeded',
   'TLE is never a micro-optimisation problem. It means the complexity '
    'class is wrong, and tightening the inner loop will not save it.'),
  ('You are about to type a second nested for loop',
   'n² at n = 10⁵ is 10¹⁰ operations. Check the budget before the loop '
    'exists, not after the verdict.'),
  ('The problem has queries',
   'The cost is per query times the number of queries. 10⁵ queries × an '
    'O(n) scan is the same 10¹⁰.'),
  ('You are choosing between two correct solutions',
   'Correct and too slow scores zero. The budget is the tiebreak, and it '
    'is decidable before you write either one.'),
 ],
 "patterns": [
  ('1 ≤ n ≤ 20',
   'Subset or permutation enumeration — 2ⁿ or n·2ⁿ. Bitmask DP is in '
    'scope.'),
  ('1 ≤ n ≤ 500',
   'O(n³) fits. Interval DP and Floyd–Warshall are in scope.'),
  ('1 ≤ n ≤ 5000',
   'O(n²) fits. Two-sequence DP, quadratic LIS, all-pairs scans.'),
  ('1 ≤ n ≤ 10⁵',
   'O(n log n). Sorting, a heap, binary search, or one pass with a map.'),
  ('1 ≤ n ≤ 10⁹',
   'You cannot touch every element. Maths, binary search on the answer, or '
    'digit DP.'),
  ('Return the answer modulo 10⁹ + 7',
   'A counting problem. The count is the answer; you never build the '
    'objects you are counting.'),
  ('10⁴ queries over an array of 10⁵',
   'Precompute or use a range structure. A scan per query is 10⁹.'),
 ],
 "match": r"brute.force|quadratic|O\(n\^?2\)|O\(n\*n\)|too slow|exponential|"
          r"time limit|\bTLE\b|per query|recomput|wrong complexity|scan(s|"
          r"ned)? the entire|copied? .*(queue|heap|list) .*every|re-?sort",
 "basics": [
  ("The one table worth memorising",
   diagrams.growth_curves() +
   p("A judge does roughly 10<sup>8</sup> simple operations per second. Work backwards "
     "from <code>n</code> in the constraints to the complexity you can afford:")
   + table(("n up to", "You can afford", "Which usually means"), [
       ("10<sup>18</sup>", "O(log n)", "binary search on the answer, matrix power, math"),
       ("10<sup>6</sup>–10<sup>7</sup>", "O(n) or O(n log n)", "one pass, sort, prefix sums, sliding window, heap"),
       ("10<sup>5</sup>", "O(n log n)", "sort, BIT/segment tree, Dijkstra, DSU"),
       ("10<sup>4</sup>", "O(n<sup>2</sup>)", "DP over pairs, all-pairs scan"),
       ("500", "O(n<sup>3</sup>)", "Floyd–Warshall, interval DP"),
       ("20–25", "O(2<sup>n</sup>) or O(2<sup>n</sup>·n)", "bitmask DP, meet in the middle"),
       ("10–12", "O(n!)", "permutation search"),
   ])
   + p("This is a <em>budget</em>, not a target. If <code>n ≤ 10<sup>5</sup></code> and "
       "your idea is a nested loop, the idea is already wrong — you know that before "
       "you have written any code, and before the judge tells you.")),

  ("Where the time actually goes",
   p("Cost is per-operation × number-of-operations. Two things in your history burn "
     "time in ways that are easy to miss:")
   + ul("<strong>Work inside a query loop.</strong> <code>q</code> queries × O(n) work "
        "each is O(qn), even though neither number looks large on its own.",
        "<strong>Rebuilding state you already had.</strong> Copying a heap, re-sorting a "
        "list, or re-scanning a table on every call turns an O(1) query into O(n log n)."))
  ,
  ("Your own case: find-median-from-data-stream",
   diagrams.two_heaps() +
   p("You replaced two heaps with one <code>PriorityQueue</code>, then on every "
     "<code>findMedian()</code> copied the queue and drained it with <code>poll()</code> "
     "to walk to the middle. Each query became O(n log n) instead of O(1).")
   + p("The two-heap invariant is the whole trick, and it is small:")
   + code("""
// max-heap holds the smaller half, min-heap holds the larger half
PriorityQueue<Integer> lo = new PriorityQueue<>(Comparator.reverseOrder());
PriorityQueue<Integer> hi = new PriorityQueue<>();

void addNum(int num) {
    lo.offer(num);
    hi.offer(lo.poll());              // push the largest of lo across
    if (hi.size() > lo.size()) {      // keep lo.size() == hi.size() or one more
        lo.offer(hi.poll());
    }
}

double findMedian() {
    return lo.size() > hi.size() ? lo.peek() : (lo.peek() + hi.peek()) / 2.0;
}
""")
   + p("Invariant: <code>lo</code> holds the smaller half, <code>hi</code> the larger, "
       "and <code>lo.size()</code> is <code>hi.size()</code> or one more. Every "
       "operation restores it. The median then falls out in O(1).")),
 ],
 "rules": [
  "Read the constraint line before the problem statement. Write the complexity budget down.",
  "If the idea in your head exceeds the budget, do not code it — you already know it fails.",
  "Count work inside loops multiplicatively: q queries × O(n) each is O(qn).",
  "Never copy or drain a container inside a query. If a query is O(n), you need different state.",
 ],
 "drill": "Take five problems you solved by brute force first. For each, write the "
          "constraint, the budget, and the structure that meets it — before looking at "
          "your old code. Then compare.",
},


# ==========================================================================
{
 "slug": "integer-width",
 "title": "Fixed-width integers: overflow and the modulus",
 "one_line": "A Java int silently wraps at 2,147,483,647. Widen at the first multiply, not at the assignment.",
 "why": "43 overflow bugs and 30 modular-arithmetic bugs, and — more telling — you fixed "
        "this exact bug in sum-of-subarray-minimums, then reintroduced the identical "
        "shape in number-of-zero-filled-subarrays during a later cleanup. The rule is "
        "not being applied; each instance is being patched individually.",
 "summary": (
  p('A Java <code>int</code> is exactly 32 bits. It does not grow. When a '
     'result needs a 33rd bit, the top bit is discarded and the value '
     'silently becomes something else — very often a negative number. '
     'Nothing throws, and the compiler does not warn.') +
  p('The only defence is knowing where the widening belongs: at the first '
     'operation that can leave the range, not at the assignment that stores '
     'the result. <code>long x = a * b;</code> has already overflowed by the '
     'time the assignment runs.')
 ),
 "used_for": [
  ('Multiplying two values that can each reach 10⁵',
   '10⁵ × 10⁵ = 10¹⁰, more than four times the int limit. The multiply overflows '
    'before the assignment happens.'),
  ('Summing an array of 10⁵ elements that each reach 10⁴',
   'The running total leaves int range long before the loop ends.'),
  ('Computing a midpoint in binary search',
   '(lo + hi) overflows when both are near 2³¹. lo + (hi - lo) / 2 cannot.'),
  ('Anything that says “modulo 10⁹ + 7”',
   'The modulus alone is 30 bits, so a product of two reduced values is 60 '
    'bits and must be computed in long.'),
  ('Picking a sentinel for a running maximum',
   'Integer.MIN_VALUE plus any negative number wraps to a positive one. '
    'The sentinel needs the same width discipline as the data.'),
 ],
 "patterns": [
  ('0 ≤ nums[i] ≤ 10⁹',
   'Any sum or product of two elements needs long.'),
  ('Return the answer modulo 10⁹ + 7',
   'Every multiply is (long) a * b % MOD, and every add is followed by a '
    'reduction.'),
  ('The answer is guaranteed to fit in a 32-bit integer',
   'The answer fits. The intermediate values usually do not — that '
    'sentence is about the return type only.'),
  ('Count the number of pairs / subarrays / subsequences',
   'The count is O(n²) or larger, so it needs long even when every element '
    'is small.'),
  ('1 ≤ n ≤ 10⁹, compute f(n)',
   'Fast exponentiation under a modulus — every step is a long multiply.'),
  ('Values may be negative and you take an absolute value',
   'Math.abs(Integer.MIN_VALUE) is still Integer.MIN_VALUE. The one input '
    'that has no positive counterpart.'),
 ],
 "match": r"overflow|truncat|widen|\(long\)|\blong\[\]|int accumulator|modul|"
          r"\bMOD\b|1e9|10\^9|1_000_000_007|modular inverse",
 "basics": [
  ("What actually happens",
   diagrams.twos_complement() +
   p("A Java <code>int</code> is 32 bits, two's complement, range "
     "−2,147,483,648 … 2,147,483,647. When a computation leaves that range it does "
     "<em>not</em> throw — it wraps around silently:")
   + code("""
int a = 2_000_000_000;
int b = a + a;            // b == -294967296.  No error. No warning.

long c = a + a;           // STILL -294967296: the addition happens in int,
                          // then the wrong answer is widened to long.
long d = (long) a + a;    // 4000000000.  Correct: one operand widened first.
""")
   + p("That third line is the trap, and it is the one in your code. The type of the "
       "<em>destination</em> does not change how the arithmetic is done. Java picks the "
       "arithmetic width from the <em>operands</em>. Widening after the fact widens a "
       "value that is already wrong.")),

  ("Your own case: sum-of-subarray-minimums",
   diagrams.widening_order() +
   code("""
// what you submitted
int ans = 0;
ans += nums[i] * (nextSmaller[i] - i) * (i - prevSmaller[i]);
ans %= 1_000_000_007;
""")
   + p("Both multiplications happen in <code>int</code>. With <code>nums[i]</code> up to "
       "3·10<sup>4</sup> and the two spans up to 3·10<sup>4</sup> each, the product "
       "reaches ~2.7·10<sup>13</sup> — it has wrapped long before <code>%</code> is "
       "reached. Taking the modulus later cannot undo a wrap.")
   + code("""
// correct
long ans = 0;
long term = (long) nums[i] * (nextSmaller[i] - i) % MOD * (i - prevSmaller[i]) % MOD;
ans = (ans + term) % MOD;
""")
   + p("You then tried, in a post-solve pass, taking <code>% mod</code> after each "
       "multiplication while everything was still <code>int</code>. That does not help: "
       "the very first multiplication has already overflowed. The width is the fix; the "
       "modulus placement is a separate, second requirement.")),

  ("The modulus rules",
   ul("<strong>Reduce after every multiply and every add</strong>, not once at the end. "
      "Two values below 10<sup>9</sup>+7 multiply to ~10<sup>18</sup>, which fits in "
      "<code>long</code> but not in anything narrower — so <code>long</code> plus a "
      "reduction after each step is exactly enough.",
      "<strong>Subtraction can go negative.</strong> Use "
      "<code>((a - b) % MOD + MOD) % MOD</code>.",
      "<strong>Division does not distribute over the modulus.</strong> Multiply by the "
      "modular inverse instead — <code>modPow(b, MOD - 2, MOD)</code> when MOD is prime.")),

  ("Sentinels have a width too",
   p("<code>Arrays.fill(dist, Integer.MAX_VALUE)</code> on a <code>long[]</code> "
     "compiles cleanly and is wrong: it fills with 2.1·10<sup>9</sup>, which real path "
     "costs in your problems exceed. You hit this in <code>jump-game-viii</code>, fixed "
     "it, then reintroduced it in a later cleanup pass. Match the sentinel to the array: "
     "<code>Long.MAX_VALUE</code> for <code>long[]</code>.")
   + p("And when a sentinel will be added to, use <code>Long.MAX_VALUE / 2</code> — so "
       "<code>dist[u] + w</code> cannot itself overflow during a relaxation you were "
       "going to reject anyway.")),
 ],
 "rules": [
  "Cast the FIRST operand of any product that could exceed ~2·10⁹: (long) a * b.",
  "The destination type never changes how the arithmetic is done. Widen the operands.",
  "Reduce mod after every multiply and add, never once at the end.",
  "((a - b) % MOD + MOD) % MOD for subtraction. Modular inverse for division.",
  "Sentinel width must match the array width. Use MAX_VALUE / 2 if it will be added to.",
 ],
 "drill": "Grep your accepted Java for `int` accumulators that receive a product. "
          "Every one is a latent bug on a larger test set.",
},


# ==========================================================================
{
 "slug": "sentinels",
 "title": "Sentinels and identity elements",
 "one_line": "0 is not the identity for max when values can be negative. Pick the identity from the operation.",
 "why": "53 mistakes involving a sentinel or an uninitialised value, across 29 topics. "
        "The shape is always the same: an initial value that quietly assumes the data is "
        "non-negative, non-empty, or in range — and one test case where it isn't.",
 "summary": (
  p('A sentinel is the value you start a fold with, or the value that means '
     '“nothing here yet”. Choosing it is arithmetic, not style: the identity '
     'for + is 0, for × it is 1, for max it is negative infinity, for min it '
     'is positive infinity, for gcd it is 0.') +
  p('Pick the wrong one and the bug only shows on inputs that happen to be '
     'all-negative, or empty, or a single node — which is exactly the input '
     'the judge has and your hand-written samples do not.')
 ),
 "used_for": [
  ('Folding a list into a max, min, sum or product',
   "The starting value has to be the operation's identity, or the first "
    'real element is combined with garbage.'),
  ('A DP table where “unreachable” must differ from “zero”',
   '0 is a legitimate answer for most DP tables. Unreachable needs a value '
    'outside the answer domain.'),
  ('Inserting or deleting at the head of a linked list',
   'A dummy head is a structural sentinel: it stops the first node from '
    'being a special case.'),
  ('Grid or array scans that read one past the edge',
   'A padded border row and column remove the bounds test from the inner '
    'loop entirely.'),
  ('A monotonic stack that has to drain at the end',
   'Appending one sentinel element that beats everything pops the stack '
    'empty without a second loop.'),
 ],
 "patterns": [
  ('nums[i] can be negative',
   'Your max accumulator cannot start at 0. Start at nums[0], or at '
    'Integer.MIN_VALUE.'),
  ('Return -1 if no such element exists',
   '−1 is out of the answer domain here — confirm it cannot also be a '
    'legitimate answer.'),
  ('The tree may have a single node / the array may be empty',
   'The fold has to be correct with zero or one element folded in. That is '
    'a stated requirement, not an edge case.'),
  ('Insert into or delete from a sorted linked list',
   'Dummy head. Every “what if it is the first node” branch disappears.'),
  ('Minimum cost, where some states are unreachable',
   'A large sentinel such as Integer.MAX_VALUE / 2 — halved so that adding '
    'to it cannot overflow.'),
  ('Find the maximum path sum in a tree of possibly negative values',
   'The identity for max is not 0. A branch that only hurts contributes 0 '
    'by choice, not by accident.'),
 ],
 "match": r"sentinel|MAX_VALUE|MIN_VALUE|uninitiali|initiali[sz]ed to|"
          r"initial value|dummy (node|head|tail)|starts at 0|seeded with|"
          r"placeholder|never linked|default value|assumes .*non-negative",
 "basics": [
  ("What an identity element is",
   diagrams.identity_competition() +
   p("For an operation <code>op</code>, the identity <code>e</code> is the value where "
     "<code>op(e, x) == x</code> for every <code>x</code>. When you fold a collection "
     "you must start from the identity, or the starting value competes with the data:")
   + table(("Operation", "Identity", "Java"), [
       ("sum", "0", "<code>0</code> / <code>0L</code>"),
       ("product", "1", "<code>1L</code>"),
       ("max", "−∞", "<code>Integer.MIN_VALUE</code> / <code>Long.MIN_VALUE</code>"),
       ("min", "+∞", "<code>Integer.MAX_VALUE</code> / <code>Long.MAX_VALUE</code>"),
       ("AND (bitwise)", "all ones", "<code>-1</code>"),
       ("OR / XOR", "0", "<code>0</code>"),
       ("GCD", "0", "<code>0</code>"),
       ("min-distance (Dijkstra)", "+∞", "<code>Long.MAX_VALUE / 2</code>"),
   ])
   + p("<code>max</code> starting at <code>0</code> is correct only if you have already "
       "proved every value is ≥ 0. That proof is where the bug lives.")),

  ("Your own case: binary-tree-maximum-path-sum",
   p("You started <code>globalMax</code> at <code>0</code> and the local accumulators at "
     "<code>-1</code>. On a tree whose node values are all negative, the true answer is "
     "the least-negative single node — but <code>0</code> outranks it, and the function "
     "returns a path that does not exist.")
   + code("""
// wrong: 0 is a value that can beat real data
int globalMax = 0;

// right: the identity for max is negative infinity
int globalMax = Integer.MIN_VALUE;
""")
   + p("You fixed <code>globalMax</code> and left the <code>-1</code> locals in place. "
       "They have the same defect for the same reason.")),

  ("When you need an out-of-domain sentinel",
   p("Sometimes you need a value meaning \"nothing here yet\" that cannot collide with "
     "real data. That value has to be provably outside the problem's stated value range "
     "— which the constraints give you. In "
     "<code>remove-duplicates-from-sorted-list-ii</code> you used <code>-101</code> "
     "because the constraints cap values at 100. That is the right method: read the "
     "bound, step outside it.")
   + p("The alternative, and usually the better one, is to not need a sentinel at all — "
       "carry a separate <code>boolean seen</code> or use "
       "<code>Optional</code>/<code>null</code>, so \"absent\" and \"a real value\" are "
       "different types rather than different numbers.")),

  ("Structural sentinels: dummy nodes",
   diagrams.dummy_nodes() +
   p("In linked structures a sentinel is a node, not a number, and its job is to delete "
     "the special cases at the head and tail. In <code>lru-cache</code> you introduced "
     "head/tail dummies but never linked them in the constructor, so the first "
     "<code>put()</code> dereferenced <code>tail.prev == null</code>.")
   + code("""
Node head = new Node(), tail = new Node();
head.next = tail;      // both directions, in the constructor,
tail.prev = head;      // before any operation can run
""")
   + p("A dummy head/tail pair means <code>add</code> and <code>remove</code> never need "
       "a null check — that is the entire reason to have them. If they are not wired up, "
       "you have paid the cost and kept the bug.")),
 ],
 "rules": [
  "Name the operation, then take its identity from the table. Never default to 0.",
  "If you use 0 or -1 as 'empty', prove from the constraints that no real value can be 0 or -1.",
  "Prefer a separate `seen` flag over an in-band magic number.",
  "Dummy nodes must be linked to each other in the constructor, both directions.",
 ],
 "drill": "Re-solve binary-tree-maximum-path-sum cold, on a tree of all-negative values, "
          "before you look at anything else.",
},


# ==========================================================================
{
 "slug": "bounds",
 "title": "Array bounds: check before you read",
 "one_line": "The guard must come before the access, not before the recursive call. And derive the size — never guess a bigger constant.",
 "why": "97 bounds, null and empty-input mistakes across 45 topics — your single largest "
        "category, and 123 Runtime Errors overall. Two distinct habits produce them: "
        "checking bounds one step too late, and sizing arrays by guessing.",
 "summary": (
  p('Every array access has a precondition, and the guard that enforces it '
     'has to run <em>before</em> the read, in the order the JVM evaluates. '
     'Two things break this. Writing <code>if (grid[r][c] == 1 &amp;&amp; '
     'inBounds(r, c))</code> reads first and checks second. Guarding in the '
     'caller instead of at the top of the recursive function covers the '
     'first call and none of the recursive ones.') +
  p('Sizing is the other half. Derive the array length from the constraints '
     '— 26 for lowercase letters, n + 1 for a 1-indexed Fenwick tree — '
     'rather than rounding up to a constant that looks big enough.')
 ),
 "used_for": [
  ('Any grid DFS or BFS with four-direction moves',
   'Guard at the top of the function so every entry point is covered, '
    'rather than before each recursive call.'),
  ('Reading s.charAt(i + 1) inside a loop',
   'The loop bound must be i < n - 1, or the last iteration reads past the '
    'end.'),
  ('Sizing a counting array from a character or value range',
   'new int[26] for lowercase, new int[128] for ASCII — derived from the '
    'constraint, not guessed.'),
  ('Two-pointer loops that advance inside the body',
   'The inner while (l < r && ...) needs its own bound test; the outer '
    "loop's condition does not cover it."),
  ('Anything that dereferences a node or unboxes a map lookup',
   'map.get(k) returns null, and unboxing null throws. Check membership '
    'before you unbox.'),
 ],
 "patterns": [
  ('m x n grid / board',
   'Write inBounds(r, c) once and call it first inside the recursion, '
    'before touching the cell.'),
  ('1 ≤ s.length (with no guarantee of a non-empty result)',
   'An empty intermediate is legal. The first access has to be guarded.'),
  ('The array is 1-indexed',
   'Fenwick trees are 1-indexed and the input is not. The off-by-one lives '
    'exactly here.'),
  ('s consists of lowercase English letters',
   "A 26-slot counting array is exact — and c - 'a' must be the only index "
    'expression.'),
  ('The list may be empty, and the answer is then 0',
   'The empty case is part of the specification, not something to discover '
    'from a Runtime Error.'),
  ('Return null if the node does not exist',
   'Every caller of that method now has a null path to handle.'),
 ],
 "match": r"out of bounds|IndexOutOf|ArrayIndex|NullPointer|null (check|guard|"
          r"pointer)|no guard|unguarded|missing guard|empty (array|input|list|"
          r"string|collection)|guessed (buffer|size|array)|hardcoded (size|"
          r"array)|new int\[\d|before .*(bounds|range) (were|was|are) checked|"
          r"past the end",
 "basics": [
  ("Order of operations in a guard",
   diagrams.guard_order() +
   diagrams.grid_bounds() +
   p("Java evaluates <code>&&</code> left to right and short-circuits. That is what makes "
     "a bounds guard work — and what makes it fail if the terms are in the wrong order:")
   + code("""
// WRONG: board[x][y] is read before x,y are known to be in range
if (board[x][y] == c && x >= 0 && x < m && y >= 0 && y < n) { ... }

// RIGHT: range first, then the read
if (x >= 0 && x < m && y >= 0 && y < n && board[x][y] == c) { ... }
""", compiles=False)
   + p("In <code>word-search-ii</code> you guarded the <em>recursive call</em> but read "
       "<code>board[newX][newY]</code> before it. The read is the access — it is what "
       "throws. It took three attempts to move the check above it.")
   + p("The reliable structure is to bounds-check at the <em>top of the callee</em>, once, "
       "rather than at every call site:")
   + code("""
void dfs(char[][] board, int x, int y, ...) {
    if (x < 0 || x >= board.length || y < 0 || y >= board[0].length) return;
    if (visited[x][y]) return;
    // from here down, (x, y) is known good
}
""", compiles=False)),

  ("Size arrays from the constraints, never by guessing",
   p("In <code>maximum-twin-sum-of-a-linked-list</code> you wrote "
     "<code>new int[10000]</code>; the constraints allow 10<sup>5</sup> nodes. In "
     "<code>concatenate-non-zero-digits</code> a lookup table was resized four times — "
     "11 → 10001 → 20001 → 100001 — across four consecutive Runtime Errors.")
   + p("Each of those resubmissions cost an attempt and taught nothing, because the "
       "constraint line already had the answer. Two options, both better than guessing:")
   + ul("<strong>Read the bound from the problem</strong> and write it as a named "
        "constant: <code>static final int MAX_N = 100_001;</code>",
        "<strong>Size from the input</strong>: <code>new int[nums.length + 1]</code>. This "
        "is strictly better — it cannot be wrong, and it does not need the constraint "
        "line at all.")),

  ("Unbounded scans",
   p("A loop that walks until it finds something must also stop at the edge:")
   + code("""
// smallest-missing-integer...: exists is boolean[51], ans can walk past 50
while (exists[ans]) ans++;

// bound the walk
while (ans <= 50 && exists[ans]) ans++;
""")
   + p("Any <code>while</code> whose condition reads an array needs a second clause "
       "keeping the index in range. There is no exception to this.")),

  ("Empty and single-element inputs",
   p("The three inputs that break more code than any others: the empty collection, the "
     "one-element collection, and the all-same collection. They are cheap to check "
     "mentally and they are where your Runtime Errors live. Before submitting, run "
     "<code>n = 0</code> and <code>n = 1</code> through the code in your head.")),
 ],
 "rules": [
  "Range check first, array read second — always, within a single && chain.",
  "Bounds-check at the top of the recursive function, not at each call site.",
  "Size arrays from the input (nums.length) or a named constant read off the constraints.",
  "Every while-loop condition that indexes an array needs an index-range clause too.",
  "Mentally run n = 0 and n = 1 before submitting.",
 ],
 "drill": "Re-solve word-search-ii cold. It cost you 8 failed attempts across four "
          "distinct bug classes — it is the densest single lesson in your export.",
},


# ==========================================================================
{
 "slug": "degenerate-inputs",
 "title": "Empty, one, two: the inputs you did not try",
 "one_line": "The algorithm is right. It has just never been shown fewer than "
             "three elements.",
 "why": "{{mistakes:degenerate-inputs}} diagnosed mistakes and "
        "{{habits:degenerate-inputs}} habits in accepted code, across "
        "{{problems:degenerate-inputs}} problems and "
        "{{topics:degenerate-inputs}} topics, are a correct algorithm meeting an input too small to run "
        "it on: an empty array indexed "
        "at [0], a single-node list whose next is null, a two-element window with no "
        "interior. These are the cheapest bugs in the export to prevent and among "
        "the most expensive you actually paid for. On reverse-linked-list you made "
        "the identical missing null check three separate times, once in a rewrite "
        "the same day as the fix. On linked-list-cycle a guard written with && "
        "instead of || crashed on exactly the input it was added to protect, and "
        "was carried through two more submissions before the operator changed. On "
        "path-sum-iii the root == null guard was added, dropped during a refactor, "
        "and added back. On rank-transform-of-an-array the empty-array oversight "
        "from the original solve recurred verbatim in a later revisit.",
 "summary": (
  p('Every algorithm you write is derived on a picture in your head, and the '
    'picture has enough elements to show the idea &mdash; four or five boxes, '
    'a left half and a right half, an interior to scan. The derivation is '
    'sound for that picture. Then the grader hands you a picture with no '
    'boxes in it.') +
  p('There are only three sizes that matter here, and you can check all three '
    'in about twenty seconds: <strong>zero, one, and two</strong>. Zero '
    'breaks anything that reads an element before checking there is one. One '
    'breaks anything with a &ldquo;previous&rdquo; or a &ldquo;next&rdquo;. '
    'Two breaks anything that assumes the first and last positions are '
    'different, or that there is an interior between them.') +
  p('This is not a lesson about being careful. Care is what you already spent '
    'on the algorithm. This is a lesson about a fixed, short checklist that '
    'costs the same whether you are tired or not.')
 ),
 "used_for": [
  ('Anything that reads index 0 or index n-1 before a loop',
   'The read happens whether or not the array has that index.'),
  ('Linked list and tree code',
   'null is a legal value of the type, so the compiler is satisfied and the '
   'dereference is not.'),
  ('Two-pointer and sliding-window scans',
   'They assume left and right start somewhere different. At n = 1 they do not.'),
  ('Divide and conquer',
   'The recursion bottoms out on the sizes you did not draw.'),
  ('Any formula with a division or a modulus by a length',
   'Length zero is a crash, not a wrong answer.'),
  ('Greedy scans that carry a running best',
   'The seed value is the n = 0 answer, and it is usually wrong.'),
 ],
 "patterns": [
  ('Runtime error on the first submission, wrong answer on none of the samples',
   'The samples are never degenerate. The hidden tests always are.'),
  ('ArrayIndexOutOfBounds at index 0',
   'You read before you counted.'),
  ('NullPointerException with no null anywhere in the statement',
   'An empty list, an empty tree, or a map lookup that missed.'),
  ('Divide by zero in a modulus you took over a length',
   'The length is zero and the statement allowed it.'),
  ('The answer is right on every input except the smallest one',
   'A special case that the general path happens to get wrong.'),
  ('The constraints say 1 &le; n, and you relaxed anyway',
   'Read them. If n cannot be 0, half this lesson does not apply and you '
   'should not pay for the guard.'),
 ],
 "match": r"empty (array|list|string|input|stack|queue|map|set|builder|heap|deque|"
          r"subarray|grid|tree|interval|window|result set)|"
          r"(array|list|string|input|stack|builder|heap|queue|window) (is |was |being )?empty|"
          r"\bisEmpty\b|empty-(array|list|string|input|stack|builder)|"
          r"\bn ?== ?0\b|\bnums\.length ?== ?0\b|\.length ?== ?0\b|"
          r"single[- ](element|node|character|item|row|column|cell|word|entry|letter)|"
          r"one[- ]element|only one (element|node|item|character)|"
          r"length ?== ?1\b|size\(\) ?== ?[01]\b|(degenerate|corner|edge)[- ]case|"
          r"two[- ](element|node)|null (input|head|root|array|list|string)|"
          r"(head|root|nums|s) ?== ?null",
 "basics": [

  ("The three sizes, and what each one breaks",
   p("Run these three before you submit. Not as tests &mdash; in your head, "
     "against the code on screen.")
   + table(("Size", "What it breaks", "Your own instance"), [
       ("n = 0", "any read of nums[0], any % length, any peek()",
        "missing-ranges: <code>nums[0]</code> read before the length check"),
       ("n = 1", "anything with a previous, a next, or a pair",
        "reverse-linked-list: <code>reverseTail(head.next)</code> on a lone node"),
       ("n = 2", "anything with an interior, or first != last",
        "spiral-matrix: the single-row guard, without the single-column one"),
     ])
   + p("The <em>spiral-matrix</em> row is the one worth staring at. The fix for "
       "the first degenerate case &mdash; a matrix that has collapsed to one row "
       "&mdash; was written and shipped. The mirror case, one column, was not, and "
       "cost another submission. <strong>Degenerate cases come in families. When "
       "you find one, write down its reflections before you fix it.</strong>")
   + p("There is a fourth size worth a moment, and it is not a size: the "
       "<em>all-same</em> and <em>all-negative</em> inputs. On "
       "<em>maximum-sum-circular-subarray</em> the wraparound trick has no "
       "meaning when every element is negative, because the &ldquo;inverted&rdquo; "
       "subarray is the whole array. That is not a small input; it is an input "
       "where a step of the derivation quietly stops being true.")),

  ("&amp;&amp; is not a guard",
   diagrams.guard_short_circuit() +
   p("This one is worth its own section because you have written it more than "
     "once and it looks correct on the page. A guard exists to stop the next "
     "expression from running. <code>&amp;&amp;</code> can only decide it is true "
     "by running that expression.")
   + code("""
if (head == nullptr && head->next == nullptr) return false;   // crashes on empty
if (head == nullptr || head->next == nullptr) return false;   // guards
""")
   + p("From <em>linked-list-cycle</em>, both lines. The first survived two more "
       "submissions &mdash; one of which added a null check to the "
       "<em>other</em> pointer and left this one alone &mdash; before the operator "
       "was changed. The same shape appears in "
       "<em>the-k-th-lexicographical-string-of-all-happy-strings-of-length-n</em>, "
       "where <code>sb.isEmpty() &amp;&amp; c != sb.charAt(sb.length() - 1)</code> "
       "calls <code>charAt</code> on an empty builder at exactly the moment the "
       "guard was written to prevent it.")
   + p("<strong>The rule that removes the whole class:</strong> in a guard, the "
       "cheap safety test and the thing it protects are joined by "
       "<code>||</code> when you are bailing out, and by <code>&amp;&amp;</code> "
       "when you are proceeding. Say it as a sentence and the operator falls out: "
       "&ldquo;bail if it is empty <em>or</em> it has one node&rdquo;; "
       "&ldquo;continue while it is non-null <em>and</em> its next is non-null&rdquo;.")
   + p("Related and worth checking in the same pass: mixing "
       "<code>&amp;&amp;</code> and <code>||</code> in one condition without "
       "parentheses. <code>&amp;&amp;</code> binds tighter. Your accepted version "
       "of the happy-strings problem had the parentheses; a later resubmission "
       "dropped them, silently changing the condition. It still passed, which is "
       "how latent regressions get in.")),

  ("The guard that dies in a refactor",
   p("The three <em>path-sum-iii</em> entries are one story. The "
     "<code>root == null</code> guard was missing, so it was added. Then the "
     "prefix-count map was refactored into an instance field, the method signature "
     "was trimmed, and the guard went with it. Then it was restored.")
   + p("The same thing happened across years on "
       "<em>rank-transform-of-an-array</em>: the empty-array oversight from the "
       "original solve recurred verbatim on a later revisit, with the analysis "
       "noting it as <q>the exact same empty-array oversight</q>.")
   + p("A guard on its own line at the top of a method is the most deletable "
       "thing in a function. It has no callers, no return value anyone reads, and "
       "no relationship to the lines around it. That is precisely why it "
       "disappears.")
   + p("<strong>The durable fix is to not have a special case at all.</strong> "
       "Structure the algorithm so the degenerate input falls out of the general "
       "path. A dummy head node makes an empty list a list with one node in it and "
       "deletes every <code>head == null</code> branch downstream &mdash; that is "
       "the whole technique in [[sentinels]]. Seeding a running maximum from "
       "<code>nums[0]</code> rather than <code>Integer.MIN_VALUE</code> makes the "
       "one-element case the base case, and also removes the overflow you hit on "
       "<em>maximum-sum-circular-subarray</em> when a negative number was added to "
       "<code>MIN_VALUE</code>.")
   + code("""
// two guards and a sentinel that can overflow
int best = Integer.MIN_VALUE, cur = Integer.MIN_VALUE;
for (int x : nums) { cur = Math.max(x, cur + x); best = Math.max(best, cur); }

// no guard, no sentinel: n = 1 is the base case
int best = nums[0], cur = nums[0];
for (int i = 1; i < nums.length; i++) {
    cur  = Math.max(nums[i], cur + nums[i]);
    best = Math.max(best, cur);
}
""")
   + p("The second version still needs <code>nums.length &gt; 0</code> &mdash; but "
       "that is one guard for the whole method instead of a sentinel value that "
       "has to survive arithmetic. See [[integer-width]] for why "
       "<code>MIN_VALUE</code> as a seed is a trap independent of this lesson.")),

  ("The degenerate cases that are not about size",
   p("Once the three sizes are habit, the remaining instances in your export are "
     "the same idea applied to a parameter rather than a length.")
   + ul("<strong>k at its extremes.</strong> On "
        "<em>find-the-largest-almost-missing-integer</em> the "
        "<code>k == nums.length</code> case &mdash; the whole array is the only "
        "window &mdash; was missed, because the <code>k &gt; 1</code> branch only "
        "ever inspected the two ends. On <em>cracking-the-safe</em>, "
        "<code>k == 1</code> got its own early return rather than a fix to the "
        "general padding logic, which the analysis flags as sidestepping.",
        "<strong>The value zero, where absent is also possible.</strong> A "
        "counting array cannot tell &ldquo;seen zero times&rdquo; from "
        "&ldquo;stores the value 0&rdquo;. On <em>valid-sudoku</em> the empty "
        "cell <code>'.'</code> cast to 0 collided with itself and false-flagged "
        "duplicates. More on this in [[counting-arrays]].",
        "<strong>A no-op that is not the identity.</strong> On "
        "<em>rotate-list</em>, when the rotation is a multiple of the length the "
        "code still detached the tail and returned a pointer read before the "
        "truncation, producing an empty list. The fix added "
        "<code>if (k == 0) return head;</code> &mdash; which, as the analysis "
        "notes, covers the literal zero and not the other multiples.",
        "<strong>The answer at the boundary of the range.</strong> "
        "<em>fibonacci-number</em> at n = 0: the loop body never ran, so the "
        "function returned the seed. The first fix added the guard and returned "
        "the wrong constant.")
   + p("The pattern across all four: a special case was noticed, and the fix "
       "addressed the literal input that failed rather than the class it belonged "
       "to. <strong>When a degenerate input breaks you, ask what set it is a "
       "member of before you write the guard.</strong>")),

  ("The twenty-second pass",
   p("Before submitting anything that indexes, walks, or divides:")
   + ul("Say &ldquo;n equals zero&rdquo; and read the first three lines of the "
        "method. Does anything touch an element?",
        "Say &ldquo;n equals one&rdquo; and find every <code>.next</code>, "
        "<code>[i-1]</code>, <code>[i+1]</code> and pair comparison.",
        "Say &ldquo;n equals two&rdquo; and ask whether the code believes there "
        "is an interior.",
        "Read the constraints. If they say <code>1 &le; n</code>, skip the "
        "first one and do not pay for a guard you do not need.")
   + p("Four sentences. On this evidence they are worth roughly one submission in "
       "twelve.")),
 ],
 "rules": [
  "Run n = 0, n = 1, n = 2 in your head before every submit. It takes twenty seconds.",
  "Read the constraints first: if n >= 1 is guaranteed, do not write the empty guard.",
  "A bail-out guard joins its clauses with ||. Say the sentence out loud and the operator falls out.",
  "Parenthesise any condition that mixes && and ||, every time.",
  "When one degenerate case breaks, write down its mirror cases before fixing it.",
  "Prefer a structure with no special case -- a dummy node, a seed from nums[0] -- over a guard that a refactor can delete.",
  "Seed running extremes from the first element, never from MIN_VALUE or MAX_VALUE.",
  "When a specific input fails, fix the class it belongs to, not the literal value.",
 ],
 "drill": "Take reverse-linked-list, linked-list-cycle, path-sum-iii and "
          "rank-transform-of-an-array. For each, write the empty and one-element "
          "input on paper first, then write the solution so that neither needs a "
          "guard -- dummy node, seeded accumulator, or a base case that already "
          "covers it. Then take your last ten accepted submissions and, for each, "
          "answer in one sentence what it returns on the empty input. Where you "
          "cannot answer without rereading the code, the guard is not doing its job.",
},
# ==========================================================================
{
 "slug": "case-analysis",
 "title": "Cases that tile: the branch you never wrote",
 "one_line": "Every if claims the rest of the input space is handled somewhere "
             "else. Check that it is.",
 "why": "{{mistakes:case-analysis}} diagnosed mistakes and "
        "{{habits:case-analysis}} habits in accepted code, across "
        "{{problems:case-analysis}} problems and {{topics:case-analysis}} "
        "topics, are a missing or overlapping branch rather than a wrong one. The signature is unmistakable "
        "in your history: a problem is patched two, three, five times, each "
        "submission adding one more condition for one more failing input, and the "
        "analysis of the accepted version records the result as a smell rather than "
        "a solution. equal-sum-grid-partition-ii is the extreme case -- five nearly "
        "identical branches accumulated one Wrong Answer at a time, and the "
        "post-solve resubmission kept adding more. The cost is not the missing "
        "branch. It is that patching one input at a time cannot converge, because "
        "nothing in the process ever asks what the complete set of cases is.",
 "summary": (
  p('A case analysis is a claim about the whole input space: these branches, '
    'taken together, cover everything, and no input lands in two of them. '
    'Both halves of that claim can fail, and they fail differently.') +
  p('<strong>A gap is silent.</strong> An input that matches no branch does '
    'not error; control falls past the last <code>else if</code> and returns '
    'whatever was there. <strong>An overlap is loud but misleading</strong> '
    '&mdash; the first matching branch wins, so the bug appears to be in that '
    'branch rather than in the ordering.') +
  p('The technique is to write the cases down before writing any of them, and '
    'to check that they tile. It takes a minute and it is the only thing that '
    'converges; patching per failing input does not, and your export contains '
    'the receipts.')
 ),
 "used_for": [
  ('Grid and matrix problems with boundary rows or columns',
   'The corners belong to two boundaries at once, and that is a case of its own.'),
  ('Anything with a sign',
   'Negative, zero and positive are three cases, and zero is the one that gets '
   'folded into the wrong neighbour.'),
  ('Interval and range logic',
   'Two intervals have six orderings, not two.'),
  ('Binary search that must return a neighbour rather than a hit',
   'Found and not-found are different answers, and not-found has two sides.'),
  ('Mappings that must be one-to-one',
   'A bijection is two obligations. Writing one of them is the default mistake.'),
  ('State machines and character classification',
   'Every character is in exactly one class, and the class you forgot is the '
   'one the tests use.'),
 ],
 "patterns": [
  ('You have patched the same problem twice for two different inputs',
   'Stop. The next patch will not converge either. Enumerate instead.'),
  ('A condition uses || where the two clauses are not alternatives',
   'An || of two range tests is true almost always. You meant &&, or you '
   'meant separate branches.'),
  ('The statement says "or" and your code has one branch',
   'The statement is telling you the case count.'),
  ('The answer is right in the middle of the array and wrong at both ends',
   'The boundary case is missing, not the formula.'),
  ('A branch you added made a different input start failing',
   'The branches overlap and you changed which one wins.'),
  ('The accepted solution has five branches that look almost the same',
   'It is accepted, not correct. Re-derive it once as a single rule.'),
 ],
 "match": r"(missed|missing|omitted|forgot|failed to handle|did not handle|"
          r"never handled|only handled|handled only|no branch for|no case for|"
          r"left out) .{0,45}(case|branch|scenario|situation|possibilit|"
          r"combination|configuration|sign|direction|orientation|variant)|"
          r"(one|two|third|fourth|another|remaining|other) .{0,20}"
          r"(case|branch|scenario|configuration)s? (was|were|is|are|remained) "
          r"(not |never |un)?(handled|covered|considered|checked)|"
          r"only (checked|considered|covered|handled) (the |one |two )|"
          r"(three|four|five|six|both|all) .{0,15}(cases|branches|scenarios|"
          r"configurations|orientations|directions)|non[- ]exhaustive|"
          r"not exhaustive|else branch|missing else|fell through|falls through|"
          r"catch[- ]all",
 "basics": [

  ("Overlap and gap",
   diagrams.case_space() +
   p("Those are the only two ways a case analysis fails, and only one of them "
     "announces itself.")
   + p("An overlap gives a wrong answer you can localise: the input hit a branch, "
       "the branch ran, you can print from inside it. A gap gives a wrong answer "
       "with no branch to put a print in. Nothing ran. That is why gaps take four "
       "submissions and overlaps take one.")
   + p("The check is mechanical. Write the branches as a list of conditions and "
       "ask two questions: is there an input satisfying none of them, and is there "
       "an input satisfying two? If your conditions are ranges over one variable, "
       "the second question is answered by sorting the endpoints; if they are "
       "combinations of booleans, it is answered by counting &mdash; three "
       "independent booleans need eight branches or an argument for why fewer "
       "suffice.")),

  ("The || that is not a case split",
   p("From <em>equal-sum-grid-partition-ii</em>, the single most patched problem "
     "in this family:")
   + code("""
if (i > 0 || i < n - 2) { ... }     // intended: not the first or last column
""", compiles=False)
   + p("Read it as a set. <code>i &gt; 0</code> is everything except 0; "
       "<code>i &lt; n-2</code> is everything except the last two. Their "
       "<em>union</em> is every index. The condition is true almost always, and the "
       "branch fired on inputs it was written to skip.")
   + p("The next submission changed <code>||</code> to <code>&amp;&amp;</code>, "
       "which is the right operator and still the wrong shape &mdash; a submission "
       "after that abandoned the single condition and wrote explicit "
       "<code>i == 0</code>, <code>i == n-1</code> and interior branches. Then a "
       "further submission found that the interior branch had never handled the "
       "plainest possibility of all: the split that is already balanced, with no "
       "boundary cell moved at all.")
   + p("<strong>The lesson is in the sequence, not the operator.</strong> Three "
       "submissions went into converting one condition into three branches, one "
       "failing input at a time. Writing the three branches down first &mdash; "
       "left edge, right edge, interior &mdash; costs a minute and makes the "
       "missing fourth case (<em>already balanced</em>) visible as a hole in a "
       "list rather than as a wrong answer on a hidden test.")
   + p("A negation rule that would have caught the original line: the complement "
       "of <code>a &amp;&amp; b</code> is <code>!a || !b</code>. You wanted "
       "&ldquo;not (first or last)&rdquo;, which is "
       "<code>i != 0 &amp;&amp; i != n-1</code>. When you find yourself writing "
       "the negation of a compound condition by hand, write it with De Morgan "
       "rather than by intuition &mdash; intuition swaps the operator about half "
       "the time.")),

  ("Patch accumulation is the diagnostic",
   p("The analysis of the accepted <em>equal-sum-grid-partition-ii</em> submission "
     "records the shape rather than a bug: five nearly identical branches "
     "accumulated one Wrong-Answer-fix at a time, with even the post-solve "
     "resubmission adding more ad hoc cases instead of consolidating.")
   + p("That is worth naming as a rule, because it is detectable from your own "
       "behaviour without knowing the right answer:")
   + p("<strong>Two patches on the same problem for two different inputs means "
       "the case analysis is wrong, not the arithmetic.</strong> Stop editing. "
       "Take a blank line and write out the cases as a list. Almost every time, "
       "the list is shorter than the branch pile you had accumulated, and the "
       "missing case is obvious once the others are written next to it.")
   + p("The same signal appears in <em>top-k-frequent-elements</em>, where a "
       "partition comparison was toggled between <code>&lt;=</code> and "
       "<code>&lt;</code> across three successive submissions. Toggling an "
       "operator is patch accumulation with one branch: each submission tests a "
       "guess rather than a derivation, and the space of guesses is small enough "
       "to exhaust without ever being right for a reason.")),

  ("Obligations that come in pairs",
   p("A distinct sub-family: the case you missed is not a range, it is the mirror "
     "image of the one you wrote.")
   + code("""
// isomorphic-strings: only the forward direction was recorded
map.put(s.charAt(i), t.charAt(i));
// nothing stopped two different s-chars mapping to the same t-char
""")
   + p("A bijection is two constraints, and writing one of them is the natural "
       "thing to do because the statement reads as one sentence. The same shape "
       "produced the <em>spiral-matrix</em> single-row guard without the "
       "single-column guard, and appears wherever a problem has a symmetry: left "
       "and right, forward and backward, min and max, insert and delete.")
   + p("<strong>When a problem has a symmetry, the case list has an even number "
       "of entries.</strong> Write both halves at the same time, even if the "
       "second is a copy of the first with names swapped &mdash; and then, per "
       "[[wrong-name]], rename the targets in the copy before you touch anything "
       "else.")
   + p("The <em>successful-pairs-of-spells-and-potions</em> entry is the same "
       "idea inside a binary search: the code returned <code>mid</code> only on an "
       "exact match, and had no answer for the far more common case where the "
       "value is not present and you want its neighbour. Found and not-found are "
       "two cases; see [[binary-search]] for why the not-found answer should be "
       "the loop's postcondition rather than a branch.")),

  ("Writing the enumeration down",
   p("The whole technique, concretely. Before writing branches, make a table with "
     "one row per case and three columns: the condition, an example input that "
     "lands in it, and the answer. Fill in the example column first &mdash; a "
     "case you cannot produce an input for is not a case, and an input you cannot "
     "place in a row is a missing one.")
   + table(("Condition", "Example", "Answer"), [
       ("i == 0", "split before the first column", "compare 0 against the total"),
       ("i == n-1", "split after the last column", "the mirror of the above"),
       ("0 &lt; i &lt; n-1", "an interior split", "prefix vs total - prefix"),
       ("already balanced", "an interior split that needs no move",
        "<strong>the row that was missing</strong>"),
     ])
   + p("Four rows, two minutes, and it replaces three submissions. The table is "
       "also the thing to keep when the code changes: a rewrite that drops a "
       "branch is visible against the table, and invisible against the previous "
       "version of the code.")),
 ],
 "rules": [
  "Write the case list before writing any branch. Conditions, one example input each, and the answer.",
  "A case you cannot produce an example for is not a case. An input you cannot place is a missing one.",
  "Check both halves: no input matches zero branches, no input matches two.",
  "Two patches on one problem for two different inputs means the case analysis is wrong. Stop and enumerate.",
  "Negate compound conditions with De Morgan, never by intuition.",
  "An || of two range tests is almost always true. Read every compound condition as a set union.",
  "A problem with a symmetry has an even number of cases. Write both halves together.",
  "Toggling an operator between submissions is guessing. Derive the comparison once instead.",
 ],
 "drill": "Take equal-sum-grid-partition-ii and rewrite it from the statement "
          "without looking at your submissions: enumerate the cases in a table "
          "first, then write one branch per row. Compare your table against the "
          "five branches in the accepted version and count how many of them are "
          "the same case twice. Then do the same for isomorphic-strings and "
          "successful-pairs-of-spells-and-potions, and for each write down the "
          "mirror obligation you would have missed.",
},
# ==========================================================================
{
 "slug": "last-group",
 "title": "The last group: loops that emit on a transition",
 "one_line": "A loop that writes a group out when it sees the next one differ is "
             "correct for every group except the final one.",
 "why": "The keyword join finds {{mistakes:last-group}} diagnosed mistakes across "
        "{{topics:last-group}} topics and {{problems:last-group}} separate "
        "problems; eleven of them are exactly this bug. A run-length scan that never "
        "emitted its last run, a digit multiplication that dropped its final carry, a "
        "merge that never added the interval it was still building. The code is right "
        "about the hard part and wrong about the end of the array, which is why it "
        "passes the sample and fails the judge. It gets its own lesson because the fix "
        "is one line and you have written the bug at least eleven times.",
 "summary": (
  p('A large family of loops accumulates something and writes it out when a '
    '<strong>transition</strong> says the thing is finished: the next '
    'character differs, the next interval does not overlap, the buffer is '
    'full, the run has ended. The write lives inside an <code>if</code> that '
    'only fires on that transition.') +
  p('Every group is followed by a transition except one. The last group runs '
    'off the end of the input instead, the <code>if</code> never fires, and '
    'the group is silently dropped. Nothing throws; the answer is simply one '
    'group short. <strong>The fix always has the same shape: repeat the emit '
    'after the loop.</strong>') +
  p('Once you can see the shape it stops being about strings. A leftover '
    '<code>carry</code>, a half-full <code>StringBuilder</code>, an open '
    'interval, a pending count and the final field of a split are the same '
    'bug in different clothes.')
 ),
 "used_for": [
  ('Run-length encoding, and any group-by over a sequence',
   'The final run has no following element to close it.'),
  ('Adding or multiplying numbers digit by digit',
   'The carry out of the most significant column has no next column to land in.'),
  ('Merging intervals',
   'The interval you are still extending is added only when a gap appears, '
   'and no gap follows the last one.'),
  ('Splitting on a separator',
   'The text after the final separator is a field too.'),
  ('Buffering into fixed-size chunks',
   'The last chunk is almost never exactly full.'),
  ('Sweeping and keeping a running maximum',
   'Safe, and worth knowing: a best-so-far needs no flush because it is '
   'written on every iteration, not on a transition.'),
 ],
 "patterns": [
  ('Compress or encode a string of repeated characters',
   'Run-length. Emit on change, then emit once more after the loop.'),
  ('Add or multiply two numbers given as strings',
   'A carry that survives the final column.'),
  ('Merge all overlapping intervals',
   'One interval is still open when the loop ends.'),
  ('Reverse the words, or return the last word',
   'The final word ends at the string boundary, not at a space.'),
  ('Find the maximum number of consecutive X',
   'A run reaching the end of the array is still a run.'),
  ('Split into groups of k',
   'The trailing partial group counts.'),
  ('Your output list is one shorter than expected',
   'This bug. One longer, and it is the unguarded flush below.'),
 ],
 "match": r"\bflush(ed|es|ing)?\b|after the loop|post-loop|"
          r"final (run|word|group|batch|segment|carry|column)|"
          r"last (run|word|group|segment|batch|chunk)|"
          r"trailing (run|group|word|segment|carry|digit)|"
          r"(never|not) (got |be |been )?(flushed|emitted|appended|added|written|counted)|"
          r"leftover `?carry|emit(ted|s)? (the |an? )?(final|last)",
 "basics": [

  ("The shape, and where the hole is",
   diagrams.emit_on_transition() +
   p("The bug in its smallest form. Run-length encode <code>aaabbcc</code> and the "
     "answer should be <code>a3b2c2</code>.")
   + code("""
// WRONG -- drops the final run
StringBuilder sb = new StringBuilder();
int count = 1;
for (int i = 1; i < s.length(); i++) {
    if (s.charAt(i) == s.charAt(i - 1)) count++;
    else { sb.append(s.charAt(i - 1)).append(count); count = 1; }  // emit on CHANGE
}
return sb.toString();          // "a3b2" -- c2 never happened
""")
   + p("The <code>else</code> branch is the only writer, and it runs only when a "
       "character differs from the one before it. The run of <code>c</code>s never "
       "meets a different character. It meets the end of the string, so it is never "
       "written.")
   + p("The fix is one line, and it is the same line as the emit:")
   + code("""
// RIGHT -- the loop handles every transition, the tail handles the end
for (int i = 1; i < s.length(); i++) {
    if (s.charAt(i) == s.charAt(i - 1)) count++;
    else { sb.append(s.charAt(i - 1)).append(count); count = 1; }
}
sb.append(s.charAt(s.length() - 1)).append(count);   // the run still open
return sb.toString();
""")
   + p("Read those two writes as a pair. If they ever stop being identical &mdash; "
       "one gains a condition, the other does not &mdash; you have the second version "
       "of this bug, which is harder to find because the tail emits the "
       "<em>wrong</em> group rather than none at all. Your own "
       "<em>largest-unique-number</em> submission did exactly that: the post-loop "
       "flush wrote <code>ans = count</code>, the run length, where the loop wrote "
       "<code>ans = num</code>, the value.")),

  ("Every disguise it wears",
   p("This deserves a lesson rather than a footnote because the transition is "
     "rarely a character comparison. It is anything meaning &ldquo;the thing I was "
     "building is finished&rdquo;.")
   + table(("Loop", "The transition", "What is left open at the end"), [
       ("Run-length encode", "next character differs", "the final run"),
       ("Add or multiply digit strings", "move to the next column",
        "the carry out of the top column"),
       ("Merge intervals", "next interval does not overlap",
        "the interval still being extended"),
       ("Split on a separator", "a separator is seen",
        "the field after the last separator"),
       ("Chunk into blocks of k", "the block fills", "the short final block"),
       ("Group a sorted list", "the sort key changes", "the last group"),
       ("Count consecutive ones", "a zero is seen",
        "a run of ones ending at the array's end"),
     ])
   + p("Three of your own submissions sit on that table. In <em>add-strings</em> the "
       "carry after the final column was never appended. In <em>multiply-strings</em> "
       "the same carry-out dropped the most significant digit. In "
       "<em>can-place-flowers</em> a run of plantable slots that reached the end of "
       "the array was never counted &mdash; the analysis records the fix as "
       "&ldquo;added a final flush of the trailing run's count after the loop "
       "ends&rdquo;, and that identical sentence would have fixed the other two.")
   + p("The carry case is worth writing out, because the loop condition is where "
       "people try to fix it:")
   + code("""
// add-strings: the carry is a group like any other
int i = a.length() - 1, j = b.length() - 1, carry = 0;
StringBuilder out = new StringBuilder();
while (i >= 0 || j >= 0) {
    int sum = carry
            + (i >= 0 ? a.charAt(i--) - '0' : 0)
            + (j >= 0 ? b.charAt(j--) - '0' : 0);
    out.append(sum % 10);
    carry = sum / 10;
}
if (carry > 0) out.append(carry);      // the tail. "999" + "1" is four digits.
return out.reverse().toString();
""")
   + p("Note that the <code>||</code> in the loop condition already handles unequal "
       "lengths, which is the same instinct applied one level down: the shorter "
       "number's missing columns are a group nobody closes either. Widening the loop "
       "to run one extra iteration and special-casing it instead is the same code "
       "with the special case moved somewhere less visible. Keep the tail outside.")),

  ("The two ways the fix goes wrong",
   p("Adding a flush is not automatically the end of it, and both failure modes are "
     "in your own history.")
   + p("<strong>1. The unguarded flush, on empty input.</strong> If the loop never "
       "ran there is no open group to emit &mdash; but the flush emits one anyway. An "
       "empty string produces a phantom group; a string ending in a separator "
       "produces a phantom empty field. This is the bug that makes your output one "
       "<em>longer</em> than expected.")
   + code("""
if (opened) emit(current);                  // guard on "did a group open?"
if (sb.length() > 0) out.add(sb.toString());   // not on "was the input non-empty?"
""")
   + p("<strong>2. The flush placed in the wrong branch.</strong> Your "
       "<em>remove-comments</em> submission nested the end-of-line flush three levels "
       "deep inside the plain-character branch, so a line ending on a comment marker "
       "dropped its entire accumulated buffer. The analysis of the eventual fix "
       "states the general rule: pull the flush out to run after the inner loop "
       "entirely. A flush inside a conditional is not a flush &mdash; it is another "
       "transition, with the same hole underneath it.")
   + p("The same nesting mistake caused the <em>insert-interval</em> failure: the "
       "merged interval was appended only in the loop's <code>else</code> branch, so "
       "an interval overlapping everything to the end of the list was silently "
       "dropped. The correction, a trailing "
       "<code>if (!added) result.add(...)</code>, then over-corrected and inserted at "
       "the wrong position &mdash; the usual cost of fixing this under time pressure "
       "rather than by construction.")),

  ("Writing it so the hole cannot exist",
   p("A flush is a patch on a loop shape that has a hole in it. Two restructurings "
     "remove the hole instead, and both are shorter than the patched version.")
   + p("<strong>Sentinel.</strong> Run one iteration past the end and treat that "
       "position as a transition that always fires. Every group, including the last, "
       "is then closed inside the loop. This is [[sentinels]]'s sentinel idea used "
       "structurally rather than arithmetically.")
   + code("""
// one extra iteration, and the tail disappears
for (int i = 1; i <= s.length(); i++) {                      // note: <=
    if (i < s.length() && s.charAt(i) == s.charAt(i - 1)) count++;
    else { sb.append(s.charAt(i - 1)).append(count); count = 1; }
}
""")
   + p("<strong>Emit on entry, not on exit.</strong> Invert the loop. Instead of "
       "closing the previous group when a new one starts, find each group whole when "
       "you reach its first element, and write it immediately. Nothing is ever left "
       "open, because nothing is pending between iterations.")
   + code("""
int i = 0;
while (i < n) {
    int j = i;
    while (j < n && s.charAt(j) == s.charAt(i)) j++;   // the whole run, found first
    sb.append(s.charAt(i)).append(j - i);              // emitted immediately
    i = j;
}
""")
   + p("The second form is the one to reach for under interview conditions. It "
       "carries no pending state, so there is nothing to forget to write out, and the "
       "loop bound is the only thing left that can be wrong &mdash; which [[bounds]] "
       "already covered. It generalises unchanged to intervals, to chunking, and to "
       "grouping a sorted list.")),
 ],
 "rules": [
  "Find the write inside your loop and ask what closes the last one. If the answer is 'the end of the input', you need a tail.",
  "The post-loop emit must be identical to the in-loop emit. Different code in the two places is the harder version of this bug.",
  "Guard the tail on 'did a group open?', not on 'was the input non-empty?'.",
  "A flush nested inside a conditional is not a flush. Hoist it out of the branch, or out of the loop entirely.",
  "carry, remainder and a partly-filled buffer are groups. They need the same tail.",
  "Prefer emit-on-entry -- find the whole group, then write it -- over emit-on-transition. It cannot have this bug.",
  "Test three inputs before submitting: empty, one element, and one whose last group is the longest.",
 ],
 "drill": "string-compression, then add-strings and multiply-strings back to back "
          "-- the carry is the same tail. Then merge-intervals and "
          "reverse-words-in-a-string. Write the emit-on-entry version of each (an "
          "inner while that consumes the whole group) rather than the "
          "emit-on-transition one, and notice that none of them then needs a flush.",
},
# ==========================================================================
{
 "slug": "binary-search",
 "title": "Binary search: one invariant, written down",
 "one_line": "Pick half-open [lo, hi), state what the invariant is, and every boundary follows from it.",
 "why": "76 boundary mistakes across 34 topics, and your binary-search topic sits at a 50% "
        "first-attempt rate over 91 problems. In "
        "find-building-where-alice-and-bob-can-meet you flipped >= against > and l "
        "against mid across four consecutive Wrong Answers — the signature of guessing "
        "at boundaries rather than deriving them.",
 "summary": (
  p('Binary search is not “look at the middle”. It is: hold an interval '
     'that is guaranteed to contain the answer, and halve it every step '
     'without ever letting the answer fall outside. That sentence is the '
     'invariant, and every boundary decision follows from it mechanically.') +
  p('All the variants — first true, last false, lower bound, upper bound, '
     'search on the answer — are the same loop. The only thing that changes '
     'is the predicate. Once you commit to half-open <code>[lo, hi)</code> '
     'and write the invariant down, the boundaries stop being something you '
     'tune until the samples pass.')
 ),
 "used_for": [
  ('A sorted array and a position to find',
   'O(log n) instead of a scan, and the insertion point for a missing '
    'value comes out for free.'),
  ('The answer is a number, and “is x achievable?” is easy to check',
   'Binary search on the answer: the checker is O(n) and the search costs '
    'log(range) of them.'),
  ('The predicate is monotone — false…false true…true',
   'Monotonicity is the only precondition. The data itself does not have '
    'to be sorted.'),
  ('You need the first and last index equal to a value',
   'Two searches, lower bound and upper bound, delimit the whole equal '
    'range.'),
  ('Minimise the maximum, or maximise the minimum',
   'Always this pattern. Binary search the bound and check feasibility '
    'greedily.'),
  ('The array is small (n ≤ 1000)',
   'A linear scan is simpler and you will not get the boundaries wrong. '
    'Laziness is allowed to win here.'),
 ],
 "patterns": [
  ('The array is sorted in non-decreasing order',
   'Plain binary search, or lower/upper bound when duplicates exist.'),
  ('Minimise the largest … / maximise the smallest …',
   'Binary search on the answer with a feasibility check.'),
  ('Return the minimum capacity / speed / days such that …',
   'The same — the “such that” clause is the monotone predicate.'),
  ('Find the smallest index i for which P(i) holds',
   'First-true search. The invariant is “the answer is in [lo, hi)”.'),
  ('Find a peak element in O(log n)',
   'Compare mid with mid + 1 and discard the half that cannot contain a '
    'peak.'),
  ('The array is rotated',
   'One half is always sorted. Decide which, then decide whether the '
    'target lives inside it.'),
  ('Do it in O(log(m + n))',
   'Binary search over the partition point of the shorter array, not over '
    'the values.'),
 ],
 "match": r"binary.search|\bmid\b|lower.bound|upper.bound|\bl(o)? = mid|"
          r"\bh?i? = mid|inclusive|exclusive|half.open|monotone|bisect|"
          r"\(l \+ r\)|l \+ r / 2",
 "basics": [
  ("The idea, from zero",
   diagrams.binary_search_steps() +
   p("Binary search does not need a sorted array. It needs a <strong>monotone "
     "predicate</strong>: a yes/no question about an index whose answer, once it turns "
     "true, stays true.")
   + code("""
index:      0     1     2     3     4     5     6
predicate:  F     F     F     T     T     T     T
                              ^
                       the first true — what you are looking for
""", compiles=False)
   + p("Sorted-array search is one instance (<code>arr[i] >= target</code> is monotone). "
       "\"Binary search on the answer\" is another (<code>can we finish in t "
       "minutes?</code>). Once you can name the predicate and argue it is monotone, the "
       "search is mechanical.")),

  ("The one template",
   p("Use half-open <code>[lo, hi)</code> — <code>lo</code> included, <code>hi</code> "
     "excluded. It is the convention where the arithmetic works out with no +1/−1 "
     "juggling.")
   + code("""
// Returns the first index in [0, n] where pred is true.
// Returns n if pred is never true.
int lo = 0, hi = n;                    // hi = n, not n - 1
while (lo < hi) {                      // strict <
    int mid = lo + (hi - lo) / 2;      // never (lo + hi) / 2 — that can overflow
    if (pred(mid)) {
        hi = mid;                      // mid might be the answer: KEEP it
    } else {
        lo = mid + 1;                  // mid is not the answer: DISCARD it
    }
}
return lo;                             // lo == hi == first true
""")
   + p("<strong>The invariant:</strong> the answer is always inside <code>[lo, hi]</code>. "
       "Every branch preserves it. That single sentence decides all four choices:")
   + ul("<code>hi = n</code>, because \"no index satisfies it\" must be representable.",
        "<code>while (lo &lt; hi)</code>, because the range is empty when they meet.",
        "<code>hi = mid</code> and not <code>mid - 1</code>, because <code>mid</code> "
        "satisfied the predicate and might be the first one.",
        "<code>lo = mid + 1</code> and not <code>mid</code>, because <code>mid</code> "
        "failed — keeping it would loop forever.")),

  ("Everything else is the same template",
   code("""
// first index with arr[i] >= target      (lower bound)
pred(i) = arr[i] >= target

// first index with arr[i] > target       (upper bound)
pred(i) = arr[i] > target

// count of elements < target             = lowerBound(target)
// count of elements == target            = upperBound(target) - lowerBound(target)

// smallest t such that we finish in time  (binary search on the answer)
pred(t) = canFinish(t)
""", compiles=False)
   + p("You do not need four templates. You need one, plus the ability to write the "
       "predicate down.")),

  ("The mid computation",
   p("<code>(lo + hi) / 2</code> overflows when both are large. Use "
     "<code>lo + (hi - lo) / 2</code>. And in "
     "<code>maximum-number-of-books-you-can-take</code> you wrote "
     "<code>int mid = l + r / 2</code> — missing parentheses, so it computed "
     "<code>l + (r/2)</code>. Both are avoided by typing the same line every time and "
     "never improvising it.")),

  ("Worked example: search-insert-position, traced",
   p("<code>nums = [1, 3, 5, 6]</code>, <code>target = 5</code>. The predicate is "
     "<code>nums[i] &gt;= 5</code> — monotone false-then-true, so the template applies "
     "unchanged. Half-open <code>[lo, hi)</code> with <code>hi = 4</code>:")
   + traces.binary_search([1, 3, 5, 6], 5)
   + p("Now change the target to <code>2</code>, which is <em>absent</em>, and run "
       "the same code with nothing modified:")
   + traces.binary_search([1, 3, 5, 6], 2)
   + p("<strong>The same code, unmodified, answers both questions</strong> — the "
       "index of the target when it is present, and the index it would be inserted "
       "at when it is not. That is what the predicate framing buys you, and it is "
       "why there is only one template to remember.")
   + p("Note what never appears in that table: no <code>nums[mid] == target</code> "
       "branch, no <code>return mid</code>, no <code>lo &lt;= hi</code>, no "
       "<code>hi - 1</code>. Those are the four places your Wrong Answers came from.")),

  ("Binary search on the answer",
   diagrams.answer_space() +
   p("The array does not have to exist. If you can write a monotone "
     "<code>feasible(x)</code> — true for every x above some threshold, false below — "
     "you can binary search the threshold itself. This is the form that shows up in "
     "koko-eating-bananas, split-array-largest-sum, minimize-max-distance:")
   + code("""
// smallest speed k such that Koko finishes within h hours
int lo = 1, hi = max(piles);              // [lo, hi] both feasible-bounded
while (lo < hi) {
    int mid = lo + (hi - lo) / 2;
    if (hours(piles, mid) <= h) hi = mid;  // feasible -> answer is at or below mid
    else                        lo = mid + 1;
}
return lo;
""")
   + p("Two obligations, and both are on you, not the template: "
       "<strong>(1)</strong> prove <code>feasible</code> is monotone — if speed "
       "<code>k</code> works then <code>k+1</code> works, obviously true here; "
       "<strong>(2)</strong> pick <code>hi</code> so the answer is definitely inside "
       "the range. A <code>hi</code> that is too small returns a wrong answer with no "
       "symptom at all — the loop terminates happily on a range that never contained "
       "the answer.")),
 ],
 "rules": [
  "Write the predicate as a sentence first. If it is not monotone, binary search is the wrong tool.",
  "Half-open [lo, hi). hi starts at n. Loop while lo < hi. Return lo.",
  "pred true → hi = mid (keep it). pred false → lo = mid + 1 (discard it).",
  "int mid = lo + (hi - lo) / 2. Type it, do not improvise it.",
  "Test on n=0, n=1, all-false, and all-true before submitting.",
 ],
 "drill": "Re-solve find-building-where-alice-and-bob-can-meet cold. Write the predicate "
          "sentence in a comment before any code.",
},


# ==========================================================================
{
 "slug": "comparators",
 "title": "Comparators and ordered collections",
 "one_line": "Never subtract in a comparator. And TreeSet dedupes with compareTo, not equals.",
 "why": "45 comparator and sort-key mistakes across 28 topics, including a compile error "
        "on a long subtraction and a TreeSet whose ordering and equality disagreed — a "
        "bug class that produces silently wrong answers, not exceptions.",
 "summary": (
  p("A comparator declares a total order, and Java's sort takes you at your "
     'word. Break the contract and you do not get a wrong answer — you get '
     '<code>IllegalArgumentException: Comparison method violates its general '
     'contract!</code> thrown by TimSort, on the judge, on an input you '
     'cannot see.') +
  p('There are two ways to break it. Subtracting ints that can overflow '
     'makes the sign wrong for far-apart values. Returning 0 for elements '
     'you consider different makes the order non-total — and because '
     '<code>TreeSet</code> and <code>TreeMap</code> decide equality with '
     '<code>compareTo</code> rather than <code>equals</code>, that 0 '
     'silently deletes elements.')
 ),
 "used_for": [
  ('Sorting objects or int[] rows by more than one key',
   'Comparator.comparingInt(...).thenComparing(...) composes without hand- '
    'written branch chains.'),
  ('A priority queue where the ordering is the algorithm',
   'Dijkstra, top-k, merge-k: the comparator direction is the design, not '
    'a detail of it.'),
  ('A TreeMap used as an ordered index',
   'floorKey, ceilingKey and higherKey are what you came for, and the '
    'comparator defines all three.'),
  ('Deduplicating while keeping order',
   "Only if the comparator's 0 genuinely means “same element”. Otherwise a "
    'HashSet is the right structure.'),
  ('Sorting intervals',
   'By start to merge, by end to schedule. Same data, two comparators, two '
    'different problems.'),
 ],
 "patterns": [
  ('Sort by score descending, then by name ascending',
   'comparing(...).reversed().thenComparing(...) — never a hand-rolled '
    'subtraction chain.'),
  ('Values up to 10⁹, sorted by value',
   'a - b overflows. Integer.compare(a, b) is the same length and correct.'),
  ('Return the k largest / smallest elements',
   'A size-k heap whose comparator points the opposite way to your '
    'instinct.'),
  ('Keep a sorted set of distinct values',
   'TreeSet — and the comparator must return 0 only for genuinely equal '
    'elements.'),
  ('Find the closest value not greater than x',
   'TreeMap.floorEntry. This is the reason to pay for an ordered '
    'structure.'),
  ('Sort the array in-place by a custom rule',
   'int[] has no Comparator overload. Box to Integer[], or sort a key '
    'array.'),
 ],
 "match": r"[Cc]omparator|compareTo|TreeSet|TreeMap|reverseOrder|\.sort\(|"
          r"sorted by|sort key|tie.?break|comparingInt|comparingLong|"
          r"PriorityQueue.*compar",
 "basics": [
  ("The contract",
   p("A comparator must define a <strong>total order</strong>: for all a, b, c —")
   + ul("<code>sgn(compare(a,b)) == -sgn(compare(b,a))</code> (antisymmetric)",
        "<code>compare(a,b) &gt; 0 &amp;&amp; compare(b,c) &gt; 0</code> implies "
        "<code>compare(a,c) &gt; 0</code> (transitive)",
        "<code>compare(a,b) == 0</code> implies a and b compare identically against "
        "everything else (consistent)")
   + p("Java's sort <em>detects</em> violations and throws "
       "<code>IllegalArgumentException: Comparison method violates its general "
       "contract!</code> — but only sometimes, on large inputs. On small inputs a broken "
       "comparator just produces a wrong order, silently.")),

  ("Never subtract",
   diagrams.comparator_overflow() +
   code("""
// WRONG: overflows. a=2_000_000_000, b=-2_000_000_000 → a-b wraps negative
(a, b) -> a - b

// WRONG: does not compile for long. Comparator must return int.
//        This is the jump-game-viii compile error.
(a, b) -> a[1] - b[1]        // where a[1] is long

// RIGHT
(a, b) -> Integer.compare(a, b)
Comparator.comparingInt(x -> x.count)
Comparator.comparingLong(a -> a[1])
Comparator.comparingInt(Foo::getCount).thenComparing(Foo::getName)
Comparator.reverseOrder()
""", compiles=False)
   + p("<code>Integer.compare</code> and the <code>comparing*</code> factories are "
       "correct on every input and shorter than the subtraction. There is no case where "
       "subtraction is the right choice.")),

  ("TreeSet and TreeMap use compareTo, not equals",
   diagrams.treeset_collapse() +
   p("This is the trap in <code>stock-price-fluctuation</code>. You defined "
     "<code>compareTo</code> on price and <code>equals</code>/<code>hashCode</code> on "
     "timestamp. A <code>TreeSet</code> decides both <em>ordering</em> and "
     "<em>duplicate detection</em> from <code>compareTo</code> alone — it never calls "
     "<code>equals</code>. So two records with different timestamps but the same price "
     "were treated as the same element, and one was dropped.")
   + code("""
// If compareTo returns 0, TreeSet considers them THE SAME ELEMENT.
// So compareTo must break every tie you care about:
(a, b) -> a.price != b.price
            ? Integer.compare(a.price, b.price)
            : Integer.compare(a.timestamp, b.timestamp);   // tiebreak, always
""", compiles=False)
   + p("Rule: in a <code>TreeSet</code>/<code>TreeMap</code>, <code>compareTo</code> must "
       "be consistent with <code>equals</code> — return 0 exactly when the objects are "
       "equal. If you need duplicates by one key ordered by another, you want a "
       "<code>TreeMap&lt;key, List&lt;value&gt;&gt;</code> or a "
       "<code>PriorityQueue</code>, not a <code>TreeSet</code>.")),

  ("Ordered collection cheat sheet",
   table(("Need", "Use", "Cost"), [
       ("min or max only", "<code>PriorityQueue</code>", "O(log n) push/pop, O(1) peek"),
       ("sorted, with predecessor/successor", "<code>TreeMap</code> / <code>TreeSet</code>",
        "O(log n), <code>floorKey</code>/<code>ceilingKey</code>/<code>higherKey</code>"),
       ("sorted once, then read", "<code>Arrays.sort</code> + binary search", "O(n log n) once"),
       ("counts by key, ordered", "<code>TreeMap&lt;K, Integer&gt;</code>", "O(log n) per update"),
       ("k largest", "min-heap of size k", "O(n log k)"),
   ])),
 ],
 "rules": [
  "Never write (a, b) -> a - b. Use Integer.compare / Comparator.comparingInt / comparingLong.",
  "A Comparator lambda must return int — comparingLong for long keys.",
  "In TreeSet/TreeMap, compareTo returning 0 means 'same element'. Break every tie.",
  "compareTo must agree with equals in any sorted collection.",
 ],
 "drill": "Re-solve stock-price-fluctuation. Decide the container from the operations you "
          "need (getMax, getMin, update) before writing the class.",
},


# ==========================================================================
{
 "slug": "heaps",
 "title": "Heaps and priority queues",
 "one_line": "A heap is partially ordered, not sorted. For the k largest you need a "
             "min-heap — and the comparator is the whole design.",
 "why": "heap-priority-queue is 59 problems at a 48% first-attempt rate, your "
        "third-largest weak topic. The mistakes cluster in three places: treating the "
        "heap as if it were sorted, picking the wrong heap direction for a top-k "
        "question, and doing O(n) work per query — the find-median-from-data-stream "
        "rewrite in [[complexity-budget]] drained the whole queue on every call.",
 "summary": (
  p('A binary heap keeps exactly one guarantee: the root is the minimum (or '
     'maximum) of everything in it. Nothing else is ordered. Iterating a '
     '<code>PriorityQueue</code> does <strong>not</strong> give sorted '
     'output, and <code>contains</code> and <code>remove(Object)</code> are '
     'O(n) scans, not O(log n).') +
  p('Push and pop are O(log n), peek is O(1), and building from a '
     'collection is O(n). The design of a heap solution is therefore two '
     'choices and no more: which direction the comparator points, and what '
     'object you push.')
 ),
 "used_for": [
  ('The k largest or k smallest from a stream or a large array',
   'A size-k heap pointing the opposite way: k largest needs a min-heap, '
    'so the weakest survivor sits at the root and is cheap to evict.'),
  ('Repeatedly take the current best',
   'Dijkstra, task scheduling, Huffman coding — “best so far” is precisely '
    "the heap's contract."),
  ('Merging k sorted lists or streams',
   'A heap of the k current heads: pop the smallest, push its successor.'),
  ('The running median',
   'Two heaps — a max-heap of the lower half and a min-heap of the upper, '
    'kept within one in size.'),
  ('The k-th element of a static array and nothing else',
   'Quickselect is O(n) on average and beats a heap. A heap wins when the '
    'data arrives over time.'),
  ('You need every element in order',
   'Sort. A heap you drain completely is a slower sort with extra code.'),
 ],
 "patterns": [
  ('Return the k most frequent / k closest / k largest',
   'Size-k heap in the opposite direction — or bucket sort when the key '
    'range is small.'),
  ('Merge k sorted linked lists',
   'A heap of the k current heads.'),
  ('Find the median from a data stream',
   'Two heaps.'),
  ('The maximum in every sliding window',
   'A monotonic deque, not a heap: a heap cannot evict the element that '
    'just left the window.'),
  ('Minimum cost to connect / combine all of them',
   'Repeatedly combine the two cheapest — a min-heap loop.'),
  ('Tasks with a cooldown / CPU scheduling',
   'A heap keyed on remaining count, plus a queue for the cooling ones.'),
  ('Schedule meetings and report the number of rooms',
   'A min-heap of end times; the heap size is the answer.'),
 ],
 "match": r"PriorityQueue|min[- ]?heap|max[- ]?heap|\bheap\b|heapif|reverseOrder|"
          r"pq\.(poll|offer|peek)|top[- ]?k\b|k-?th (largest|smallest|closest)|"
          r"priority queue",
 "basics": [

  ("What a heap is, and what it is not",
   diagrams.heap_layout() +
   p("A binary heap is a <strong>complete</strong> binary tree — every level full except "
     "possibly the last, filled left to right — with the property that every parent is "
     "≤ (min-heap) or ≥ (max-heap) both of its children. Because it is complete it can "
     "be stored in a flat array with no pointers at all, which is why it is fast and "
     "why its code is short.")
   + p("The critical negative: <strong>a heap is not sorted.</strong> Only the root is "
       "guaranteed to be the extreme. In the diagram above, index 5 holds 4 while index "
       "3 holds 9 — perfectly valid. Concretely, this means:")
   + ul("Iterating a <code>PriorityQueue</code> does <em>not</em> visit elements in "
        "order. Neither does <code>toString()</code>, and neither does "
        "<code>toArray()</code>. This surprises people while debugging.",
        "<code>peek()</code> is the only O(1) read, and only of the extreme.",
        "There is no efficient search: <code>contains()</code> and "
        "<code>remove(Object)</code> are O(n).")
   + table(("Operation", "Cost", "Java"), [
       ("peek the extreme", "O(1)", "<code>pq.peek()</code>"),
       ("insert", "O(log n)", "<code>pq.offer(x)</code>"),
       ("remove the extreme", "O(log n)", "<code>pq.poll()</code>"),
       ("build from n items", "<strong>O(n)</strong>", "<code>new PriorityQueue&lt;&gt;(collection)</code>"),
       ("find or remove an arbitrary item", "O(n)", "<code>pq.remove(x)</code> — avoid"),
   ])
   + p("Building from a collection is O(n), not O(n log n) — heapify works bottom-up "
       "and the cost telescopes. If you need all n elements in a heap, hand them to the "
       "constructor rather than looping <code>offer</code>.")),

  ("Top-k: the direction is the opposite of your instinct",
   diagrams.heap_top_k() +
   p("For the <strong>k largest</strong>, keep a <strong>min</strong>-heap of size k. "
     "The root is then the smallest of the ones you are keeping, which is exactly the "
     "element to evict when something better arrives. Using a max-heap here is a real "
     "and common bug: it evicts your best answers and passes tests where k ≥ n.")
   + code("""
// k largest elements, O(n log k) time and O(k) space
PriorityQueue<Integer> pq = new PriorityQueue<>();   // MIN-heap
for (int x : nums) {
    pq.offer(x);
    if (pq.size() > k) pq.poll();                    // drop the smallest kept
}
// pq now holds the k largest -- in NO particular order
""")
   + p("The same shape answers k-closest-points-to-origin (max-heap on distance, keep "
       "the k nearest), top-k-frequent-elements (count first, then min-heap on count), "
       "and kth-largest-element-in-a-stream (min-heap of size k held as a field; "
       "<code>add()</code> returns <code>pq.peek()</code>).")
   + p("<strong>When k is close to n</strong>, sorting is simpler and no slower — "
       "O(n log k) and O(n log n) meet. And when you need the k-th element but not the "
       "k set, Quickselect is O(n) average; it is worth knowing but not worth writing "
       "under time pressure unless the constraints demand it.")),

  ("The comparator is the design",
   p("Most heap problems are really comparator problems. Get it wrong and everything "
     "downstream is wrong, silently. [[Comparators]]'s rule applies with full force here — "
     "<strong>never subtract</strong>:")
   + code("""
new PriorityQueue<>()                                    // natural order, min-heap
new PriorityQueue<>(Comparator.reverseOrder())           // max-heap
new PriorityQueue<>((a, b) -> Integer.compare(a[1], b[1]))         // by column 1 asc
new PriorityQueue<>(Comparator.comparingInt(a -> a[1]))            // same, clearer
new PriorityQueue<>(Comparator.comparingInt((int[] a) -> a[0])
                              .thenComparing(a -> a[1]))           // tie-break
new PriorityQueue<>(Comparator.comparingLong(Task::cost).reversed())
""", compiles=False)
   + p("<code>Comparator.comparingInt</code> is worth preferring over a lambda that "
       "subtracts: it cannot overflow, and it reads as the intent. When elements are "
       "<code>long</code>, use <code>comparingLong</code> — "
       "<code>comparingInt</code> on a long silently truncates.")
   + p("<strong>Mutating an element while it is in the heap corrupts the heap.</strong> "
       "The position was chosen from the old comparator value, and nothing re-heapifies. "
       "This is why Dijkstra pushes new <code>(dist, node)</code> entries rather than "
       "updating existing ones, and then discards stale entries on pop — which is "
       "[[graph-traversal]]'s <em>finalise on pop</em> seen from the heap's side:")
   + code("""
while (!pq.isEmpty()) {
    int[] top = pq.poll();
    int d = top[0], u = top[1];
    if (d > dist[u]) continue;         // stale entry -- a better one already ran
    ...
}
""", compiles=False)),

  ("Two heaps, and the k-way merge",
   p("Two patterns cover most of the rest of the topic.")
   + p("<strong>Two heaps facing each other</strong> maintain a split of the data — the "
       "median ([[complexity-budget]]), or a running balance in problems like "
       "sliding-window-median and ipo. The invariant is a size relation, restored after "
       "every insert. When elements also <em>leave</em> (a sliding window), "
       "<code>remove(Object)</code> is O(n) and will time out; the standard answer is "
       "lazy deletion — keep a map of counts pending removal and discard entries at the "
       "top when you pop them.")
   + p("<strong>K-way merge</strong> seeds the heap with one element from each of k "
       "sources and, on each pop, pushes the successor from the same source. "
       "merge-k-sorted-lists, smallest-range-covering-elements-from-k-lists and "
       "kth-smallest-element-in-a-sorted-matrix are all this:")
   + code("""
PriorityQueue<ListNode> pq =
    new PriorityQueue<>(Comparator.comparingInt(n -> n.val));
for (ListNode head : lists) if (head != null) pq.offer(head);   // null check matters

ListNode dummy = new ListNode(0), cur = dummy;      // [[sentinels]]'s dummy node
while (!pq.isEmpty()) {
    ListNode n = pq.poll();
    cur.next = n; cur = n;
    if (n.next != null) pq.offer(n.next);           // one successor, not the whole list
}
return dummy.next;
""")
   + p("O(N log k) for N total elements. The heap never holds more than k entries — "
       "pushing entire lists in makes it O(N log N) and defeats the point.")),
 ],
 "rules": [
  "k largest -> min-heap of size k. k smallest -> max-heap. Write the direction down before coding.",
  "Never iterate a heap expecting sorted order. Only peek() is ordered.",
  "Build from a collection with the constructor -- O(n) -- not with a loop of offer().",
  "Comparator.comparingInt / comparingLong, never a - b.",
  "Never mutate an element that is inside a heap. Push a new entry and skip stale ones on pop.",
  "If a query drains or copies the heap, the state is wrong -- fix the invariant, not the query.",
 ],
 "drill": "Implement kth-largest-element-in-a-stream, k-closest-points-to-origin and "
          "merge-k-sorted-lists from scratch in one sitting. For each, write the heap "
          "direction and its size bound in a comment before the declaration. Then do "
          "sliding-window-median, which forces you to solve the removal problem.",
},

# ==========================================================================
{
 "slug": "equality-hashing",
 "title": "Equality, hashing and boxing",
 "one_line": "== on boxed Integers compares identity outside −128…127. It works in testing and fails on the judge.",
 "why": "32 equality and hashing mistakes across 24 topics. This class is nastier than "
        "most because the wrong code passes small tests: Java caches boxed Integers in "
        "−128…127, so == appears to work until a value exceeds 127.",
 "summary": (
  p('<code>==</code> on references asks “the same object?”. '
     '<code>.equals</code> asks “the same value?”. Autoboxing makes the '
     'distinction dangerous, because Java caches <code>Integer</code> '
     'objects for −128…127 and hands out the same instance every time — so '
     '<code>==</code> works in every example you type by hand and fails the '
     'moment a value exceeds 127.') +
  p('The same split governs hash collections. A key type whose '
     '<code>equals</code> and <code>hashCode</code> disagree stores '
     'duplicates you cannot look up, and arrays hash by identity, so an '
     '<code>int[]</code> key never matches anything.')
 ),
 "used_for": [
  ('Comparing two boxed values pulled out of a Map or List',
   'Use .equals, or unbox to int first. == is an identity test that '
    'happens to work on small numbers.'),
  ('Using an object or an array as a HashMap key',
   'Arrays hash by identity. Use a String, a List, a record, or an encoded '
    'long.'),
  ('Counting occurrences',
   'map.merge(k, 1, Integer::sum) — one call, no null check, no boxing '
    'comparison anywhere.'),
  ('Deduplicating unordered data',
   'HashSet, which uses equals/hashCode. TreeSet, which uses compareTo, '
    'answers a different question.'),
  ('Hot loops over millions of values',
   'Boxing allocates. An int[] or a primitive-keyed structure wins when '
    'the key range is small and known.'),
 ],
 "patterns": [
  ('Values can be up to 10⁹ and you compare them from a Map',
   'Outside the Integer cache. == passes locally and fails on the judge.'),
  ('Group the anagrams / group by signature',
   'The key must be a canonical form — a sorted String or a 26-count key — '
    'never the array itself.'),
  ('Return true if the two arrays are equal',
   'Arrays.equals, and Arrays.deepEquals for nested arrays.'),
  ('Use a coordinate pair (r, c) as a key',
   'Encode as r * cols + c, or a String, or a record — never an int[].'),
  ('Detect a repeat by remembering seen states',
   "The state's equality must be value equality, or you will never get a "
    'hit.'),
  ('The keys are characters over a known alphabet',
   "Skip the map. int[26] indexed by c - 'a' has none of these problems."),
 ],
 "match": r"boxed|Integer.*==|==.*Integer|\.equals\(|hashCode|"
          r"reference equality|object identity|HashSet<Integer>|"
          r"HashMap<Integer|autobox|unbox",
 "basics": [
  ("The Integer cache",
   diagrams.integer_cache() +
   code("""
Integer a = 127, b = 127;
boolean cached   = (a == b);      // true  — both point at the same cached object

Integer c = 128, d = 128;
boolean distinct = (c == d);      // FALSE — two distinct objects, equal values
boolean correct  = c.equals(d);   // true  — the comparison you meant
""")
   + p("Java caches <code>Integer</code> objects for −128…127 and allocates fresh ones "
       "outside that range. So <code>==</code> on boxed integers is a test that passes "
       "on small inputs and fails on real ones — which is exactly what happened in "
       "<code>range-module</code>, where <code>map.get(start1) == start2</code> silently "
       "returned false for equal keys above 127.")
   + p("This applies to every boxed type and to <code>String</code>. The fix is always "
       "the same:")
   + code("""
Map<String, Integer> map = new HashMap<>();
Integer target = 3;

// wrong -- compares two references, and is true only below 128
if (map.get("k") == target) { }

// right — and null-safe in both directions
if (Objects.equals(map.get("k"), target)) { }

// or unbox explicitly, having checked for null
Integer v = map.get("k");
if (v != null && v == target) { }   // v == target unboxes v, so this is fine
""")),

  ("The equals/hashCode contract",
   p("If you put your own class in a <code>HashMap</code> or <code>HashSet</code>, you "
     "must override both:")
   + ul("Equal objects must have equal hash codes. (If not, the set stores duplicates.)",
        "Unequal objects <em>may</em> share a hash code. (That is just a collision.)",
        "Both must be computed from the <em>same</em> fields.",
        "Those fields must not change while the object is in the collection.")
   + code("""
record Point(int x, int y) { }        // records generate both, correctly, for free
""")
   + p("A Java <code>record</code> gives you correct <code>equals</code>, "
       "<code>hashCode</code> and <code>toString</code> from the components. For a value "
       "type in a collection, prefer it over a hand-written class.")),

  ("Boxing costs, and when it matters",
   p("<code>HashSet&lt;Integer&gt;</code> stores a pointer to a heap object per element, "
     "and every lookup hashes and unboxes. Over ~10<sup>6</sup> elements that is the "
     "difference between passing and a TLE — which is what happened in "
     "<code>number-of-unique-xor-triplets-ii</code>.")
   + table(("Instead of", "Use", "Why"), [
       ("<code>HashSet&lt;Integer&gt;</code> over a bounded range",
        "<code>boolean[]</code> or <code>long[]</code> bitset", "no boxing, no hashing, cache-friendly"),
       ("<code>HashMap&lt;Integer,Integer&gt;</code> over 0..n",
        "<code>int[]</code>", "direct indexing"),
       ("<code>List&lt;Integer&gt;</code> in a hot loop", "<code>int[]</code> with a size counter", "no per-element object"),
       ("<code>Map&lt;Character,Integer&gt;</code>", "<code>int[26]</code> or <code>int[128]</code>", "the alphabet is the index"),
   ])
   + p("This is not premature optimisation — it is picking the representation the problem "
       "already implies. When keys are dense small integers, an array <em>is</em> the "
       "hash map.")),
 ],
 "rules": [
  "Never == between boxed values. Objects.equals, or unbox after a null check.",
  "Override equals and hashCode together, from the same fields, or use a record.",
  "Dense integer keys in a known range → int[]/boolean[], not HashMap/HashSet.",
  "Characters over a fixed alphabet → int[26] or int[128].",
 ],
 "drill": "Find every `HashMap<Integer, Integer>` in your accepted code where the keys are "
          "array indices. Each one is an int[] you didn't write.",
},


# ==========================================================================
{
 "slug": "library-edges",
 "title": "Java means it: boxing, casts and contracts you did not read",
 "one_line": "The compiler accepted it because you asked for something. Just not "
             "the thing you meant.",
 "why": "{{mistakes:library-edges}} diagnosed mistakes and "
        "{{habits:library-edges}} habits in accepted code, across "
        "{{problems:library-edges}} problems and {{topics:library-edges}} "
        "topics, are the language and its standard library behaving exactly "
        "as specified while you expected something else: a cast that bound to the "
        "wrong operand, an int autoboxed to Integer where Long was needed, an "
        "unboxed null, a TreeSet ordering by a comparator that disagrees with "
        "equals, a division that truncated in silence. None of these are algorithm "
        "errors and none of them are typos. They are places where Java's rules are "
        "unambiguous and different from the ones in your head, which is why "
        "rereading the code does not find them.",
 "summary": (
  p('Every item in this lesson has the same structure. You wrote an '
    'expression; Java gave it a meaning; the meaning was well-defined, legal, '
    'and not yours. Because the code is legal, there is no compiler warning '
    'and nothing to notice on a reread &mdash; the expression looks like what '
    'you intended, which is exactly the problem.') +
  p('So this is a lesson of specific facts rather than a technique. The facts '
    'are short, they are each responsible for at least one of your failed '
    'submissions, and once known they are seen instantly. The value is in '
    'knowing which handful to look for.') +
  p('Boxing runs through most of them, because <code>int</code> and '
    '<code>Integer</code> are different types that Java converts between '
    'automatically, and every automatic conversion is a place where a '
    'decision was made without you.')
 ),
 "used_for": [
  ('Any arithmetic that mixes literals and casts',
   'A cast binds to the operand next to it, not to the expression.'),
  ('Generic collections holding numbers',
   'Autoboxing picks a type from the literal, and it never widens to match '
   'the type parameter.'),
  ('Comparing boxed values',
   '== on two Integers compares references, and small values happen to work.'),
  ('Sorted collections of your own objects',
   'TreeMap and TreeSet use compareTo; HashMap and HashSet use equals and '
   'hashCode. Defining one is not defining the other.'),
  ('Any map or heap read used directly in arithmetic',
   'A miss returns null, and unboxing null is a NullPointerException far from '
   'any visible null.'),
  ('Hot loops over 10^5 elements or more',
   'Boxing is a constant factor, and at 10^6 it is the difference between '
   'accepted and timed out.'),
 ],
 "patterns": [
  ('A compile error about incompatible types on a line that looks obviously right',
   'Autoboxing chose Integer, and the target wanted Long.'),
  ('NullPointerException on a line with no dot on the left of it',
   'Something unboxed. Look for a map get or a heap peek inside a comparison.'),
  ('Correct on small inputs, wrong on large ones, no overflow in sight',
   'An == between boxed values, working inside the cache range and failing '
   'outside it.'),
  ('A sorted set silently drops or keeps the wrong element',
   'compareTo returned 0 for two things your equals calls different.'),
  ('The formula is right and the result is systematically too small',
   'Integer division truncated before the multiplication you meant to happen '
   'first.'),
  ('Time Limit Exceeded on a solution with the right complexity',
   'Boxing in the inner loop. Move to primitive arrays.'),
 ],
 "match": r"\bInteger\b.{0,40}(==|cache|identity|unbox|autobox|NullPointer)|"
          r"(auto)?box(ed|ing|es)|unbox(ed|es|ing)|instead of `?\.?equals|"
          r"remove\((int|Integer|index)|Arrays\.asList|"
          r"Arrays\.sort.{0,45}(comparator|Comparator|int\[\])|integer division|"
          r"(implicit|silent|unintended) (cast|conversion|widening|narrowing|truncat)|"
          r"(cast|casts) .{0,30}(binds|applies) (only )?to|"
          r"(TreeSet|TreeMap).{0,60}(compareTo|equals\(\))|"
          r"PriorityQueue.{0,40}(contains|remove\(|peek\(\))|"
          r"HashMap.{0,25}(iteration )?order|size_t|unsigned|nullptr|"
          r"doesn't type-check|does not type-?check|Math\.abs\(|"
          r"subtraction .{0,20}(comparator|overflow)|(String|char)\[\].{0,25}sort",
 "basics": [

  ("A cast binds to the operand, not the expression",
   code("""
long r = (long) 8 * 1e15;     // rejected: 8 * 1e15 is a double
""")
   + p("From <em>minimum-number-of-seconds-to-make-mountain-height-zero</em>. The "
       "cast applies to <code>8</code> alone, giving <code>(long) 8</code>; that "
       "operand then meets a <code>double</code> literal, the whole product "
       "promotes to <code>double</code>, and Java refuses the implicit narrowing "
       "back to <code>long</code>. The intent was a large integer constant and "
       "the expression never contained one.")
   + p("Two fixes, and the second is better:")
   + code("""
long r = (long) (8 * 1e15);   // works, but the arithmetic still went through double
long r = 8_000_000_000_000_000L;   // an integer constant, written as one
""")
   + p("<strong>Scientific notation in Java is always a double.</strong> "
       "<code>1e15</code> is not an integer literal and never was; using it as one "
       "silently routes the value through 53 bits of mantissa. When you want a "
       "wide integer bound, write the digits with an <code>L</code>, or use "
       "<code>Long.MAX_VALUE</code> and the guidance in [[integer-width]].")),

  ("Autoboxing picks a type, and it is not inference",
   p("Two of your compile failures are one rule:")
   + code("""
Map<Integer, Long> sumMap = ...;
sumMap.put(key, prices[i]);        // prices[i] is int -> boxes to Integer, not Long

List<Long> stack = ...;
stack.add(0);                      // 0 is int -> boxes to Integer, not Long
""", compiles=False)
   + p("From <em>maximum-linear-stock-score</em> and <em>path-sum-iii</em>. "
       "Autoboxing converts <code>int</code> to <code>Integer</code> and stops. It "
       "will not then widen <code>Integer</code> to <code>Long</code>, because "
       "widening a reference type is not a conversion Java performs. The value "
       "fits, the intent is obvious, and the call does not type-check.")
   + p("The fix is to make the literal or the expression already have the right "
       "primitive type, so boxing has nothing to choose:")
   + code("""
sumMap.put(key, (long) prices[i]);
stack.add(0L);
""")
   + p("The same rule is why <code>Arrays.asList(intArray)</code> gives you a "
       "one-element <code>List&lt;int[]&gt;</code> rather than a list of ints, and "
       "why <code>Arrays.sort(int[], comparator)</code> does not exist &mdash; "
       "there is no <code>Comparator&lt;int&gt;</code>, so sorting primitives by a "
       "custom order means boxing to <code>Integer[]</code> first and paying for "
       "it.")),

  ("Unboxing a null",
   code("""
void check(PriorityQueue<Integer> pq, int val, int k) {
    // peek() returns null on an empty heap, and unboxing null throws
    if (pq.peek() > val && pq.size() >= k) { }

    // the test that makes the read safe has to be on the left of the &&
    if (pq.size() >= k && pq.peek() > val) { }
}
""")
   + p("From <em>kth-largest-element-in-a-stream</em>. The <code>&gt;</code> "
       "forces <code>pq.peek()</code> to unbox, and <code>peek()</code> returns "
       "null on an empty heap, so this throws a NullPointerException on a line "
       "with no dereference written in it. The size test that would have prevented "
       "it is on the wrong side of the <code>&amp;&amp;</code> &mdash; the same "
       "short-circuit shape as [[degenerate-inputs]], with the added twist that "
       "the dereference is invisible.")
   + p("The identical shape produced the <em>majority-element</em> "
       "NullPointerException, where <code>containsKey(i)</code> was asked about a "
       "position while <code>put</code> stored values, so the subsequent "
       "<code>get</code> returned null and unboxed into arithmetic. That one is "
       "also [[wrong-name]]; both lessons apply, and the exception message names "
       "neither.")
   + p("<strong>Any <code>Map.get</code>, <code>PriorityQueue.peek</code> or "
       "<code>poll</code> whose result is used in arithmetic or a comparison is a "
       "potential NPE.</strong> Use <code>getOrDefault</code>, check "
       "<code>isEmpty()</code> first, or assign to a boxed local and test it &mdash; "
       "but decide, rather than letting the unboxing decide for you.")),

  ("compareTo orders, equals identifies, and they must agree",
   diagrams.integer_cache() +
   p("Two separate facts collide here, and both cost you a submission.")
   + p("The first is identity. <code>==</code> on two <code>Integer</code> "
       "references compares references, and Java caches boxed values in "
       "<code>[-128, 127]</code>, so the comparison is true for small numbers and "
       "false for large ones with no change to the code. Full treatment in "
       "[[equality-hashing]]; the reason it belongs here too is that nothing about "
       "the expression says a reference comparison is happening.")
   + p("The second is the contract. From "
       "<em>stock-price-fluctuation</em>: a <code>TreeSet&lt;TimePrice&gt;</code> "
       "whose <code>compareTo</code> ordered by price, and whose "
       "<code>equals</code> and <code>hashCode</code> were written on timestamp. "
       "A <code>TreeSet</code> decides membership with <code>compareTo</code>, "
       "never with <code>equals</code> &mdash; so two entries at different "
       "timestamps with the same price were the same element as far as the set was "
       "concerned, and one of them was silently discarded.")
   + p("<strong>The rule: a sorted collection uses <code>compareTo</code> for "
       "identity, a hashed collection uses <code>equals</code> and "
       "<code>hashCode</code>, and if you put a type in both, the two definitions "
       "must agree on which objects are the same one.</strong> Break the tie "
       "explicitly &mdash; order by price and then by timestamp &mdash; so that "
       "<code>compareTo</code> returns 0 exactly when <code>equals</code> is true. "
       "See [[comparators]] for the rest of the comparator contract.")
   + p("The related performance trap in the same family: "
       "<code>PriorityQueue.remove(Object)</code> and <code>contains</code> are "
       "linear scans, not heap operations. A heap is not a set, and treating it as "
       "one turns an O(log n) algorithm into O(n) per operation without any change "
       "to the code you would look at.")),

  ("Division truncates, and never mentions it",
   code("""
int a = (point1[1] - point2[1]) / (point1[0] - point2[0]);   // the slope
""")
   + p("From <em>max-points-on-a-line</em>. Every non-integer slope truncates to "
       "the integer below, so distinct lines collapse onto each other and points "
       "that are not collinear are reported as collinear. The result is not "
       "approximate; it is a different equivalence relation.")
   + p("<strong>Integer division is exact division composed with a floor, and the "
       "floor is invisible.</strong> When a ratio is the thing you care about, do "
       "not compute the ratio &mdash; compare cross-products "
       "(<code>dy1 * dx2 == dy2 * dx1</code>), or store the reduced fraction as a "
       "pair divided by its gcd. Both stay in integers and neither loses anything.")
   + p("The same truncation is behind the <em>count-ways-to-make-array-with-"
       "product</em> failures, where <code>nCr</code> was computed with "
       "<code>ans *= (n - i); ans /= (i + 1); ans %= P;</code>. Once a value has "
       "been reduced modulo P, dividing it by <code>(i + 1)</code> is meaningless "
       "&mdash; the quotient in the modular world is multiplication by an inverse, "
       "not division. [[number-theory]] covers the fix; the point here is that the "
       "<code>/</code> gave an answer instead of an error.")
   + p("Note also that <code>Math.abs(Integer.MIN_VALUE)</code> is negative, for "
       "the same reason two's complement has one more negative value than positive "
       "one &mdash; another operation that returns a wrong answer rather than "
       "complaining. [[integer-width]] has the picture.")),

  ("Boxing as a constant factor",
   p("Nineteen habits in your accepted code are boxing that costs time without "
     "costing correctness: a <code>List&lt;Integer&gt;</code> read with "
     "<code>.get(i)</code> in a hot recursive loop in <em>perfect-squares</em>; a "
     "<code>HashMap&lt;List&lt;Integer&gt;, Integer&gt;</code> memo in "
     "<em>count-beautiful-numbers</em> that boxes four ints into a list to build "
     "one key; a hand-rolled <code>Pair</code> class used purely as a map key "
     "where a packed <code>long</code> would do.")
   + p("Usually that is a style note. Once in your export it was the submission: "
       "<em>number-of-unique-xor-triplets-ii</em> used "
       "<code>HashSet&lt;Integer&gt;</code> over roughly a million pairwise XORs "
       "and timed out with the right algorithm.")
   + p("<strong>The threshold worth remembering: at around 10^6 operations, boxed "
       "collections stop being a style question.</strong> A "
       "<code>HashSet&lt;Integer&gt;</code> allocates, hashes and chases a pointer "
       "per element; a <code>boolean[]</code> or a sorted <code>int[]</code> does "
       "none of that. When the value range is bounded &mdash; and in these "
       "problems it usually is &mdash; the primitive array is both faster and "
       "shorter. [[complexity-budget]] is where to work out whether you are near "
       "that line.")),
 ],
 "rules": [
  "A cast binds to the operand beside it. Parenthesise the expression, or write the literal with L.",
  "Scientific notation is a double, always. Use digit literals with L for wide integer bounds.",
  "Autoboxing goes int -> Integer and stops. Cast to the primitive the collection wants before adding.",
  "Any map get, heap peek or poll used in a comparison can unbox null. Test emptiness first, on the correct side of the &&.",
  "Never == two boxed values. It is true below 128 and false above it.",
  "Sorted collections identify by compareTo; hashed ones by equals and hashCode. If a type is in both, make them agree.",
  "PriorityQueue.contains and remove(Object) are linear. A heap is not a set.",
  "When a ratio matters, compare cross-products or store a reduced fraction. Never divide.",
  "Past about 10^6 operations, replace boxed collections with primitive arrays.",
 ],
 "drill": "Write a scratch file with these six lines and predict each result "
          "before running it: `(long) 8 * 1e15`, `Integer.valueOf(127) == "
          "Integer.valueOf(127)`, `Integer.valueOf(128) == Integer.valueOf(128)`, "
          "`Math.abs(Integer.MIN_VALUE)`, `Arrays.asList(new int[]{1,2,3}).size()`, "
          "and `-7 / 2`. Then revisit max-points-on-a-line and rewrite the "
          "collinearity test with cross-products, and stock-price-fluctuation with "
          "a compareTo that agrees with equals.",
},
# ==========================================================================
{
 "slug": "counting-arrays",
 "title": "Counting arrays: the histogram and its four traps",
 "one_line": "An int[] indexed by value, not by position. Faster than a map, and it "
             "cannot tell 'absent' from 'zero'.",
 "why": "{{mistakes:counting-arrays}} diagnosed mistakes and "
        "{{habits:counting-arrays}} smells across {{problems:counting-arrays}} "
        "problems and {{topics:counting-arrays}} topics touch a "
        "frequency table, and the failures cluster into four repeats: an array sized by "
        "guess instead of by the data's range, a minimum decided by empty buckets, a "
        "count read with the loop index instead of the value, and a prefix sum computed "
        "in place over the array it is reading. H-Index alone took five submissions to "
        "the last of those. The structure is two lines of code, which is exactly why "
        "nobody checks it.",
 "summary": (
  p('A counting array is an <code>int[]</code> whose <em>index is a value '
    'from your data</em> and whose contents are how many times that value '
    'occurred. <code>int[26]</code> for lowercase letters, '
    '<code>int[10]</code> for digits, <code>int[maxValue + 1]</code> for '
    'bounded integers.') +
  p('It is the fastest thing in the toolbox for a small, known range: array '
    'indexing rather than hashing, no boxing, and it iterates in sorted key '
    'order for free &mdash; which is what makes counting sort, bucket sort '
    'and every anagram check work. [[Equality-hashing]] covers what to do when the range '
    'is not small or not known; this is the case where it is.') +
  p('The catch is that the table has an entry for every value in the range, '
    'including the ones that never appeared. <strong>Absent and zero are the '
    'same number.</strong> Three of the four traps below are that single '
    'fact resurfacing.')
 ),
 "used_for": [
  ('Anagrams, permutations and "same multiset?" checks',
   'Count both sides into int[26] and compare with Arrays.equals. One pass, '
   'no sorting.'),
  ('Sliding windows over a small alphabet',
   'Add on the right, subtract on the left, and the window state is one '
   'array you never rebuild.'),
  ('Sorting values from a small known range',
   'Counting sort: fill the table, then walk it in index order. O(n + k) '
   'and stable.'),
  ('Top-k frequent, or the most/least common element',
   'Count first, then bucket by frequency to avoid a sort entirely.'),
  ('Any "can these be rearranged into..." question',
   'Parity of the counts answers most of them, palindromes especially.'),
  ('Ranges up to 1e9, or unbounded values',
   'Do not. That is a HashMap or coordinate compression -- the array would '
   'need four gigabytes.'),
 ],
 "patterns": [
  ('The string consists of lowercase English letters',
   'int[26]. The constraint is telling you the table size.'),
  ('Check whether two strings are anagrams',
   'One table, ++ for the first string and -- for the second, then assert '
   'all zero.'),
  ('Return the most / least frequent element or character',
   'Count, then argmax -- and for argmin, skip the empty buckets.'),
  ('Values are in the range 1..n, or 0 <= nums[i] <= 100',
   'A counting array is O(n) where a sort would be O(n log n).'),
  ('How many pairs (i, j) have the same value',
   'Sum c*(c-1)/2 over the buckets. The /2 is the part that gets dropped.'),
  ('At most k distinct characters in the window',
   'Keep a distinct counter alongside the table; increment when a bucket '
   'leaves 0, decrement when it returns to 0.'),
  ('Sort an array of 0s, 1s and 2s',
   'Counting sort in three buckets -- or Dutch national flag if one pass '
   'and O(1) space are required.'),
 ],
 "match": r"freq\[|frequenc(y|ies)|\bcounts?\[|\bint\[26\]|\bnew int\[|histogram|"
          r"bucket|tally|counting array|`?- ?'a'`?",
 "basics": [

  ("Trap 1: the zero bucket wins every minimum",
   diagrams.counting_array_zero() +
   p("This is the one you have hit most often, and it is invisible in a "
     "maximum. <code>argmax</code> over the table is correct, because a bucket "
     "holding zero can never be the largest. <code>argmin</code> over the table is "
     "always wrong, because a bucket holding zero is almost always the smallest.")
   + code("""
// WRONG -- find-the-least-frequent-digit
int best = 0;
for (int d = 1; d < 10; d++)
    if (freq[d] < freq[best]) best = d;    // every absent digit has freq 0
return best;                               // returns a digit that is not in n

// RIGHT -- the range you iterate is "values present", not "values possible"
int best = -1;
for (int d = 0; d < 10; d++)
    if (freq[d] > 0 && (best == -1 || freq[d] < freq[best])) best = d;
return best;
""")
   + p("Your export contains this twice, in problems ten months apart: "
       "<em>find-the-least-frequent-digit</em>, where the analysis notes &ldquo;a "
       "digit absent from n always won&rdquo;, and "
       "<em>maximum-difference-between-even-and-odd-frequency-i</em>, where the same "
       "hole is worse &mdash; an absent letter has frequency 0, and 0 is even, so it "
       "wins the minimum-even-frequency search outright.")
   + p("The parity version is worth stating on its own, because the guard is not "
       "obviously needed: <strong>any even/odd test over a counting array must skip "
       "the empty buckets first</strong>, since zero is even and there are usually a "
       "lot of it. The eventual fix on that problem sidestepped the whole class by "
       "switching to a map of only the letters actually present, which is the "
       "structural answer &mdash; a <code>HashMap</code> has no entry for a value that "
       "never occurred, so the question cannot arise.")),

  ("Trap 2: sizing the array by guess instead of by the data",
   p("The table's length must come from the problem's stated range or from the "
     "data itself. Both alternatives &mdash; a round number that looks big enough, "
     "or a length borrowed from the wrong quantity &mdash; appear in your history.")
   + code("""
int[] count = new int[n];                 // WRONG: n is how many elements
int[] count = new int[100001];            // WRONG: a guess, even a correct one
int[] count = new int[max + 1];           // RIGHT: derived, and +1 for the value itself
""")
   + p("In <em>count-the-number-of-k-free-subsets</em> the table was sized "
       "<code>new int[n]</code>, the element count, while it was indexed by element "
       "<em>value</em> &mdash; so any value at least <code>n</code> went out of "
       "bounds. The fix computed <code>maxEl</code> and sized "
       "<code>count[maxEl + 1]</code>. That <code>+ 1</code> is not decoration: an "
       "array of length <code>max</code> has no slot <code>max</code>, and [[bounds]] "
       "is the general form of the same off-by-one.")
   + p("The guessed-constant version is slower to fail and worse to debug. Your "
       "<em>partition-equal-subset-sum</em> smell records a <code>boolean[]</code> "
       "sized 20000, then 10001, then 20001, then 10001 again across four post-solve "
       "resubmissions &mdash; a bound found by trial against the judge rather than "
       "derived from <code>sum / 2</code>. When the constant is right it is right by "
       "luck, and the next problem's constraints are different.")
   + p("The third variant is an assumption about the alphabet rather than the "
       "range. <em>longest-substring-with-at-most-two-distinct-characters</em> "
       "indexed <code>freq[26]</code> with <code>c - 'a'</code> on input that was not "
       "lowercase-only, which produces a negative index. Reach for "
       "<code>new int[128]</code> indexed by the raw char whenever the statement does "
       "not explicitly promise lowercase &mdash; the memory is free and the "
       "assumption disappears.")),

  ("Trap 3: indexing with the position instead of the value",
   p("A counting array is defined by the fact that its index is a value. Every "
     "surrounding loop is indexed by position. The two are both small integers, so "
     "nothing in the type system objects when they are swapped.")
   + code("""
for (int i = 0; i < s.length(); i++) {
    freq[i]++;                    // WRONG -- counts positions
    freq[s.charAt(i) - 'a']++;    // RIGHT -- counts characters
}
""")
   + p("The analysis found this in <em>top-k-frequent-elements</em> as "
       "<code>count.getOrDefault(count, 0)</code> &mdash; the map passed as its own "
       "key &mdash; and it survived <strong>four consecutive submissions</strong> "
       "while unrelated symptoms were patched around it. In "
       "<em>majority-element</em>, <code>put</code> and <code>get</code> were "
       "corrected to index by <code>nums[i]</code> while <code>containsKey(i)</code> "
       "was left checking the loop index, so the fix landed on two of three call "
       "sites. And in one string problem the analysis notes the same index-vs-"
       "character confusion recurring in a <em>later, independent rewrite</em> of a "
       "file where it had already been fixed once.")
   + p("That last observation is the useful one: this is not a typo that happens "
       "and passes. It is a habit that regenerates, because <code>i</code> is what "
       "the fingers type. [[Wrong-name]] is the general treatment; the counting-array "
       "case is worth naming here because the wrong version reads a real bucket "
       "every time and produces plausible numbers.")),

  ("Trap 4: turning counts into prefix sums, in place",
   p("Counting sort and every &ldquo;how many are at least i&rdquo; question needs "
     "the table converted to a running total. Done in place, the accumulator and the "
     "array reads interleave, and the value you just wrote gets folded in again. "
     "Both columns below come from running both versions on the same counts:")
   + traces.prefix_sums([3, 0, 2, 1])
   + p("Your <em>h-index</em> history is five submissions on exactly this, and it "
       "is worth reading as a sequence. The first wrote "
       "<code>counts[i] += total</code> before <code>total += counts[i]</code>, "
       "double-counting each bucket. The second swapped the two statements, and "
       "double-counted in the other order. The third clamped the runaway value with "
       "<code>Math.min</code>, which bounds the symptom without touching the cause. "
       "Only the fourth separated the two quantities:")
   + code("""
// h-index: papers with >= i citations, right to left
int total = 0;
for (int i = counts.length - 1; i >= 0; i--) {
    int prevTotal = total;         // snapshot BEFORE this bucket joins it
    total += counts[i];
    counts[i] = counts[i] + prevTotal;
}
""")
   + p("The general rule is the one that ends this whole family: <strong>when a "
       "loop both reads and writes one array, decide on every line whether you mean "
       "the old value or the new one</strong>. A snapshot variable makes the choice "
       "explicit; a second array makes it impossible to get wrong. Your "
       "<em>total-characters-in-string-after-transformations-ii</em> submission hit "
       "the identical bug one dimension up, writing into <code>freq[i]</code> while "
       "other iterations still needed the old <code>freq[j]</code>, and the fix was "
       "the second array: write <code>newFreq</code>, then assign "
       "<code>freq = newFreq</code> after the pass completes.")
   + p("One arithmetic footnote from the same family. Counting pairs within a "
       "bucket is <code>c * (c - 1) / 2</code>, not <code>c * (c - 1)</code> &mdash; "
       "your <em>number-of-equivalent-domino-pairs</em> submission dropped the "
       "division and double-counted every unordered pair. And if <code>c</code> can "
       "reach 1e5, that product needs <code>long</code>, which is [[integer-width]].")),

  ("The whole structure, correct",
   p("For reference, the shape all four traps are deviations from:")
   + code("""
int[] atLeast(String s) {
    // 1. size from the range, never from a guess and never from n.
    int[] freq = new int[26];              // the stated constraint: lowercase
    // int[] freq = new int[max + 1];      // or derived from the data itself

    // 2. index by VALUE, never by the loop position
    for (char c : s.toCharArray()) freq[c - 'a']++;

    // 3. read back over PRESENT values only, whenever the question is a
    //    minimum, an argmin, or a parity test
    int rarest = -1;
    for (int v = 0; v < freq.length; v++) {
        if (freq[v] == 0) continue;        // absent is not zero
        if (rarest < 0 || freq[v] < freq[rarest]) rarest = v;
    }

    // 4. counts to a running total: a second array, so no cell is read
    //    after it has been overwritten
    int[] running = new int[freq.length];
    int total = 0;
    for (int v = freq.length - 1; v >= 0; v--) {
        total += freq[v];
        running[v] = total;
    }
    return running;
}
""")
   + p("Two habits make the whole class visible while you type. Name the variable "
       "for what it counts &mdash; <code>letterFreq</code>, <code>digitCount</code> "
       "&mdash; so <code>letterFreq[i]</code> reads as obviously wrong next to a "
       "position loop. And write the table's size as an expression rather than a "
       "literal, so the constraint that justifies it stays visible in the code.")),
 ],
 "rules": [
  "Size the table from the stated range or from max(data) + 1. Never from n, never from a round number.",
  "Index by value. If the subscript is the loop position, it is wrong -- reread the line.",
  "Any minimum, argmin or even/odd test over the table must skip freq[v] == 0 first. Absent is not zero.",
  "Maximum and argmax need no such guard. Knowing which need it is the point.",
  "Not promised lowercase? Use int[128] and the raw char, not int[26] and c - 'a'.",
  "Converting counts to prefix sums: snapshot the running total, or write into a second array.",
  "Pairs within a bucket are c*(c-1)/2, and the product may need a long.",
  "Range above ~1e6 or unknown? HashMap or coordinate compression instead.",
 ],
 "drill": "valid-anagram and find-the-difference with int[26], then "
          "top-k-frequent-elements twice -- once with a HashMap, once with frequency "
          "buckets -- and h-index with counting sort, writing the prefix-sum pass with "
          "an explicit prevTotal snapshot. Finish with "
          "sort-colors, which is a three-bucket count you are then asked to do in one "
          "pass instead.",
},
# ==========================================================================
{
 "slug": "union-find",
 "title": "Union-Find (disjoint set union)",
 "one_line": "union() touches roots and nothing else. Write it once, correctly, and reuse it.",
 "why": "Your single most repeated implementation bug, appearing independently in three "
        "problems: number-of-islands-ii (caught), graph-valid-tree's rewrite (caught), "
        "and a post-solve rewrite of path-existence-queries-in-a-graph-i (never caught — "
        "it passed only because that problem always unions adjacent indices).",
 "summary": (
  p('Disjoint Set Union answers one question — “are these two in the same '
     'group?” — and supports one change: merge two groups. It is a forest '
     'where every element points at a parent and every group is named by its '
     'root.') +
  p('Everything correct about it follows from one rule: <code>union</code> '
     'links one <strong>root</strong> to another root. Link a non-root and '
     'the tree forks into two groups that should have been one, with no '
     'error and no symptom until a much later query returns the wrong count. '
     'That is the single most repeated implementation bug in this export.')
 ),
 "used_for": [
  ('Counting connected components as edges arrive',
   'Online. BFS or DFS would have to re-run after every edge; DSU is near- '
    'constant per edge.'),
  ("Kruskal's minimum spanning tree",
   'The cycle test is literally find(a) == find(b).'),
  ('Detecting a cycle in an undirected graph',
   'An edge whose endpoints already share a root closes a cycle.'),
  ('Equations or equivalences: a == b, b == c',
   'Equality is an equivalence relation, which is exactly the structure '
    'DSU represents.'),
  ('Grid flood-fill where cells become land over time',
   'Adding a cell is one union with each existing neighbour — the Number '
    'of Islands II shape.'),
  ('You need the actual path between two nodes',
   'Not DSU. It knows connectivity and nothing about routes.'),
 ],
 "patterns": [
  ('Return the number of connected components',
   'DSU with a counter decremented on each successful union.'),
  ('Given a list of edges, decide whether the graph is a valid tree',
   'n − 1 edges, and no union where both endpoints already share a root.'),
  ('Process queries: are a and b connected?',
   'DSU. Any traversal costs O(V + E) per query.'),
  ('Cells are added one at a time; report the count after each',
   'Incremental DSU — the classic online case.'),
  ('Redundant connection / find the edge to remove',
   'The first edge whose two endpoints already share a root.'),
  ('Accounts merge / friend circles / equivalent strings',
   'Grouping by a shared attribute is the same equivalence relation.'),
 ],
 "match": r"union|\bDSU\b|disjoint set|parent\[|union by (rank|size)|"
          r"path compression|connected component|unify|UnionFind|uf\.|root[XY]",
 "basics": [
  ("What it is",
   p("A DSU maintains a partition of <code>0..n-1</code> into disjoint sets, supporting "
     "two operations in near-constant amortised time:")
   + ul("<code>find(x)</code> — which set is x in? (returns the set's representative, "
        "its <em>root</em>)",
        "<code>union(x, y)</code> — merge the two sets containing x and y")
   + p("It is stored as a forest: <code>parent[i]</code> points at i's parent, and a root "
       "points at itself. The set's identity <em>is</em> its root — which is why every "
       "operation has to go through <code>find</code>.")),

  ("The correct implementation, in full",
   diagrams.dsu_union() +
   code("""
class DSU {
    private final int[] parent, size;
    private int components;

    DSU(int n) {
        parent = new int[n];
        size = new int[n];
        components = n;
        for (int i = 0; i < n; i++) { parent[i] = i; size[i] = 1; }
    }

    int find(int x) {                       // path compression
        if (parent[x] != x) parent[x] = find(parent[x]);
        return parent[x];
    }

    boolean union(int x, int y) {           // returns false if already together
        int rx = find(x), ry = find(y);     // ROOTS. Nothing below uses x or y.
        if (rx == ry) return false;
        if (size[rx] < size[ry]) { int t = rx; rx = ry; ry = t; }  // union by size
        parent[ry] = rx;
        size[rx] += size[ry];
        components--;
        return true;
    }

    boolean connected(int x, int y) { return find(x) == find(y); }
    int componentCount() { return components; }
}
""")
   + p("Read <code>union</code> again: after the first line, <code>x</code> and "
       "<code>y</code> are never mentioned. That is the invariant. If <code>x</code> or "
       "<code>y</code> appears below that line, the code is wrong.")),

  ("Your three instances of the same bug",
   code("""
// number-of-islands-ii — parent[y], parent[x] instead of parent[rootY], parent[rootX]
if (rank[rootX] > rank[rootY])      parent[y] = rootX;
else if (rank[rootY] > rank[rootX]) parent[x] = rootY;

// path-existence-queries-in-a-graph-i (post-solve rewrite) — same shape,
// PLUS both branches test the same condition, so the second is dead code:
if (degree[x] > degree[y])      parent[y] = x;
else if (degree[y] < degree[x]) parent[x] = y;      // never reachable
else                            { parent[x] = y; degree[y]++; }
""")
   + p("Why it sometimes passes: if you only ever union elements that are still their own "
       "roots — for example adjacent indices merged left to right — then "
       "<code>x == find(x)</code> happens to hold and the bug is invisible. Change the "
       "union order and it breaks. That is the worst kind of bug: correct-looking, "
       "test-passing, and load-bearing on an accident.")
   + p("Good news: your <em>first-accept</em> solution to that problem is textbook "
       "correct. The bug only appears in rewrites — which is where the habit of "
       "retyping DSU from memory shows up.")),

  ("Why union by size/rank matters",
   diagrams.dsu_path_compression() +
   p("Path compression alone gives O(log n) amortised. With union by size it becomes "
     "O(α(n)) — inverse Ackermann, effectively constant. Attaching the smaller tree "
     "under the larger is what keeps depth bounded; without it a chain of unions can "
     "build a path of length n.")
   + traces.path_compression()
   + p("Union by <em>size</em> is easier to get right than by rank, because "
       "<code>size</code> is meaningful on its own (it answers \"how big is this "
       "component?\") and it updates unconditionally. Rank only updates on ties, which "
       "is one more thing to forget.")),

  ("What DSU is for",
   ul("Connected components in an undirected graph, especially when edges arrive over time",
      "Cycle detection while adding edges — <code>union</code> returning false means a cycle",
      "Kruskal's minimum spanning tree",
      "Grouping by equivalence (accounts merge, string equations, redundant connections)",
      "Offline queries processed in sorted order")
   + p("What it cannot do: split a set, or handle directed reachability.")),

  ("Worked example: number-of-provinces, traced",
   p("<code>isConnected = [[1,1,0],[1,1,0],[0,0,1]]</code>. Start with three singleton "
     "sets and a counter at 3; each successful union drops it by one.")
   + traces.union_find(3, [(0, 1), (1, 0)])
   + p("Vertex 2 has no edges at all, so it never appears in the table and stays a "
       "singleton — which is the third component. Two things in that table are "
       "doing real work. The "
       "<code>rootX == rootY</code> early return is what makes the counter correct — "
       "without it the second edge decrements again and you report 1. And the counter "
       "lives in the DSU, decremented inside <code>union</code>, so it cannot drift out "
       "of sync with the structure:")
   + code("""
boolean union(int x, int y) {
    int rx = find(x), ry = find(y);
    if (rx == ry) return false;        // already together -- the count does not change
    if (size[rx] < size[ry]) { int t = rx; rx = ry; ry = t; }
    parent[ry] = rx;
    size[rx] += size[ry];
    components--;                      // exactly here, and nowhere else
    return true;
}
""")
   + p("Returning <code>boolean</code> is free and pays for itself immediately: "
       "Kruskal's algorithm, cycle detection in an undirected graph, and "
       "redundant-connection all reduce to <em>\"did this union actually do "
       "something?\"</em>")),
 ],
 "rules": [
  "After `int rx = find(x), ry = find(y);` the variables x and y must not appear again.",
  "Keep one DSU class. Paste it; do not retype it from memory.",
  "Union by size, with path compression. Both, always.",
  "Have union() return boolean — 'did this merge anything' answers cycle detection for free.",
 ],
 "drill": "Write the DSU above from scratch, then diff it against this page. Then re-solve "
          "number-of-islands-ii and graph-valid-tree using it unchanged.",
},


# ==========================================================================
{
 "slug": "graph-traversal",
 "title": "Graph traversal invariants: BFS, Dijkstra, Kahn",
 "one_line": "BFS marks visited on push. Dijkstra finalises on pop. Kahn counts incoming edges. Mixing them up is your recurring graph bug.",
 "why": "48 visited/state-tracking mistakes plus 11 edge-direction mistakes. The "
        "topological-sort confusion — which node's indegree to increment, which way the "
        "edge points — is the cleanest repeat in your whole corpus: it caused "
        "course-schedule-ii's first failure, reappeared in apply-substitutions months "
        "later, and returned a third time on a revisit to course-schedule-ii 15 months on.",
 "summary": (
  p('Three algorithms that look alike in code and differ entirely in their '
     'invariant. BFS explores in layers, so the first time you '
     '<em>reach</em> a node is already the shortest unweighted path — mark '
     'visited on push. Dijkstra explores by cheapest-so-far, so a distance '
     'is only final when you <em>pop</em> the node — mark it done there, and '
     "skip stale queue entries. Kahn's algorithm is neither: it repeatedly "
     'removes nodes with no remaining incoming edges.') +
  p('Getting the invariant from the wrong one of the three is the most '
     'repeated graph bug in this export. Say which one you are writing, out '
     'loud, before the first line.')
 ),
 "used_for": [
  ('Shortest path where every edge costs 1',
   'BFS. The layer index is the distance and no priority queue is needed.'),
  ('Shortest path with non-negative weights',
   'Dijkstra. Lazy deletion with a dist[] check is shorter than decrease- '
    'key and just as correct.'),
  ('Edges cost 0 or 1',
   '0-1 BFS with a deque: push-front on a 0 edge, push-back on a 1 edge. '
    'O(V + E).'),
  ('Ordering tasks with prerequisites',
   'Kahn. If fewer than n nodes come out, the graph has a cycle.'),
  ('Counting components, or flood fill',
   'DFS or BFS — either works, because no distance is being claimed.'),
  ('Any negative edge weight',
   'Neither: Bellman-Ford. Finalise-on-pop is exactly what a negative edge '
    'invalidates.'),
 ],
 "patterns": [
  ('Minimum number of steps / moves / transformations',
   'Unweighted shortest path — BFS, visited on push.'),
  ('Minimum time / cost, and the weights vary',
   'Dijkstra, finalised on pop.'),
  ('You must take course b before course a',
   'A directed edge b → a. Kahn, with the indegree counted on a.'),
  ('Return any valid order, or an empty array if impossible',
   'Topological sort with the “did all n come out?” cycle check.'),
  ('Rotting oranges / walls and gates / spreading from several sources',
   'Multi-source BFS — push every source before the first pop, not one BFS '
    'per source.'),
  ('Cells cost 1 to break through and 0 to walk',
   '0-1 BFS.'),
  ('Shortest path visiting a set of nodes, n ≤ 12',
   'BFS or Dijkstra over (node, bitmask) states.'),
 ],
 "match": r"visited|indegree|in-degree|edge direction|reversed edge|"
          r"dependency direction|topological|Kahn|Dijkstra|relax(ed|ation|"
          r"es)?\b|dist\[|adjacenc|adjList|\bBFS\b|\bDFS\b|shortest path|"
          r"dequeu|enqueu",
 "basics": [
  ("BFS: visited on push",
   diagrams.bfs_layers() +
   p("On an <strong>unweighted</strong> graph, the first time BFS reaches a node it has "
     "reached it by a shortest path. So marking visited at enqueue time is correct, and "
     "it is also necessary — marking at dequeue time lets a node enter the queue many "
     "times.")
   + code("""
Deque<Integer> q = new ArrayDeque<>();
boolean[] visited = new boolean[n];
q.add(src);
visited[src] = true;                      // mark when PUSHING
while (!q.isEmpty()) {
    int u = q.poll();
    for (int v : adj[u]) {
        if (!visited[v]) {
            visited[v] = true;            // here, not after the poll
            dist[v] = dist[u] + 1;
            q.add(v);
        }
    }
}
""")),

  ("Dijkstra: finalise on pop",
   diagrams.dijkstra_counterexample() +
   p("With <strong>weighted</strong> edges the first time you <em>see</em> a node is not "
     "the cheapest way to reach it. Only when it comes off the priority queue is its "
     "distance final. Marking visited at push time — which you did in "
     "<code>number-of-ways-to-arrive-at-destination</code> — locks in the first, wrong, "
     "distance.")
   + code("""
long[] dist = new long[n];
Arrays.fill(dist, Long.MAX_VALUE / 2);         // width matches the array; /2 so +w is safe
dist[src] = 0;

PriorityQueue<long[]> pq =
    new PriorityQueue<>(Comparator.comparingLong(a -> a[1]));   // not a[1] - b[1]
pq.add(new long[]{src, 0});

while (!pq.isEmpty()) {
    long[] cur = pq.poll();
    int u = (int) cur[0];
    long d = cur[1];
    if (d > dist[u]) continue;                 // stale entry — THIS is the visited check
    for (int[] e : adj[u]) {
        int v = e[0];
        long w = e[1];
        if (dist[u] + w < dist[v]) {           // relax
            dist[v] = dist[u] + w;
            pq.add(new long[]{v, dist[v]});
        }
    }
}
""")
   + p("The <code>if (d &gt; dist[u]) continue;</code> line replaces a visited array "
       "entirely — it is the lazy-deletion idiom, and it is why you never need to update "
       "a heap entry in place. Note also: <code>Long.MAX_VALUE</code>, not "
       "<code>Integer.MAX_VALUE</code>, and not <code>Long.MIN_VALUE</code> — you have "
       "written all three.")),

  ("Kahn: the direction question, answered once",
   diagrams.kahn_direction() +
   p("This is your repeat bug, so here is the rule in one sentence: "
     "<strong>an edge u → v means \"u must come before v\", so it increments "
     "<code>indegree[v]</code> — the arrow head, never the tail.</strong>")
   + code("""
// "to take course b you must first take course a"  →  edge a → b
for (int[] pre : prerequisites) {
    int a = pre[1];                 // prerequisite — the tail
    int b = pre[0];                 // dependent    — the head
    adj[a].add(b);                  // a → b
    indegree[b]++;                  // the HEAD's indegree
}

Deque<Integer> q = new ArrayDeque<>();
for (int i = 0; i < n; i++) if (indegree[i] == 0) q.add(i);   // ALL zero-indegree nodes

List<Integer> order = new ArrayList<>();
while (!q.isEmpty()) {
    int u = q.poll();
    order.add(u);
    for (int v : adj[u]) {
        if (--indegree[v] == 0) q.add(v);
    }
}
return order.size() == n ? order : new int[0];   // short means a cycle
""")
   + p("Two things you have got wrong separately, both visible above:")
   + ul("<strong>Which node's indegree.</strong> The head. Say the sentence out loud — "
        "\"a before b\" — and the head is the second one you name.",
        "<strong>The starting set.</strong> <em>Every</em> node with indegree 0, not just "
        "node 0 and not just the first one found. A DAG can have many roots.")
   + p("Before writing any Kahn's BFS, write this comment first: "
       "<code>// edge a -&gt; b means a before b; indegree[b]++</code>. It costs three "
       "seconds and it is the bug.")),

  ("Choosing between them",
   table(("Situation", "Algorithm", "Cost"), [
       ("Unweighted shortest path", "BFS", "O(V + E)"),
       ("Weights 0 or 1", "0-1 BFS (deque, push-front on 0)", "O(V + E)"),
       ("Non-negative weights", "Dijkstra", "O(E log V)"),
       ("Negative weights", "Bellman–Ford", "O(VE)"),
       ("All pairs, small V", "Floyd–Warshall", "O(V³)"),
       ("Ordering under dependencies", "Kahn / DFS topological sort", "O(V + E)"),
       ("Connectivity only, edges arriving", "DSU", "O(α(n))"),
   ])),

  ("Worked example: 0-1 BFS, the case between BFS and Dijkstra",
   p("When every edge weight is 0 or 1 you do not need a priority queue. A deque is "
     "enough: a 0-edge goes on the front, a 1-edge on the back, and the deque stays "
     "sorted by distance on its own. O(V + E) instead of O(E log V).")
   + code("""
Deque<Integer> dq = new ArrayDeque<>();
int[] dist = new int[n];
Arrays.fill(dist, Integer.MAX_VALUE);
dist[src] = 0;
dq.add(src);
while (!dq.isEmpty()) {
    int u = dq.pollFirst();
    for (int[] e : adj[u]) {
        int v = e[0], w = e[1];
        if (dist[u] + w < dist[v]) {
            dist[v] = dist[u] + w;
            if (w == 0) dq.addFirst(v); else dq.addLast(v);
        }
    }
}
""")
   + p("This is the right structure for minimum-obstacle-removal and "
       "minimum-cost-to-make-at-least-one-valid-path-in-a-grid — grid problems where "
       "moving costs nothing and changing something costs one.")
   + p("Note that it is still <em>relax-on-improve</em>, not mark-on-push. The pattern "
       "generalises: the only algorithm in this family that may mark on push is plain "
       "BFS, and only because every edge there has the same weight.")),

  ("The decision, as a table",
   table(("Situation", "Structure", "Marked when"), [
       ("Unweighted, shortest path or level order", "queue", "on push"),
       ("Weights 0 or 1", "deque", "on improvement"),
       ("Non-negative weights", "priority queue", "on pop"),
       ("Negative weights", "Bellman–Ford, V−1 rounds", "n/a — relax all edges"),
       ("Negative weights, all pairs", "Floyd–Warshall, O(V³)", "n/a"),
       ("Ordering under prerequisites", "queue of indegree-0 nodes", "on push"),
       ("Any reachability, no distance", "stack or recursion", "on push"),
   ])
   + p("Pick the row <em>before</em> you write the loop. Every one of your graph Wrong "
       "Answers in this export is a case of running the code from one row against a "
       "problem from another.")),
 ],
 "rules": [
  "BFS: mark visited when pushing. Dijkstra: skip stale entries when popping.",
  "Dijkstra's 'visited' is `if (d > dist[u]) continue;` — not a boolean array.",
  "Write `// edge a -> b means a before b; indegree[b]++` before any Kahn's BFS.",
  "Seed the topological queue with EVERY zero-indegree node.",
  "dist[] init: Long.MAX_VALUE / 2, matching the array's width.",
 ],
 "drill": "Re-solve course-schedule-ii cold. You have got the same edge-direction bug "
          "three times on it across 15 months — that is the definition of an "
          "un-internalised invariant.",
},


# ==========================================================================
{
 "slug": "range-structures",
 "title": "Fenwick trees and segment trees",
 "one_line": "A BIT is not your array. Everything goes in through add(); nothing is assigned into the backing store.",
 "why": "binary-indexed-tree is your weakest topic at an 11% first-attempt rate — 23 Wrong "
        "Answers against 9 Accepts over 9 problems — and segment-tree is second-worst at "
        "29% with the lowest self-solve rate of any substantial topic. Both are also "
        "topics where you reach for the structure only after a brute force has already "
        "failed.",
 "summary": (
  p('Both structures answer “aggregate over a range” while the data keeps '
     'changing. A Fenwick tree (BIT) stores overlapping partial sums so that '
     'both update and prefix query cost O(log n) — but the array it holds is '
     '<strong>not</strong> your data, so nothing is ever assigned into it. '
     'Everything goes in through <code>add(i, delta)</code>.') +
  p('A segment tree stores an explicit tree of range aggregates. It costs '
     'more memory and more code, and buys you any associative merge — min, '
     'max, gcd, “count of ones” — plus lazy range updates.')
 ),
 "used_for": [
  ('Prefix sums that have to survive updates',
   'Rebuilding a prefix array is O(n) per update; a BIT is O(log n).'),
  ('Counting inversions, or “how many smaller to the right”',
   'Coordinate-compress the values, then sweep with a BIT of counts.'),
  ('Range minimum or maximum with updates',
   'Segment tree. A BIT cannot handle a min that decreases.'),
  ('Range assign or range add over many queries',
   'Segment tree with lazy propagation.'),
  ('A static array with no updates at all',
   'Neither. A prefix-sum array, or a sparse table for min/max. Do not '
    'build a tree you never update.'),
  ('Values up to 10⁹ but only 10⁵ of them',
   'Coordinate compression first: the structure is sized by the number of '
    'distinct values, not the value range.'),
 ],
 "patterns": [
  ('Query the sum of a subarray and update elements, 10⁵ of each',
   'Fenwick tree.'),
  ('Count of smaller numbers after self / count inversions',
   'A BIT over compressed values, swept from the right.'),
  ('Range minimum query with point updates',
   'Segment tree whose merge is Math.min.'),
  ('Add v to every element in [l, r], then query',
   'Segment tree with lazy — or a difference array if every update '
    'precedes every query.'),
  ('Number of ranges covering each point',
   'Difference array for small coordinates, event sweep otherwise.'),
  ('Find the k-th smallest element under insertions and deletions',
   'A BIT over value counts, descended in O(log n).'),
 ],
 "match": r"[Ff]enwick|\bBIT\b|binary indexed|segment tree|lazy propagat|"
          r"sparse table|tree\[|merge (step|guard|function|is)|"
          r"prefix sum (array|tree)|range (sum|min|max) quer",
 "basics": [
  ("When you need one at all",
   p("You need a range structure when <em>both</em> hold: queries ask about a range, "
     "<em>and</em> the data changes between queries. If the data is static, a prefix-sum "
     "array is O(1) per query and takes three lines. Reaching for a segment tree on "
     "static data is a common way to lose time.")
   + table(("Updates?", "Query", "Use"), [
       ("none", "range sum", "prefix sums — <code>pre[r+1] - pre[l]</code>"),
       ("none", "range min/max", "sparse table, O(1) query"),
       ("point", "prefix/range sum", "<strong>Fenwick (BIT)</strong> — smallest code"),
       ("point", "range min/max/gcd/any monoid", "<strong>segment tree</strong>"),
       ("range", "range anything", "segment tree with lazy propagation"),
       ("point", "k-th element / order statistic", "BIT over values"),
   ])),

  ("Fenwick tree: what the array holds",
   diagrams.bit_coverage() +
   p("This is the misconception behind your <code>shortest-path-in-a-weighted-tree</code> "
     "bug, where you wrote <code>tree = dist</code> — assigning the value array straight "
     "into the BIT's backing store.")
   + p("<code>tree[i]</code> does <strong>not</strong> hold <code>a[i]</code>. It holds "
       "the sum of a block of length <code>i &amp; -i</code> ending at <code>i</code>. "
       "The array is an encoding, not the data:")
   + code("""
i (1-based)   1     2     3     4     5     6     7     8
i & -i        1     2     1     4     1     2     1     8
tree[i] =    a1  a1+a2   a3  a1..a4   a5  a5+a6   a7  a1..a8
""", compiles=False)
   + p("So there is exactly one way to put data in — call <code>add()</code> for each "
       "element — and assigning into <code>tree</code> directly produces a structure "
       "whose invariant never held.")
   + code("""
class BIT {
    private final long[] tree;         // 1-indexed; tree[0] unused
    private final int n;

    BIT(int n) { this.n = n; this.tree = new long[n + 1]; }

    void add(int i, long delta) {      // i is 0-based on the outside
        for (i++; i <= n; i += i & -i) tree[i] += delta;
    }

    long prefix(int i) {               // sum of a[0..i], 0-based inclusive
        long s = 0;
        for (i++; i > 0; i -= i & -i) s += tree[i];
        return s;
    }

    long range(int l, int r) { return prefix(r) - prefix(l - 1); }
}

// building from an array: through add(), the only door in
BIT bit = new BIT(a.length);
for (int i = 0; i < a.length; i++) bit.add(i, a[i]);
""")
   + p("<code>i &amp; -i</code> isolates the lowest set bit. <code>add</code> walks up "
       "adding it; <code>prefix</code> walks down subtracting it. That is the entire "
       "data structure.")),

  ("Size it from the data",
   p("In <code>block-placement-queries</code> you allocated a fixed oversized tree and hit "
     "a TLE, then \"fixed\" it once by stripping whitespace before the real fix — dynamic "
     "sizing — landed. A BIT's cost is O(log n) where n is its <em>allocated</em> size, "
     "not the number of live elements. An oversized tree is slower for no benefit. Size "
     "it from the input.")),

  ("Segment tree: the merge is the whole thing",
   diagrams.segment_tree_shape() +
   p("A segment tree stores an answer for each node's interval and combines children with "
     "a <code>merge</code>. <code>merge</code> must be <strong>associative</strong> and "
     "have an <strong>identity</strong> — that is the only requirement, and it is why the "
     "same tree does sum, min, max, gcd, or 'longest run of ones'.")
   + code("""
class SegTree {
    private final int n;
    private final long[] t;

    SegTree(long[] a) {
        n = a.length;
        t = new long[2 * n];                       // iterative, bottom-up
        System.arraycopy(a, 0, t, n, n);
        for (int i = n - 1; i > 0; i--) t[i] = merge(t[2 * i], t[2 * i + 1]);
    }

    private long merge(long x, long y) { return Math.max(x, y); }   // any monoid
    private long identity() { return Long.MIN_VALUE; }

    void set(int i, long v) {
        for (t[i += n] = v; i > 1; i >>= 1) t[i >> 1] = merge(t[i], t[i ^ 1]);
    }

    long query(int l, int r) {                     // [l, r) half-open
        long res = identity();
        for (l += n, r += n; l < r; l >>= 1, r >>= 1) {
            if ((l & 1) != 0) res = merge(res, t[l++]);
            if ((r & 1) != 0) res = merge(res, t[--r]);
        }
        return res;
    }
}
""")
   + p("Your merge bugs are all in the same place. In "
       "<code>maximize-active-section-with-trade-ii</code> the merge guard used "
       "<code>||</code> where <code>&amp;&amp;</code> was needed. A merge that is wrong "
       "on two adjacent singletons is wrong everywhere, and it is trivial to check: "
       "build a 2-element tree by hand and verify the root.")
   + p("Note the half-open <code>[l, r)</code> convention — the same one as binary search. "
       "Using one convention everywhere removes a whole class of off-by-one. Your "
       "<code>range-module</code> bug was exactly an inclusive/exclusive mismatch against "
       "<code>subSet()</code>.")),

  ("Worked example: count-of-smaller-numbers-after-self",
   p("This is the problem that turns a BIT from \"a range-sum gadget\" into a general "
     "counting tool, and it is worth tracing because the array being indexed is not the "
     "input array at all — it is <em>value space</em>.")
   + p("<code>nums = [5, 2, 6, 1]</code>. Walk right to left; for each value, ask how "
       "many values strictly smaller have already been inserted, then insert it. "
       "Coordinate-compress first so values become ranks <code>1..4</code>: "
       "<code>1→1, 2→2, 5→3, 6→4</code>.")
   + table(("i", "nums[i]", "rank", "query(rank − 1)", "result", "then"), [
       ("3", "1", "1", "sum of ranks ≤ 0", "0", "<code>add(1, 1)</code>"),
       ("2", "6", "4", "sum of ranks ≤ 3", "1", "<code>add(4, 1)</code>"),
       ("1", "2", "2", "sum of ranks ≤ 1", "1", "<code>add(2, 1)</code>"),
       ("0", "5", "3", "sum of ranks ≤ 2", "2", "<code>add(3, 1)</code>"),
   ])
   + p("Reversed, the results are <code>[2, 1, 1, 0]</code>. The BIT never held "
       "<code>nums</code>; it held a histogram over ranks, and <code>query(r)</code> "
       "answered \"how many inserted values have rank ≤ r\". Sizing it comes from the "
       "number of <em>distinct values</em>, not from <code>nums.length</code> and "
       "certainly not from a guessed constant.")
   + p("Three ideas travel together here and are worth naming, because they recur: "
       "<strong>coordinate compression</strong> (values → dense ranks), <strong>BIT "
       "over value space</strong> (counting, not summing), and <strong>processing in "
       "an order that makes the question one-sided</strong> (right to left, so "
       "\"already inserted\" means \"to the right of me\").")),
 ],
 "rules": [
  "Data enters a BIT only through add(). Never assign into the backing array.",
  "Size the tree from the input length, not a guessed constant.",
  "BIT is 1-indexed internally. Convert at the boundary and nowhere else.",
  "Test merge() on a 2-element tree by hand before trusting the whole structure.",
  "Pick half-open [l, r) and use it in every range structure you write.",
 ],
 "drill": "Write the BIT above from scratch and solve range-sum-query-mutable with it. "
          "Then re-solve shortest-path-in-a-weighted-tree — the one where you assigned "
          "into the backing array.",
},


# ==========================================================================
{
 "slug": "windows",
 "title": "Sliding windows and two pointers",
 "one_line": "Write the invariant as a sentence. The shrink condition is a `while`, not an `if`.",
 "why": "44 window and two-pointer invariant mistakes across 22 topics, and two-pointers "
        "is a 98-problem topic sitting at a 49% first-attempt rate. The failures are "
        "almost never the idea — they are the moment the window stops being valid.",
 "summary": (
  p('A sliding window holds a contiguous range <code>[l, r]</code> plus an '
     'invariant about its contents — “no repeated character”, “at most k '
     'zeros”, “sum ≤ target”. You extend <code>r</code> unconditionally, and '
     'whenever the invariant breaks you shrink from <code>l</code> until it '
     'holds again.') +
  p('Because neither pointer ever moves backwards, the whole scan is O(n) '
     'even though it reads like a nested loop. The shrink has to be a '
     '<code>while</code> and not an <code>if</code>: one step of extension '
     "can break the invariant by more than one step's worth.")
 ),
 "used_for": [
  ('Longest or shortest contiguous subarray satisfying a property',
   'The property has to be monotone under shrinking — that is what makes a '
    'window valid at all.'),
  ('Fixed-size window statistics',
   'Add the element entering, remove the one leaving. There is no inner '
    'loop.'),
  ('Counting subarrays with at most k of something',
   'atMost(k) − atMost(k−1) turns “exactly k” into two window scans.'),
  ('A sorted array and a target pair or triple',
   'Two pointers from both ends — same discipline, opposite directions.'),
  ('Anagram or permutation substring search',
   'A 26-slot count array plus a match counter makes each step O(1).'),
  ('The array contains negatives and you want a subarray sum',
   'A window will not work: shrinking no longer reduces the sum. Prefix '
    'sums plus a HashMap instead.'),
 ],
 "patterns": [
  ('Longest substring without repeating characters',
   'Variable window; shrink until the duplicate leaves.'),
  ('Contiguous / consecutive / substring',
   'The word “contiguous” is the window signal. “Subsequence” is not.'),
  ('At most k replacements / no more than k zeros',
   'Window over the count of violations.'),
  ("Find all start indices of p's anagrams in s",
   'Fixed-size window with a frequency match count.'),
  ('Two sum on a sorted array',
   'Two pointers from both ends, O(1) extra space.'),
  ('Minimum window substring containing all of t',
   'Variable window with a “how many required characters are satisfied” '
    'counter.'),
  ('Subarray sum equals k, values may be negative',
   'Not a window. Prefix sum with a count map.'),
 ],
 "match": r"sliding window|window (invariant|is|was|size|bound)|only window|"
          r"two.pointer|left pointer|right pointer|shrink|expand the|"
          r"prefix sum|left\+\+|right\+\+",
 "basics": [
  ("The shape",
   diagrams.sliding_window() +
   p("A sliding window maintains a range <code>[left, right]</code> that always satisfies "
     "some property. <code>right</code> advances once per iteration; <code>left</code> "
     "advances only enough to restore the property. Each index enters and leaves once, so "
     "the whole thing is O(n) despite the nested loop.")
   + code("""
int left = 0;
for (int right = 0; right < n; right++) {
    add(nums[right]);                       // extend

    while (!valid()) {                      // WHILE, not IF —
        remove(nums[left++]);               // one removal may not be enough
    }

    best = Math.max(best, right - left + 1);   // window is valid here
}
""")
   + p("Three things decide correctness, and you should write all three down before "
       "coding:")
   + ul("<strong>The invariant</strong> — one sentence: \"the window contains at most k "
        "distinct characters\".",
        "<strong>The shrink condition</strong> — the negation of the invariant. It is a "
        "<code>while</code>, because one removal may not restore it.",
        "<strong>Where you record the answer</strong> — after the shrink loop, when the "
        "window is known valid. Recording inside the loop measures an invalid window.")),

  ("Fixed size versus variable size",
   code("""
// FIXED window of size k — no shrink loop, just evict one when full
for (int i = 0; i < n; i++) {
    add(nums[i]);
    if (i >= k) remove(nums[i - k]);        // i - k, not i - k + 1
    if (i >= k - 1) best = Math.max(best, current);
}
""")
   + p("The two off-by-ones here are the eviction index (<code>i - k</code>) and the first "
       "index at which a full window exists (<code>k - 1</code>). Derive both from a "
       "concrete small case — k = 2, i = 1 — rather than adjusting until the tests pass.")),

  ("Two pointers from both ends",
   p("A different pattern with a different invariant: <code>left</code> and "
     "<code>right</code> start at opposite ends and move toward each other, and you must "
     "be able to argue that moving one of them can never skip the answer.")
   + code("""
int l = 0, r = n - 1;
while (l < r) {
    int sum = nums[l] + nums[r];
    if (sum == target) return new int[]{l, r};
    if (sum < target) l++;        // nums[l] is too small with EVERY remaining r
    else r--;                     // nums[r] is too large with EVERY remaining l
}
""")
   + p("The comments are the proof, and they only hold because the array is sorted. If "
       "you cannot write that justification, the pattern does not apply.")),

  ("When a window will not work",
   diagrams.window_negatives() +
   p("Sliding window needs the property to be <strong>monotone in the window</strong>: "
     "extending can only break it, shrinking can only fix it. \"At most k distinct\" is "
     "monotone. \"Sum equals exactly k\" with negative numbers is not — shrinking can "
     "make the sum go either way, so no shrink loop can be correct. Use a prefix-sum "
     "plus hash map instead:")
   + code("""
// count subarrays with sum == k, negatives allowed
Map<Long, Integer> seen = new HashMap<>();
seen.put(0L, 1);                              // the empty prefix
long sum = 0; int count = 0;
for (int x : nums) {
    sum += x;
    count += seen.getOrDefault(sum - k, 0);
    seen.merge(sum, 1, Integer::sum);
}
""")
   + p("The <code>seen.put(0L, 1)</code> is the identity case — a prefix that is itself "
       "the answer. Forgetting it is the standard bug in this template, and it is the "
       "same identity-element issue as the sentinel lesson.")),

  ("Worked example: longest substring without repeating characters",
   p("Invariant, as a sentence: <em>the window contains no repeated character</em>. "
     "Input <code>\"abcabcbb\"</code>. <code>last</code> maps a character to the last "
     "index it was seen at.")
   + traces.sliding_window("abcabcbb")
   + p("The one subtlety, and it is the bug people hit: <code>L</code> must move "
       "<em>forward only</em>. If the last sighting of the character is already left of "
       "<code>L</code>, it is not in the window and <code>L</code> must not move "
       "backwards to it:")
   + code("""
int L = 0, best = 0;
Map<Character, Integer> last = new HashMap<>();
for (int R = 0; R < s.length(); R++) {
    char c = s.charAt(R);
    if (last.containsKey(c)) {
        L = Math.max(L, last.get(c) + 1);   // max(), not assignment
    }
    last.put(c, R);
    best = Math.max(best, R - L + 1);
}
""")
   + p("Drop the <code>Math.max</code> and <code>\"abba\"</code> fails: at "
       "<code>R = 3</code> the character <code>'a'</code> was last seen at index 0, "
       "<code>L</code> jumps back to 1, and the window silently readmits the "
       "<code>'b'</code> it had already evicted.")),
 ],
 "rules": [
  "Write the invariant as one sentence before writing the loop.",
  "The shrink is a while, never an if.",
  "Record the answer after the shrink loop, where the window is valid.",
  "Negative values? The window is probably not monotone — use prefix sums plus a map.",
  "Seed prefix-sum maps with {0: 1}.",
 ],
 "drill": "Take three window problems you solved and, without looking, write only the "
          "invariant sentence for each. If you cannot, you pattern-matched rather than "
          "reasoned.",
},


# ==========================================================================
{
 "slug": "recursion",
 "title": "Recursion, base cases and backtracking",
 "one_line": "Every path returns. Every mutation is undone. Memo keys include everything the answer depends on.",
 "why": "recursion sits at a 37% first-attempt rate over 27 problems, with 37 Wrong "
        "Answers against 27 Accepts — and 22 logged mistakes are specifically missing "
        "base cases, missing returns, or un-restored state.",
 "summary": (
  p('A recursive function is a contract: given a smaller input, it returns '
     'the right answer. Three things make the contract hold — a base case '
     'that returns without recursing, a step that strictly shrinks the '
     'input, and a <code>return</code> on <em>every</em> path. A branch that '
     'falls through without returning produces a silently wrong value, not a '
     'compile error.') +
  p('Backtracking adds a fourth requirement: every mutation made before the '
     'recursive call is undone after it, exactly and in reverse order. '
     'Memoisation adds a fifth: the key has to contain everything the answer '
     'depends on, or you will read back an answer computed under different '
     'conditions.')
 ),
 "used_for": [
  ('Trees, and anything shaped like a tree',
   'The structure is recursive, so the code is a three-line match on the '
    'structure.'),
  ('Enumerating subsets, permutations or combinations',
   'Choose, recurse, un-choose. n ≤ about 20 for subsets, n ≤ about 10 for '
    'permutations.'),
  ('Divide and conquer — merge sort, quickselect, sorted-array-to-BST',
   'Split, solve both halves, combine. The combine step is where the '
    'algorithm actually lives.'),
  ('A recurrence you can state but cannot yet order into loops',
   'Write the memoised recursion first. The bottom-up loop order can come '
    'later, or never.'),
  ('A chain of 10⁵ nodes',
   'Do not recurse. The default JVM stack overflows somewhere around 10⁴ '
    'frames.'),
 ],
 "patterns": [
  ('Return all possible combinations / all valid …',
   'Backtracking. The size of the output is the complexity.'),
  ('n ≤ 20, enumerate or count the subsets',
   '2ⁿ recursion, or bitmask DP if subproblems repeat.'),
  ('Given the root of a binary tree',
   'Recursion with the null child as the base case.'),
  ('Generate parentheses / word search / N-queens',
   'Backtracking with a pruning condition — the pruning is the difference '
    'between Accepted and TLE.'),
  ('The list can have up to 10⁵ nodes',
   'Iterate. Recursion depth is a constraint you can read off the '
    'statement.'),
  ('Return the k-th permutation / combination',
   'Do not enumerate. Count how many each prefix covers and skip whole '
    'blocks.'),
 ],
 "match": r"recursion|recursive|base case|missing return|backtrack|memo(is|iz)|"
          r"memoi|StackOverflow|stack overflow|undo|restore.*(state|path)|"
          r"helper recurs",
 "basics": [
  ("The three questions",
   p("Before writing a recursive function, answer these in a comment. Every recursion bug "
     "you have logged is one of them left unanswered:")
   + ul("<strong>What does one call return?</strong> Say it precisely: \"the max path sum "
        "starting at this node and going down one side\" — not \"the answer for this "
        "node\".",
        "<strong>When does it stop?</strong> The base case, and every way of reaching it "
        "(null, empty, index past the end, budget exhausted).",
        "<strong>How do children combine?</strong> The one line that builds this call's "
        "answer from the recursive results.")),

  ("Every path returns",
   diagrams.record_vs_return() +
   code("""
// missing return on one branch: Java catches this at compile time,
// but the equivalent logical hole — a branch that returns a default —
// is silent
int dfs(TreeNode node) {
    if (node == null) return 0;              // base case FIRST
    int left  = Math.max(0, dfs(node.left));  // clamp: a negative branch is
    int right = Math.max(0, dfs(node.right)); // worth skipping entirely
    best = Math.max(best, node.val + left + right);   // record the through-path
    return node.val + Math.max(left, right);          // return the down-path
}
""")
   + p("Note the two different values: what you <em>record</em> (a path through this node, "
       "using both children) and what you <em>return</em> (a path that can extend upward, "
       "so only one child). Conflating them is the classic error on this problem shape, "
       "and it is why question one above has to be answered precisely.")),

  ("Backtracking: undo exactly what you did",
   diagrams.backtracking_tree() +
   code("""
void backtrack(int start, List<Integer> path) {
    if (isComplete(path)) { results.add(new ArrayList<>(path)); return; }
    //                                  ^^^^^^^^^^^^^^^^^^^^^ COPY, or every
    //                                  result aliases the same mutating list
    for (int i = start; i < n; i++) {
        if (!allowed(i)) continue;
        path.add(nums[i]);           // do
        used[i] = true;              // do  — every mutation
        backtrack(i + 1, path);      // recurse
        used[i] = false;             // undo — in reverse order
        path.remove(path.size() - 1);// undo
    }
}
""")
   + p("Two rules: <strong>copy on collect</strong> (the path keeps mutating after you "
       "store it), and <strong>undo every mutation</strong>, in reverse order, "
       "immediately after the recursive call. If you mutate three things and undo two, "
       "the bug appears many branches later and looks unrelated to the cause.")),

  ("Memoisation: the key is the state",
   p("A memo key must contain <em>everything</em> the return value depends on. If the "
     "answer depends on <code>(index, remaining, lastChoice)</code> and you key on "
     "<code>index</code> alone, you will return an answer computed under different "
     "conditions — and it will be right on small tests.")
   + code("""
// key on the FULL state
Map<Long, Integer> memo = new HashMap<>();
long key = ((long) i << 20) | (remaining << 4) | lastChoice;

// or, when the dimensions are small and known, an array — faster and clearer
int[][] memo = new int[n][k + 1];
for (int[] row : memo) Arrays.fill(row, -1);      // -1 = "not computed"
""")
   + p("That <code>-1</code> is a sentinel, and it needs the same scrutiny as any other: "
       "if <code>-1</code> is a legitimate answer, use a separate "
       "<code>boolean[][] computed</code> instead.")),

  ("Recursion depth",
   p("The JVM's default stack handles roughly 10<sup>4</sup> frames. A linked list or a "
     "path-shaped tree of 10<sup>5</sup> nodes will overflow it. If <code>n</code> can "
     "reach 10<sup>5</sup> and the recursion is linear in <code>n</code>, convert to an "
     "explicit stack, or to iteration, before you submit — not after the "
     "StackOverflowError.")),
 ],
 "rules": [
  "Write the three questions as a comment before the function body.",
  "Base case first, and cover every way of reaching it.",
  "Backtracking: copy on collect; undo every mutation in reverse order.",
  "The memo key contains every variable the answer depends on.",
  "Linear recursion with n up to 10⁵ → use an explicit stack.",
 ],
 "drill": "Re-solve binary-tree-maximum-path-sum and word-search-ii cold. Between them "
          "they cover the record-vs-return distinction, the negative-value base case, and "
          "backtracking restore.",
},


# ==========================================================================
{
 "slug": "dynamic-programming",
 "title": "Dynamic programming: state, transition, order",
 "one_line": "Every DP is three decisions. Name the state as a sentence, derive the "
             "transition from it, and let the dependency direction dictate the loop order.",
 "why": "dynamic-programming is your largest weak topic by a wide margin: 151 problems "
        "at a 42% first-attempt rate. It is not one skill — it is a dozen recurring "
        "shapes, and your history shows the same failure across all of them. You reach "
        "for a recurrence before you have written down what a state means, so the "
        "transition is guessed rather than derived, and the loop order is then adjusted "
        "until the samples pass. This lesson covers every shape that appears in your "
        "export, and the debugging procedure for when one is wrong.",
 "summary": (
  p('A DP is three decisions, and they are always made in this order. '
     '<strong>State</strong>: what does <code>dp[i][j]</code> mean, written '
     'as a complete English sentence. <strong>Transition</strong>: given '
     'that sentence, what does the value depend on. <strong>Order</strong>: '
     'iterate so that everything a cell reads has already been computed.') +
  p('If you cannot say the sentence, you cannot derive the transition, and '
     'the loop order becomes something you adjust until the samples pass. '
     'That is the failure this export shows on every DP topic at once. The '
     'thirteen shapes below are not thirteen algorithms — they are thirteen '
     'answers to “what goes in the state”.')
 ),
 "used_for": [
  ('Overlapping subproblems and optimal substructure',
   'The two preconditions. Without overlap use plain recursion; without '
    'optimal substructure DP is wrong, not merely slow.'),
  ('Counting the number of ways',
   'Almost always DP, and almost always under a modulus.'),
  ('Optimising a value over a chain of sequential choices',
   'Max or min over decisions — knapsack, house robber, stock trading, '
    'jump games.'),
  ('Greedy looks right but you cannot prove it',
   'DP is the safe version of a greedy you have not justified. Slower and '
    'correct beats fast and wrong.'),
  ('n ≤ 20 and the state is “which items are used”',
   'Bitmask DP — the subset itself is the state.'),
  ('A range that splits at a pivot',
   'Interval DP, iterated by increasing length so both halves exist first.'),
  ('Every subproblem is used exactly once',
   'Not DP. There is nothing to memoise; write the recursion.'),
 ],
 "patterns": [
  ('In how many ways …, modulo 10⁹ + 7',
   'Counting DP. The loop nesting decides combinations versus '
    'permutations.'),
  ('Maximum / minimum cost with sequential choices',
   'Linear or state-machine DP.'),
  ('You may complete at most k transactions',
   'State-machine DP with k as an extra dimension.'),
  ('Each item may be used at most once',
   '0/1 knapsack — the capacity loop runs descending.'),
  ('You have an infinite supply of each coin',
   'Unbounded knapsack — the capacity loop runs ascending.'),
  ('Longest common … / edit distance / interleaving',
   'Two-sequence DP over an (i, j) table.'),
  ('Longest palindromic subsequence / burst balloons / matrix chain',
   'Interval DP by increasing length.'),
  ('n ≤ 15…20 and “assign every task to someone”',
   'Bitmask DP over the set already assigned.'),
  ('Count the numbers in [1, N] with a digit property',
   'Digit DP with a tight flag.'),
  ('Two players play optimally',
   "Game-theory DP: your best move minimises the opponent's best reply."),
  ('Expected number of … / probability that …',
   'Probability DP. The transitions are weighted sums, not maxima.'),
 ],
 "match": r"\bdp\[|\bDP\b|dynamic programming|recurrence|state (definition|design|was|"
          r"space|transition)|(dp|state|recurrence) transition|transition (function|"
          r"is|was|takes|reads|used|misses)|subproblem|bottom[- ]up|top[- ]down|tabulat|"
          r"knapsack|\bLIS\b|longest (increasing|common)|kadane|memo\w* (key|state|"
          r"dimension)|rolling array|base case of the dp",
 "basics": [

  ("The three questions, before any code",
   p("A dynamic program is a recursion whose subproblems repeat, plus a table so each "
     "one is solved once. That is the whole idea. Everything difficult about DP is in "
     "three decisions you make <em>before</em> writing the recurrence, and in your "
     "history the failures are almost always in the first one:")
   + table(("Question", "What a good answer looks like"), [
       ("<strong>1. What is a state?</strong>",
        "A complete English sentence with every index bound. "
        "<em>\"dp[i][j] is the length of the longest common subsequence of the first i "
        "characters of a and the first j of b.\"</em> If you cannot finish the "
        "sentence, you do not have a state yet."),
       ("<strong>2. What is the transition?</strong>",
        "How dp[state] is built from strictly <em>smaller</em> states. This should "
        "follow from the sentence, not from pattern-matching another problem."),
       ("<strong>3. What order fills the table?</strong>",
        "Any order in which every state's dependencies are already computed. Read the "
        "arrows in the transition and the order is forced."),
   ])
   + p("The single highest-value habit in this lesson: <strong>write question 1's "
       "sentence in a comment above the array declaration.</strong> A state you can "
       "state precisely almost always has an obvious transition. A transition you are "
       "guessing at is a sign the state is underspecified — usually because it is "
       "missing a dimension.")
   + p("<strong>The missing-dimension test.</strong> Ask: <em>could two different "
       "situations map to the same state but have different answers?</em> If yes, the "
       "state is missing a dimension. Holding a stock or not, transactions used so far, "
       "whether the previous element was taken, remainder mod k, whose turn it is — "
       "each of those is a dimension that problems forget, and each produces a DP that "
       "is subtly, quietly wrong.")),

  ("Top-down or bottom-up: pick either, but know the trade",
   p("These are the same algorithm. Top-down is a recursion with a cache; bottom-up "
     "fills a table in dependency order.")
   + code("""
String a, b;                    // the two sequences, held once
Integer[][] memo;

// top-down: the recurrence is literally the code
int solve(int i, int j) {
    if (i == 0 || j == 0) return 0;                  // base case
    if (memo[i][j] != null) return memo[i][j];       // cache hit
    int best = a.charAt(i-1) == b.charAt(j-1)
             ? solve(i-1, j-1) + 1
             : Math.max(solve(i-1, j), solve(i, j-1));
    return memo[i][j] = best;
}

// bottom-up: same recurrence, explicit order, no stack
int bottomUp() {
    int n = a.length(), m = b.length();
    int[][] dp = new int[n + 1][m + 1];
    for (int i = 1; i <= n; i++)
        for (int j = 1; j <= m; j++)
            dp[i][j] = a.charAt(i-1) == b.charAt(j-1)
                     ? dp[i-1][j-1] + 1
                     : Math.max(dp[i-1][j], dp[i][j-1]);
    return dp[n][m];
}
""")
   + table(("", "Top-down", "Bottom-up"), [
       ("Order", "handled for you by the call stack", "you must derive it"),
       ("States visited", "only reachable ones", "all of them"),
       ("Risk", "StackOverflowError at depth ~10⁴", "wrong loop order, silently"),
       ("Space optimisation", "hard", "easy — rolling arrays"),
       ("Best for", "unclear order, sparse states, first draft", "tight memory, deep recursion"),
   ])
   + p("Practical advice given your history: <strong>write it top-down first.</strong> "
       "It forces you to state the recurrence and it cannot have a loop-order bug. "
       "Convert to bottom-up only when you need the space or hit the stack depth. Two "
       "cache gotchas: use <code>Integer[]</code> (null = not computed) rather than "
       "<code>int[]</code> filled with <code>-1</code> when <code>-1</code> is a legal "
       "answer, and make sure the memo key contains <em>every</em> parameter the answer "
       "depends on.")),

  ("Shape 1 — linear DP over one index",
   p("State: <em>dp[i] = the answer for the prefix ending at (or before) i.</em> The "
     "simplest shape and the one everything else generalises.")
   + code("""
// house-robber: dp[i] = most money from houses 0..i
dp[i] = Math.max(dp[i-1],            // skip house i
                 dp[i-2] + nums[i]); // take it, so i-1 is off limits

// climbing-stairs / decode-ways: dp[i] = ways to reach i
dp[i] = dp[i-1] + dp[i-2];

// word-break: dp[i] = can s[0..i) be segmented?
for (int j = 0; j < i; j++)
    if (dp[j] && dict.contains(s.substring(j, i))) { dp[i] = true; break; }
""")
   + p("Only two of these are O(n) — <code>word-break</code> is O(n²) because its "
       "transition scans every split point. Recognising which of the two you have is "
       "the complexity budget question from [[complexity-budget]] applied to DP: <em>how many states "
       "× how much work per state</em>.")
   + p("<strong>Kadane's algorithm is this shape at its most degenerate.</strong> "
       "<code>dp[i] = max subarray sum ending exactly at i</code>, which is "
       "<code>max(nums[i], dp[i-1] + nums[i])</code>, and since only <code>dp[i-1]</code> "
       "is ever read it collapses to two variables. Note the state says <em>ending "
       "exactly at i</em> — that is the sentence that makes the recurrence work, and "
       "\"the best subarray in the first i\" would not.")),

  ("Shape 2 — knapsack: the loop direction is the whole difference",
   diagrams.knapsack_loop_direction() +
   p("The knapsack family is one recurrence with four presentations. State: "
     "<em>dp[w] = the best value achievable with capacity exactly w (or at most w).</em>")
   + table(("Variant", "Question", "Inner loop"), [
       ("0/1 knapsack", "each item at most once", "<code>w = cap … wt</code> (descending)"),
       ("Unbounded", "unlimited copies of each item", "<code>w = wt … cap</code> (ascending)"),
       ("Bounded (k copies)", "at most k of each", "binary-split each item into 1,2,4,… copies, then 0/1"),
       ("Subset sum / partition", "is a total reachable at all?", "<code>boolean[]</code>, descending"),
   ])
   + code("""
// partition-equal-subset-sum: reachable totals, 0/1 style
boolean[] can = new boolean[sum / 2 + 1];
can[0] = true;                                  // the empty subset -- the identity
for (int x : nums)
    for (int t = sum / 2; t >= x; t--)          // DESCENDING: each number used once
        can[t] |= can[t - x];
return can[sum / 2];
""")
   + p("Write the ascending loop there instead and <code>[1, 5]</code> reports that 2 "
       "is reachable, because <code>can[1]</code> was set by this same 1 a moment "
       "earlier. The direction is not a style choice; it encodes whether the item may "
       "be reused. <code>can[0] = true</code> is [[sentinels]]'s identity element — the "
       "empty subset sums to zero.")),

  ("Shape 3 — counting: combinations or permutations",
   diagrams.coin_change_nesting() +
   p("When the DP counts <em>ways</em> rather than optimising, the loop nesting decides "
     "whether <code>1+2</code> and <code>2+1</code> are the same answer. This is not a "
     "subtle performance difference — it is two different problems with the same code.")
   + p("Two more things always travel with counting DP. First, the count overflows: "
       "reach for <code>long</code> and the modulus ([[integer-width]]) at the "
       "<em>declaration</em>, not after the first Wrong Answer. Second, the base case "
       "<code>dp[0] = 1</code> — there is exactly one way to make nothing, the empty "
       "selection. Setting it to 0 makes every answer 0, and setting the wrong cell to "
       "1 quietly inflates everything.")),

  ("Shape 4 — grid DP",
   p("State: <em>dp[r][c] = the answer for the path ending at cell (r, c).</em> The "
     "table has the same shape as the input, which makes this the friendliest shape to "
     "debug — you can print it next to the grid.")
   + code("""
// minimum-path-sum
dp[0][0] = grid[0][0];
for (int r = 0; r < m; r++)
    for (int c = 0; c < n; c++) {
        if (r == 0 && c == 0) continue;
        int best = Integer.MAX_VALUE;                 // identity for min ([[sentinels]])
        if (r > 0) best = Math.min(best, dp[r-1][c]);
        if (c > 0) best = Math.min(best, dp[r][c-1]);
        dp[r][c] = best + grid[r][c];
    }
""")
   + p("Guarding with <code>if (r &gt; 0)</code> before reading <code>dp[r-1][c]</code> "
       "is [[bounds]]'s rule, and using <code>MAX_VALUE</code> rather than 0 as the "
       "starting best is [[sentinels]]'s. Grid DP is where those two lessons are exercised "
       "hardest.")
   + p("<strong>When grid DP does not apply.</strong> If movement is in all four "
       "directions, the dependency graph has cycles and there is no valid fill order — "
       "it is a shortest-path problem, not a DP. Use BFS or Dijkstra ([[graph-traversal]]). "
       "Problems where a cell's answer can depend on a cell you have not filled yet are "
       "the tell.")),

  ("Shape 5 — two sequences",
   diagrams.dp_grid_dependency() +
   p("State: <em>dp[i][j] = the answer for the first i of a and the first j of b.</em> "
     "The <code>+1</code> sizing and the 1-based indexing into a 0-based string are "
     "deliberate: row 0 and column 0 hold the empty-prefix base cases, so no transition "
     "needs a bounds check.")
   + table(("Problem", "Match", "Mismatch"), [
       ("Longest common subsequence",
        "<code>dp[i-1][j-1] + 1</code>",
        "<code>max(dp[i-1][j], dp[i][j-1])</code>"),
       ("Edit distance",
        "<code>dp[i-1][j-1]</code>",
        "<code>1 + min(replace, delete, insert)</code>"),
       ("Longest common <em>substring</em>",
        "<code>dp[i-1][j-1] + 1</code>",
        "<code>0</code> — and the answer is the max over all cells, not dp[n][m]"),
       ("Distinct subsequences",
        "<code>dp[i-1][j-1] + dp[i-1][j]</code>",
        "<code>dp[i-1][j]</code>"),
   ])
   + p("Substring versus subsequence is worth pausing on, because the two tables look "
       "identical and differ in exactly two places: the mismatch resets to 0, and the "
       "answer is the maximum over the whole table rather than the bottom-right corner. "
       "<code>dp[n][m]</code> only holds the answer when the recurrence is monotone "
       "along both axes.")
   + p("Regex and wildcard matching are this shape with a third case for the "
       "<code>*</code> character: <code>dp[i][j] = dp[i][j-2]</code> (zero occurrences) "
       "<code>|| (matches(i, j-1) &amp;&amp; dp[i-1][j])</code> (one more). They are "
       "hard because the state is easy and the case analysis is not — enumerate the "
       "cases on paper first.")),

  ("Shape 6 — subsequence DP and LIS",
   diagrams.lis_patience() +
   p("State: <em>dp[i] = the length of the longest increasing subsequence ending "
     "exactly at i.</em> Again \"ending exactly at\" is what makes the transition work:")
   + code("""
// O(n^2): for each i, look back at everything smaller
for (int i = 0; i < n; i++) {
    dp[i] = 1;
    for (int j = 0; j < i; j++)
        if (nums[j] < nums[i]) dp[i] = Math.max(dp[i], dp[j] + 1);
}
return Arrays.stream(dp).max().orElse(0);   // NOT dp[n-1]
""")
   + p("<code>dp[n-1]</code> is a real and easy mistake here: the longest subsequence "
       "need not end at the last element. Whenever the state says \"ending exactly at "
       "i\", the answer is a maximum over the table.")
   + p("The O(n log n) version replaces the inner scan with a binary search over "
       "<code>tails</code> — <code>lowerBound</code> for strictly increasing, "
       "<code>upperBound</code> for non-decreasing. Many problems reduce to it after a "
       "sort: russian-doll-envelopes sorts by width ascending then height "
       "<em>descending</em>, precisely so that equal widths cannot chain, then runs LIS "
       "on the heights. That tie-break is the entire problem.")),

  ("Shape 7 — interval DP",
   diagrams.interval_dp_order() +
   p("State: <em>dp[i][j] = the answer for the subarray a[i..j].</em> The transition "
     "splits the interval at some k and combines, so the fill order must be by "
     "increasing <em>length</em> — row order does not work, because dp[i][j] depends on "
     "dp[i][k] and dp[k][j], which are shorter but on the same row.")
   + code("""
// burst-balloons: dp[i][j] = max coins from bursting everything strictly inside (i, j)
for (int len = 2; len <= n + 1; len++)
    for (int i = 0; i + len <= n + 1; i++) {
        int j = i + len;
        for (int k = i + 1; k < j; k++)          // k is burst LAST
            dp[i][j] = Math.max(dp[i][j],
                                dp[i][k] + dp[k][j] + a[i] * a[k] * a[j]);
    }
""")
   + p("Burst-balloons is the canonical example of a state that has to be chosen "
       "carefully: the natural reading (\"which balloon do I burst first?\") gives "
       "subproblems that are not independent, because bursting changes the neighbours. "
       "Asking instead <em>which balloon is burst last</em> makes the two sides "
       "independent, and the DP falls out. When a DP will not decompose, the state is "
       "usually asking the question in the wrong direction.")
   + p("Same shape: matrix-chain multiplication, palindrome partitioning, "
       "minimum-cost-to-cut-a-stick, stone-game variants. O(n³) — check the constraint "
       "allows it, which usually means n ≤ 500.")),

  ("Shape 8 — state machine DP",
   diagrams.dp_state_machine() +
   p("When the answer depends not just on <em>where</em> you are but on <em>what mode "
     "you are in</em>, add a dimension for the mode. The stock problems are the family "
     "everyone meets first:")
   + code("""
// best-time-to-buy-and-sell-stock-with-cooldown
int hold = Integer.MIN_VALUE, free = 0, cool = 0;   // identities, [[sentinels]]
for (int price : prices) {
    int pHold = hold, pFree = free, pCool = cool;
    hold = Math.max(pHold, pFree - price);          // keep holding, or buy
    free = Math.max(pFree, pCool);                  // idle, or come off cooldown
    cool = pHold + price;                           // sell today
}
return Math.max(free, cool);
""")
   + p("Two details that cause real bugs. <strong>Snapshot the previous values.</strong> "
       "Updating <code>hold</code> before reading it in the <code>free</code> line uses "
       "this iteration's value and silently permits a same-day buy-and-sell. "
       "<strong>Initialise <code>hold</code> to MIN_VALUE, not 0</strong> — 0 would "
       "claim you can hold a stock having paid nothing.")
   + p("The k-transaction variants (best-time-iii and -iv) are the same machine with a "
       "transaction counter: <code>buy[k]</code> and <code>sell[k]</code> arrays, "
       "iterated k from high to low. And when <code>k >= n/2</code> the constraint is "
       "not binding at all and the problem collapses to \"take every upward step\" — "
       "worth special-casing, since k can be 10⁹.")),

  ("Shape 9 — tree DP",
   p("State: <em>dp[node] = the answer for the subtree rooted at node.</em> The fill "
     "order is a post-order traversal — children before parents — which recursion gives "
     "you for free. This is [[recursion]]'s <em>return one thing, record another</em> rule "
     "in its natural habitat.")
   + code("""
// house-robber-iii: return {best if node NOT robbed, best if node IS robbed}
int[] rob(TreeNode node) {
    if (node == null) return new int[]{0, 0};
    int[] l = rob(node.left), r = rob(node.right);
    int skip = Math.max(l[0], l[1]) + Math.max(r[0], r[1]);  // children free to choose
    int take = node.val + l[0] + r[0];                       // children must be skipped
    return new int[]{skip, take};
}
""")
   + p("Returning a small array or a record of the states, rather than one number, is "
       "the technique that makes tree DP tractable. Trying to return a single value "
       "forces a second traversal or a wrong answer. Same shape: "
       "binary-tree-maximum-path-sum (return the best downward arm, record the best "
       "through-path), diameter-of-binary-tree, "
       "binary-tree-cameras.")
   + p("<strong>Rerooting.</strong> When the question is asked for every node as root — "
       "sum-of-distances-in-tree — one post-order pass computes the answer for the "
       "chosen root plus subtree sizes, and a second pre-order pass slides the answer "
       "from parent to child in O(1) each. Two passes, O(n) total, instead of n "
       "traversals.")),

  ("Shape 10 — bitmask DP",
   p("State: <em>dp[mask] = the answer having already used exactly the set of items in "
     "mask.</em> Viable only when n ≤ ~20, because there are 2ⁿ states — which is "
     "precisely why a constraint of n ≤ 20 in a problem statement is a strong hint that "
     "this is the intended solution.")
   + code("""
// assignment problem: n tasks to n workers, minimum cost
int[] dp = new int[1 << n];
Arrays.fill(dp, Integer.MAX_VALUE);
dp[0] = 0;
for (int mask = 0; mask < (1 << n); mask++) {
    if (dp[mask] == Integer.MAX_VALUE) continue;       // unreachable
    int i = Integer.bitCount(mask);                    // next worker to assign
    if (i == n) continue;
    for (int j = 0; j < n; j++)
        if ((mask & (1 << j)) == 0)                    // task j still free
            dp[mask | (1 << j)] = Math.min(dp[mask | (1 << j)], dp[mask] + cost[i][j]);
}
return dp[(1 << n) - 1];
""")
   + p("<code>Integer.bitCount(mask)</code> deriving the current index is the trick "
       "that keeps this at one dimension instead of two — how many items are placed is "
       "implied by the mask, so storing it would be redundant. The travelling salesman "
       "variant does need the second dimension, <code>dp[mask][last]</code>, because "
       "the cost of the next hop depends on where you are standing.")
   + p("Useful idioms: iterate the submasks of <code>m</code> with "
       "<code>for (int s = m; s > 0; s = (s - 1) &amp; m)</code>; the lowest set bit is "
       "<code>m &amp; -m</code> (the same trick as the Fenwick tree in [[range-structures]]); and "
       "<code>1 &lt;&lt; n</code> overflows for n ≥ 31, so use <code>1L &lt;&lt; n</code> "
       "if n can be large — [[integer-width]] again.")),

  ("Shape 11 — digit DP",
   p("Counting numbers in a range with some property. State: <em>dp[position][tight]"
     "[extra] = how many ways to fill the remaining digits.</em> The "
     "<code>tight</code> flag is the one that everybody forgets and it is what makes "
     "the technique work — it records whether the prefix built so far is still equal to "
     "the bound's prefix, and therefore whether the next digit is capped.")
   + code("""
// count numbers <= n with some digit property
int go(int pos, boolean tight, int extra) {
    if (pos == digits.length) return valid(extra) ? 1 : 0;
    if (!tight && memo[pos][extra] != -1) return memo[pos][extra];  // cache only when free
    int limit = tight ? digits[pos] : 9;
    int total = 0;
    for (int d = 0; d <= limit; d++)
        total += go(pos + 1, tight && d == limit, next(extra, d));
    if (!tight) memo[pos][extra] = total;
    return total;
}
""")
   + p("Note that the memo deliberately excludes the tight case: there is only one "
       "tight path at each position, so caching it would be both useless and wrong "
       "(the tight subtree is not the same as the free one). Count-in-range problems "
       "are then answered as <code>f(hi) − f(lo − 1)</code>.")),

  ("Shape 12 — game theory DP",
   p("Two players alternate, both play optimally, and the question is who wins or by "
     "how much. State: <em>dp[i][j] = the best score difference the player to move can "
     "force on the subarray a[i..j].</em>")
   + code("""
// stone-game: score DIFFERENCE, from the perspective of whoever moves now
for (int len = 1; len <= n; len++)
    for (int i = 0; i + len <= n; i++) {
        int j = i + len - 1;
        dp[i][j] = (len == 1) ? a[i]
                 : Math.max(a[i] - dp[i+1][j],      // take the left end
                            a[j] - dp[i][j-1]);     // take the right end
    }
return dp[0][n-1] > 0;
""")
   + p("The <em>minus</em> is the entire idea. Storing a difference from the current "
       "mover's viewpoint means the opponent's best play is subtracted rather than "
       "handled by a separate turn dimension — that is how a minimax becomes a plain "
       "maximisation. Trying to store \"player 1's score\" instead forces a "
       "<code>whoseTurn</code> dimension and is where these go wrong.")
   + p("The related shape is <strong>win/lose (Sprague–Grundy-lite)</strong>: "
       "<em>dp[n] = can the player to move force a win from n?</em> A position is "
       "winning if <em>any</em> move leads to a losing position for the opponent — "
       "<code>dp[n] = OR over moves of !dp[n - move]</code>. That is stone-game-iv and "
       "nim-style problems. Note this is your <code>zero-sum-game</code> topic, where "
       "you have a 0% first-attempt rate.")),

  ("Shape 13 — probability and expected value",
   p("Same machinery, different arithmetic. State: <em>dp[state] = the probability of "
     "reaching state</em>, or <em>the expected value from state onward</em>. Two rules "
     "keep these correct:")
   + ul("Probabilities are <code>double</code> and <strong>sum forwards</strong>: "
        "<code>dp[next] += dp[cur] * p</code>.",
        "Expectations <strong>recurse backwards</strong>: "
        "<code>E[cur] = cost + Σ p · E[next]</code>, which needs the state graph to be "
        "acyclic — if it is not, you are solving a linear system, not filling a table.")
   + p("knight-probability-in-chessboard is the forward kind: "
       "<code>dp[k][r][c] = P(still on the board after k moves)</code>, each move "
       "contributing <code>dp[k-1][r'][c'] / 8</code>. new-21-game is the sliding-window "
       "kind, where the naive transition is O(nk) and collapses to O(n) by keeping a "
       "running sum — [[windows]]'s technique applied inside a DP.")),

  ("Space optimisation: only after it is correct",
   p("If <code>dp[i]</code> reads only <code>dp[i-1]</code>, you need two rows, not n. "
     "If it reads only <code>dp[i-1][j']</code> for <code>j' &lt;= j</code>, one row "
     "iterated in the right direction is enough — which is exactly the knapsack trick "
     "above, and now you can see why the direction is what it is.")
   + code("""
int[] prev = new int[m + 1], cur = new int[m + 1];
for (int i = 1; i <= n; i++) {
    for (int j = 1; j <= m; j++) cur[j] = f(prev[j], prev[j-1], cur[j-1]);
    int[] t = prev; prev = cur; cur = t;      // swap, do not copy
    // cur now holds stale row i-1 values -- clear it if the recurrence writes conditionally
}
""")
   + p("The stale-row bug is the reason to do this second: after the swap, "
       "<code>cur</code> still contains row <code>i-1</code>. If your inner loop "
       "assigns to every cell unconditionally that is harmless; if it only sometimes "
       "assigns, you silently read two-rows-ago values. Clear the row, or assign "
       "unconditionally.")
   + p("Get it correct with the full 2D table first. A wrong answer in a rolling-array "
       "DP is dramatically harder to debug, because you can no longer print the table "
       "and look at it.")),

  ("When the DP is wrong: a procedure",
   p("This is the part that pays off most in your history, where the repeated pattern "
     "is adjusting the recurrence until the samples pass rather than locating the "
     "defect. In order:")
   + table(("Symptom", "Look here first"), [
       ("Off by a constant, or 0 everywhere",
        "the base case — especially <code>dp[0]</code>. Counting DPs need "
        "<code>dp[0] = 1</code>; min-DPs need an identity of ∞, not 0."),
       ("Correct on small inputs, wrong on large",
        "overflow ([[integer-width]]), or a state that is missing a dimension and only collides "
        "once the input is big enough."),
       ("Correct sometimes, no pattern",
        "loop order — a cell is reading a dependency that has not been filled yet. "
        "Print the table and find the first wrong cell."),
       ("Answer is a valid answer, but not optimal",
        "the transition is missing a case. Enumerate the choices at one state "
        "exhaustively on paper and compare with the code."),
       ("Time limit exceeded",
        "count the states and the work per state. If states × work exceeds the budget, "
        "the state itself is wrong — a dimension needs removing, not the code speeding "
        "up."),
   ])
   + p("<strong>Find the first wrong cell.</strong> For a table small enough to print, "
       "compute the answer by brute force, print both tables, and scan for the earliest "
       "disagreement. Every cell before it is right, so the bug is in that one cell's "
       "transition — this turns \"the DP is wrong\" into a two-line question. It is "
       "faster than re-reading the recurrence, every time.")),
 ],
 "rules": [
  "Write the state as a full English sentence in a comment before declaring the array.",
  "Ask whether two different situations could share a state. If yes, add the missing dimension.",
  "Derive the loop order from the transition's dependency direction. Never adjust it until the samples pass.",
  "Counting DP: dp[0] = 1, use long, apply the modulus at every += and *.",
  "Optimising DP: the base case is the identity of the operation -- MAX_VALUE for min, MIN_VALUE for max.",
  "\"Ending exactly at i\" states are answered by a max over the table, not by dp[n-1].",
  "Write it top-down first. Convert to bottom-up only for space or stack depth.",
  "Space-optimise last, after it is correct and only if you need to.",
  "Debug by finding the first cell that disagrees with brute force, not by re-reading the recurrence.",
 ],
 "drill": "Take five DP problems you have solved. For each, write only the state "
          "sentence and the transition -- no code -- then classify it into one of the "
          "shapes above. The point is the classification: once you can name the shape "
          "in under a minute, the loop order and base case stop being decisions. Then "
          "do stone-game-iv and count-numbers-with-unique-digits, which are the two "
          "shapes above you have never attempted.",
},
# ==========================================================================
{
 "slug": "monotonic-stack",
 "title": "Monotonic stacks",
 "one_line": "One stack, one direction, one invariant: it holds the indices whose answer "
             "has not arrived yet.",
 "why": "monotonic-stack sits at a 50% first-attempt rate over 24 problems, and 21 "
        "diagnosed mistakes across 13 topics involve a stack that was not kept in the "
        "right order or was popped on the wrong condition. It is a small, closed "
        "technique — once the invariant is written down it is very hard to get wrong, "
        "which makes it one of the highest-return lessons here.",
 "summary": (
  p('A monotonic stack holds the indices of elements whose answer has not '
     'arrived yet, in an order that never breaks — strictly increasing or '
     'strictly decreasing by value. When an element arrives that breaks the '
     'order, everything it beats is popped, and for each of those the '
     'newcomer <em>is</em> the answer.') +
  p('Every index is pushed once and popped once, so the whole thing is O(n) '
     'despite the inner <code>while</code>. Store indices rather than '
     'values: you almost always need the distance, and the value is one '
     'lookup away.')
 ),
 "used_for": [
  ('Next greater or next smaller element, in either direction',
   'All four variants are one template with the comparison and the scan '
    'direction flipped.'),
  ('Largest rectangle in a histogram',
   "Each bar's rectangle is bounded by the first smaller bar on each side "
    '— exactly what the stack produces.'),
  ('Trapping rain water',
   'A monotonic stack, or two pointers. Both O(n); the two-pointer version '
    'uses O(1) space.'),
  ('Daily temperatures / stock span',
   'The literal “next greater” question, with the index difference as the '
    'answer.'),
  ('Maximum of every window of size k',
   'A monotonic deque: the same invariant plus eviction from the front.'),
  ('Smallest subsequence / remove k digits',
   'Greedy with a stack — pop while the top is worse and enough elements '
    'remain to refill.'),
 ],
 "patterns": [
  ('For each element, the first element to its right that is greater',
   'Decreasing stack, one left-to-right pass.'),
  ('How many days until a warmer temperature',
   'The same, and the answer is the index difference.'),
  ('Largest rectangle / maximal rectangle in a matrix',
   'A histogram per row, then the stack.'),
  ('The maximum of every window of size k',
   'Monotonic deque.'),
  ('Remove k digits to make the smallest possible number',
   'Greedy stack; pop while the top is larger and removals remain.'),
  ('Sum of subarray minimums',
   'Count, per element, the subarrays where it is the minimum — previous- '
    'smaller and next-smaller boundaries.'),
  ('Next greater element in a circular array',
   'Two passes over the array, or one pass over 2n with i % n.'),
 ],
 "match": r"monotonic(?! (predicate|condition|function|property|check|in ))|"
          r"next (greater|smaller|larger|warmer)|previous (greater|smaller)|"
          r"stack (invariant|holds|of indices|was|kept|order)|(increas|decreas)ing stack|"
          r"pop(ping|ped)? while|st\.(push|pop|peek)|stack\.(push|pop|peek)|"
          r"largest rectangle|trapping rain",
 "basics": [

  ("The invariant, and the trace",
   diagrams.monotonic_stack_trace() +
   p("A monotonic stack keeps its contents in sorted order by pushing normally and "
     "popping anything that would break the order. The insight is <em>what the stack "
     "means</em>: it holds the indices whose answer is still unknown, and an index is "
     "popped at exactly the moment its answer arrives.")
   + p("That gives the O(n) bound for free — each index is pushed once and popped at "
       "most once, so the inner <code>while</code> loop does not make it quadratic, "
       "however alarming it looks.")
   + code("""
// next greater element to the right; ans[i] = -1 if none
int[] ans = new int[n];
Arrays.fill(ans, -1);                       // the sentinel, decided up front
Deque<Integer> st = new ArrayDeque<>();     // indices, values DECREASING
for (int i = 0; i < n; i++) {
    while (!st.isEmpty() && nums[st.peek()] < nums[i])
        ans[st.pop()] = nums[i];            // nums[i] is the answer for the popped index
    st.push(i);
}
// anything still on the stack has no greater element -- it keeps the sentinel
""")
   + traces.monotonic_stack([2, 1, 2, 4, 3])),

  ("Choosing the four variants",
   p("There are exactly four questions, and they differ only in the comparison and the "
     "scan direction. Derive the one you need rather than recalling it:")
   + table(("You want", "Scan", "Pop while", "Stack order"), [
       ("next greater to the right", "left → right", "<code>nums[top] &lt; nums[i]</code>", "decreasing"),
       ("next smaller to the right", "left → right", "<code>nums[top] &gt; nums[i]</code>", "increasing"),
       ("previous greater to the left", "right → left", "<code>nums[top] &lt; nums[i]</code>", "decreasing"),
       ("previous smaller to the left", "right → left", "<code>nums[top] &gt; nums[i]</code>", "increasing"),
   ])
   + p("The derivation, if you would rather not memorise the table: the stack must hold "
       "candidates that could still be someone's answer. If you are looking for a "
       "<em>greater</em> element, a smaller candidate sitting below a larger one can "
       "never be chosen — so smaller ones are popped, and the stack is decreasing.")
   + p("<strong>Strict versus non-strict.</strong> Whether the comparison is "
       "<code>&lt;</code> or <code>&lt;=</code> decides how equal values are handled, "
       "and it matters whenever the problem counts things. For "
       "sum-of-subarray-minimums — a problem in your export — use strict on one side and "
       "non-strict on the other, so that a run of equal values is attributed to exactly "
       "one of them and no subarray is counted twice.")),

  ("Store indices, not values",
   p("Almost every monotonic-stack problem eventually needs a <em>distance</em> or a "
     "<em>width</em>, and you cannot recover an index from a value. Push indices and "
     "read <code>nums[st.peek()]</code> — it costs nothing and keeps every variant open:")
   + code("""
// daily-temperatures: how many days until a warmer one
while (!st.isEmpty() && temps[st.peek()] < temps[i])
    { int j = st.pop(); ans[j] = i - j; }     // needs BOTH indices
""")
   + p("<strong>The count-of-subarrays trick.</strong> Once you have, for each index i, "
       "the distance to the previous smaller element and to the next smaller element, "
       "the number of subarrays in which <code>nums[i]</code> is the minimum is "
       "<code>left × right</code>. Sum <code>nums[i] × left × right</code> and you have "
       "solved sum-of-subarray-minimums in O(n) — with the overflow and modulus care "
       "from [[integer-width]], which is where your first attempt at it went wrong.")),

  ("Largest rectangle, and the sentinel that removes the special case",
   p("largest-rectangle-in-histogram is the archetype. For each bar, the widest "
     "rectangle of that height extends until a strictly shorter bar on either side — "
     "which is exactly previous-smaller and next-smaller.")
   + code("""
Deque<Integer> st = new ArrayDeque<>();
int best = 0;
for (int i = 0; i <= n; i++) {
    int h = (i == n) ? 0 : heights[i];      // sentinel bar of height 0 at the end
    while (!st.isEmpty() && heights[st.peek()] > h) {
        int height = heights[st.pop()];
        int left = st.isEmpty() ? -1 : st.peek();
        best = Math.max(best, height * (i - left - 1));
    }
    st.push(i);
}
""")
   + p("Two sentinels are doing the work here, both instances of [[sentinels]]. The virtual "
       "bar of height 0 at index n forces the stack to drain, so there is no separate "
       "cleanup loop after the main one. And <code>left = -1</code> when the stack "
       "empties represents a virtual boundary before the array, which makes the width "
       "formula uniform. Without them you need two extra code paths, and those paths "
       "are where the bugs live.")
   + p("maximal-rectangle is this run once per row over a histogram of consecutive "
       "ones. trapping-rain-water can be solved with the same stack, though the "
       "two-pointer version from [[windows]] is shorter.")),
 ],
 "rules": [
  "Write the invariant as a sentence first: what does the stack hold, and in what order?",
  "Push indices, never values.",
  "Derive the pop condition from what you are looking for -- do not recall it.",
  "Decide strict vs non-strict deliberately whenever the problem counts anything.",
  "Add a boundary sentinel to drain the stack instead of writing a cleanup loop.",
  "Anything left on the stack at the end has no answer: that is the sentinel value.",
 ],
 "drill": "next-greater-element-i, daily-temperatures, largest-rectangle-in-histogram, "
          "sum-of-subarray-minimums, in that order, in one sitting. They are the same "
          "twelve lines four times; the point is to feel that.",
},

# ==========================================================================
{
 "slug": "strings",
 "title": "Strings in Java: cost, characters and building",
 "one_line": "String concatenation in a loop is O(n²). charAt beats substring. And the "
             "unit of a string is not always a char.",
 "why": "String handling is the most-cited theme in your entire export — 102 diagnosed "
        "mistakes across 33 topics touch charAt, substring, StringBuilder or palindrome "
        "logic. Unlike the other lessons here it is not one algorithm; it is a set of "
        "costs and conventions that, once known, remove a whole class of Time Limit "
        "Exceeded and off-by-one verdicts.",
 "summary": (
  p('A Java <code>String</code> is immutable, so <code>s += c</code> inside '
     'a loop copies the entire string every iteration and turns an O(n) job '
     'into O(n²). <code>StringBuilder</code> exists for exactly that.') +
  p('The second thing worth internalising is that a <code>char</code> is a '
     "16-bit integer. <code>c - 'a'</code> is an array index, and a 26-slot "
     '<code>int[]</code> beats a <code>HashMap&lt;Character, '
     'Integer&gt;</code> every time the alphabet is known. The rest of this '
     'lesson is cost: <code>substring</code> copies, <code>charAt</code> '
     'does not.')
 ),
 "used_for": [
  ('Building output character by character',
   'StringBuilder. Every time, with no exception worth remembering.'),
  ('Counting characters over a known alphabet',
   "int[26] indexed by c - 'a': O(1), no boxing, no hashing."),
  ('Anagram grouping or comparison',
   'A canonical form — sorted characters, or the 26-count rendered as a '
    'key.'),
  ('Palindrome checking or counting',
   'Expand around each of the 2n − 1 centres: O(n²) time, O(1) space, and '
    'no DP table to get wrong.'),
  ('Substring search',
   'String.indexOf first. Reach for KMP or a rolling hash only when the '
    'constraint forces it.'),
  ('Prefix queries over many words',
   'A trie, with new Node[26] children when the alphabet is fixed.'),
 ],
 "patterns": [
  ('Build and return the string after n operations',
   'StringBuilder, and never += inside the loop.'),
  ('s consists of lowercase English letters',
   'A 26-slot count array is exact and free.'),
  ('Longest palindromic substring / count palindromic substrings',
   'Expand around centre.'),
  ('Group the anagrams',
   'A canonical key in a HashMap.'),
  ('Check whether t is a permutation of a window of s',
   'Sliding window over a count array.'),
  ('Find the longest common prefix',
   'A vertical scan. No data structure is needed.'),
  ('Compare version strings / simplify a path',
   'split plus a stack — the parsing is the entire problem.'),
  ('s.length up to 10⁵ and you are calling substring in a loop',
   'That is O(n²) hidden in a library call. Use indices.'),
 ],
 "match": r"charAt|StringBuilder|substring|toCharArray|String\.(valueOf|format|join)|"
          r"\bsplit\(|palindrom|string concat|\+= *\"|new String|\.equals\(|"
          r"character (count|frequency|array)|\bchar\[\]",
 "basics": [

  ("The cost table nobody tells you",
   diagrams.string_concat_cost() +
   p("Java strings are immutable. Every operation that looks like it modifies one "
     "actually allocates a new one, and that is where the time goes:")
   + table(("Operation", "Cost", "Note"), [
       ("<code>s.charAt(i)</code>", "O(1)", "the right way to read a character"),
       ("<code>s.length()</code>", "O(1)", "safe in a loop condition"),
       ("<code>s.substring(a, b)</code>", "<strong>O(b − a)</strong>",
        "copies since Java 7 — it is not a view"),
       ("<code>s += t</code>", "<strong>O(|s| + |t|)</strong>",
        "allocates a whole new string every time"),
       ("<code>sb.append(t)</code>", "O(|t|) amortised", "use this"),
       ("<code>s.equals(t)</code>", "O(n)", "and <code>==</code> is wrong — see [[equality-hashing]]"),
       ("<code>s.toCharArray()</code>", "O(n)", "one copy; hoist it out of loops"),
       ("<code>s.split(regex)</code>", "O(n) + regex compile", "compile the Pattern once if it is hot"),
   ])
   + p("The one that costs the most in practice:")
   + code("""
String out = "";
for (String w : words) out += w;          // O(total^2) -- quietly quadratic

StringBuilder sb = new StringBuilder();
for (String w : words) sb.append(w);      // O(total)
return sb.toString();
""")
   + p("A loop of 10⁵ appends is instant with a StringBuilder and roughly 10¹⁰ character "
       "copies with <code>+=</code>. This is [[complexity-budget]]'s budget question hiding inside a "
       "line that does not look like a loop.")
   + p("<code>substring</code> deserves the same suspicion. A double loop that takes "
       "<code>s.substring(i, j)</code> for every pair is O(n³), not O(n²) — the copy is "
       "inside the loop. Compare with <code>charAt</code> in place, or hash the "
       "substrings, or use a DP table.")),

  ("Characters are small integers — use that",
   p("<code>char</code> is a 16-bit unsigned integer, and arithmetic on it is ordinary "
     "integer arithmetic. For lowercase-only alphabets this replaces a HashMap with an "
     "array, which is both faster and shorter:")
   + code("""
int[] count = new int[26];
for (char c : s.toCharArray()) count[c - 'a']++;      // 'a' is just 97

// anagram check, no map, no sort
for (char c : t.toCharArray())
    if (--count[c - 'a'] < 0) return false;
""")
   + p("Size the array from the stated alphabet: 26 for lowercase, 128 for ASCII, 256 "
       "for extended. Guessing 26 when the problem says \"any character\" is an "
       "ArrayIndexOutOfBoundsException — [[bounds]]'s rule about deriving sizes.")
   + p("<strong>The trap: <code>char</code> promotes to <code>int</code> in "
       "arithmetic.</strong> <code>'a' + 1</code> is the <code>int</code> 98, not the "
       "char <code>'b'</code>. Appending it to a StringBuilder appends \"98\". Cast "
       "explicitly: <code>(char)('a' + 1)</code>.")
   + p("<strong>And Unicode.</strong> <code>length()</code> counts UTF-16 code units, "
       "not characters — an emoji is two of them. LeetCode problems almost always "
       "guarantee ASCII, so this rarely bites there, but the assumption is worth making "
       "consciously rather than by accident.")),

  ("Palindromes: expand around centre",
   diagrams.palindrome_expand() +
   p("The DP table for palindromic substrings is O(n²) time <em>and</em> O(n²) space. "
     "Expanding around each centre is O(n²) time and O(1) space, and it is less code:")
   + code("""
int countPalindromes(String s) {
    int count = 0;
    for (int i = 0; i < s.length(); i++) {
        count += expand(s, i, i);        // odd-length centres
        count += expand(s, i, i + 1);    // even-length centres -- do not forget these
    }
    return count;
}

int expand(String s, int l, int r) {
    int found = 0;
    while (l >= 0 && r < s.length() && s.charAt(l) == s.charAt(r)) {
        found++; l--; r++;           // bounds BEFORE the read -- [[bounds]]
    }
    return found;
}
""")
   + p("Omitting the even centres is the single most common bug in this family: "
       "<code>&quot;abba&quot;</code> then reports its longest palindrome as length 1. "
       "There are 2n−1 centres, not n.")
   + p("For the O(n) version, Manacher's algorithm exists; it is rarely required and "
       "rarely worth the risk under time pressure. Know that it exists, reach for it "
       "only when n makes O(n²) infeasible.")),

  ("Comparison, keys and canonical forms",
   p("A great many string problems reduce to <em>choose a canonical form and group by "
     "it</em>. group-anagrams is the clearest case, and the choice of key is the whole "
     "decision:")
   + code("""
// key by sorted characters -- O(k log k) per word
char[] a = w.toCharArray(); Arrays.sort(a);
String key = new String(a);

// key by counts -- O(k) per word, better when words are long
int[] c = new int[26];
for (char ch : w.toCharArray()) c[ch - 'a']++;
String key = Arrays.toString(c);          // a stable, printable key
""")
   + p("Both are correct; the second is asymptotically better and the first is shorter. "
       "That is a real trade-off to make on purpose, not by default.")
   + p("Two more things that recur. <strong>Equality:</strong> always "
       "<code>equals</code>, never <code>==</code> — string literals are interned so "
       "<code>==</code> appears to work on small tests and then does not, the same "
       "failure mode as boxed <code>Integer</code> in [[equality-hashing]]. <strong>Splitting:</strong> "
       "<code>split</code> takes a <em>regex</em>, so <code>split(&quot;.&quot;)</code> "
       "returns an empty array; you want <code>split(&quot;\\\\.&quot;)</code>. And "
       "<code>split(&quot; &quot;)</code> keeps empty tokens from runs of spaces, while "
       "<code>split(&quot;\\\\s+&quot;)</code> does not — with a leading space still "
       "producing an empty first token, which is a classic "
       "reverse-words-in-a-string bug. <code>trim()</code> first.")),

  ("Rolling hashes and tries, in one paragraph each",
   p("<strong>Rolling hash (Rabin–Karp)</strong> compares substrings in O(1) after O(n) "
     "preprocessing, by treating a substring as a base-B number modulo a large prime. "
     "It turns \"is this substring equal to that one\" into an integer comparison, which "
     "is what makes repeated-dna-sequences and longest-duplicate-substring tractable. "
     "Two cautions: use a <code>long</code> and a large modulus ([[integer-width]]), and "
     "remember it is a <em>probabilistic</em> equality — verify a hit with a real "
     "comparison when correctness matters.")
   + p("<strong>Tries</strong> store a set of strings as a character tree, giving "
       "prefix queries in O(length) independent of how many words are stored. Your trie "
       "topic sits at a 38% first-attempt rate, and the recurring defect there is the "
       "node shape: use <code>TrieNode[] children = new TrieNode[26]</code> with an "
       "explicit <code>boolean isWord</code>, and be clear that <em>a node existing "
       "does not mean a word ends there</em>. Conflating \"has children\" with \"is a "
       "word\" is the bug.")
   + code("""
class TrieNode {
    TrieNode[] next = new TrieNode[26];
    boolean isWord;                        // NOT the same as "has no children"
}
""")),
 ],
 "rules": [
  "Never build a string with += in a loop. StringBuilder, always.",
  "substring() copies. Prefer charAt, or hoist the copy out of the loop.",
  "Count with int[26] (or [128]) sized from the stated alphabet, not with a HashMap by reflex.",
  "Cast back to char after arithmetic: (char)('a' + k).",
  "Palindromes: 2n-1 centres. Test \"abba\" before submitting.",
  "equals(), never ==. split() takes a regex, so escape the dot.",
  "In a trie, isWord is a separate flag from having children.",
 ],
 "drill": "Rewrite three of your accepted string solutions to remove every substring "
          "call from inside a loop, and time them. Then do longest-palindromic-substring "
          "with expand-around-centre and group-anagrams with the count key -- both "
          "without looking at your old code.",
},

# ==========================================================================
{
 "slug": "number-theory",
 "title": "Number theory: gcd, primes and counting under a modulus",
 "one_line": "Division does not exist modulo p — you multiply by an inverse. And the "
             "sieve, gcd and fast power are three short routines worth knowing cold.",
 "why": "number-theory sits at a 41% first-attempt rate over 22 problems and "
        "combinatorics at 44% over 16 — both in your weakest ten. [[Integer-width]] covers the "
        "mechanics of not overflowing; this one covers the mathematics you are expected "
        "to already have: modular inverses, binomial coefficients under a prime "
        "modulus, and the handful of routines that appear again and again.",
 "summary": (
  p('Four short routines carry almost every maths-flavoured problem: '
     "Euclid's gcd (three lines, O(log n)), the sieve of Eratosthenes (every "
     'prime below n in O(n log log n)), fast exponentiation (a^b mod p in '
     'O(log b)), and modular inverse — which is fast exponentiation with the '
     'exponent p − 2.') +
  p('The idea that catches people is that division does not exist modulo a '
     'prime. You multiply by an inverse instead, and any code that writes '
     '<code>/ k % MOD</code> is wrong even on the inputs where it happens to '
     'produce the right number.')
 ),
 "used_for": [
  ('Reducing a fraction, or finding a repeat length',
   'gcd. And lcm(a, b) = a / gcd(a, b) * b — divide first so the product '
    'cannot overflow.'),
  ('“How many primes below n”',
   'Sieve. Trial division per number stops being fast somewhere past 10⁵.'),
  ('Factorising one number',
   'Trial division to √n: fine for a single number, hopeless across a '
    'range.'),
  ('Counting arrangements modulo 10⁹ + 7',
   'Precomputed factorials and inverse factorials give each binomial '
    'coefficient in O(1).'),
  ('a^b where b is huge',
   'Fast exponentiation, every multiply in long and reduced at each step.'),
  ('Anything periodic — clocks, cycles, wrap-around',
   'Modular arithmetic, with the negative case handled: ((x % m) + m) % m.'),
 ],
 "patterns": [
  ('Return the answer modulo 10⁹ + 7',
   'The modulus is prime, so inverses exist and division becomes pow(x, '
    'MOD − 2).'),
  ('Count the number of ways to choose k from n',
   'A binomial coefficient from precomputed factorials.'),
  ('How many numbers in [1, n] are divisible by …',
   'Inclusion–exclusion over the divisors, not a loop over n.'),
  ('1 ≤ n ≤ 10⁹',
   'You cannot iterate. Look for a closed form, a digit DP, or a divisor '
    'argument.'),
  ('Find the greatest common divisor of the array',
   'Fold gcd across it. The identity is 0, not 1.'),
  ('The result may be a repeating decimal or a fraction',
   'Reduce with gcd, and carry the sign separately.'),
  ('Is n a power of two / count the set bits',
   'Bit tricks, not arithmetic: n & (n − 1) removes the lowest set bit.'),
 ],
 "match": r"\bgcd\b|\blcm\b|sieve|\bprime\b|modular inverse|modpow|fast (power|exponent"
          r"iation)|Fermat|\bnCr\b|binomial|factorial|coprime|Euclid|totient|"
          r"combinator|permutation count|divisor",
 "basics": [

  ("gcd, lcm, and why Euclid is three lines",
   diagrams.euclid_steps() +
   p("The greatest common divisor is the one routine here you will use most, and the "
     "recursive form is short enough that there is no excuse for a loop:")
   + code("""
long gcd(long a, long b) { return b == 0 ? a : gcd(b, a % b); }

long lcm(long a, long b) { return a / gcd(a, b) * b; }   // divide FIRST, then multiply
""")
   + p("The <code>lcm</code> line is deliberate: <code>a * b / gcd</code> overflows for "
       "inputs that <code>a / gcd * b</code> handles fine, and the division is exact so "
       "nothing is lost. This is [[integer-width]]'s rule in its most compact form.")
   + p("Two facts that turn problems into one-liners. Fractions are compared and "
       "deduplicated by reducing with the gcd — and by <strong>normalising the sign</strong>, "
       "or <code>1/2</code> and <code>-1/-2</code> become different keys. And a set of "
       "points is collinear, or a set of intervals shares a period, exactly when the "
       "gcd of the differences says so; <code>gcd(0, x) == x</code> makes 0 the "
       "identity for a running gcd ([[sentinels]] again).")),

  ("Primes: the sieve, and factorising one number",
   diagrams.sieve() +
   p("Two different jobs, two different tools. To know primality for <em>every</em> "
     "number up to n, sieve once in O(n log log n). To factorise <em>one</em> number, "
     "trial-divide to √n in O(√n):")
   + code("""
// all prime factors of one n, with multiplicity
for (long p = 2; p * p <= n; p++)
    while (n % p == 0) { factors.add(p); n /= p; }
if (n > 1) factors.add(n);          // the leftover is prime -- do not forget it
""")
   + p("That trailing <code>if</code> is the bug people ship: after the loop, whatever "
       "remains of <code>n</code> is either 1 or a prime larger than √n, and dropping it "
       "loses the largest factor entirely. A number has at most one such factor, which "
       "is why the loop can stop at √n at all.")
   + p("A useful middle case: a <em>smallest prime factor</em> sieve stores, for each "
       "number, its least prime divisor. That gives full factorisation of any number up "
       "to n in O(log n) per query, which is what you want when a problem factorises "
       "many numbers rather than one.")),

  ("Working modulo a prime",
   p("When a problem says \"return the answer modulo 10⁹+7\", it is telling you the "
     "answer is astronomically large and that you must never hold it whole. The modulus "
     "is applied continuously, not at the end. Addition, subtraction and multiplication "
     "all distribute over it:")
   + code("""
static final int MOD = 1_000_000_007;

int add(int a, int b) { return (int) (((long) a + b) % MOD); }
int sub(int a, int b) { return (int) (((long) a - b + MOD) % MOD); }   // + MOD first
int mul(int a, int b) { return (int) ((long) a * b % MOD); }           // cast BEFORE
""")
   + ul("<strong>Subtraction</strong> can go negative, and Java's <code>%</code> keeps "
        "the sign — <code>-3 % 7</code> is <code>-3</code>, not <code>4</code>. Add MOD "
        "before reducing.",
        "<strong>Multiplication</strong> must be cast to <code>long</code> before the "
        "multiply. Two values just under 10⁹ overflow an <code>int</code> immediately.",
        "<strong>Comparison</strong> is meaningless: reduced values carry no ordering, "
        "so you cannot take a max of two answers that have been reduced.")
   + p("<strong>Division does not exist.</strong> There is no <code>/</code> modulo p. "
       "Instead you multiply by the modular inverse, and when p is prime, Fermat's "
       "little theorem gives it directly as <code>a<sup>p−2</sup> mod p</code>:")
   + code("""
long power(long base, long exp, long mod) {      // fast exponentiation, O(log exp)
    long result = 1;
    base %= mod;
    while (exp > 0) {
        if ((exp & 1) == 1) result = result * base % mod;
        base = base * base % mod;
        exp >>= 1;
    }
    return result;
}

long inverse(long a) { return power(a, MOD - 2, MOD); }   // valid only for PRIME MOD
""")
   + p("Fast exponentiation is worth having in muscle memory for its own sake — it is "
       "also how you raise a matrix to a power for linear recurrences, and how "
       "binary-search-on-the-answer problems evaluate a huge power without looping.")),

  ("Binomial coefficients and counting",
   p("Most combinatorics problems reduce to <em>choose k from n</em>, and under a prime "
     "modulus the efficient way is to precompute factorials once:")
   + code("""
static final int MOD = 1_000_000_007, N = 200_000;
long[] fact = new long[N + 1], inv = new long[N + 1];

void precompute() {
    fact[0] = 1;
    for (int i = 1; i <= N; i++) fact[i] = fact[i-1] * i % MOD;
    inv[N] = power(fact[N], MOD - 2, MOD);
    for (int i = N; i > 0; i--) inv[i-1] = inv[i] * i % MOD;   // backwards -- one power call
}

long nCr(int n, int r) {
    if (r < 0 || r > n) return 0;                          // out of range, not an error
    return fact[n] * inv[r] % MOD * inv[n-r] % MOD;
}
""")
   + p("Computing the inverse factorials backwards from a single "
       "<code>power</code> call is the standard trick — n calls to <code>power</code> "
       "would be O(n log MOD) and this is O(n). The <code>r &lt; 0 || r &gt; n</code> "
       "guard returning 0 rather than throwing matters, because inclusion–exclusion "
       "formulas routinely produce out-of-range terms that should contribute nothing.")
   + p("The identities worth recognising on sight:")
   + table(("Question", "Formula"), [
       ("Choose k from n, order irrelevant", "C(n, k)"),
       ("Arrange k of n, order matters", "P(n, k) = n! / (n−k)!"),
       ("Distribute n identical items into k labelled boxes",
        "C(n + k − 1, k − 1) — \"stars and bars\""),
       ("Paths on a grid from (0,0) to (m,n), right/down only", "C(m + n, m)"),
       ("Subsets of an n-set", "2ⁿ"),
       ("Balanced bracket sequences of length 2n", "Catalan(n) = C(2n, n) / (n + 1)"),
   ])
   + p("Recognising the grid-path identity is often what turns an O(mn) DP into an O(1) "
       "formula, and Catalan numbers count far more than brackets — binary tree shapes, "
       "triangulations, and non-crossing pairings all reduce to them.")),
 ],
 "rules": [
  "lcm: divide by the gcd before multiplying.",
  "After trial division to sqrt(n), the remainder above 1 is a prime factor. Add it.",
  "Cast to long before every modular multiply; add MOD before every modular subtract.",
  "Never compare or take a max of values that have been reduced modulo p.",
  "Division modulo a prime is multiplication by power(a, MOD - 2, MOD).",
  "Precompute factorials and inverse factorials once; derive inverses backwards from one power call.",
  "nCr must return 0 for out-of-range r, not throw.",
 ],
 "drill": "Write gcd, power, a sieve and an nCr table from memory into a scratch file, "
          "then solve unique-paths with the binomial formula rather than a DP table. "
          "Then count-the-number-of-ideal-arrays or "
          "number-of-ways-to-reach-a-position-after-exactly-k-steps, which need the "
          "factorial precomputation to fit in time.",
},

# ==========================================================================
{
 "slug": "intervals",
 "title": "Intervals: sort, sweep, and count",
 "one_line": "Sort by start to merge, by end to schedule, and turn endpoints into ±1 "
             "events when you need a running count.",
 "why": "24 diagnosed mistakes across 16 topics involve overlapping ranges, and the "
        "failure is nearly always the same: sorting by the wrong key, or overwriting an "
        "interval's end instead of extending it. It is a small technique with three "
        "variants, and picking the wrong variant produces answers that look plausible "
        "and are wrong on the swallowed-interval case.",
 "summary": (
  p('Almost every interval problem is decided by one choice: what you sort '
     'on. Sort by <strong>start</strong> and you can sweep left to right '
     'merging overlaps. Sort by <strong>end</strong> and the greedy “keep '
     'the one that finishes soonest” is optimal, which is the whole of '
     'interval scheduling.') +
  p('When you need a running count of how many intervals cover a point, '
     'stop thinking in intervals at all: turn each into a <code>+1</code> at '
     'its start and a <code>−1</code> at its end, sort the events, and take '
     'a prefix sum.')
 ),
 "used_for": [
  ('Merging overlapping ranges',
   'Sort by start, then extend the current end with max — never assign it.'),
  ('The maximum number of non-overlapping intervals',
   'Sort by end and take greedily. Sorting by start is provably wrong for '
    'this one.'),
  ('Minimum number of rooms, platforms or machines',
   'The maximum concurrent coverage — a ±1 event sweep.'),
  ('Inserting one interval into a sorted, disjoint list',
   'Three phases: entirely before, overlapping (merge), entirely after. No '
    're-sort needed.'),
  ('Counting how many ranges cover each point',
   'A difference array when the coordinates are small; an event sweep when '
    'they are not.'),
  ('Do any two intervals overlap?',
   'Sort by start and compare each start against the previous end.'),
 ],
 "patterns": [
  ('Merge all overlapping intervals',
   'Sort by start.'),
  ('Remove the minimum number of intervals so the rest do not overlap',
   'Sort by end, then take greedily.'),
  ('Can a person attend all meetings / how many meeting rooms',
   'An overlap check, then the ±1 sweep for the count.'),
  ('Book a slot, and return false if it double-books',
   'A TreeMap of events, or an ordered set queried with floor and ceiling.'),
  ('Add v to every index in [l, r], many times, then read the array',
   'A difference array — O(1) per update and one prefix sum at the end.'),
  ('Endpoints up to 10⁹',
   'Coordinate compression, or event sorting. Never an array over the '
    'coordinate range.'),
  ('Find the employee free time across several schedules',
   'Merge everything, then read the gaps.'),
 ],
 "match": r"\binterval|overlap|sweep line|\bmerge.{0,20}(range|interval)|meeting room|"
          r"sort(ed)? by (start|end)|non-overlapping|\bendpoint|\bevents?\b",
 "basics": [

  ("Merging: sort by start, and extend rather than assign",
   diagrams.interval_sweep() +
   p("Once intervals are sorted by start, an interval can only overlap the one "
     "currently being built. That is what makes a single pass sufficient.")
   + code("""
Arrays.sort(iv, (a, b) -> Integer.compare(a[0], b[0]));   // by START
List<int[]> out = new ArrayList<>();
int[] cur = iv[0].clone();                                // clone -- do not alias input
for (int i = 1; i < iv.length; i++) {
    if (iv[i][0] <= cur[1]) cur[1] = Math.max(cur[1], iv[i][1]);   // EXTEND
    else { out.add(cur); cur = iv[i].clone(); }
}
out.add(cur);                                             // the last one, always
""")
   + p("Three things fail here regularly. <strong><code>Math.max</code>, not "
       "assignment</strong> — <code>[1,10]</code> followed by <code>[2,3]</code> would "
       "otherwise shrink to <code>[1,3]</code>. <strong>The final "
       "<code>out.add(cur)</code></strong> — the loop emits an interval only when it "
       "finds a gap, so the last one is never emitted inside it. And "
       "<strong><code>clone()</code></strong> — mutating <code>cur[1]</code> when "
       "<code>cur</code> still points into the input array silently corrupts the "
       "caller's data.")
   + p("<strong>Touching or not?</strong> Whether <code>[1,2]</code> and "
       "<code>[2,3]</code> overlap depends on whether the interval is closed "
       "<code>[a,b]</code> or half-open <code>[a,b)</code> — <code>&lt;=</code> versus "
       "<code>&lt;</code> in the test. The problem statement decides; read it and write "
       "the choice in a comment.")),

  ("Scheduling: sort by END",
   diagrams.interval_sort_choice() +
   p("The classic greedy: to keep as many non-overlapping intervals as possible, "
     "repeatedly take the one that <em>finishes earliest</em>. Sorting by start here is "
     "the mistake, and it is one that passes many tests.")
   + code("""
// erase-overlap-intervals: minimum removals to make the rest disjoint
Arrays.sort(iv, (a, b) -> Integer.compare(a[1], b[1]));   // by END
int kept = 0, lastEnd = Integer.MIN_VALUE;                // identity, [[sentinels]]
for (int[] x : iv)
    if (x[0] >= lastEnd) { kept++; lastEnd = x[1]; }
return iv.length - kept;
""")
   + p("Why earliest-finish is optimal, in one line — the exchange argument: whatever "
       "the optimal solution's first interval is, swapping it for the "
       "earliest-finishing one cannot conflict with anything the optimum kept, because "
       "it ends no later. So an optimal solution exists that starts with it, and "
       "induction does the rest. Being able to state that is what separates a greedy "
       "you trust from a greedy you are hoping about.")
   + p("Same shape: non-overlapping-intervals, "
       "maximum-number-of-events-that-can-be-attended, and the classic "
       "activity-selection problem.")),

  ("Counting: turn endpoints into events",
   p("When the question is \"how many overlap at once\" — meeting rooms, car pooling, "
     "population by year — stop thinking about intervals and think about "
     "<em>events</em>. Each interval contributes +1 at its start and −1 at its end; "
     "sort all events by time and sweep, keeping a running total.")
   + code("""
// meeting-rooms-ii: how many rooms are needed?
int minRooms(int[] starts, int[] ends) {
int n = starts.length;
Arrays.sort(starts); Arrays.sort(ends);
int rooms = 0, best = 0, j = 0;
for (int i = 0; i < n; i++) {
    while (j < n && ends[j] <= starts[i]) { rooms--; j++; }   // frees BEFORE the start
    rooms++;
    best = Math.max(best, rooms);
}
return best;
}
""")
   + p("<strong>The tie rule is the whole problem.</strong> When one interval ends at "
       "exactly the moment another begins, does the room free up in time? Here "
       "<code>ends[j] &lt;= starts[i]</code> says yes. Change it to <code>&lt;</code> "
       "and you have solved a different, also-legitimate problem. Sorting a single "
       "event list needs the same care: process −1 before +1 at equal times to allow "
       "reuse, and +1 before −1 to forbid it.")
   + p("Two variants worth knowing. When times are small integers, a "
       "<strong>difference array</strong> — <code>d[start]++, d[end]--</code> then a "
       "prefix sum — is O(n + range) and simpler than sorting; this is "
       "corporate-flight-bookings and range-addition. When they are not, a "
       "<code>TreeMap&lt;Integer, Integer&gt;</code> of deltas gives the same sweep in "
       "O(n log n) and lets you query <code>floorKey</code> for the state at any moment "
       "— which is how my-calendar and range-module are built.")),
 ],
 "rules": [
  "Merging -> sort by start. Scheduling the most intervals -> sort by end. Counting overlap -> sweep events.",
  "cur[1] = max(cur[1], next[1]). Never plain assignment.",
  "Emit the final interval after the loop.",
  "clone() before mutating anything that came from the input.",
  "Decide closed vs half-open from the statement and write it in a comment.",
  "Decide the equal-time tie order deliberately: it changes the answer.",
 ],
 "drill": "merge-intervals, insert-interval, erase-overlap-intervals and meeting-rooms-ii "
          "back to back. For each, write down which sort key it needs and why, before "
          "you write the comparator. Then do my-calendar-i with a TreeMap.",
},

# ==========================================================================
{
 "slug": "linked-list",
 "title": "Linked lists: dummy nodes and two pointers",
 "one_line": "A dummy head removes every special case at the front. Two pointers give "
             "you the middle, the cycle and the k-th from the end in one pass.",
 "why": "linked-list is 38 problems at a 42% first-attempt rate. The mistakes are almost "
        "entirely structural rather than algorithmic: a null dereference on "
        "fast.next.next, a lost reference during a reversal, or special-case code for "
        "the head that a dummy node would have deleted. [[Sentinels]] introduced the dummy "
        "node; this is where it earns its keep.",
 "summary": (
  p('Two techniques cover nearly all of it. A <strong>dummy head</strong> — '
     'one throwaway node in front of the list — means the first node stops '
     'being a special case, so insertion, deletion and merging lose their '
     '<code>if (head == null)</code> branches and you return '
     '<code>dummy.next</code>.') +
  p('<strong>Two pointers</strong> at different speeds, or with a fixed '
     'gap, give you the middle, the k-th node from the end and cycle '
     'detection in one pass with O(1) extra space. The third thing is '
     'pointer order in reversal: save <code>next</code> before you overwrite '
     'it, or the rest of the list is unreachable.')
 ),
 "used_for": [
  ('Deleting a node that might be the head',
   'Dummy head; the delete becomes prev.next = prev.next.next with no '
    'special case at all.'),
  ('Merging two sorted lists',
   'Dummy head plus a tail pointer, and return dummy.next.'),
  ('Finding the middle',
   'Slow one step, fast two. Which node you land on depends on the loop '
    'condition — decide which you need first.'),
  ('Detecting a cycle and finding where it starts',
   'Floyd: meet inside the loop, then walk one pointer from the head at '
    'equal speed.'),
  ('Removing the n-th node from the end',
   'Two pointers with an n-gap, over a dummy head.'),
  ('Sorting in O(1) extra space',
   'Bottom-up merge sort on the list. Recursion would cost O(log n) of '
    'stack.'),
 ],
 "patterns": [
  ('Remove all nodes with value v / remove duplicates',
   'Dummy head.'),
  ('Remove the n-th node from the end in one pass',
   'A gap of n, then advance both pointers together.'),
  ('Reorder / rotate / partition the list',
   'Split with fast-slow, reverse one half, then interleave.'),
  ('Determine if the list has a cycle using O(1) memory',
   'Floyd. A HashSet answers it too, which is what the memory constraint '
    'is there to rule out.'),
  ('The list has up to 5 × 10⁴ nodes',
   'Iterate. Recursion on a list that long overflows the stack.'),
  ('Copy a list with random pointers',
   'Interleave the copies into the original list, or use a HashMap from '
    'old node to new.'),
  ('Add two numbers represented as lists',
   'Dummy head, a carry variable, and a loop condition that outlives both '
    'lists.'),
 ],
 "match": r"ListNode|dummy (head|node)|sentinel (head|node|dummy)|slow.{0,20}fast|"
          r"fast.{0,20}slow|reverse the list|linked[- ]list|\.next\.next|cycle detect|"
          r"Floyd|\bunlink|node\.(next|prev)|\.prev\b|head/tail|\bhead and tail\b",
 "basics": [

  ("The dummy head deletes the special cases",
   p("Every operation on a linked list has an awkward case: what if the node being "
     "removed is the head? What if the list becomes empty? A dummy node in front means "
     "there <em>is</em> no head case — every real node has a predecessor.")
   + code("""
// remove all nodes with value val
ListNode dummy = new ListNode(0, head);
ListNode prev = dummy;
while (prev.next != null) {
    if (prev.next.val == val) prev.next = prev.next.next;   // unlink; do not advance
    else                      prev = prev.next;
}
return dummy.next;      // NOT head -- head may have been removed
""")
   + p("<code>return dummy.next</code>, never <code>return head</code>: the original "
       "head may be gone. And note that after unlinking, <code>prev</code> must "
       "<em>not</em> advance — the new <code>prev.next</code> has not been examined yet. "
       "Advancing unconditionally is how consecutive matching nodes get missed.")
   + p("Use a dummy whenever the head might change: removal, insertion at the front, "
       "merging, partitioning, and building any new list. Building with a "
       "<code>dummy</code>/<code>tail</code> pair is uniformly cleaner than special-casing "
       "the first append.")),

  ("Reversal: three pointers, in the right order",
   p("Reversing is four lines and every one of them matters. The rule is: "
     "<strong>save the next pointer before you overwrite it.</strong>")
   + code("""
ListNode prev = null, cur = head;
while (cur != null) {
    ListNode next = cur.next;   // 1. SAVE -- or the rest of the list is unreachable
    cur.next = prev;            // 2. flip
    prev = cur;                 // 3. advance prev
    cur = next;                 // 4. advance cur
}
return prev;                    // prev is the new head; cur is null
""")
   + p("Reorder those four lines in any way and you either lose the tail or spin in an "
       "infinite loop. Worth writing from memory a few times until the order is "
       "automatic — it is a subroutine of reverse-nodes-in-k-group, "
       "palindrome-linked-list, reorder-list and add-two-numbers-ii.")
   + p("The recursive version is shorter but O(n) stack, which is a real constraint at "
       "n = 5·10⁴ ([[recursion]]). Prefer the iterative one by default.")),

  ("Two pointers: middle, k-th from the end, and cycles",
   diagrams.fast_slow_pointers() +
   diagrams.floyd_cycle() +
   p("One traversal, two cursors moving at different speeds, answers three different "
     "questions:")
   + code("""
// 1. middle node -- slow lands on the middle when fast runs off the end
ListNode slow = head, fast = head;
while (fast != null && fast.next != null) { slow = slow.next; fast = fast.next.next; }
// even length: slow is the SECOND middle. Start fast at head.next for the first.

// 2. k-th from the end -- open a gap of k, then move together
ListNode lead = head;
for (int i = 0; i < k; i++) lead = lead.next;      // guard if k may exceed the length
while (lead != null) { lead = lead.next; slow = slow.next; }

// 3. cycle -- they meet iff one exists
while (fast != null && fast.next != null) {
    slow = slow.next; fast = fast.next.next;
    if (slow == fast) return true;
}
""")
   + p("<strong><code>while (fast != null &amp;&amp; fast.next != null)</code></strong> "
       "is the guard, and both halves are required — this is [[bounds]]'s "
       "check-before-you-read applied to pointers. Checking only <code>fast</code> "
       "throws on the last node of an even-length list, and it is the single most "
       "common NullPointerException in this topic.")
   + p("For the <em>start</em> of the cycle, the second phase of Floyd's algorithm: "
       "after the meeting, reset one pointer to the head and advance both one step at a "
       "time. They meet at the cycle entry. The reason is arithmetic, not magic — if "
       "the tail has length <code>a</code> and the meeting point is <code>b</code> into "
       "a cycle of length <code>c</code>, then <code>a ≡ (c − b) mod c</code>, so both "
       "pointers arrive together.")),

  ("Merging, and the O(1)-space sort",
   p("Merging two sorted lists is the dummy-node pattern at its cleanest, and it is the "
     "building block for sorting one:")
   + code("""
ListNode merge(ListNode a, ListNode b) {
    ListNode dummy = new ListNode(0), tail = dummy;
    while (a != null && b != null) {
        if (a.val <= b.val) { tail.next = a; a = a.next; }
        else                { tail.next = b; b = b.next; }
        tail = tail.next;
    }
    tail.next = (a != null) ? a : b;      // attach the remainder wholesale
    return dummy.next;
}
""")
   + p("<code>tail.next = (a != null) ? a : b</code> is the line that makes this short: "
       "one of the two lists is already sorted and already linked, so there is nothing "
       "to copy. Looping over the remainder instead is a common and pointless "
       "expansion.")
   + p("<strong>sort-list</strong> is merge sort on this structure: split at the middle "
       "with the slow/fast trick, recurse, merge. It is the one sort that is O(n log n) "
       "time in O(1) auxiliary space here — quicksort needs random access and heapsort "
       "needs an array. Remember to <em>cut</em> the list at the midpoint "
       "(<code>prev.next = null</code>); forgetting that gives infinite recursion, not "
       "a wrong answer.")),
 ],
 "rules": [
  "Use a dummy head whenever the head can change. Return dummy.next, never head.",
  "After unlinking a node, do not advance prev.",
  "Reversal: save next, flip, advance prev, advance cur -- in that order.",
  "Guard with (fast != null && fast.next != null). Both halves.",
  "Attach the remainder of a merge in one assignment.",
  "Cut the list before recursing in sort-list.",
  "Draw the pointers on paper for a 2-node and a 3-node list before submitting.",
 ],
 "drill": "reverse-linked-list, merge-two-sorted-lists, linked-list-cycle-ii, "
          "remove-nth-node-from-end-of-list and sort-list, iteratively, in one sitting. "
          "Then reverse-nodes-in-k-group, which needs all of them at once.",
},

# ==========================================================================
{
 "slug": "mutable-state",
 "title": "State that changes underneath you",
 "one_line": "The read was correct when you wrote the line. Something else moved "
             "before it ran.",
 "why": "{{mistakes:mutable-state}} diagnosed mistakes and "
        "{{habits:mutable-state}} habits in accepted code, across "
        "{{problems:mutable-state}} problems and {{topics:mutable-state}} "
        "topics, are a value that was right when the algorithm was derived "
        "and wrong by the time it was read: an array used as both the input and "
        "the output buffer, a loop bound that calls size() on a collection the body "
        "is growing, a state computed into a local and never written back, a "
        "visited set that a refactor dropped. They are the hardest class in this "
        "book to find by rereading, because every individual line is correct. The "
        "bug lives in the order the lines run, which the code does not show. On "
        "total-characters-in-string-after-transformations the same aliasing error "
        "was made twice in one problem, at two different levels of the same "
        "solution.",
 "summary": (
  p('An algorithm derived on paper is a set of equations. '
    '<code>prefix[i] = prefix[i-1] * a[i]</code> is true as a statement about '
    'values. Turning it into code adds something the equation never had: a '
    'moment in time at which each name is read, and another at which it is '
    'written.') +
  p('Everything in this lesson is a place where those moments got '
    'interleaved. The equation stays on the screen looking correct while the '
    'value behind one of its names has already been replaced. Nothing about '
    'the syntax records that.') +
  p('The defence is a habit rather than a check: <strong>know, for every '
    'mutable thing in a loop, whether the body reads it, writes it, or '
    'both</strong> &mdash; and make sure that at most one of your structures '
    'is in the "both" column.')
 ),
 "used_for": [
  ('Prefix, suffix and rolling computations',
   'The classic place to save memory by reusing the input array, and the '
   'classic place it breaks.'),
  ('Matrix operations that produce a matrix',
   'Squaring, transposing and rotating all read cells they have already '
   'written unless you say otherwise.'),
  ('Level-order traversals',
   'The queue you are draining is the queue you are filling.'),
  ('Backtracking',
   'Shared state must be restored exactly, on every path out, including the '
   'early returns.'),
  ('Anything holding state across calls',
   'Design-a-structure problems, where a field survives between operations '
   'and must be written back.'),
  ('String matching with a carried pointer',
   'A partial match that fails leaves the pointer somewhere that the next '
   'iteration assumes it is not.'),
 ],
 "patterns": [
  ('The first element is right and the error compounds along the array',
   'You are reading a cell you already overwrote.'),
  ('A loop that should run k times runs fewer, or does not stop',
   'The bound calls a method on the collection the body is changing.'),
  ('The first query is right and every one after it is wrong',
   'Something was computed and never written back.'),
  ('A rewrite that fixed one thing broke something the old version handled',
   'The old version had a reset, a copy or a visited set that the rewrite '
   'dropped.'),
  ('The answer is right for one test and wrong when the same object is reused',
   'State carried over between runs that should have been reset.'),
  ('Backtracking that returns wrong counts but never crashes',
   'A path that returns early without undoing its mutation.'),
 ],
 "match": r"alias|still being read|(wrote|writes|writing|written) .{0,40}(into|to) "
          r"the (same|array|matrix|row|grid|map|list)|"
          r"read(s|ing)? .{0,45}(already|just|partially) (updated|overwritten|"
          r"written|modified|mutated)|"
          r"overwr(ote|ite|ites|itten) .{0,40}(before|while|still|that|which)|"
          r"modif(y|ied|ies|ying) .{0,30}(while|during) (iterat|scan|loop)|"
          r"mutat(e|ed|es|ing) .{0,30}(while|during) (iterat|scanning|looping)|"
          r"ConcurrentModification|mutat(e|es|ed|ing) (the )?(shared|same|cached|underlying)|"
          r"shar(ed|es) (the same )?(mutable|reference|list|array|object)|shallow copy|"
          r"(without|no) (a )?(deep )?cop(y|ies)|same (list|array|object|map) (reference|instance)|"
          r"forgot to write|never (wrote|written) back|write.{0,15}back|"
          r"(size|length)\(\).{0,40}(shrink|grow|chang|mutat)|snapshot|"
          r"restore(s|d)? .{0,20}(the )?(array|state|visited|indegree)|"
          r"(stale|reused) (state|visited|dp|seen|memo)|not reset|never reset|"
          r"failed to reset|reset .{0,25}between",
 "basics": [

  ("Reading a buffer you have already written",
   diagrams.aliased_write() +
   p("From <em>product-of-array-except-self</em>: the <code>result</code> array "
     "was reused in place as the running prefix-product array to save memory, then "
     "overwritten ascending. Every cell after the first read a value that the "
     "previous iteration had already replaced.")
   + p("The equation <code>result[i] = result[i-1] * nums[i]</code> is fine. The "
       "code is fine <em>if</em> <code>result[i-1]</code> still holds a prefix "
       "product when cell <code>i</code> is computed &mdash; which is a claim about "
       "iteration order that appears nowhere in the line.")
   + p("The same error appears one level up in "
       "<em>total-characters-in-string-after-transformations</em>, where the "
       "matrix-squaring step wrote <code>transformationMatrix[i][j] = newV</code> "
       "directly into the matrix it was still reading from. The analysis notes it "
       "as the <q>same aliasing bug</q> recurring &mdash; the same mistake, twice, "
       "inside one problem.")
   + p("<strong>In-place is an optimisation, and like every optimisation it needs "
       "a reason and a proof.</strong> The proof is: every read of a cell happens "
       "strictly before the write that lands on it. Sometimes that is true by "
       "iterating in the other direction; sometimes it is only true with a second "
       "array. Write the second array first, get it accepted, and only then "
       "collapse it &mdash; and when you collapse it, state the direction argument "
       "in a comment, because it is the only record that the collapse was "
       "deliberate.")
   + code("""
// correct by construction: two arrays, no ordering claim needed
int[] prefix = new int[n];
prefix[0] = 1;
for (int i = 1; i < n; i++) prefix[i] = prefix[i-1] * nums[i-1];

// in place, and only correct because nothing reads result[j] for j > i afterwards
int suffix = 1;
for (int i = n - 1; i >= 0; i--) { result[i] = prefix[i] * suffix; suffix *= nums[i]; }
""")),

  ("A bound that moves",
   code("""
void drain(Queue<Integer> q, PriorityQueue<Integer> pq, int child) {
    for (int i = 0; i < q.size(); i++) { q.add(child); }   // bound grows
    for (int i = 0; i < pq.size() / 2; i++) pq.poll();     // bound shrinks
}
""")
   + p("Both are yours &mdash; the first from "
       "<em>maximum-level-sum-of-a-binary-tree</em>, where the loop was meant to "
       "process exactly one level and instead kept absorbing the children it was "
       "enqueueing; the second from <em>find-median-from-data-stream</em>, where a "
       "loop intended to run three times ran one and a half.")
   + p("<code>q.size()</code> in the condition is re-evaluated on every iteration. "
       "That is not a subtlety of Java; it is what a <code>for</code> condition "
       "means. It only surprises because the mental model of the loop is "
       "&ldquo;repeat this many times&rdquo;, and the code says "
       "&ldquo;repeat while this is true&rdquo;.")
   + code("""
void level(Queue<Integer> q) {
    final int levelSize = q.size();           // read once, before mutating
    for (int i = 0; i < levelSize; i++) { q.add(q.poll()); }
}
""")
   + p("<strong>Any loop bound that calls a method on a collection the body "
       "mutates is wrong.</strong> Snapshot it into a <code>final</code> local. "
       "The <code>final</code> is not ceremony &mdash; it is the thing that makes "
       "a later edit reintroducing the mutation fail to compile. The same rule "
       "appears in [[wrong-name]], from the other direction: there it is about "
       "which variable the bound names, here about when it is read.")),

  ("Computed, and never written back",
   p("Two problems, one shape:")
   + ul("<em>cinema-seat-allocation</em>: a bitmask rewrite read the row's state "
        "out of the map, computed a new state locally by clearing bits, and never "
        "put the new value back. Every subsequent query saw the original row.",
        "<em>shortest-path-in-a-weighted-tree</em>: an edge-weight update read "
        "<code>oldWeight</code> to compute the delta and never wrote the new "
        "weight, so a second update on the same edge computed its delta from a "
        "stale base.")
   + p("Both are the read-modify-write cycle with the write missing, and both have "
       "the same tell: <strong>the first operation is correct and every one after "
       "it is wrong.</strong> That signature is worth memorising, because it "
       "points straight at persistent state rather than at the arithmetic, which "
       "is where the attention naturally goes.")
   + p("Java makes this easy to write by accident because reading a boxed value "
       "out of a map gives you a copy, while reading an array or an object gives "
       "you a reference. <code>map.get(k)</code> then mutating the local does "
       "nothing; <code>arr[i]</code> then mutating the element changes the array. "
       "The two look identical on the page.")
   + code("""
int state = rows.get(r);          // a copy
state &= ~mask;                   // changes the copy
rows.put(r, state);               // the line that is easy to forget
""")
   + p("<strong>Write the put on the same line-group as the get, before filling in "
       "the middle.</strong> A read-modify-write is three lines that belong "
       "together; typing them in order and then editing the middle one is the "
       "cheapest possible defence.")),

  ("State that must be reset",
   p("The third family is state that is correct at the start of a run and must be "
     "returned to that condition &mdash; between iterations, between test cases, or "
     "on the way out of a recursive branch.")
   + ul("<em>find-the-index-of-the-first-occurrence-in-a-string</em>: a needle "
        "pointer advanced on each character match and was never reset on a "
        "mismatch, so a partial match that failed part-way was never abandoned. "
        "The pointer carried a claim about the previous alignment into the next "
        "one.",
        "<em>course-schedule</em>: fixing the cycle-detection condition also "
        "dropped the per-traversal <code>visited</code> set that the previous "
        "attempt had, so the corrected traversal re-enqueued nodes it had already "
        "processed. The fix was right; what went with it was not.",
        "<em>maximum-profit-from-valid-topological-orders</em> (a habit in "
        "accepted code): the shared <code>indegree[]</code> array is mutated in "
        "place and manually restored after each recursive branch.")
   + p("The last one is worth separating, because it is the correct version of "
       "this pattern and still a liability. Mutate-and-restore works, and it costs "
       "you a proof obligation on every exit path from the branch &mdash; including "
       "the early returns you add later, which is how it eventually breaks. Where "
       "the state is small, passing an immutable value down is shorter and needs "
       "no proof:")
   + code("""
int[] indegree;

void visit(int v, int remaining) {
    // mutate and restore: correct, and every future early return is a bug
    indegree[v]--;  visit(v, remaining);  indegree[v]++;

    // no restoration needed: the value only exists on this path
    visit(v, remaining - 1);
}
""")
   + p("The <em>course-schedule</em> entry generalises into the most useful rule "
       "here: <strong>when a fix and a rewrite happen in the same submission, the "
       "thing that breaks is whatever the old version did that the new one "
       "forgot.</strong> Diff your own two versions before submitting, not after. "
       "This book renders that diff for every failed attempt you have on record; "
       "reading a few of them is the fastest way to see how much a rewrite "
       "silently drops.")),

  ("The audit, in one pass",
   p("For each loop or recursive body, put every mutable name it touches into one "
     "of three columns:")
   + table(("Column", "What to check", "Typical bug"), [
       ("read only", "nothing", "&mdash;"),
       ("written only", "is every path writing it?",
        "the missing write-back"),
       ("both", "does every read precede the write that lands on it?",
        "aliasing, moving bounds, missing reset"),
     ])
   + p("The third column should have one entry, or zero. When it has three, the "
       "body is doing too much and the interleaving is no longer something you can "
       "hold in your head &mdash; split it, or introduce the second array and stop "
       "paying for the optimisation.")),
 ],
 "rules": [
  "Before writing a loop, classify each mutable name as read, written, or both. Keep the 'both' column at one entry.",
  "In-place is an optimisation. Write the two-array version first, get it accepted, then collapse it with a stated reason.",
  "When you do write in place, put the ordering argument in a comment. It is the only record that it was deliberate.",
  "Snapshot any loop bound that calls a method on a collection the body mutates, into a final local.",
  "Type read-modify-write as three lines at once, then fill in the middle.",
  "First operation right, all later ones wrong, means a missing write-back. Look at persistence, not arithmetic.",
  "Prefer passing a value down to mutating shared state and restoring it. Restoration is an obligation on every exit path.",
  "When a submission both fixes and rewrites, diff it against the previous one and look for what was dropped.",
 ],
 "drill": "Rewrite product-of-array-except-self twice: once with two auxiliary "
          "arrays and no in-place trick, once in place with a comment stating why "
          "each read precedes its write. Then take maximum-level-sum-of-a-binary-"
          "tree and find every loop bound in your last twenty submissions that "
          "calls size() or length() on something the body changes. Finally, open "
          "the rendered diff for the course-schedule attempts in this book and "
          "write down, in one sentence, what the rewrite dropped.",
},
# ==========================================================================
{
 "slug": "wrong-name",
 "title": "The index you meant: loop variables and the wrong name",
 "one_line": "It compiles, it runs, it reads a real element every time -- just never "
             "the one you meant.",
 "why": "{{mistakes:wrong-name}} diagnosed mistakes across "
        "{{problems:wrong-name}} problems and {{topics:wrong-name}} topics "
        "are a name, not an "
        "algorithm: bank[i] where j was meant, containsKey(i) where nums[i] was meant, "
        "preMax[i] in a loop copy-pasted to build postMin, a loop bound written in "
        "terms of itself. These cost the same attempt as a wrong algorithm and take "
        "longer to find, because the code looks right and the output is merely wrong. "
        "One of them survived four consecutive submissions while unrelated symptoms "
        "were patched around it, and the analysis records another recurring in a later, "
        "independent rewrite of a file where it had already been fixed once.",
 "summary": (
  p('This is not an algorithms lesson. It is about the largest single class '
    'of bug in your export that has no algorithmic content at all: reading '
    'the right structure with the wrong subscript.') +
  p('These bugs share a signature. They <strong>compile</strong>, because '
    'every index in the expression is an <code>int</code> and every array is '
    'an array. They <strong>run</strong>, because the wrong index is usually '
    'still in range. And they produce <strong>plausible output</strong>, '
    'because a real element was read &mdash; just not the one the algorithm '
    'needed. Nothing about the failure points at the line that caused it.') +
  p('The fix is not to be more careful. It is to make the two things '
    'unconfusable: name every index for what it ranges over, and let the '
    'wrong pairing look wrong on the page.')
 ),
 "used_for": [
  ('Any nested loop over two different collections',
   'The outer and inner index range over different spaces; only names keep '
   'them apart.'),
  ('Two-pointer scans',
   'l and r are the same type over the same array, and swapping them is '
   'silent.'),
  ('A loop body copy-pasted to build a second array',
   'The most reliable producer of this bug in your history. The target name '
   'is what the paste forgets.'),
  ('Anything indexed by value rather than position',
   'Maps and counting arrays, where the loop index is a valid-looking key.'),
  ('Recursion that carries an offset',
   'The local index and the global index are both small integers and both '
   'in scope.'),
  ('A single loop over one array',
   'The one case that is genuinely safe. If your loop is this shape, spend '
   'the attention elsewhere.'),
 ],
 "patterns": [
  ('Your answer is plausible but wrong, and off by a value rather than a count',
   'Suspect a subscript before you suspect the algorithm.'),
  ('Two attempts in a row fixed a symptom and did not help',
   'Stop patching. Read every subscript in the block aloud as "which space '
   'is this?"'),
  ('You just copy-pasted a loop and changed the condition',
   'Check the write target. That is the half a paste forgets.'),
  ('Runtime error, index out of bounds, on the first line that reads an array',
   'The subscript is from a different space, and that space is larger.'),
  ('The code works on the sample and fails on a longer input',
   'A wrong index that stays in range on small inputs.'),
  ('You have used i for two different things in one method',
   'Rename now, before the bug rather than after it.'),
 ],
 "match": r"wrong[- ](loop |array |index |pointer )?variable|loop variable|"
          r"instead of (the )?(its own|the actual|the current|the loop|the real)|"
          r"reused the wrong|undeclared|name mismatch|\btypo\b|"
          r"instead of `?[a-z_]+\[|the loop \*?bound\*?|shadow",
 "basics": [

  ("Two loops, two index spaces, one name",
   diagrams.index_spaces() +
   p("Your <em>minimum-genetic-mutation</em> submission is the clean specimen. An "
     "outer loop ran over the eight character positions of a gene string; an inner "
     "loop was meant to run over the entries of the bank. The inner loop indexed "
     "<code>bank[i]</code>.")
   + code("""
for (int i = 0; i < 8; i++)             // i: character positions, 0..7
    for (int j = 0; j < bank.length; j++)
        if (matches(bank[i], cur))      // WRONG: bank has an entry 0..3
            ...
""", compiles=False)
   + p("<code>bank[i]</code> is a valid expression. For <code>i &lt; 4</code> it even "
       "reads a real bank entry, so the code runs and returns something. There is no "
       "signal anywhere except a wrong answer.")
   + p("The rule that removes this: <strong>an index is named for what it ranges "
       "over, not for its depth in the nesting.</strong> <code>i</code> and "
       "<code>j</code> carry no information, so they cannot contradict a misuse. "
       "<code>pos</code> and <code>entry</code> can:")
   + code("""
for (int pos = 0; pos < 8; pos++)
    for (int entry = 0; entry < bank.length; entry++)
        if (matches(bank[pos], cur))    // reads wrong: a position indexing entries
""", compiles=False)
   + p("This is the whole technique. It costs six characters and it converts a "
       "silent wrong answer into something you notice while typing. Keep "
       "<code>i</code> only where there is exactly one index in scope.")),

  ("Value or position: the second question every subscript asks",
   p("The other half of the family is not confusing two loops. It is confusing "
     "<em>where</em> something is with <em>what</em> it is &mdash; and in Java both "
     "are <code>int</code>.")
   + table(("Written", "Reads", "Meant"), [
       ("map.containsKey(i)", "is the position a key?", "map.containsKey(nums[i])"),
       ("count.getOrDefault(count, 0)", "the map as its own key",
        "count.getOrDefault(num, 0)"),
       ("freq[i]++", "count of position i", "freq[s.charAt(i) - 'a']++"),
       ("return r;", "the index it stopped at", "return nums[r];"),
       ("ansIndex = max(l, ansIndex)", "the search boundary", "max(mid, ansIndex)"),
       ("left.get(left.lastKey())", "how many times it occurs", "left.lastKey()"),
     ])
   + p("Every row is from your own export. The <em>top-k-frequent-elements</em> row "
       "&mdash; a <code>HashMap</code> passed as its own lookup key &mdash; survived "
       "four consecutive submissions: a null-bucket exception was fixed by adding a "
       "null check, then bucket-scan conditions were adjusted, while the counting "
       "itself had been broken from the first line. Each patch made the symptom move "
       "without making the answer right, which is the tell that you are editing the "
       "wrong line.")
   + p("<strong>The check, and it takes five seconds.</strong> Point at a subscript "
       "and say out loud what space it belongs to. &ldquo;<code>bank</code> is "
       "indexed by entry; <code>i</code> is a position; those are different.&rdquo; "
       "You cannot do this silently &mdash; reading is exactly the faculty that "
       "auto-corrects the bug &mdash; but you also cannot say a wrong pairing out "
       "loud without hearing it.")),

  ("The copy-paste, and what it forgets",
   p("The single most productive source of these in your history is a loop pasted "
     "to build a second thing. The paste updates the interesting parts &mdash; the "
     "direction, the comparison &mdash; and leaves the write target pointing at the "
     "original array.")
   + code("""
for (int i = 0; i < n; i++)      { max = Math.max(max, a[i]); preMax[i]  = max; }
for (int i = n - 1; i >= 0; i--) { min = Math.min(min, a[i]); preMax[i]  = min; }
//                                                            ^^^^^^ never renamed
""")
   + p("The analysis of that submission puts it exactly: the second loop &ldquo;was "
       "copy-pasted from the first and never had its target array renamed&rdquo;. The "
       "same shape appears in <em>finding-mk-average</em>, where the right-bucket "
       "rebalance branch was pasted from the left-bucket one and left reading "
       "<code>left.getOrDefault(...)</code>, silently corrupting counts; and in a "
       "Dijkstra variant that returned <code>dp[0]</code>, the source, instead of "
       "<code>dp[n-1]</code>, the destination.")
   + p("<strong>The habit that fixes it:</strong> after pasting a block, edit the "
       "write targets <em>first</em>, before you touch anything else. They are the "
       "part with no compiler support and no test coverage, and they are the part "
       "your attention has already skipped past on its way to the logic.")
   + p("The stronger version is to not paste. Two loops that differ only in "
       "direction and a comparison are one method called twice, and a method makes "
       "the target a parameter &mdash; which the compiler then checks:")
   + code("""
int[] scan(int[] a, boolean forward, IntBinaryOperator pick) { ... }
int[] preMax  = scan(a, true,  Math::max);
int[] postMin = scan(a, false, Math::min);
""", compiles=False)),

  ("Bounds that refer to the wrong thing",
   p("The loop header has the same failure mode as the loop body, with one extra "
     "trick available to it: a bound can refer to the variable it is bounding, or to "
     "a collection that is changing underneath it.")
   + code("""
for (int j = i; j < j + k; j++) ...        // j < j + k  is  0 < k  -- always true
for (int i = 0; i < counts; i++) ...       // the array, not counts.length
for (int i = 0; i < pq.size() / 2; i++) pq.poll();   // size() shrinks as you poll
""", compiles=False)
   + p("All three are yours. The first, from "
       "<em>adjacent-increasing-subarrays-detection-i</em>, is the interesting one: "
       "<code>j &lt; j + k</code> is not a bound at all, it is the constant "
       "<code>0 &lt; k</code>, so the intended limit was never enforced and the loop "
       "ran on whatever the body's own guards happened to stop. The compiler is "
       "content; the expression is well-typed and its operands are in scope.")
   + p("The third is subtler and comes from <em>find-median-from-data-stream</em>. "
       "<code>pq.size()</code> is re-evaluated every iteration, and <code>poll()</code> "
       "shrinks it, so a loop intended to run three times runs one and a half. "
       "<strong>Any loop bound that calls a method on a collection the body mutates "
       "is wrong.</strong> Snapshot it:")
   + code("""
final int half = pq.size() / 2;            // read once, before mutating
for (int i = 0; i < half; i++) pq.poll();
""")
   + p("A related near-miss from the same family: a name that differs from the one "
       "you declared by a single character. <code>distance</code> for "
       "<code>distances</code>, <code>count</code> for <code>counts</code>. Those at "
       "least fail to compile &mdash; which puts them in [[edit-hygiene]], not this one. The "
       "dangerous ones are the pairs where both names exist.")),

  ("What to do when the answer is wrong and the algorithm is right",
   p("This lesson has a debugging procedure, because that is when it is needed. "
     "Two failed patches on the same problem is the signal to run it &mdash; your "
     "export contains several runs of four or five submissions where every attempt "
     "moved a symptom and the real subscript was never touched.")
   + p("<strong>Stop editing.</strong> Take the block that computes the wrong "
       "value and, for each subscript in it:")
   + ul("Name the space the index ranges over, out loud.",
        "Name the space the structure is indexed by.",
        "If those two sentences differ, you have found it.")
   + p("Then check the writes separately from the reads. A read from the wrong "
       "place gives a wrong answer; a write to the wrong place corrupts state that "
       "something else will read later, which is why those take longest to find.")
   + p("If the block survives that pass, the algorithm really is wrong and you "
       "should go back to the statement &mdash; but run the pass first. It takes a "
       "minute, and on this evidence it is where the bug is more often than not.")),
 ],
 "rules": [
  "Name every index for what it ranges over. Keep i only where exactly one index is in scope.",
  "Before submitting, point at each subscript and say which space it belongs to. Out loud.",
  "After pasting a loop, rename the write targets first, before touching the logic.",
  "Two loops differing only in direction are one method called twice. Let the compiler check the target.",
  "A subscript is a position or a value. Decide which the structure wants, every time.",
  "Never write a loop bound in terms of the variable it bounds.",
  "Snapshot any bound that calls a method on a collection the body mutates.",
  "Two failed patches on one problem: stop editing and audit the subscripts instead.",
 ],
 "drill": "Take the four problems where this cost you the most -- "
          "top-k-frequent-elements, majority-element, minimum-genetic-mutation and "
          "adjacent-increasing-subarrays-detection-i -- and rewrite each from scratch "
          "with no index named i or j. Then reread your last ten accepted "
          "submissions and rename every index in them; the point is not the rename, "
          "it is noticing how many were doing two jobs.",
},
# ==========================================================================
{
 "slug": "edit-hygiene",
 "title": "Edit hygiene: the 242 compile errors",
 "one_line": "Not an algorithms lesson. 242 submissions never ran, and every one cost an attempt.",
 "why": "{{status:Compile Error}} Compile Errors out of "
        "{{overview:total_submissions}} submissions — {{share:Compile Error}} of "
        "everything you have ever submitted. The causes logged in your "
        "findings are half-finished renames (queries/query, an undeclared `stats`), a "
        "`while { }` with no condition, a Comparator lambda returning long, a zero-arg "
        "`List.sort()`. None of these are thinking errors. All of them are the judge "
        "being used as a compiler.",
 "summary": (
  p('This is not an algorithms lesson. 242 submissions in this export never '
     'compiled, and a submission that never runs costs exactly the same '
     'attempt as one that runs and is wrong.') +
  p('The causes are mechanical — an edit applied in the wrong scope, a '
     'helper renamed on one side only, a brace left unbalanced after a paste '
     '— and so is the fix. Compile locally before you submit. The second '
     'half of the lesson is the related habit: patching the symptom the '
     'failing case shows instead of the cause it points at.')
 ),
 "used_for": [
  ('Before every submission',
   'One local compile catches this whole class. It costs seconds; the '
    'judge charges an attempt.'),
  ('After pasting or moving a block',
   'The most common single source: a paste that lands inside the wrong '
    'scope.'),
  ('After renaming anything',
   'Rename the declaration and every call site in one edit, not in two.'),
  ("After changing a data structure's type",
   'The compiler will find every place that still assumes the old one — if '
    'you let it.'),
  ('When a fix “should have worked”',
   'Re-read the failing case before editing again. Two symptom patches in '
    'a row means the cause is upstream of both.'),
 ],
 "patterns": [
  ('Your submission returns Compile Error',
   'Nothing about the algorithm was tested. Compile locally, then '
    'resubmit.'),
  ('You are on attempt three or more of the same problem',
   'Stop editing. Write down what the failing case actually is, then '
    'change exactly one thing.'),
  ('The fix is “add a null check” for the third time',
   'You are patching symptoms; the cause is upstream of all three.'),
  ("You changed a helper's signature",
   'Every call site, in the same edit.'),
  ('The verdict changed from Wrong Answer to Runtime Error',
   'That is progress information, not a setback: the last edit moved the '
    'failure, so read where it moved to.'),
 ],
 "match": r"compile|rename|undeclared|cannot find symbol|does not (exist|"
          r"compile)|mid-edit|typo|missing (parenthes|semicolon|brace)|"
          r"copy.?paste|stale variable|wrong loop variable|scaffolding|"
          r"no condition|missing (import|closing|the `?\)|brace|paren)|"
          r"forgot `?use |dropped again|stray (extra |literal )?(\)|\}|character|brace)|"
          r"unfinished (method|stub)|half-written|never (initiali[sz]ed|declared)|"
          r"no declaration|left (a |the )?debug|System\.out\.print|duplicate (nested|`case)|"
          r"illegal .{0,14}syntax|omitting the `?class|not valid Java|implicitly narrow|"
          r"before it was declared|leftover|paste artifact|fat.finger|editing slip|"
          r"pasted inside|wrapping the real function",
 "basics": [
  ("What it actually costs",
   diagrams.submit_loop() +
   p("A compile error is not free. It burns a submission, it puts a failed attempt on the "
     "record — which is what your first-attempt accept rate measures — and it breaks the "
     "debugging loop, because you go back to the editor with no information about whether "
     "the <em>logic</em> was right.")
   + p("At 4.6% of submissions, roughly one in every 22 attempts told you nothing at all.")),

  ("The fix is mechanical",
   ul("<strong>Compile locally before submitting.</strong> <code>javac Solution.java</code> "
      "takes under a second and catches every one of the errors in your log.",
      "<strong>Rename with the IDE, not by hand.</strong> Every logged rename failure — "
      "<code>queries</code>/<code>query</code>, the undeclared <code>stats</code> — is a "
      "manual find-and-replace that missed a site. An IDE rename cannot miss one.",
      "<strong>Never submit mid-edit.</strong> The <code>while { }</code> with no "
      "condition in <code>number-of-days-between-two-dates</code> was submitted in the "
      "middle of a thought.")),

  ("The related habit: patching the symptom",
   p("Adjacent to the compile errors is a pattern worth naming, because it costs "
     "attempts the same way. In <code>block-placement-queries</code> a TLE was "
     "\"fixed\" once by stripping whitespace. In "
     "<code>concatenate-non-zero-digits</code> a lookup table was resized four times "
     "across four Runtime Errors. In <code>sum-of-subarray-minimums</code> an overflow "
     "was \"fixed\" by moving the modulus while the type stayed <code>int</code>.")
   + p("Each of those is a submission made without a hypothesis. The discipline is one "
       "sentence, written before you resubmit: <strong>\"I believe it failed because X, "
       "and this change addresses X.\"</strong> If you cannot complete that sentence, the "
       "next submission is a guess, and guesses are what your Wrong Answer counts are "
       "made of.")),

  ("The other side of it",
   p("Your debugging loop is genuinely fast — submit, read the verdict, patch, resubmit, "
     "often within a minute. That speed is an asset. The cost is that it is shallow: the "
     "same bug class (edge direction, DSU raw args, sentinel width) resurfaces in "
     "unrelated code months later, because each instance was patched rather than "
     "understood. Slowing down by one sentence per resubmission is the smallest change "
     "that turns a patch into a lesson.")),
 ],
 "rules": [
  "javac locally before every submission. One second, catches all 242.",
  "Rename via the IDE. Never by hand.",
  "Before resubmitting, complete: 'It failed because X, and this change addresses X.'",
  "If you cannot complete that sentence, do not submit — read the code instead.",
 ],
 "drill": "For one week, write the hypothesis sentence in a comment at the top of every "
          "resubmission. Delete it before submitting. The point is the writing, not the "
          "comment.",
},

{
 "slug": "post-solve-regression",
 "title": "After the green tick: the rewrite that broke what worked",
 "one_line": "The problem was already Accepted. Then you rewrote it, and the rewrite was wrong.",
 "why": "{{mistakes:post-solve-regression}} diagnosed mistakes across "
        "{{problems:post-solve-regression}} problems were made *after* the problem "
        "was already solved. That is the single largest slice of your export, and "
        "it is the one slice that cost you nothing on the scoreboard and everything "
        "in time: a `Set` swapped for a `List` that then double-counts, a Java "
        "solution ported to Python without `self`, a working stack rewritten as a "
        "counter pair that loses the running maximum. You are right to revisit "
        "solved problems -- that is where the learning is. The failure is treating "
        "the rewrite as an edit when it is a new solution.",
 "summary": "<p>Roughly one in five of your diagnosed mistakes happens on a problem "
            "you had already solved. These are post-solve submissions: you go back to "
            "optimise, to port to another language, or to re-solve from scratch as "
            "practice.</p>"
            "<p>That instinct is good and this lesson does not ask you to stop. It asks "
            "you to notice that you have an oracle sitting right there -- the accepted "
            "version -- and that you almost never use it. A rewrite is a new solution "
            "with an old solution available to check it against, and checking it "
            "against that costs less than the resubmission does.</p>",
 "used_for": [
  ("Optimising an accepted solution",
   "The accepted version is your reference implementation. Keep it open, and diff behaviour, not just code."),
  ("Porting to another language",
   "The signature and the call convention are part of the port, and they are the part you skip."),
  ("Re-solving from scratch as practice",
   "Deliberate practice is the whole point. Just do not submit the practice attempt as if it were a fix."),
  ("Cleaning up code you are not happy with",
   "A readability rewrite changes behaviour more often than a performance one, because nobody expects it to."),
 ],
 "patterns": [
  ("You are editing a problem that already shows Accepted",
   "You are in the highest-risk mode in your history. Slow down by exactly one step: keep the old version."),
  ("The rewrite changes the algorithm and the language at once",
   "Two changes, one submission, no bisect. Split them."),
  ("The rewrite fails twice in a row",
   "Go back to the accepted version and start again from it. Patching a broken rewrite is how three attempts become seven."),
  ("You are simplifying an expression you no longer remember deriving",
   "That is where the division you dropped was load-bearing. Re-derive before you simplify."),
 ],
 "match": r"post.?solve|post_solve|already (solved|accepted|working)|already-Accepted|"
          r"revisit(ed|ing)?\b|re-?introduc|rewrite (that )?(introduced|broke)|"
          r"refactor(ing)? introduced|on a problem already",
 "basics": [
  ("The mode you are in when it happens",
   "<p>A post-solve submission is any submission on a problem whose Accepted verdict "
   "you already have. Your export separates them, and the separation is stark: these "
   "attempts cost no solve-rate and appear in no first-attempt metric, so nothing in "
   "the scoreboard ever told you they were going wrong.</p>"
   "<p>Three shapes account for nearly all of them.</p>"
   "<p><strong>The port.</strong> You have Java that works and you rewrite it in "
   "Python, Rust or C++. On <code>stone-game-ii</code> the port went out as a bare "
   "top-level function with no <code>class Solution</code> wrapper; the next attempt "
   "added the wrapper but omitted Python's explicit <code>self</code>; the attempt "
   "after that stripped the type hints and still omitted <code>self</code>. Three "
   "Runtime Errors in a row, none of them about the algorithm, which had been correct "
   "for months.</p>"
   "<p><strong>The optimisation.</strong> You replace a working structure with a "
   "faster one. On <code>first-unique-character-in-a-string</code> a refactor "
   "introduced <code>unordered_map&lt;int,int&gt; c</code> and then counted with "
   "<code>c[i]++</code> instead of <code>c[s[i]]++</code> -- keyed on position rather "
   "than on the letter, which is not a slower answer but a different one.</p>"
   "<p><strong>The rewrite.</strong> You throw the solution away and solve it again. "
   "On <code>longest-valid-parentheses</code> a stack solution that worked was "
   "replaced by a pair of counters, which loses the running maximum across groups; "
   "the follow-up rewrite added an accumulator and was still wrong, and the session "
   "ended without recovering the working answer.</p>"),
  ("You already have the oracle",
   "<p>This is the part that makes post-solve regressions different from every other "
   "class of mistake in this book. Everywhere else, when you want to know whether your "
   "code is right, you have to reason about it. Here you do not: there is a program "
   "sitting in your submission history that is known to be correct on this exact "
   "problem.</p>"
   "<p>So run both. Generate a few hundred small random inputs, run the old solution "
   "and the new one, and compare outputs. Small is the operative word -- the "
   "disagreements show up on <code>n = 0</code>, <code>n = 1</code> and repeated "
   "elements, not on the large cases. This is differential testing, and it takes about "
   "twenty lines of scaffolding that you write once and keep.</p>"
   "<p>It catches the entire class. The <code>c[i]++</code> keying bug, the dropped "
   "<code>// self._prefix[~k]</code> division on "
   "<code>product-of-the-last-k-numbers</code>, the pivot double-counted on "
   "<code>max-points-on-a-line</code> -- every one of them disagrees with the accepted "
   "version on inputs a random generator produces in its first dozen tries.</p>"),
  ("One change per submission",
   "<p>The rewrites that took the most attempts to recover are the ones that changed "
   "several things at once. On <code>basic-calculator</code>, a same-day revisit four "
   "months after the first solve rebuilt the parser around a <code>Token</code> class "
   "carrying multiply and divide types the problem does not have, and at the same time "
   "tried to encode unary minus with a boolean flag flipped in several places. When "
   "that failed there was no way to tell which half was wrong, so the flag became an "
   "int counter, and then it was abandoned.</p>"
   "<p>The rule is the one you would apply to a commit. Change the data structure, or "
   "change the language, or change the algorithm -- not two of them in one "
   "submission. Not because a big rewrite is wrong, but because when it fails you want "
   "the failure to name its cause.</p>"),
  ("When to stop and roll back",
   "<p>There is a specific moment worth learning to recognise: the second consecutive "
   "failure of a rewrite. At that point you are debugging code you wrote ten minutes "
   "ago against a problem you solved months ago, and the accepted version is still "
   "sitting there.</p>"
   "<p>Go back to it. Start the rewrite again from the working code, changing one "
   "thing. The alternative is on the record: <code>reconstruct-itinerary</code> ran "
   "four attempts deep into a phantom-edge balancing scheme, fixing a wrap-around "
   "off-by-one inside a strategy that was then abandoned wholesale for a direct "
   "Hierholzer walk. Every attempt after the second was spent on an approach that did "
   "not survive.</p>"),
 ],
 "rules": [
  "Before a post-solve rewrite, keep the accepted version open. It is your oracle, not just your history.",
  "Diff the rewrite against the accepted version on a few hundred small random inputs before submitting.",
  "One change per submission: the structure, or the language, or the algorithm. Never two.",
  "Second consecutive failure of a rewrite: roll back to the accepted version and restart from it.",
 ],
 "drill": "Pick three problems you have re-solved post-solve and write the twenty-line "
          "differential harness once: random small input, both solutions, compare. Keep "
          "it. Every future rewrite reuses it, and the whole class of bug in this lesson "
          "stops reaching the judge.",
},

{
 "slug": "derive-dont-guess",
 "title": "Guess and check: the constant you tuned until it passed",
 "one_line": "Four attempts, four different paddings, and the one that finally passed was the first one you tried.",
 "why": "{{mistakes:derive-dont-guess}} diagnosed mistakes across "
        "{{problems:derive-dont-guess}} problems are a value adjusted until the judge "
        "agreed rather than derived until it was right: a bound bumped from `10001` to "
        "`100001`, a `return result + 1` bolted onto a double-count, seven attempts of "
        "ad hoc wall detection on `trapping-rain-water`. The judge is a test suite, not "
        "a proof, and code that passes it by coincidence passes it silently.",
 "summary": "<p>This is a lesson about a debugging mode rather than an algorithm. It "
            "starts when a submission is close, and instead of asking why it is wrong "
            "you adjust something and resubmit to find out.</p>"
            "<p>The adjustment is usually small and usually plausible -- a bound, a "
            "constant, a comparison, a <code>+1</code>. Sometimes it passes. When it "
            "does, you have not learned what was wrong, and the export shows the "
            "cost: on the problems where this happened, the accepted submission is "
            "routinely a value you had already tried several attempts earlier.</p>",
 "used_for": [
  ("A submission that is wrong by a small, constant amount",
   "The strongest temptation to patch, and the strongest signal of a specific structural cause."),
  ("Choosing an array size or a loop bound",
   "Derive it from the constraint line. A number that came from a failing test fits that test."),
  ("A formula you cannot re-derive on paper",
   "If you cannot get back to it, you cannot tell a typo in it from a truth."),
  ("Any fix whose whole content is a number",
   "Changing a literal is the cheapest edit to make and the most expensive one to be wrong about."),
 ],
 "patterns": [
  ("The fix under consideration is adding or subtracting one",
   "You have found the symptom. Find what is counted twice, or not at all."),
  ("You are on the third variation of the same idea",
   "Stop submitting. The idea is what is wrong, not this instance of it."),
  ("A constant in your code has no name and no derivation",
   "Say out loud what it means. If you cannot, it is a bug that has not failed yet."),
  ("The accepted version is something you already tried",
   "That is the signature of guess-and-check, and it means the problem is still not understood."),
 ],
 "match": r"guess(ed|ing|es)?\b|guess-and-check|ad hoc|ad-hoc|heuristic|"
          r"plausible.{0,14}(looking|but)|without (first )?deriv|rather than deriv|"
          r"did not derive|compensating constant|hard.?cod|bumped the|blindly|"
          r"trial.and.error|magic number|patched onto the symptom|"
          r"tried .{0,25}variations|happening to match|happened to match",
 "basics": [
  ("What it looks like from the outside",
   "<p><code>cracking-the-safe</code> is the clearest case in the export, because all "
   "four attempts are recorded. The Euler tour needs the start node's "
   "<code>n-1</code> characters appended to close the circuit. Instead the code "
   "appended one literal <code>\"0\"</code>. The attempts, in order:</p>"
   "<ol>"
   "<li>Replace the single append with <code>repeat(\"0\", n - 2)</code> -- the "
   "analysis records this as guessing the padding amount rather than deriving it.</li>"
   "<li>Add <code>&amp;&amp; k &gt; 1</code> to the guard. Changes which cases pad at "
   "all; does not change what the padding is.</li>"
   "<li>Remove the padding branch entirely and return the raw tour.</li>"
   "<li>Put back the <code>n - 2</code> padding under <code>if (n &gt; 2)</code> -- "
   "the same thing tried three attempts earlier -- and this time it passed.</li>"
   "</ol>"
   "<p>Four attempts, and the accepted code is attempt one. Nothing was learned in "
   "between, because no attempt was an answer to a question. Deriving the padding "
   "takes a minute: the tour visits every length-<code>n</code> string as an edge, "
   "the start node is a length-<code>(n-1)</code> string, and closing the circuit "
   "means writing it out. That derivation also tells you the answer for "
   "<code>k = 1</code> without a special case.</p>"),
  ("The compensating constant",
   "<p>The most recognisable shape: the answer is consistently off by a fixed amount, "
   "and the fix adjusts the answer rather than the cause.</p>"
   "<p>On <code>max-points-on-a-line</code>, a rewrite started the inner loop at "
   "<code>j = i</code>, which puts the pivot point into its own angle map, and then "
   "added <code>localMax + 1</code> to the result. Every count was one too high. The "
   "attempted fix was <code>return result + 1;</code> -- a second constant to "
   "compensate for the first. The accepted version instead excluded the pivot from "
   "its own map, at which point no constant is needed anywhere.</p>"
   "<p>An off-by-a-constant answer is the most informative failure you get. A wrong "
   "algorithm is usually wrong by varying amounts; a fixed offset means something "
   "specific is counted once too often or once too rarely, and it is findable. "
   "Cancelling it with a literal throws that information away and leaves code whose "
   "two errors happen to agree on the tests you ran.</p>"),
  ("Bounds that came from a failing test",
   "<p><code>first-missing-positive</code> was written with a scan bound of "
   "<code>10001</code>. The constraint line allows <code>nums.length</code> up to "
   "10&#8309;, so answers above 10001 were unreachable. The fix bumped the literal to "
   "<code>100001</code> and passed.</p>"
   "<p>It passes, and it is still wrong in the way that matters: the number is not "
   "connected to anything. The bound the problem actually implies is "
   "<code>nums.length + 1</code>, because among <code>n</code> integers the smallest "
   "missing positive cannot exceed <code>n + 1</code>. That version needs no literal "
   "at all, is smaller, and is correct for every input rather than for every input "
   "under a hundred thousand.</p>"
   "<p>The test: for each constant in your solution, say what it means in one phrase. "
   "&ldquo;One past the largest index&rdquo; is a meaning. &ldquo;Big enough&rdquo; is "
   "not.</p>"),
  ("The exit condition",
   "<p>Guess-and-check is not always wrong. Trying something to see what happens is a "
   "legitimate way to build intuition on a problem you do not yet understand. What "
   "makes it costly is having no exit condition, so let this be it: <strong>three "
   "attempts of the same shape, then stop and derive on paper.</strong></p>"
   "<p><code>trapping-rain-water</code> is the case for the rule. Seven attempts went "
   "into an ad hoc wall-detection scheme -- local maxima, a "
   "<code>highestLastWallHeight</code>, a <code>possibleWall</code> left at "
   "<code>-1</code> and then used as an index -- drifting across four rewrites without "
   "ever becoming correct. The bookkeeping got more elaborate each time because each "
   "attempt inherited the previous one's frame. Nothing in that sequence was going to "
   "converge, and the only move that helps at attempt three is the one that leaves the "
   "editor.</p>"),
 ],
 "rules": [
  "Every constant must have a one-phrase meaning. 'Big enough' is not one.",
  "An answer wrong by a fixed amount names its own cause. Find what is double-counted before you add a compensating term.",
  "Derive bounds from the constraint line, never from the test that failed.",
  "Three attempts of the same shape: stop submitting, derive on paper.",
 ],
 "drill": "Take `cracking-the-safe` and `first-missing-positive` and, without looking at "
          "your submissions, derive each bound from the problem statement in writing -- "
          "why the padding is the start node, why the answer cannot exceed `n + 1`. Then "
          "write the solution. The point is that the code follows the derivation.",
},

{
 "slug": "read-the-statement",
 "title": "Answering the exact question that was asked",
 "one_line": "Correct algorithm, correct code, wrong question -- and the judge only ever tells you the last part.",
 "why": "{{mistakes:read-the-statement}} diagnosed mistakes across "
        "{{problems:read-the-statement}} problems are cases where the algorithm was "
        "right and the answer was not: 0-indexed positions where the problem asks for "
        "1-indexed, duplicates in a result that must be distinct, `\"EAST\"` where the "
        "expected output is `\"East\"`, a digit sum checked where the problem said "
        "digit product. These are the cheapest mistakes in the book to eliminate, "
        "because they are all findable before you write a line of code.",
 "summary": "<p>Every problem has two specifications: the interesting one, about what "
            "to compute, and the boring one, about exactly what shape the answer takes "
            "and exactly how the method is called. You reliably read the first. The "
            "second is where this class of mistake lives.</p>"
            "<p>It is worth separating from ordinary bugs because the diagnosis is "
            "different. When the algorithm is wrong you debug the algorithm. When the "
            "contract is wrong the algorithm is perfect and re-reading the code will "
            "never show you the problem, because the code says what you meant.</p>",
 "used_for": [
  ("Before writing the first line",
   "The output contract costs thirty seconds to copy down and is the whole of this lesson."),
  ("Porting a solution to another language",
   "The signature is part of the port, and it is the part that gets skipped."),
  ("Problems whose output is a list",
   "Distinct or not, sorted or not, one entry per input or one per distinct value -- four decisions, all in the statement."),
  ("Problems with a stated edge convention",
   "Leading zeros, 1-based labels, empty-input results: stated explicitly, and easy to read past."),
 ],
 "patterns": [
  ("Your output is right but rejected",
   "Read the expected output of the failing example character by character. Case, order, indexing, duplicates."),
  ("A Runtime Error on a problem you have already solved elsewhere",
   "Suspect the call convention before the logic -- a missing wrapper class or receiver parameter."),
  ("The result has repeated entries and the statement says distinct",
   "The collection type is the bug, not the loop that filled it."),
  ("You are computing something adjacent to what was asked",
   "Sum where it said product, value where it said count. Re-read the sentence with the quantity in it."),
 ],
 "match": r"misread|misunderstood|misinterpret|problem (requires|defines|only asks|asks for|statement|says)|"
          r"required (output|format|method|signature|return|to)|expected (output|call|format)|"
          r"1-?indexed|0-?indexed|1-based|0-based|method (name|signature)|declared return type|"
          r"class Solution|`self`|call convention|wrong problem|submission box|correctly-cased|"
          r"what the problem|LeetCode (requires|defines|expects)|the actual question",
 "basics": [
  ("The output contract",
   "<p>Four decisions live in the statement and nowhere in your code's logic.</p>"
   "<p><strong>Indexing.</strong> <code>two-sum-ii</code> asks for 1-indexed "
   "positions; the submission returned <code>{i, j}</code>. <code>find-the-town-judge</code> "
   "labels people 1..N and the code used those labels directly as 0-indexed array "
   "subscripts, running off the end at label N. Both are one-character fixes and both "
   "cost an attempt.</p>"
   "<p><strong>Duplicates.</strong> <code>find-the-difference-of-two-arrays</code> "
   "requires distinct output. The code collected into <code>List&lt;Integer&gt;</code>, "
   "so a value appearing twice in <code>nums1</code> appeared twice in the answer. The "
   "fix was the collection type -- <code>Set</code> instead of <code>List</code> -- not "
   "anything in the algorithm.</p>"
   "<p><strong>Format.</strong> <code>walking-robot-simulation-ii</code> expects "
   "<code>\"East\"</code>; the code returned <code>\"EAST\"</code>.</p>"
   "<p><strong>Stated conventions.</strong> <code>valid-word-abbreviation</code> "
   "defines a leading-zero digit run such as <code>\"a01b\"</code> as invalid. The "
   "rule is in the statement; the code did not have it.</p>"),
  ("The signature contract",
   "<p>The harness calls your code in a specific way, and when you are writing in the "
   "language you always use, you never think about it. Port to another language and it "
   "becomes the first thing that breaks.</p>"
   "<p><code>stone-game-ii</code> is three consecutive Runtime Errors on this and "
   "nothing else: first a bare top-level function with no <code>class Solution</code>; "
   "then the class, but with <code>def stoneGameII(piles)</code> and no "
   "<code>self</code>; then the type hints removed and still no <code>self</code>. The "
   "algorithm was already accepted in Java.</p>"
   "<p>The same class, from the other direction: on "
   "<code>design-add-and-search-words-data-structure</code>, a fix changed "
   "<code>search</code>'s declared return type to <code>void</code>, which breaks the "
   "required boolean-returning signature no matter how good the trie underneath is. "
   "And on <code>number-of-closed-islands</code>, the submission was another problem's "
   "solution entirely, pasted into the wrong tab.</p>"),
  ("The quantity contract",
   "<p>The subtlest version: you compute a real quantity, carefully and correctly, and "
   "it is not the quantity in the sentence.</p>"
   "<p><code>smallest-divisible-digit-product-i</code> asks whether the digit product "
   "of <code>n</code> is divisible by <code>t</code>. The first attempt checked "
   "whether <code>n</code> itself was divisible by <code>t</code>; the second checked "
   "the digit <em>sum</em>. Two consecutive readings of the same sentence, two "
   "different quantities, neither the right one.</p>"
   "<p><code>longest-unequal-adjacent-groups-subsequence-i</code> is the same failure "
   "at the level of the whole task: it was read as &ldquo;pick the longest word from "
   "each run of equal groups&rdquo;, and a two-pass longest-word selector was built "
   "for it. The problem only asks to keep one representative per run. The rewrite "
   "that passed is a single pass, and it is shorter than the machinery built for the "
   "misreading.</p>"),
  ("The thirty-second habit that removes the class",
   "<p>Before writing anything, copy the output specification into a comment: the "
   "return type, the indexing base, whether the result must be distinct, whether it "
   "must be sorted, and the exact format of any string. Then run the first provided "
   "example by hand and compare it to the expected output character by "
   "character.</p>"
   "<p>This is not a proof technique and it is not clever. It is thirty seconds "
   "against a class of bug that in your history costs an attempt every time it "
   "appears, and that no amount of staring at the algorithm will ever reveal -- "
   "because the algorithm is right.</p>"),
 ],
 "rules": [
  "Copy the output spec into a comment before writing code: type, indexing base, distinct, sorted, exact string format.",
  "Run the first provided example by hand and compare character by character before submitting.",
  "When porting to another language, port the signature first and submit that skeleton in your head.",
  "Underline the quantity in the sentence -- sum, product, count, value -- and check your code computes that one.",
 ],
 "drill": "For the next ten problems, write the output contract as a comment before the "
          "first line of code, and delete it only when you submit. Then check the ten "
          "against `two-sum-ii`, `find-the-difference-of-two-arrays` and "
          "`walking-robot-simulation-ii`: every one of those three would have been "
          "caught by the comment.",
},

{
 "slug": "loop-bounds",
 "title": "The bound and the operator",
 "one_line": "`<` where you meant `<=`, and a range test joined by `||` that is true for every input.",
 "why": "{{mistakes:loop-bounds}} diagnosed mistakes across "
        "{{problems:loop-bounds}} problems are a loop that ran one step too far or "
        "stopped one step short, or a comparison with the wrong strictness: "
        "`i <= s.size()/2` undoing half a reversal, `l < r` leaving the last worker "
        "unqueued, `newX >= 0 || newX < m` letting every index through. The algorithm "
        "is right in all of them. One character is not.",
 "summary": "<p>Loop bounds and comparison operators are where a correct plan becomes "
            "an incorrect program. They are worth their own lesson because the fix is "
            "always one character, which makes them feel too small to have a method -- "
            "and because they are among the most frequent diagnoses in your "
            "export.</p>"
            "<p>Two habits remove most of them: writing every range half-open unless "
            "you can say why not, and checking each new loop at <code>n = 1</code> and "
            "<code>n = 2</code> before submitting.</p>",
 "used_for": [
  ("Every loop you write",
   "The bound and the operator are two decisions, and they are usually made without being noticed."),
  ("Two-dimensional bounds checks",
   "A grid guard is four comparisons, and the way they are joined matters as much as the comparisons."),
  ("Loops over a derived space",
   "When the loop walks values rather than positions, the array's length is the wrong bound."),
  ("Any loop touching the last element",
   "Half of these mistakes are about whether the final index is included."),
 ],
 "patterns": [
  ("The answer is right except at one end",
   "The bound, not the body. Check the first and last iterations by hand."),
  ("A bounds check that never seems to reject anything",
   "Look for `||` where the range needs `&&`. It is true for every input and silently does nothing."),
  ("Equal elements behave like unequal ones",
   "The comparison's strictness is the bug: `<` where `<=` was meant, or the reverse."),
  ("A loop guard using `<` when the range is inclusive",
   "The last candidate is never considered. This is the single most common shape here."),
 ],
 "match": r"off.by.one|loop (bound|condition|guard|termination)|"
          r"strict(ly)? (`?<|`?>|less|greater|inequality)|non-strict|"
          r"changed (both |the )?(comparison|bound|guard|loop condition)|"
          r"instead of `?&&|`?\|\|`? instead of|one (index |slot )?too (far|early|many)|"
          r"stops one|one extra|one index too|one node too|one step (early|too)|"
          r"upper bound|loop bound|the last (index|slot|element) ",
 "basics": [
  ("Half-open, unless you can say why not",
   "<p>Write <code>for (int i = 0; i &lt; n; i++)</code> and the bound is the size, "
   "the count of iterations is the size, and there is nothing to get wrong. Every "
   "<code>&lt;=</code> is a claim that the last index is one you want, and every one "
   "of them should be justifiable in a phrase.</p>"
   "<p>Both directions appear in your history. <code>reverse-string</code> used "
   "<code>i &lt;= s.size()/2</code>, performing one extra swap at the midpoint that "
   "undid part of the reversal for even-length input. <code>total-cost-to-hire-k-workers</code> "
   "went the other way: the refill guard was <code>l &lt; r</code>, so the case where "
   "exactly one worker sits outside both windows -- <code>l == r</code> -- was never "
   "queued. <code>first-missing-positive</code> made the same <code>l &lt; r</code> "
   "mistake in the cyclic sort, leaving the last slot unchecked.</p>"
   "<p>The rule is not that <code>&lt;=</code> is wrong. It is that half-open is the "
   "default, and a closed range is a decision you should be able to defend.</p>"),
  ("A range test is two comparisons joined by AND",
   "<p><code>maximum-number-of-points-from-grid-queries</code> guarded a grid access "
   "with:</p>"
   "<pre><code>if (newX &gt;= 0 || newX &lt; m &amp;&amp; newY &gt;= 0 || newY &lt; n)</code></pre>"
   "<p>Read it as the machine does. Every integer satisfies "
   "<code>newX &gt;= 0</code> or <code>newX &lt; m</code>, so the whole condition is "
   "true for every input and the guard rejects nothing. It crashed.</p>"
   "<p>The same substitution appears twice more. "
   "<code>maximize-active-section-with-trade-ii</code> bailed out when "
   "<code>left.counts.size() &lt;= 2 || right.counts.size() &lt;= 2</code>, refusing a "
   "valid merge whenever <em>either</em> side was short. "
   "<code>kth-largest-element-in-a-stream</code> carried the same OR-for-AND "
   "short-circuit through two submissions; the second only tightened "
   "<code>&gt;</code> to <code>&gt;=</code> and left the operator alone.</p>"
   "<p>Write grid guards with the halves parenthesised -- "
   "<code>(x &gt;= 0 &amp;&amp; x &lt; m) &amp;&amp; (y &gt;= 0 &amp;&amp; y &lt; n)</code> "
   "-- or better, write the guard once as a helper and never write it again.</p>"),
  ("Bound the loop by the space it walks",
   "<p>When a loop walks something other than the array it was born from, the array's "
   "length stops being the right bound and nothing in the code says so.</p>"
   "<p><code>count-the-number-of-k-free-subsets</code> walks residue classes over the "
   "<em>value</em> space with <code>for (int j = i; j &lt; n; j += k)</code>, where "
   "<code>n</code> is the element count. Values at or above <code>n</code> were "
   "silently skipped; the fix was <code>j &lt;= maxEl</code>. "
   "<code>sequential-digits</code> ran its digit-count loop up to a bound that can "
   "reach 10, generating a garbage 10-digit candidate when no such number exists -- "
   "capped with <code>Math.min(9, dCountHigh)</code>. "
   "<code>adjacent-increasing-subarrays-detection-i</code> wrote "
   "<code>for (int j = i; j &lt; j + k; j++)</code>, comparing <code>j</code> against "
   "itself plus <code>k</code>, which reduces to the constant <code>0 &lt; k</code> -- "
   "always true, bound never enforced.</p>"
   "<p>Name the bound after the space: <code>maxValue</code>, <code>digitCount</code>, "
   "<code>rows</code>. A bound called <code>n</code> in a loop that is not walking "
   "<code>n</code> things is where this hides.</p>"),
  ("The five-second check",
   "<p>Run every new loop at <code>n = 1</code> and <code>n = 2</code> in your head "
   "before you submit. Not the algorithm -- just the bound. What is the first index "
   "touched, what is the last, and is the last one you wanted?</p>"
   "<p>That check catches every example in this lesson. "
   "<code>maximum-linear-stock-score</code> looped to "
   "<code>prices.length - 1</code>, dropping the final price: visible at "
   "<code>n = 2</code>. <code>alternating-groups-ii</code> iterated to "
   "<code>i &lt; n + k</code>, one past the last valid start: visible at the smallest "
   "case. <code>reverse-string</code>'s extra midpoint swap: visible at "
   "<code>n = 2</code>.</p>"
   "<p>These are not hard bugs. They are unchecked ones, and the check is short "
   "enough to always do.</p>"),
 ],
 "rules": [
  "Half-open by default: `i < n`. Every `<=` is a claim you should be able to defend in a phrase.",
  "A range test is two comparisons joined by `&&`. An `||` between them is true for every input.",
  "Bound the loop by the space it walks, and name the bound after that space.",
  "Check every new loop at n = 1 and n = 2 before submitting.",
 ],
 "drill": "Take the four problems where a bound cost you the most -- `reverse-string`, "
          "`total-cost-to-hire-k-workers`, `alternating-groups-ii` and "
          "`adjacent-increasing-subarrays-detection-i` -- and for each, write down the "
          "first and last index the loop touches before running anything. Then run it. "
          "The gap between the two answers is the lesson.",
},

]


# --------------------------------------------------------------------------
# Objectives, prerequisites and recall questions.
#
# Kept out of the lesson literals above and merged in below, because they are
# the same three fields twenty-seven times and reading them side by side is the
# only way to tell whether the course actually has an order. `prereqs` names
# lessons by slug, and build_book.py asserts every one of them is taught
# earlier -- which is what moved `heaps` ahead of `graph-traversal`, Dijkstra
# being a priority queue with a distance array attached.
#
#   objectives  [str]         what you should be able to DO afterwards
#   prereqs     [slug]        what must already be true, all taught earlier
#   recall      [(q, a)]      asked before the explanation, answers disclosed
# --------------------------------------------------------------------------

LESSON_EXTRAS = {

"complexity-budget": {
 "objectives": [
  "Read a constraint line and name the complexity class it allows, without "
  "looking at the examples.",
  "Turn a plan into an operation count -- loops multiplied, queries multiplied "
  "-- and compare it against 10⁸ before writing any code.",
  "Diagnose a Time Limit Exceeded verdict as the wrong complexity class rather "
  "than a slow inner loop.",
 ],
 "prereqs": [],
 "recall": [
  ("`n ≤ 10⁵` and the problem asks 10⁵ queries. What is your per-query budget?",
   "O(log n), or O(1) after an O(n log n) precomputation. 10⁵ queries × an O(n) "
   "scan is 10¹⁰ operations, a hundred times over budget. The cost is per query "
   "*multiplied by* the number of queries, never the larger of the two."),
  ("You have a correct O(n²) solution and `n ≤ 5000`. Do you optimise it?",
   "No. 5000² is 2.5×10⁷, which fits comfortably. The budget decides, not the "
   "shape of the loop -- a nested loop is only a problem when the constraints "
   "say it is."),
  ("A submission comes back Time Limit Exceeded. What is the one thing you must "
   "not do?",
   "Micro-optimise the inner loop. TLE means the complexity class is wrong, and "
   "hoisting an allocation will not turn n² into n log n. Go back to the budget "
   "and pick a different structure."),
 ],
},

"integer-width": {
 "objectives": [
  "Find the first expression in a method that can exceed 2·10⁹ and widen its "
  "first operand.",
  "Write a modular add, subtract and multiply that cannot produce a negative or "
  "an overflowed result.",
  "Pick a sentinel whose width matches the array it lives in.",
 ],
 "prereqs": [],
 "recall": [
  ("`long x = a * b;` with two ints. When is this wrong?",
   "Whenever `a * b` exceeds 2,147,483,647. The multiply happens in `int` and "
   "wraps before anything is assigned -- the destination type never changes how "
   "the arithmetic is done. Write `(long) a * b`."),
  ("Why is `(a - b) % MOD` not enough?",
   "Java's `%` keeps the sign of the left operand, so `a < b` gives a negative "
   "result that then indexes or compares wrongly. `((a - b) % MOD + MOD) % MOD`."),
  ("You initialise a min-cost array to `Integer.MAX_VALUE` and then add a weight "
   "to it. What breaks?",
   "The add overflows to a large negative number, which wins every subsequent "
   "minimum. Use `MAX_VALUE / 2`, or `Long.MAX_VALUE / 2` in a long array."),
 ],
},

"sentinels": {
 "objectives": [
  "Name the identity element of any operation you fold over an array, and "
  "justify it from the operation rather than from habit.",
  "Decide whether a magic value is safe by proving from the constraints that no "
  "real value can collide with it.",
 ],
 "prereqs": ["integer-width"],
 "recall": [
  ("`int best = 0;` then `best = Math.max(best, sum);`. What input breaks it?",
   "Any input whose answer is negative -- an all-negative array. 0 is the "
   "identity for *sum*, not for *max*. The identity for max is "
   "`Integer.MIN_VALUE`, or seed from the first element."),
  ("When is −1 a safe “not found” marker?",
   "Only when the constraints guarantee every real value is non-negative. "
   "Otherwise a legitimate −1 is indistinguishable from absence; use a separate "
   "boolean rather than an in-band magic number."),
  ("What must a dummy head and tail be wired to in the constructor?",
   "Each other, in both directions: `head.next = tail; tail.prev = head;`. A "
   "half-linked pair fails on the first insertion into an empty list."),
 ],
},

"bounds": {
 "objectives": [
  "Order a compound guard so the range test runs before the array read, every "
  "time.",
  "Size an array from the input or a named constraint rather than from a "
  "guessed constant.",
 ],
 "prereqs": [],
 "recall": [
  ("`if (grid[r][c] == 1 && r < n)` -- what is wrong, and why does it sometimes "
   "pass?",
   "The read happens before the bounds test. `&&` evaluates left to right, so "
   "the access throws before `r < n` is ever consulted. It passes whenever the "
   "traversal happens not to walk off the edge on the sample inputs."),
  ("Where does the bounds check for a recursive grid walk belong?",
   "At the top of the function, once, before touching the grid. At the call "
   "sites you would have to repeat it four times and will eventually forget one."),
  ("`while (nums[i] < target) i++;` -- what is missing?",
   "An index-range clause: `while (i < nums.length && nums[i] < target)`. Every "
   "while condition that indexes an array needs one."),
 ],
},

"degenerate-inputs": {
 "objectives": [
  "Run n = 0, n = 1 and n = 2 through any loop or pointer walk in your head "
  "before submitting.",
  "Write a bail-out guard with the operator that actually means “any of "
  "these”.",
 ],
 "prereqs": ["bounds"],
 "recall": [
  ("`if (head == null && head.next == null) return head;` -- what does this "
   "guard actually do?",
   "Nothing safe. `&&` short-circuits only when the left side is *false*, so a "
   "null head falls through to `head.next` and throws. A bail-out over several "
   "failing conditions joins with `||`."),
  ("Which three input sizes do you check, and what does each catch?",
   "Zero -- every unguarded first read. One -- every loop that pairs an element "
   "with its neighbour. Two -- every fast/slow pointer walk and every "
   "“compare with the middle”."),
  ("The constraints say `1 ≤ n`. Should you still write the empty guard?",
   "No. An unreachable guard is dead code that hides which cases are real, and "
   "writing it suggests the constraints were not read."),
 ],
},

"case-analysis": {
 "objectives": [
  "Write the case list down -- conditions plus one example input each -- before "
  "writing any branch.",
  "Check a branch set for overlaps as well as for gaps.",
 ],
 "prereqs": ["degenerate-inputs"],
 "recall": [
  ("`if (i > 0 || i < n - 2)` -- how often is this true?",
   "Always, for every index. Each one is either positive or below n−2, and most "
   "are both. An `||` of two range tests is a set *union*, and unions of "
   "overlapping ranges cover everything."),
  ("Two patches on one problem, for two different failing inputs. What does that "
   "mean?",
   "The case analysis is wrong, not the arithmetic. Stop patching and enumerate "
   "-- a third input is already waiting."),
  ("What are the two things a case list must satisfy?",
   "No input matches zero branches (no gap) and no input matches two (no "
   "overlap). Most people check only the first."),
 ],
},

"last-group": {
 "objectives": [
  "Recognise an emit-on-transition loop and supply the tail that closes the "
  "final group.",
  "Prefer emit-on-entry, which cannot have the bug at all.",
 ],
 "prereqs": ["degenerate-inputs"],
 "recall": [
  ("A loop writes a group out when it sees the next element differ. Which group "
   "is missing?",
   "The last one -- nothing follows it to trigger the write. It needs a "
   "post-loop emit identical to the one inside the loop."),
  ("Should the tail be guarded on “the input was non-empty”?",
   "No -- on “a group was opened”. The two differ whenever the loop can "
   "consume input without starting a group, and that is exactly the input that "
   "breaks the wrong guard."),
  ("Name three things that are secretly a last group.",
   "A carry out of the final digit, a remainder after the final full chunk, and "
   "a partly-filled buffer at the end of a stream."),
 ],
},

"binary-search": {
 "objectives": [
  "Write a half-open lower-bound binary search from memory, and say which of "
  "the four boundary variants a problem needs.",
  "State the predicate as a sentence and check it is monotone before writing "
  "the loop.",
 ],
 "prereqs": ["bounds", "case-analysis"],
 "recall": [
  ("In the half-open template: what is `hi` initially, what is the loop "
   "condition, and what do you return?",
   "`hi = n`, `while (lo < hi)`, `return lo`. The live interval is [lo, hi) "
   "throughout, and when it empties `lo == hi` is the answer."),
  ("The predicate is true at `mid`. Which side moves, and to what?",
   "`hi = mid` -- keep mid, because it is still a candidate. False means "
   "`lo = mid + 1`, discarding it. Keep-or-discard is the entire rule."),
  ("Why `lo + (hi - lo) / 2` rather than `(lo + hi) / 2`?",
   "`lo + hi` overflows int once both are near 2³¹. The subtracting form cannot, "
   "and typing it by habit costs nothing."),
 ],
},

"comparators": {
 "objectives": [
  "Write a comparator for any key type that can neither overflow nor break "
  "transitivity.",
  "Say what `compareTo` returning 0 means inside a TreeSet, and add the tiebreak "
  "it implies.",
 ],
 "prereqs": ["integer-width"],
 "recall": [
  ("What is wrong with `(a, b) -> a - b`?",
   "It overflows whenever `a - b` leaves int range -- a large positive minus a "
   "large negative -- and returns the wrong sign, which breaks the sort's "
   "transitivity contract. `Integer.compare(a, b)`."),
  ("A TreeSet holds price records and `compareTo` compares only the price. What "
   "happens to two different records at the same price?",
   "The second is silently dropped. Sorted collections identify elements by "
   "`compareTo == 0`, not by `equals`. Break every tie with a second field."),
  ("The sort key is a long. What does `comparingInt` do?",
   "Truncates it to int, silently reordering large values. Use `comparingLong`."),
 ],
},

"heaps": {
 "objectives": [
  "Choose the heap direction for a top-k problem by writing down what you need "
  "to evict.",
  "Design the element type and the comparator together, so the heap orders by "
  "the thing the problem actually ranks.",
 ],
 "prereqs": ["comparators"],
 "recall": [
  ("k largest elements. Which heap, and why is it the opposite of instinct?",
   "A min-heap of size k. Its root is the smallest of the current best k, which "
   "is precisely the element to evict when a bigger one arrives. A max-heap "
   "would put the wrong end within reach."),
  ("Can you iterate a `PriorityQueue` to get sorted order?",
   "No. A heap is partially ordered -- only `peek()` is guaranteed. Iteration "
   "returns the backing array's order, which looks sorted on small inputs."),
  ("You need to lower an element's priority while it sits in the heap. What do "
   "you do?",
   "Push a new entry and skip stale ones on pop. Mutating an element inside a "
   "heap corrupts the ordering invariant with no error and no exception."),
 ],
},

"equality-hashing": {
 "objectives": [
  "Say when `==` is safe on boxed values, and write the comparison that is "
  "always safe.",
  "Choose between an array and a hash structure from the key range rather than "
  "by reflex.",
 ],
 "prereqs": [],
 "recall": [
  ("`Integer a = 127, b = 127; a == b` -- and the same at 128?",
   "True at 127, false at 128. Java caches boxes for −128…127, so identity "
   "comparison accidentally works on small test values and fails on the judge."),
  ("You override `equals` but not `hashCode`. What breaks, and when?",
   "Every hashed collection: two equal objects land in different buckets, so "
   "`contains` returns false for something you just added. Nothing fails at "
   "compile time and nothing throws."),
  ("Keys are the characters `a`..`z`. Map or array?",
   "`int[26]`. Dense keys in a known range make a map a pure constant-factor "
   "tax -- and past about 10⁶ operations that factor is the difference between "
   "Accepted and Time Limit Exceeded."),
 ],
},

"library-edges": {
 "objectives": [
  "Predict what an expression mixing casts, boxing and integer division "
  "actually evaluates to, before running it.",
  "Find the unboxing NullPointerException in a comparison that calls `get`, "
  "`peek` or `poll`.",
 ],
 "prereqs": ["equality-hashing", "integer-width"],
 "recall": [
  ("`(long) 8 * 1e15` -- what type is this, and is it exact?",
   "A `double`. `1e15` is a double literal, so the long is widened and the whole "
   "product is floating point. Write `8L * 1_000_000_000_000_000L`."),
  ("`map.get(k) > 5` where the map is `Map<Integer, Long>`. What can go wrong "
   "twice?",
   "An absent key returns null and unboxing it throws; and a bare `int` key "
   "autoboxes to `Integer`, which never equals a `Long` key. Both compile "
   "without a warning."),
  ("You need to compare two slopes, `dy1/dx1` against `dy2/dx2`, in ints. How?",
   "Cross-multiply in long: `dy1 * dx2` against `dy2 * dx1`. Integer division "
   "truncates silently, so two different slopes compare equal."),
 ],
},

"counting-arrays": {
 "objectives": [
  "Build a frequency table sized from the data, indexed by value, and say which "
  "queries over it need a zero guard.",
  "Convert counts to prefix sums without reading a cell you have already "
  "overwritten.",
 ],
 "prereqs": ["bounds", "equality-hashing"],
 "recall": [
  ("What is the one thing an `int[26]` can never tell you?",
   "The difference between *absent* and *zero*. Both read as 0, which is why "
   "every minimum, argmin and parity test over the table needs a "
   "`freq[v] == 0` skip first."),
  ("Which of argmax and argmin needs the guard, and why only one?",
   "argmin. An absent value's 0 beats every real count and wins the minimum. "
   "For argmax a 0 loses to any real count, so it is harmless."),
  ("You are turning counts into a running total in place. What breaks?",
   "`freq[v] += freq[v-1]` reads a cell that has already become a prefix sum. "
   "Snapshot the running total in a local, or write into a second array."),
 ],
},

"union-find": {
 "objectives": [
  "Write a DSU with path compression and union by size from memory, and use its "
  "return value for cycle detection.",
  "Spot the raw-argument bug: any use of `x` or `y` after the roots are "
  "computed.",
 ],
 "prereqs": ["bounds"],
 "recall": [
  ("`int rx = find(x), ry = find(y);` and then `size[x] += size[y];`. What is "
   "wrong?",
   "It updates the sizes of two members instead of two roots. After the finds, "
   "`x` and `y` must not appear again anywhere in the method."),
  ("What should `union()` return, and what does that buy you?",
   "A boolean: whether it actually merged two different sets. False means the "
   "edge closes a cycle, which answers cycle detection with no extra code."),
  ("Why union by size *as well as* path compression?",
   "Compression alone still degrades under an adversarial merge order. Together "
   "they give effectively constant amortised time. Both, always."),
 ],
},

"graph-traversal": {
 "objectives": [
  "State the marking rule for BFS, Dijkstra and Kahn without looking, and say "
  "why each is different.",
  "Write the indegree-direction comment before any topological sort.",
 ],
 "prereqs": ["heaps", "bounds"],
 "recall": [
  ("When does BFS mark a node visited?",
   "On push. Marking on pop lets the same node enter the queue many times "
   "before its first pop, which blows up on dense graphs and still returns the "
   "right answer on small ones."),
  ("What is Dijkstra's “visited” actually?",
   "A staleness check on pop: `if (d > dist[u]) continue;`. Distances are "
   "finalised on pop, and a boolean set on push would freeze a distance before "
   "its shorter path arrives."),
  ("Edge `a → b` means a comes before b. Which indegree goes up?",
   "`indegree[b]`. Write that comment first: it is the single decision Kahn's "
   "algorithm turns on, and it is a coin flip if you do not."),
 ],
},

"range-structures": {
 "objectives": [
  "Say when an O(n) scan per query is genuinely out of budget, and reach for a "
  "range structure only then.",
  "Use a Fenwick tree through `add()` alone, sized from the data.",
 ],
 "prereqs": ["complexity-budget", "bounds"],
 "recall": [
  ("Can you assign into a BIT's backing array to set a value?",
   "No. That array holds partial sums over ranges, not values. Everything "
   "enters through `add(i, delta)`; to *set*, add the difference."),
  ("A segment tree is right on the samples and wrong on a big input. Where do "
   "you look first?",
   "`merge()`. It is the only part that encodes the problem -- the rest is "
   "boilerplate that is either right or catastrophically wrong. Test it on a "
   "two-element tree by hand."),
  ("Which index convention, and where do you convert?",
   "A BIT is 1-indexed internally. Convert once at the boundary of the class, "
   "never at the call sites."),
 ],
},

"windows": {
 "objectives": [
  "Write the window invariant as one sentence and derive the shrink loop from "
  "it.",
  "Recognise the inputs that make a window invalid, and reach for prefix sums "
  "with a map instead.",
 ],
 "prereqs": ["bounds", "degenerate-inputs"],
 "recall": [
  ("Shrink with `if` or `while`?",
   "`while`. One removal is not guaranteed to restore the invariant -- after "
   "adding a single element the window may have to give up several."),
  ("Where do you record the answer?",
   "After the shrink loop, where the window is valid by construction. Recording "
   "before it measures a window that violates the invariant."),
  ("The array contains negatives and you want subarrays summing to k. Why does "
   "a window fail?",
   "Extending no longer moves the sum monotonically, so the current sum cannot "
   "tell you whether to shrink. Use prefix sums with a map seeded `{0: 1}`."),
 ],
},

"recursion": {
 "objectives": [
  "Answer the three questions -- what does this return, what is the base case, "
  "what shrinks -- before writing a recursive body.",
  "Undo every mutation on every exit path, and include every dependency in the "
  "memo key.",
 ],
 "prereqs": ["degenerate-inputs", "case-analysis"],
 "recall": [
  ("Your recursion is right on some inputs and returns 0 on others. What is the "
   "usual cause?",
   "A path with no return -- a branch that falls off the end of the method, or "
   "a recursive call whose result is computed and then discarded."),
  ("What belongs in a memo key?",
   "Every variable the answer depends on. A key missing one dimension returns "
   "an answer computed under different circumstances, silently, and it reads "
   "like a transition bug."),
  ("n can be 10⁵ and the recursion is linear. What do you do?",
   "Convert to an explicit stack or an iterative pass. The JVM's default stack "
   "overflows somewhere in the low tens of thousands of frames."),
 ],
},

"dynamic-programming": {
 "objectives": [
  "State a DP's state as an English sentence, derive the transition from it, "
  "and read the loop order off the dependency direction.",
  "Debug a wrong DP by finding the first cell that disagrees with brute force.",
 ],
 "prereqs": ["recursion", "complexity-budget"],
 "recall": [
  ("What do you write before the array declaration?",
   "The state as a full English sentence in a comment. Everything else is "
   "derived from it, and a state you cannot say out loud is itself the bug."),
  ("0/1 knapsack versus unbounded -- what is the only difference?",
   "The direction of the capacity loop. Descending reads the previous row, so "
   "each item is used once; ascending reads the current row and allows reuse."),
  ("The state is “best subarray ending exactly at i”. Where is the "
   "answer?",
   "The maximum over the whole table, not `dp[n-1]`. States that end *exactly* "
   "at i never answer the question directly."),
 ],
},

"monotonic-stack": {
 "objectives": [
  "Say what the stack holds and in what order before writing the loop, and "
  "derive the pop condition from the question.",
  "Use a boundary sentinel instead of a cleanup loop.",
 ],
 "prereqs": ["last-group", "sentinels"],
 "recall": [
  ("What does the stack actually hold?",
   "The indices whose answer has not arrived yet, in the order that makes the "
   "next arrival resolve them. Values lose the position you need for distances."),
  ("Next greater element: pop on `<=` or on `<`?",
   "Derive it, do not recall it. If equal elements must not resolve each other, "
   "pop strictly. It changes the answer whenever the problem counts anything."),
  ("What is left on the stack at the end, and what do you do with it?",
   "Everything with no answer. Either assign the sentinel value in a drain "
   "loop, or push a boundary element and let the main loop drain it for you."),
 ],
},

"strings": {
 "objectives": [
  "Choose between `charAt`, `substring` and `StringBuilder` from their costs "
  "rather than from readability.",
  "Count characters into an array sized from the stated alphabet.",
 ],
 "prereqs": ["counting-arrays", "complexity-budget"],
 "recall": [
  ("`s += c` inside a loop over 10⁵ characters. What does it cost?",
   "O(n²) -- every `+=` copies the whole string. `StringBuilder.append` is "
   "amortised O(1)."),
  ("How many centres does expand-around-centre need?",
   "2n − 1: n single characters and n − 1 gaps. Missing the even case is why "
   "`abba` is the test to run before submitting."),
  ("`split(\".\")` returns an empty array. Why?",
   "`split` takes a regex, and `.` matches every character. Escape it."),
 ],
},

"number-theory": {
 "objectives": [
  "Write gcd, a sieve and modular fast power from memory.",
  "Divide under a prime modulus by multiplying with an inverse, and never "
  "compare reduced values.",
 ],
 "prereqs": ["integer-width"],
 "recall": [
  ("`lcm(a, b)` for a and b up to 10⁹ -- what is the safe form?",
   "`a / gcd(a, b) * b`, in long. Multiplying first overflows; dividing first "
   "cannot, because the gcd divides a exactly."),
  ("How do you divide by k modulo a prime p?",
   "Multiply by `power(k, p - 2, p)`. Division does not exist in modular "
   "arithmetic; the multiplicative inverse does, by Fermat's little theorem."),
  ("Why must you never take a max of two values reduced mod p?",
   "Reduction destroys order -- a larger number can reduce to a smaller "
   "residue. A modulus is for counting answers, never for comparing them."),
 ],
},

"intervals": {
 "objectives": [
  "Pick the sort key from the task: start to merge, end to schedule, events to "
  "count.",
  "Emit the final interval after the loop, and extend the right endpoint rather "
  "than assigning it.",
 ],
 "prereqs": ["comparators", "last-group"],
 "recall": [
  ("Merging overlaps: `cur[1] = next[1]` or `cur[1] = max(cur[1], next[1])`?",
   "`max`. A fully contained interval would otherwise shrink the merged one -- "
   "the classic `[1,10]`, `[2,3]` failure."),
  ("Maximum number of non-overlapping intervals -- which sort?",
   "By end. Taking the earliest-ending compatible interval leaves the most room "
   "for what follows, and it is the one greedy in this family that is provably "
   "optimal."),
  ("Two events at the same time, one start and one end. Which goes first?",
   "Whichever the statement demands -- and write the choice down. Touching "
   "intervals count as overlapping under one order and not the other."),
 ],
},

"linked-list": {
 "objectives": [
  "Use a dummy head to delete every front special case, and return "
  "`dummy.next`.",
  "Get the middle, the k-th from the end and cycle detection with two pointers "
  "in one pass.",
 ],
 "prereqs": ["sentinels", "degenerate-inputs"],
 "recall": [
  ("When do you need a dummy head?",
   "Whenever the head node can change -- deletion, insertion at the front, a "
   "merge. It turns “the first node is special” into no case at all."),
  ("Reversal: what is the order of the four statements?",
   "Save `next`, flip `cur.next` to `prev`, advance `prev` to `cur`, advance "
   "`cur` to the saved next. Any other order loses the rest of the list."),
  ("Why is the fast-pointer guard `(fast != null && fast.next != null)`?",
   "Both halves are needed -- the first for odd lengths, the second for even. "
   "Dropping either throws on a two-node list."),
 ],
},

"mutable-state": {
 "objectives": [
  "Classify every mutable name in a loop as read, written or both, and keep the "
  "“both” column down to one entry.",
  "Spot a loop bound that moves because the body mutates the collection it "
  "measures.",
 ],
 "prereqs": ["bounds", "counting-arrays"],
 "recall": [
  ("`for (int i = 0; i < q.size(); i++)` with a body that pushes onto `q`. What "
   "happens?",
   "The bound grows as you iterate, so the loop never finishes the level it was "
   "meant to. Snapshot the size into a final local before the loop."),
  ("The first operation is right and every later one is wrong. What class of bug "
   "is that?",
   "A missing write-back -- the computed result never reached the state the "
   "next operation reads. Look at persistence, not at the arithmetic."),
  ("`Arrays.fill(buckets, new ArrayList<>())` -- how many lists exist?",
   "One, shared by every slot, so every add is visible through all of them. "
   "Fill in a loop with a fresh instance per index."),
 ],
},

"wrong-name": {
 "objectives": [
  "Name every index for what it ranges over, and say which space each subscript "
  "belongs to.",
  "Rename the write targets first after pasting a loop.",
 ],
 "prereqs": ["bounds", "mutable-state"],
 "recall": [
  ("Two nested loops over different arrays, both using `i` and `j`. What is the "
   "tell that a subscript is wrong?",
   "An index whose name does not say what it ranges over. Rename each to its "
   "own space and the mismatch becomes obvious on sight."),
  ("`freq[i]` where `i` is the loop position over `nums`. Position or value?",
   "Value, almost certainly -- a frequency table is indexed by value. Every "
   "subscript answers “position or value”, and this is the one that is "
   "silently wrong."),
  ("You pasted a loop and changed the logic. What did you forget?",
   "The write target. Rename the destination first, before touching anything "
   "else, or the second loop quietly updates the first one's array."),
 ],
},

"edit-hygiene": {
 "objectives": [
  "Compile locally before every submission.",
  "State the failure hypothesis in one sentence before resubmitting, and stop "
  "when you cannot finish it.",
 ],
 "prereqs": [],
 "recall": [
  ("What does a Compile Error verdict cost you, beyond the attempt?",
   "The information. A failed submission is only useful when it ran; a compile "
   "error tells you nothing about the algorithm and still spends the attempt."),
  ("The sentence you must be able to complete before resubmitting.",
   "“It failed because X, and this change addresses X.” If X is "
   "“something in the loop”, you are guessing -- read the code instead "
   "of submitting."),
  ("Why rename through the IDE rather than by hand?",
   "A hand rename that misses one site is exactly the shape of the 242 compile "
   "errors -- and the sites it misses inside a comment or a dead branch compile "
   "fine and change behaviour."),
 ],
},


"post-solve-regression": {
 "objectives": [
  "Keep the accepted version as an oracle and diff a rewrite against it on random "
  "small inputs before submitting.",
  "Limit a post-solve submission to one change -- structure, language or algorithm -- "
  "so a failure names its cause.",
  "Recognise the second consecutive rewrite failure as the moment to roll back rather "
  "than patch.",
 ],
 "prereqs": ["complexity-budget", "edit-hygiene"],
 "recall": [
  ("You are about to rewrite an already-Accepted solution for speed. What do you have "
   "that you do not have on an unsolved problem?",
   "An oracle. The accepted version is known-correct on this exact problem, so the "
   "rewrite can be checked by comparison instead of by reasoning -- a few hundred "
   "small random inputs through both, outputs compared."),
  ("Why are post-solve mistakes invisible in your statistics?",
   "They cost no solve rate and appear in no first-attempt metric -- the problem is "
   "already green. Nothing on the scoreboard ever reported them, which is why they "
   "became the largest single slice of the diagnosed mistakes in the export."),
  ("A rewrite has now failed twice in a row. What is the move?",
   "Roll back to the accepted version and restart the change from it, one step at a "
   "time. Patching a broken rewrite is how three attempts become seven -- "
   "`reconstruct-itinerary` spent four attempts refining a strategy that was then "
   "abandoned wholesale."),
 ],
},

"derive-dont-guess": {
 "objectives": [
  "State the meaning of every constant in a solution in one phrase, and treat one you "
  "cannot state as a bug.",
  "Diagnose an answer that is wrong by a fixed amount as a double-count rather than "
  "cancelling it with a compensating term.",
  "Stop after three attempts of the same shape and derive on paper instead.",
 ],
 "prereqs": ["complexity-budget", "edit-hygiene"],
 "recall": [
  ("Your answer is consistently one too high. What does that tell you, and what is the "
   "wrong response?",
   "A fixed offset means something specific is counted exactly once too often, and "
   "that is findable. The wrong response is `return result + 1` -- on "
   "`max-points-on-a-line` the real cause was the pivot point sitting in its own angle "
   "map, and excluding it removes the need for any constant."),
  ("How do you choose the scan bound for `first-missing-positive`?",
   "From the statement: among `n` integers the smallest missing positive cannot exceed "
   "`n + 1`, so the bound is `nums.length + 1`. A literal like `10001` came from a "
   "failing test, fits that test, and says nothing about the problem."),
  ("What is the exit condition for guess-and-check?",
   "Three attempts of the same shape. Trying things to build intuition is legitimate; "
   "having no stopping rule is what turned `trapping-rain-water` into seven attempts "
   "of wall-detection bookkeeping that never converged."),
 ],
},

"read-the-statement": {
 "objectives": [
  "Write the output contract -- type, indexing base, distinctness, ordering, exact "
  "string format -- before writing any code.",
  "Port a signature deliberately when moving a solution to another language.",
  "Identify the exact quantity the statement asks for and check the code computes that "
  "one.",
 ],
 "prereqs": ["degenerate-inputs", "edit-hygiene"],
 "recall": [
  ("Your algorithm is right, your code matches your intent, and the judge says Wrong "
   "Answer. Where do you look first?",
   "The output contract, not the algorithm. Indexing base, duplicates, ordering and "
   "string format are stated in the problem and appear nowhere in your logic -- "
   "re-reading the code cannot reveal them, because the code says what you meant."),
  ("What breaks first when you port a working solution to another language?",
   "The call convention. `stone-game-ii` produced three consecutive Runtime Errors on "
   "nothing else: a missing `class Solution` wrapper, then a missing `self`, then a "
   "missing `self` again with the type hints removed."),
  ("The problem says the result must be distinct and yours has repeats. What is the "
   "bug?",
   "The collection type. On `find-the-difference-of-two-arrays` the differences were "
   "collected into a `List`, so a value appearing twice in the input appeared twice in "
   "the output; a `Set` fixes it, and nothing in the loop was ever wrong."),
 ],
},

"loop-bounds": {
 "objectives": [
  "Default to half-open ranges and justify every closed one in a phrase.",
  "Write range tests as comparisons joined by `&&`, and recognise an `||` between them "
  "as a guard that rejects nothing.",
  "Check every new loop at n = 1 and n = 2 before submitting.",
 ],
 "prereqs": ["bounds", "binary-search", "wrong-name"],
 "recall": [
  ("What is wrong with `if (newX >= 0 || newX < m && newY >= 0 || newY < n)`?",
   "Every integer satisfies `newX >= 0` or `newX < m`, so the condition is true for "
   "every input and the guard rejects nothing. A range test is two comparisons joined "
   "by `&&`: `(x >= 0 && x < m) && (y >= 0 && y < n)`."),
  ("Your loop is `for (int j = i; j < n; j += k)` and it walks values, not positions. "
   "What is the bug?",
   "`n` is the element count, not the largest value, so every value at or above `n` is "
   "skipped. Bound the loop by the space it walks -- `j <= maxEl` -- and name the "
   "bound after that space."),
  ("The cheapest check that catches most bound errors.",
   "Run the loop at n = 1 and n = 2 in your head: first index touched, last index "
   "touched, is the last one you wanted? That alone catches the extra midpoint swap in "
   "`reverse-string` and the dropped final element in "
   "`maximum-linear-stock-score`."),
 ],
},

}

# Merge, and fail loudly rather than rendering a lesson with no objectives.
assert set(LESSON_EXTRAS) == {l["slug"] for l in LESSONS}, (
    set(LESSON_EXTRAS) ^ {l["slug"] for l in LESSONS})
for _lesson in LESSONS:
    _lesson.update(LESSON_EXTRAS[_lesson["slug"]])


# The one rule from each lesson that belongs on a page you keep open while you
# solve, as an index into that lesson's `rules`. Every rule is worth following;
# these are the ones the evidence says cost the most attempts, and a checklist
# of a hundred and thirty items is a document, not a checklist.
KEY_RULE = {
 "complexity-budget": 0, "integer-width": 0, "sentinels": 0, "bounds": 0,
 "degenerate-inputs": 0, "case-analysis": 2, "last-group": 0,
 "binary-search": 1, "comparators": 0, "heaps": 0, "equality-hashing": 0,
 "library-edges": 3, "counting-arrays": 2, "union-find": 0,
 "graph-traversal": 0, "range-structures": 0, "windows": 1, "recursion": 1,
 "dynamic-programming": 0, "monotonic-stack": 1, "strings": 0,
 "number-theory": 2, "intervals": 2, "linked-list": 0, "mutable-state": 3,
 "wrong-name": 1, "edit-hygiene": 0,
 "post-solve-regression": 0, "derive-dont-guess": 0,
 "read-the-statement": 0, "loop-bounds": 0,
}

assert set(KEY_RULE) == {l["slug"] for l in LESSONS}
for _lesson in LESSONS:
    _index = KEY_RULE[_lesson["slug"]]
    assert 0 <= _index < len(_lesson["rules"]), (_lesson["slug"], _index)
    _lesson["key_rule"] = _lesson["rules"][_index]


# ===================== the reference split ===================================
# One lesson outgrew the page. Dynamic programming's thirteen shapes are a
# catalogue you consult when you meet a problem, not prose you read start to
# finish, so they move to a page of their own and the lesson keeps the part
# that is read once. Any lesson can be split this way; the predicate decides
# which of its sections are catalogue.
REFERENCE_SPLIT = {
 "dynamic-programming": (
  "The thirteen shapes of a DP",
  "<p>Almost every dynamic programming problem you will meet is one of "
  "these thirteen, wearing a costume. This is a catalogue, not a chapter: "
  "read it once to know what is in it, then come back to the one entry you "
  "need when a problem smells like DP but you cannot see the state.</p>"
  "<p>Each shape gives you the same four things -- what the state is, what "
  "the transition is, which order to fill it in, and the tell in the problem "
  "statement that says you are looking at this shape.</p>",
  lambda heading: heading.startswith("Shape "),
 ),
}

for _lesson in LESSONS:
 _split = REFERENCE_SPLIT.get(_lesson["slug"])
 if not _split:
  continue
 _title, _blurb, _belongs = _split
 _moved = [pair for pair in _lesson["basics"] if _belongs(pair[0])]
 assert _moved, f"{_lesson['slug']}: nothing matched the reference predicate"
 _lesson["basics"] = [p for p in _lesson["basics"] if not _belongs(p[0])]
 assert _lesson["basics"], f"{_lesson['slug']}: the split emptied the lesson"
 _lesson["reference"] = {"title": _title, "blurb": _blurb, "sections": _moved}


# ===================== the glossary ==========================================
# Words this book uses as if you already know them. Each entry says what the
# term means *here*, not in general, and points at the lesson that leans on it.
# (slug, term, definition, lesson slug or "")
GLOSSARY = [
 ("invariant", "invariant",
  "A statement about your variables that is true before the loop, true after "
  "every pass, and therefore true when the loop ends. Binary search is an "
  "invariant with a search over it: write down which half the answer is in, "
  "and every line either preserves that or is a bug.",
  "binary-search"),
 ("sentinel", "sentinel",
  "A value placed outside the real data so the loop body never needs a special "
  "case for the edge -- a dummy head on a list, a zero row above a grid, an "
  "infinity at the end of an array.",
  "sentinels"),
 ("identity-element", "identity element",
  "The value that leaves the operation unchanged: 0 for a sum, 1 for a "
  "product, +infinity for a minimum. It is what an empty accumulator must "
  "start at, and getting it wrong is a silent off-by-everything.",
  "sentinels"),
 ("amortised", "amortised",
  "The cost per operation averaged over a whole run, not the cost of the worst "
  "single operation. An ArrayList add is amortised O(1): most are cheap, a few "
  "copy the whole array, and the average stays constant.",
  "complexity-budget"),
 ("monotonic", "monotonic",
  "Only ever moving one way. A monotonic stack keeps its contents in sorted "
  "order by popping anything that would break it, which is what makes each "
  "element enter and leave exactly once.",
  "monotonic-stack"),
 ("prefix-sum", "prefix sum",
  "An array where entry i holds the total of everything before i, so the sum "
  "of any range is one subtraction. Building it is O(n) once; every query "
  "after that is O(1).",
  "range-structures"),
 ("memoisation", "memoisation",
  "Top-down dynamic programming: write the recursion you actually mean, then "
  "cache each answer the first time you compute it. Same recurrence as the "
  "bottom-up table, opposite direction.",
  "dynamic-programming"),
 ("tabulation", "tabulation",
  "Bottom-up dynamic programming: fill an array in an order that guarantees "
  "every value you read is already final. No recursion, no stack depth, but "
  "you have to know the fill order before you start.",
  "dynamic-programming"),
 ("state", "state",
  "The arguments that decide a subproblem's answer, and nothing else. If two "
  "different situations share a state but need different answers, the state is "
  "missing a dimension -- that is the most common DP bug in your record.",
  "dynamic-programming"),
 ("transition", "transition",
  "The rule that builds one DP entry out of entries already computed. The "
  "state says what you are asking; the transition says how the answer is "
  "assembled from smaller answers.",
  "dynamic-programming"),
 ("base-case", "base case",
  "The subproblem small enough to answer without recursing. Every recursion "
  "needs one that is reachable from every path -- an unreachable base case is "
  "a stack overflow, a wrong one is a silently wrong answer.",
  "recursion"),
 ("two-pointer", "two-pointer",
  "One pass with two indices moving under a rule, instead of two nested loops. "
  "It only works when moving a pointer can never make you miss an answer -- "
  "usually because the data is sorted.",
  "windows"),
 ("sliding-window", "sliding window",
  "A two-pointer scan where the region between the pointers is the answer you "
  "are maintaining. The window grows on the right, shrinks on the left, and "
  "the invariant is whatever makes the window legal.",
  "windows"),
 ("lower-bound", "lower bound",
  "The first position where a value could be inserted and keep the array "
  "sorted -- the first element not less than the target. Java spells it "
  "Arrays.binarySearch only for exact hits; for the general case you write it.",
  "binary-search"),
 ("comparator", "comparator",
  "An object that decides which of two elements comes first. It must be "
  "consistent: never claim both a &lt; b and b &lt; a, and never return a "
  "difference that can overflow.",
  "comparators"),
 ("natural-ordering", "natural ordering",
  "The order a type sorts in when you supply no comparator -- Comparable's "
  "compareTo. Integers ascend; strings sort by UTF-16 code unit, which is not "
  "alphabetical once you leave ASCII.",
  "comparators"),
 ("stable-sort", "stable sort",
  "A sort that leaves equal elements in the order it found them. Java's sort "
  "is stable for objects and not for primitives, which is exactly the trap "
  "when you sort by one key expecting a previous sort to survive.",
  "comparators"),
 ("autoboxing", "autoboxing",
  "Java silently converting int to Integer. It is why == sometimes compares "
  "identities rather than values, and why a HashMap of boxed keys is several "
  "times slower than an array.",
  "equality-hashing"),
 ("integer-cache", "Integer cache",
  "The JVM interns boxed integers from -128 to 127, so == on small values "
  "appears to work and then stops working at 128. The bug is not the cache; "
  "the bug is using == on objects.",
  "equality-hashing"),
 ("overflow", "overflow",
  "An arithmetic result too large for its type, which wraps silently in Java "
  "rather than raising. int holds about 2.1 billion; a sum of two large ints "
  "is negative long before you notice.",
  "integer-width"),
 ("modulo", "modulo",
  "Arithmetic done modulo a constant, usually 10^9 + 7, to keep counting "
  "problems inside a long. Take the modulus at every step, not at the end, "
  "and remember Java's % can return a negative.",
  "number-theory"),
 ("modular-inverse", "modular inverse",
  "The value that plays the part of division under a modulus. Under a prime "
  "modulus it is a^(p-2), by Fermat -- which is why combinatorics problems "
  "specify a prime.",
  "number-theory"),
 ("counting-array", "counting array",
  "A plain array indexed by the value itself rather than by position. It "
  "replaces a HashMap when the value range is small and known, and it is "
  "several times faster for it.",
  "counting-arrays"),
 ("dsu", "DSU",
  "Disjoint Set Union, also called union-find: a structure that answers "
  "&ldquo;are these two in the same group?&rdquo; while groups are merged. "
  "With union by size "
  "and path compression both operations are effectively constant time.",
  "union-find"),
 ("path-compression", "path compression",
  "Pointing every node visited during a find straight at the root, so the next "
  "find on that branch is one hop. Half of what makes union-find fast; union "
  "by size is the other half.",
  "union-find"),
 ("adjacency-list", "adjacency list",
  "A graph stored as, for each node, the list of its neighbours. Linear in the "
  "number of edges, unlike a matrix, which is why it is the default for every "
  "traversal in this book.",
  "graph-traversal"),
 ("topological-order", "topological order",
  "An ordering of a directed acyclic graph where every edge points forward. It "
  "exists exactly when there is no cycle, which is why the standard algorithm "
  "doubles as a cycle detector.",
  "graph-traversal"),
 ("relaxation", "relaxation",
  "Improving a tentative distance because a shorter route was found. Dijkstra "
  "relaxes edges out of the closest unfinished node; Bellman-Ford relaxes "
  "every edge, repeatedly.",
  "heaps"),
 ("heap", "heap",
  "A tree kept just ordered enough that the smallest (or largest) element is "
  "at the root. Java spells it PriorityQueue; iterating one does not give you "
  "sorted order, and that is a bug in your record.",
  "heaps"),
 ("fenwick", "Fenwick tree",
  "A binary indexed tree: prefix sums under point updates, both in O(log n), "
  "in one array and about ten lines. The simplest structure that beats a "
  "prefix-sum array when the data changes.",
  "range-structures"),
 ("lazy-propagation", "lazy propagation",
  "Recording a pending update on a segment tree node and pushing it down only "
  "when a query needs that node. It is what makes range updates as cheap as "
  "range queries.",
  "range-structures"),
 ("bitmask", "bitmask",
  "A set stored as the bits of one integer, so subsets are arithmetic. Only "
  "practical up to about 20 elements, which is why a constraint of n &le; 20 "
  "is a tell.",
  "dynamic-programming"),
 ("in-place", "in place",
  "Modifying the input rather than building a copy. It saves the allocation "
  "and costs you the original -- and if a later line still expects the "
  "original, that is the bug.",
  "mutable-state"),
 ("idempotent", "idempotent",
  "Safe to do twice: running it again changes nothing. A cleanup step that is "
  "not idempotent is a bug waiting for the retry.",
  "mutable-state"),
]

assert len({g[0] for g in GLOSSARY}) == len(GLOSSARY), "duplicate glossary slug"
_lesson_slugs = {l["slug"] for l in LESSONS}
for _g in GLOSSARY:
 assert not _g[3] or _g[3] in _lesson_slugs, f"glossary: no lesson {_g[3]}"
