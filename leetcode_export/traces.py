#!/usr/bin/env python3
"""Step-by-step traces for the lessons, recorded from real runs.

A diagram shows a structure at rest. A trace shows state changing, which is
what a person draws on paper when they are actually learning an algorithm --
and it is the thing the hand-written tables in this book were most likely to
get wrong, because nobody re-runs a table in prose after editing the sentence
above it.

So none of these tables are written. Each function below runs the algorithm,
records every step as it happens, and renders the recording. `_selfcheck`
compares each run's answer against an independent reference, so a table that
is rendered is a table that came from a correct run.

    python3 traces.py
"""

from __future__ import annotations

from html import escape


def _cell(text, mark: str = "") -> str:
    klass = f' class="{mark}"' if mark else ""
    return f"<td{klass}>{text}</td>"


def _table(headers: tuple[str, ...], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(r) + "</tr>" for r in rows)
    return (f'<div class="table-scroll"><table class="lesson-table trace-table">'
            f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>")


def _figure(caption: str, table: str) -> str:
    return (f'<figure class="trace">{table}'
            f"<figcaption>{caption}</figcaption></figure>")


def _mono(text) -> str:
    return f"<code>{escape(str(text))}</code>"


# --------------------------------------------------------------------------
# 1. Binary search -- the boundary variables, every iteration
# --------------------------------------------------------------------------

def lower_bound(nums: list[int], target: int) -> tuple[int, list[dict]]:
    """The half-open template from the lesson, instrumented."""
    lo, hi, steps = 0, len(nums), []
    while lo < hi:
        mid = lo + (hi - lo) // 2
        pred = nums[mid] >= target
        steps.append({"lo": lo, "hi": hi, "mid": mid, "value": nums[mid],
                      "pred": pred})
        if pred:
            hi = mid
        else:
            lo = mid + 1
    steps.append({"lo": lo, "hi": hi, "mid": None, "value": None, "pred": None})
    return lo, steps


def binary_search(nums: list[int], target: int) -> str:
    answer, steps = lower_bound(nums, target)
    rows = []
    for i, s in enumerate(steps, 1):
        if s["mid"] is None:
            rows.append([_cell(i), _cell(_mono(s["lo"]), "hl"),
                         _cell(_mono(s["hi"]), "hl"), _cell("&mdash;"),
                         _cell("&mdash;"), _cell("&mdash;"),
                         _cell(f"{_mono('lo == hi')}, the interval is empty "
                               f"&mdash; loop ends")])
            continue
        move = (f"keep it &rarr; {_mono('hi = ' + str(s['mid']))}" if s["pred"]
                else f"discard it &rarr; {_mono('lo = ' + str(s['mid'] + 1))}")
        rows.append([
            _cell(i), _cell(_mono(s["lo"])), _cell(_mono(s["hi"])),
            _cell(_mono(s["mid"])), _cell(_mono(s["value"])),
            _cell("true" if s["pred"] else "false",
                  "yes" if s["pred"] else "no"),
            _cell(move)])
    caption = (f"{_mono('lower_bound(' + str(nums) + ', ' + str(target) + ')')} "
               f"&rarr; {_mono(answer)}. The predicate is "
               f"{_mono('nums[i] >= ' + str(target))}; true means mid is still a "
               f"candidate, so it is kept.")
    return _figure(caption, _table(
        ("step", "lo", "hi", "mid", "nums[mid]", "pred", "action"), rows))


# --------------------------------------------------------------------------
# 2. Sliding window -- where the shrink actually happens
# --------------------------------------------------------------------------

def longest_unique(s: str) -> tuple[int, list[dict]]:
    last: dict[str, int] = {}
    left, best, steps = 0, 0, []
    for right, ch in enumerate(s):
        before = (left, right - 1)
        seen = last.get(ch)
        moved = seen is not None and seen >= left
        if moved:
            left = seen + 1
        last[ch] = right
        best = max(best, right - left + 1)
        steps.append({"right": right, "ch": ch, "before": before, "seen": seen,
                      "moved": moved, "left": left, "best": best})
    return best, steps


def sliding_window(s: str) -> str:
    best, steps = longest_unique(s)
    rows = []
    for st in steps:
        lo, hi = st["before"]
        before = "empty" if hi < lo else _mono(f"[{lo}, {hi}]")
        if st["moved"]:
            action = (f"{_mono(st['ch'])} last seen at {st['seen']}, inside the "
                      f"window &rarr; {_mono('L = ' + str(st['left']))}")
        elif st["seen"] is not None:
            action = (f"{_mono(st['ch'])} last seen at {st['seen']}, already left "
                      f"of L &mdash; L must <em>not</em> move back")
        else:
            action = f"{_mono(st['ch'])} is new &mdash; nothing to shrink"
        rows.append([
            _cell(st["right"]), _cell(_mono(st["ch"])), _cell(before),
            _cell(action, "hl" if st["moved"] else ""),
            _cell(_mono(f"[{st['left']}, {st['right']}]")),
            _cell(_mono(st["best"]))])
    caption = (f"Longest substring without repeating characters on "
               f"{_mono(repr(s))} &rarr; {_mono(best)}. The invariant is "
               f"&ldquo;the window contains no repeated character&rdquo;, and "
               f"the answer is read after the shrink, never before it.")
    return _figure(caption, _table(
        ("R", "char", "window before", "action", "window after", "best"), rows))


# --------------------------------------------------------------------------
# 3. Monotonic stack -- one push and one pop per index
# --------------------------------------------------------------------------

def next_greater(nums: list[int]) -> tuple[list[int], list[dict]]:
    ans = [-1] * len(nums)
    stack: list[int] = []
    steps = []
    for i, value in enumerate(nums):
        popped = []
        while stack and nums[stack[-1]] < value:
            j = stack.pop()
            ans[j] = value
            popped.append(j)
        stack.append(i)
        steps.append({"i": i, "value": value, "popped": list(popped),
                      "stack": list(stack)})
    steps.append({"i": None, "value": None, "popped": [], "stack": list(stack)})
    return ans, steps


def monotonic_stack(nums: list[int]) -> str:
    ans, steps = next_greater(nums)
    rows = []
    for st in steps:
        if st["i"] is None:
            left = ", ".join(str(j) for j in st["stack"]) or "nothing"
            rows.append([_cell("end"), _cell("&mdash;"),
                         _cell(f"{left} left on the stack &mdash; no greater "
                               f"element exists, so the sentinel stands",
                               "no"),
                         _cell(_mono(st["stack"])), _cell("&mdash;")])
            continue
        if st["popped"]:
            what = (f"{_mono(st['value'])} is greater, so it answers "
                    + ", ".join(_mono(f"index {j}") for j in st["popped"])
                    + "; then push " + _mono(st["i"]))
            recorded = ", ".join(_mono(f"ans[{j}] = {st['value']}")
                                 for j in st["popped"])
        else:
            what = f"nothing to resolve &mdash; push {_mono(st['i'])}"
            recorded = "&mdash;"
        rows.append([_cell(st["i"]), _cell(_mono(st["value"])),
                     _cell(what, "hl" if st["popped"] else ""),
                     _cell(_mono(st["stack"])), _cell(recorded)])
    caption = (f"Next greater element on {_mono(nums)} &rarr; {_mono(ans)}. The "
               f"stack holds the indices whose answer has not arrived yet, in "
               f"decreasing value order. Every index is pushed once and popped "
               f"at most once, which is where the O(n) comes from.")
    return _figure(caption, _table(
        ("i", "nums[i]", "what happens", "stack (indices)", "recorded"), rows))


# --------------------------------------------------------------------------
# 4. Union-Find -- the roots, and what path compression rewrites
# --------------------------------------------------------------------------

class _DSU:
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.size = [1] * n
        self.components = n

    def find(self, x: int) -> int:
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:      # path compression, second pass
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, x: int, y: int) -> bool:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        if self.size[rx] < self.size[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        self.size[rx] += self.size[ry]
        self.components -= 1
        return True


def provinces(n: int, edges: list[tuple[int, int]]) -> tuple[int, list[dict]]:
    dsu, steps = _DSU(n), []
    for x, y in edges:
        rx, ry = dsu.find(x), dsu.find(y)
        merged = dsu.union(x, y)
        steps.append({"edge": (x, y), "rx": rx, "ry": ry, "merged": merged,
                      "parent": list(dsu.parent), "size": list(dsu.size),
                      "components": dsu.components})
    return dsu.components, steps


def union_find(n: int, edges: list[tuple[int, int]]) -> str:
    total, steps = provinces(n, edges)
    rows = []
    for st in steps:
        x, y = st["edge"]
        if st["merged"]:
            root = st["parent"][st["ry"]]
            other = st["ry"] if root == st["rx"] else st["rx"]
            action = (f"{_mono('parent[' + str(other) + '] = ' + str(root))}, "
                      f"{_mono('size[' + str(root) + '] = ' + str(st['size'][root]))}")
        else:
            action = "same root already &mdash; return false, change nothing"
        rows.append([
            _cell(_mono(f"({x}, {y})")), _cell(_mono(st["rx"])),
            _cell(_mono(st["ry"])),
            _cell("no" if st["merged"] else "yes",
                  "yes" if st["merged"] else "no"),
            _cell(action, "hl" if st["merged"] else ""),
            _cell(_mono(st["components"]))])
    caption = (f"{_mono(str(n) + ' singletons')} and the edges "
               f"{_mono(edges)} &rarr; {_mono(total)} components. The early "
               f"return on a shared root is what keeps the counter correct: "
               f"without it, a repeated edge decrements it twice.")
    return _figure(caption, _table(
        ("edge", "find(x)", "find(y)", "same root?", "action", "components"),
        rows))


def path_compression(chain: int = 5) -> str:
    """A worst-case chain, and what one find() does to it."""
    dsu = _DSU(chain)
    for i in range(chain - 1, 0, -1):
        dsu.parent[i] = i - 1              # 0 <- 1 <- 2 <- ... a linked list
    before = list(dsu.parent)
    hops = 0
    node = chain - 1
    while dsu.parent[node] != node:
        node, hops = dsu.parent[node], hops + 1
    dsu.find(chain - 1)
    after = list(dsu.parent)
    rows = [
        [_cell("before"), _cell(_mono(before)),
         _cell(f"{hops} hops from {chain - 1} to the root")],
        [_cell("after", "hl"), _cell(_mono(after), "hl"),
         _cell("1 hop, for every node on the path", "hl")],
    ]
    caption = (f"One {_mono('find(' + str(chain - 1) + ')')} on a chain of "
               f"{chain}. The walk to the root happens either way; compression "
               f"is the second pass that makes it never happen again.")
    return _figure(caption, _table(("parent[]", "contents", "cost of the next find"),
                                   rows))


# --------------------------------------------------------------------------
# 5. Counting array -> prefix sums, both orders, side by side
# --------------------------------------------------------------------------

def prefix_orders(counts: list[int]) -> tuple[list[int], list[int], list[dict]]:
    """The in-place version and the snapshot version, run on the same input."""
    wrong, right = list(counts), list(counts)
    w_total = r_total = 0
    steps = []
    for i, c in enumerate(counts):
        wrong[i] += w_total          # reads the accumulator, then feeds itself
        w_total += wrong[i]
        snapshot = r_total           # the running total BEFORE this bucket
        r_total += right[i]
        right[i] = snapshot
        steps.append({"i": i, "count": c, "wrong": wrong[i], "w_total": w_total,
                      "right": right[i], "r_total": r_total})
    return wrong, right, steps


def prefix_sums(counts: list[int]) -> str:
    wrong, right, steps = prefix_orders(counts)
    rows = []
    for st in steps:
        bad = st["wrong"] != st["right"]
        rows.append([
            _cell(_mono(st["i"])), _cell(_mono(st["count"])),
            _cell(_mono(st["wrong"]), "no" if bad else ""),
            _cell(_mono(st["right"]), "yes")])
    caption = (f"Counts {_mono(counts)} turned into exclusive prefix sums. "
               f"In place: {_mono(wrong)}. With the running total snapshotted "
               f"first: {_mono(right)}. The in-place column folds each bucket "
               f"into its own prefix, so it runs away from the second index on.")
    return _figure(caption, _table(
        ("i", "count[i]", "in place (wrong)", "snapshot first (right)"), rows))


# --------------------------------------------------------------------------

def _selfcheck() -> None:
    """python3 traces.py -- every trace is checked against a reference."""
    import bisect
    import itertools

    for nums, target in [([1, 3, 5, 6], 5), ([1, 3, 5, 6], 2), ([1, 3, 5, 6], 7),
                         ([], 1), ([2], 2), ([2, 2, 2], 2)]:
        got, _ = lower_bound(nums, target)
        assert got == bisect.bisect_left(nums, target), (nums, target, got)

    for s in ["abcabcbb", "bbbbb", "pwwkew", "", "au", "dvdf"]:
        got, _ = longest_unique(s)
        best = max((len(set(s[i:j])) for i in range(len(s) + 1)
                    for j in range(i, len(s) + 1)
                    if len(set(s[i:j])) == j - i), default=0)
        assert got == best, (s, got, best)

    for nums in [[2, 1, 2, 4, 3], [1, 2, 3], [3, 2, 1], [5], [1, 1, 1]]:
        got, _ = next_greater(nums)
        want = [next((v for v in nums[i + 1:] if v > nums[i]), -1)
                for i in range(len(nums))]
        assert got == want, (nums, got, want)

    for n, edges in [(3, [(0, 1), (1, 0)]), (4, [(0, 1), (2, 3), (1, 2)]),
                     (5, []), (2, [(0, 1), (0, 1), (1, 0)])]:
        got, _ = provinces(n, edges)
        seen, comps = set(), 0
        adj = {i: set() for i in range(n)}
        for a, b in edges:
            adj[a].add(b)
            adj[b].add(a)
        for start in range(n):              # plain flood fill, no DSU involved
            if start in seen:
                continue
            comps += 1
            stack = [start]
            while stack:
                node = stack.pop()
                if node in seen:
                    continue
                seen.add(node)
                stack.extend(adj[node])
        assert got == comps, (n, edges, got, comps)

    # Path compression must not change what find() answers, only what it costs.
    dsu = _DSU(6)
    for i in range(5, 0, -1):
        dsu.parent[i] = i - 1
    assert dsu.find(5) == 0 and dsu.parent[5] == 0 and dsu.parent[3] == 0

    for counts in [[3, 0, 2, 1], [1, 1, 1], [0, 0, 5], [4]]:
        wrong, right, _ = prefix_orders(counts)
        want = list(itertools.accumulate([0] + counts[:-1]))
        assert right == want, (counts, right, want)
        assert len(counts) < 2 or wrong != right, "the trap must actually trap"

    # Rendering: every trace must produce a table with a body, and no stray
    # backticks -- build_book.py's prose check does not look inside modules.
    figures = [binary_search([1, 3, 5, 6], 5), sliding_window("abcabcbb"),
               monotonic_stack([2, 1, 2, 4, 3]),
               union_find(3, [(0, 1), (1, 0)]), path_compression(),
               prefix_sums([3, 0, 2, 1])]
    for fig in figures:
        assert "<tbody><tr>" in fig and "`" not in fig, fig[:120]
    print(f"traces ok: {len(figures)} tables, all checked against a reference")


if __name__ == "__main__":
    _selfcheck()
