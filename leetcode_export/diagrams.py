#!/usr/bin/env python3
"""Inline SVG diagrams for the course lessons.

Inline rather than image files: the book is a folder of static HTML with one
stylesheet and no build step, and an <svg> in the document inherits the page's
CSS variables -- so every diagram themes itself in light and dark mode for free.
No library, no assets, nothing to keep in sync.

Colour conventions, all from book.css:
    var(--ink)     text and primary strokes
    var(--muted)   labels, axes, secondary text
    var(--line)    boxes, grids, structure
    var(--panel)   box fills
    var(--accent)  the thing the diagram is about
    var(--good)    correct / accepted
    var(--bad)     wrong / the bug
    var(--code)    inert fills
"""

from __future__ import annotations

MONO = "ui-monospace,SFMono-Regular,Menlo,monospace"
SANS = "ui-sans-serif,system-ui,sans-serif"


def svg(width: int, height: int, body: str, caption: str = "", label: str = "") -> str:
    """Wrap SVG body in a responsive, captioned figure."""
    cap = f"<figcaption>{caption}</figcaption>" if caption else ""
    title = f"<title>{label or caption}</title>" if (label or caption) else ""
    return (f'<figure class="diagram">'
            f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" preserveAspectRatio="xMidYMid meet">{title}{body}</svg>'
            f"{cap}</figure>")


# -- primitives -------------------------------------------------------------

def box(x, y, w, h, text, fill="var(--panel)", stroke="var(--line)",
        color="var(--ink)", font=MONO, size=13, rx=4, weight="400"):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
            f'<text x="{x + w / 2}" y="{y + h / 2 + size * 0.36}" text-anchor="middle" '
            f'font-family="{font}" font-size="{size}" font-weight="{weight}" '
            f'fill="{color}">{text}</text>')


def label(x, y, text, color="var(--muted)", size=12, anchor="middle", font=SANS,
          weight="400"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{font}" '
            f'font-size="{size}" font-weight="{weight}" fill="{color}">{text}</text>')


def line(x1, y1, x2, y2, color="var(--line)", width=1.5, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{width}"{d}/>')


ARROWHEADS = """
<defs>
<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
        markerHeight="6" orient="auto-start-reverse">
  <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--ink)"/>
</marker>
<marker id="ah-a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
        markerHeight="6" orient="auto-start-reverse">
  <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent)"/>
</marker>
<marker id="ah-b" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
        markerHeight="6" orient="auto-start-reverse">
  <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--bad)"/>
</marker>
<marker id="ah-g" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
        markerHeight="6" orient="auto-start-reverse">
  <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--good)"/>
</marker>
</defs>
"""


def arrow(x1, y1, x2, y2, color="var(--ink)", head="ah", width=1.6, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{width}" marker-end="url(#{head})"{d}/>')


def node_arrow(x1, y1, x2, y2, r=15, color="var(--ink)", head="ah", width=1.6, dash=""):
    """Arrow between two circle centres, clipped to both circumferences."""
    dx, dy = x2 - x1, y2 - y1
    d = (dx * dx + dy * dy) ** 0.5 or 1.0
    ux, uy = dx / d, dy / d
    return arrow(x1 + ux * r, y1 + uy * r, x2 - ux * (r + 3), y2 - uy * (r + 3),
                 color, head, width, dash)


def curve(x1, y1, x2, y2, bend, color="var(--ink)", head="ah", dash=""):
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - bend
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<path d="M {x1} {y1} Q {mx} {my} {x2} {y2}" fill="none" '
            f'stroke="{color}" stroke-width="1.6" marker-end="url(#{head})"{d}/>')


# ==========================================================================
# integer-width
# ==========================================================================

def twos_complement() -> str:
    b = [ARROWHEADS]
    y = 78
    b.append(line(60, y, 620, y, "var(--line)", 2))
    for x, t in ((60, "MIN"), (340, "0"), (620, "MAX")):
        b.append(line(x, y - 7, x, y + 7, "var(--muted)", 2))
        b.append(label(x, y + 26, t, size=11, font=MONO))
    b.append(label(60, y + 42, "-2,147,483,648", size=10))
    b.append(label(620, y + 42, "2,147,483,647", size=10))

    # a + a runs off the top end and reappears at the bottom
    b.append(f'<circle cx="560" cy="{y}" r="5" fill="var(--good)"/>')
    b.append(label(560, y - 16, "a = 2·10⁹", color="var(--good)", size=11, font=MONO))
    b.append(curve(560, y - 6, 700, y - 6, 40, "var(--bad)", "ah-b"))
    b.append(label(650, y - 52, "a + a", color="var(--bad)", size=11, font=MONO))
    b.append(f'<path d="M 700 {y - 6} L 700 {y + 46} L -20 {y + 46} L -20 {y - 6}" '
             f'fill="none" stroke="var(--bad)" stroke-width="1.6" stroke-dasharray="4 3"/>')
    b.append(curve(-20, y - 6, 130, y - 6, 40, "var(--bad)", "ah-b"))
    b.append(f'<circle cx="130" cy="{y}" r="5" fill="var(--bad)"/>')
    b.append(label(130, y - 16, "-294,967,296", color="var(--bad)", size=11, font=MONO))
    b.append(label(340, 152, "no exception, no warning — the value simply wraps",
                   color="var(--bad)", size=12))
    return svg(700, 172, "".join(b),
               "A 32-bit int is a ring, not a line. Adding past MAX continues from MIN.")


def widening_order() -> str:
    b = [ARROWHEADS]
    rows = [
        (36, "long c = a + a;", "int + int", "→ wraps", "→ widen the wrong value",
         "var(--bad)"),
        (110, "long d = (long) a + a;", "long + int", "→ long", "→ correct",
         "var(--good)"),
    ]
    for y, expr, step1, step2, step3, colour in rows:
        b.append(box(14, y, 220, 34, expr, color="var(--ink)", size=12))
        b.append(arrow(240, y + 17, 274, y + 17, colour,
                       "ah-b" if colour == "var(--bad)" else "ah-g"))
        b.append(box(280, y, 108, 34, step1, fill="var(--code)", size=12))
        b.append(label(410, y + 22, step2, color=colour, size=12, font=MONO))
        b.append(label(560, y + 22, step3, color=colour, size=12))
    b.append(label(350, 176, "Java picks the arithmetic width from the OPERANDS. "
                   "The destination type is decided last, and too late.",
                   color="var(--muted)", size=12))
    return svg(700, 194, "".join(b),
               "The assignment target never changes how the arithmetic is done.")


# ==========================================================================
# sentinels
# ==========================================================================

def identity_competition() -> str:
    b = [ARROWHEADS]
    vals = [-3, -8, -1, -6]
    y = 62
    for i, v in enumerate(vals):
        x = 150 + i * 66
        b.append(box(x, y, 56, 34, str(v), fill="var(--code)"))
    b.append(label(96, y + 22, "values", color="var(--muted)", size=12, anchor="end"))

    b.append(box(150, 128, 56, 34, "0", fill="var(--panel)", stroke="var(--bad)",
                 color="var(--bad)", weight="700"))
    b.append(label(140, 150, "max starts at", color="var(--muted)", size=12, anchor="end"))
    b.append(label(224, 150, "beats every real value → answer 0",
                   color="var(--bad)", size=12, anchor="start"))

    b.append(box(150, 190, 96, 34, "MIN_VALUE", fill="var(--panel)",
                 stroke="var(--good)", color="var(--good)", size=11, weight="700"))
    b.append(label(140, 212, "max starts at", color="var(--muted)", size=12, anchor="end"))
    b.append(label(264, 212, "loses to every real value → answer -1",
                   color="var(--good)", size=12, anchor="start"))
    b.append(label(350, 28, "max over a set that may be entirely negative",
                   color="var(--ink)", size=13, weight="600"))
    return svg(700, 240, "".join(b),
               "An identity must lose to all real data. 0 does not, unless you have "
               "proved the data is non-negative.")


def dummy_nodes() -> str:
    b = [ARROWHEADS]
    def chain(y, nodes, colour, title, note):
        b.append(label(20, y - 22, title, color=colour, size=12, anchor="start",
                       weight="600"))
        xs = []
        for i, n in enumerate(nodes):
            x = 130 + i * 130
            xs.append(x)
            fill = "var(--code)" if n in ("head", "tail") else "var(--panel)"
            b.append(box(x, y, 86, 34, n, fill=fill,
                         stroke=colour if n in ("head", "tail") else "var(--line)"))
        for i in range(len(nodes) - 1):
            b.append(arrow(xs[i] + 86, y + 12, xs[i + 1], y + 12, colour,
                           "ah-b" if colour == "var(--bad)" else "ah-g"))
            b.append(arrow(xs[i + 1], y + 26, xs[i] + 86, y + 26, colour,
                           "ah-b" if colour == "var(--bad)" else "ah-g"))
        b.append(label(20, y + 22, note, color="var(--muted)", size=11, anchor="start"))

    chain(56, ["head", "tail"], "var(--bad)", "constructor forgot the links", "")
    b.append(label(360, 108, "head.next == null  →  first add() dereferences it  →  NPE",
                   color="var(--bad)", size=12, font=MONO))
    chain(168, ["head", "node", "tail"], "var(--good)",
          "head.next = tail;  tail.prev = head;", "")
    b.append(label(360, 224,
                   "every insert and remove now has a real neighbour on both sides — no null checks",
                   color="var(--good)", size=12))
    return svg(700, 244, "".join(b),
               "Dummy head/tail exist to delete the edge cases. Unlinked, they add one.")


# ==========================================================================
# bounds
# ==========================================================================

def grid_bounds() -> str:
    b = [ARROWHEADS]
    cell, ox, oy = 52, 200, 44
    for r in range(3):
        for c in range(3):
            b.append(box(ox + c * cell, oy + r * cell, cell - 4, cell - 4,
                         "·", fill="var(--panel)", color="var(--muted)"))
    # the cell being examined
    b.append(box(ox, oy, cell - 4, cell - 4, "x", fill="var(--code)",
                 stroke="var(--accent)", color="var(--accent)", weight="700"))
    b.append(label(ox + 24, oy - 14, "(0,0)", color="var(--accent)", size=11, font=MONO))
    # the four neighbours, two of which are off the grid
    for dx, dy, ok in ((-1, 0, False), (0, -1, False), (1, 0, True), (0, 1, True)):
        x, y = ox + dx * cell, oy + dy * cell
        colour = "var(--good)" if ok else "var(--bad)"
        b.append(f'<rect x="{x}" y="{y}" width="{cell - 4}" height="{cell - 4}" rx="4" '
                 f'fill="none" stroke="{colour}" stroke-width="2" stroke-dasharray="4 3"/>')
        if not ok:
            b.append(label(x + 24, y + 30, "✗", color="var(--bad)", size=18))
    b.append(label(80, 70, "in range", color="var(--good)", size=12, anchor="start"))
    b.append(label(80, 92, "off the grid", color="var(--bad)", size=12, anchor="start"))
    b.append(label(80, 114, "board[-1][0] throws", color="var(--bad)", size=11,
                   anchor="start", font=MONO))

    b.append(f'<rect x="14" y="184" width="672" height="76" rx="6" fill="var(--code)" '
             f'stroke="var(--line)"/>')
    b.append(label(30, 208, "if (board[x][y] == c  &&  x >= 0 && x < m)",
                   color="var(--bad)", size=13, anchor="start", font=MONO))
    b.append(label(560, 208, "read, then check", color="var(--bad)", size=11))
    b.append(label(30, 240, "if (x >= 0 && x < m  &&  board[x][y] == c)",
                   color="var(--good)", size=13, anchor="start", font=MONO))
    b.append(label(560, 240, "check, then read", color="var(--good)", size=11))
    return svg(700, 274, "".join(b),
               "&& short-circuits left to right, so the range test has to be written first.")


# ==========================================================================
# binary-search
# ==========================================================================

def binary_search_steps() -> str:
    b = [ARROWHEADS]
    n = 8
    cell, ox = 62, 100
    pred = [False, False, False, False, True, True, True, True]
    steps = [(0, 8, 4), (0, 4, 2), (3, 4, 3)]

    b.append(label(ox - 20, 34, "i", color="var(--muted)", size=11, anchor="end", font=MONO))
    for i in range(n):
        b.append(label(ox + i * cell + 27, 34, str(i), color="var(--muted)", size=11,
                       font=MONO))
    b.append(label(ox - 20, 66, "pred", color="var(--muted)", size=11, anchor="end",
                   font=MONO))
    for i in range(n):
        t, c = ("T", "var(--good)") if pred[i] else ("F", "var(--bad)")
        b.append(box(ox + i * cell, 46, cell - 8, 30, t, fill="var(--code)", color=c,
                     weight="700"))
    b.append(f'<path d="M {ox + 4 * cell - 4} 40 L {ox + 4 * cell - 4} 84" '
             f'stroke="var(--accent)" stroke-width="2" stroke-dasharray="3 3"/>')
    b.append(label(ox + 4 * cell - 4, 100, "first true — the answer",
                   color="var(--accent)", size=11, weight="600"))

    for k, (lo, hi, mid) in enumerate(steps):
        y = 128 + k * 46
        b.append(label(ox - 20, y + 16, f"{k + 1}", color="var(--muted)", size=11,
                       anchor="end", font=MONO))
        b.append(f'<rect x="{ox + lo * cell - 4}" y="{y}" '
                 f'width="{(hi - lo) * cell}" height="26" rx="4" '
                 f'fill="var(--code)" stroke="var(--line)"/>')
        b.append(label(ox + lo * cell + 6, y + 18, "lo", color="var(--ink)", size=10,
                       anchor="start", font=MONO))
        b.append(label(ox + hi * cell - 10, y + 18, "hi", color="var(--ink)", size=10,
                       anchor="end", font=MONO))
        b.append(f'<circle cx="{ox + mid * cell + 27}" cy="{y + 13}" r="9" '
                 f'fill="var(--accent)"/>')
        b.append(label(ox + mid * cell + 27, y + 17, "m", color="var(--bg)", size=10,
                       font=MONO, weight="700"))
        verdict = ("pred(m) = T → hi = m" if pred[mid] else "pred(m) = F → lo = m+1")
        b.append(label(ox + n * cell + 16, y + 18, verdict,
                       color="var(--good)" if pred[mid] else "var(--bad)",
                       size=11, anchor="start", font=MONO))
    b.append(label(ox - 20, 274, "→", color="var(--accent)", size=13, anchor="end"))
    b.append(label(ox + 4 * cell - 4, 274, "lo == hi == 4",
                   color="var(--accent)", size=12, font=MONO, weight="600"))
    b.append(label(ox + n * cell + 16, 274, "loop ends, lo is the answer",
                   color="var(--muted)", size=11, anchor="start"))
    return svg(800, 292, "".join(b),
               "Half-open [lo, hi). The invariant — the answer is always inside "
               "[lo, hi] — holds after every step.")


# ==========================================================================
# equality-hashing
# ==========================================================================

def integer_cache() -> str:
    b = [ARROWHEADS]
    b.append(f'<rect x="30" y="30" width="300" height="200" rx="8" fill="none" '
             f'stroke="var(--good)" stroke-width="1.5"/>')
    b.append(label(180, 52, "value 127 — inside the cache", color="var(--good)",
                   size=12, weight="600"))
    b.append(box(58, 78, 90, 32, "Integer a", fill="var(--panel)", size=12))
    b.append(box(58, 128, 90, 32, "Integer b", fill="var(--panel)", size=12))
    b.append(box(212, 100, 90, 40, "[ 127 ]", fill="var(--code)",
                 stroke="var(--good)", color="var(--good)"))
    b.append(arrow(148, 94, 212, 112, "var(--good)", "ah-g"))
    b.append(arrow(148, 144, 212, 130, "var(--good)", "ah-g"))
    b.append(label(180, 196, "one cached object", color="var(--muted)", size=11))
    b.append(label(180, 216, "a == b  →  true", color="var(--good)", size=12, font=MONO))

    b.append(f'<rect x="370" y="30" width="300" height="200" rx="8" fill="none" '
             f'stroke="var(--bad)" stroke-width="1.5"/>')
    b.append(label(520, 52, "value 128 — outside the cache", color="var(--bad)",
                   size=12, weight="600"))
    b.append(box(398, 78, 90, 32, "Integer c", fill="var(--panel)", size=12))
    b.append(box(398, 148, 90, 32, "Integer d", fill="var(--panel)", size=12))
    b.append(box(552, 72, 90, 40, "[ 128 ]", fill="var(--code)", stroke="var(--bad)",
                 color="var(--bad)"))
    b.append(box(552, 142, 90, 40, "[ 128 ]", fill="var(--code)", stroke="var(--bad)",
                 color="var(--bad)"))
    b.append(arrow(488, 94, 552, 92, "var(--bad)", "ah-b"))
    b.append(arrow(488, 164, 552, 162, "var(--bad)", "ah-b"))
    b.append(label(520, 206, "two distinct objects, equal values",
                   color="var(--muted)", size=11))
    b.append(label(520, 226, "c == d  →  FALSE", color="var(--bad)", size=12, font=MONO,
                   weight="700"))
    return svg(700, 248, "".join(b),
               "Java caches boxed <code>Integer</code>s for −128…127. Below the "
               "boundary <code>==</code> appears to work; above it, it silently does "
               "not. That is why it passes your small tests and fails on the judge.")


# ==========================================================================
# union-find
# ==========================================================================

def dsu_union() -> str:
    b = [ARROWHEADS]

    def forest(pos, edges, colour="var(--line)", ring=(), ghost=()):
        out = []
        for child, parent in edges:
            x1, y1 = pos[child]
            x2, y2 = pos[parent]
            out.append(node_arrow(x1, y1, x2, y2, 17, colour,
                                  "ah-b" if colour == "var(--bad)" else
                                  "ah-g" if colour == "var(--good)" else "ah"))
        for nid, (x, y) in pos.items():
            dashed = nid in ghost
            stroke = ("var(--bad)" if dashed else
                      "var(--accent)" if nid in ring else "var(--line)")
            dash = ' stroke-dasharray="3 3"' if dashed else ""
            out.append(f'<circle cx="{x}" cy="{y}" r="17" fill="var(--panel)" '
                       f'stroke="{stroke}" '
                       f'stroke-width="{2.5 if (dashed or nid in ring) else 1.5}"{dash}/>')
            out.append(label(x, y + 5, str(nid),
                             color="var(--bad)" if dashed else "var(--ink)",
                             size=13, font=MONO))
        return "".join(out)

    b.append(label(128, 30, "before union(3, 5)", color="var(--muted)", size=12,
                   weight="600"))
    b.append(forest({1: (64, 76), 2: (64, 140), 3: (64, 204)},
                    [(2, 1), (3, 2)], ring={1}))
    b.append(forest({4: (194, 76), 5: (194, 140)}, [(5, 4)], ring={4}))
    b.append(label(64, 240, "find(3) = 1", color="var(--accent)", size=11, font=MONO))
    b.append(label(194, 240, "find(5) = 4", color="var(--accent)", size=11, font=MONO))
    b.append(label(128, 262, "roots ringed", color="var(--muted)", size=11))

    b.append(arrow(268, 130, 322, 130, "var(--ink)"))

    b.append(label(452, 30, "correct — parent[rootY] = rootX", color="var(--good)",
                   size=12, weight="600"))
    b.append(forest({1: (452, 76), 2: (392, 150), 3: (392, 214), 4: (516, 150),
                     5: (516, 214)},
                    [(2, 1), (3, 2), (4, 1), (5, 4)], colour="var(--good)"))
    b.append(label(452, 254, "one tree — 3 and 5 are connected", color="var(--good)",
                   size=11))
    b.append(label(452, 274, "and 4's subtree came with it", color="var(--good)",
                   size=11))

    b.append(label(672, 30, "the bug — parent[y] = rootX", color="var(--bad)",
                   size=12, weight="600"))
    b.append(forest({1: (672, 76), 2: (612, 150), 3: (612, 214), 5: (736, 150),
                     4: (736, 226)},
                    [(2, 1), (3, 2), (5, 1)], colour="var(--bad)", ghost={4}))
    b.append(label(672, 274, "4 is stranded — union(3,5)", color="var(--bad)", size=11))
    b.append(label(672, 290, "never merged its tree", color="var(--bad)", size=11))
    return svg(800, 306, "".join(b),
               "union() moves whole trees, and a tree is addressed by its root. "
               "Attaching a non-root strands everything above it — the exact bug in "
               "your number-of-islands-ii Wrong Answer.")


def dsu_path_compression() -> str:
    b = [ARROWHEADS]

    def node(x, y, t, stroke="var(--line)", w=1.5):
        return (f'<circle cx="{x}" cy="{y}" r="17" fill="var(--panel)" '
                f'stroke="{stroke}" stroke-width="{w}"/>'
                + label(x, y + 5, t, color="var(--ink)", size=13, font=MONO))

    b.append(label(120, 30, "before find(1)", color="var(--muted)", size=12,
                   weight="600"))
    ys = [62, 118, 174, 230]
    for i, y in enumerate(ys):
        b.append(node(120, y, str(4 - i)))
        if i:
            b.append(node_arrow(120, y, 120, ys[i - 1], 17))
    b.append(label(120, 268, "depth 4 — every find walks all of it",
                   color="var(--muted)", size=11))

    b.append(arrow(200, 146, 268, 146, "var(--ink)"))
    b.append(label(234, 132, "find(1)", color="var(--accent)", size=11, font=MONO))

    b.append(label(500, 30, "after find(1)", color="var(--good)", size=12, weight="600"))
    b.append(node(500, 76, "4", "var(--good)", 2.5))
    for i, x in enumerate((390, 500, 610)):
        b.append(node(x, 174, str(3 - i)))
        b.append(node_arrow(x, 174, 500, 76, 17, "var(--good)", "ah-g"))
    b.append(label(500, 230, "depth 1 — every node on the path was rewired to the root",
                   color="var(--good)", size=11))
    b.append(label(500, 262, "if (parent[x] != x) parent[x] = find(parent[x]);",
                   color="var(--accent)", size=12, font=MONO))
    b.append(label(500, 282, "The assignment is the compression. Drop it and find() "
                   "stays O(n) forever.", color="var(--muted)", size=11))
    return svg(760, 300, "".join(b),
               "find() does not just read the root — on the way back up it repoints "
               "everything it walked past.")


# ==========================================================================
# graph-traversal
# ==========================================================================

def dijkstra_counterexample() -> str:
    b = [ARROWHEADS]
    nodes = {"S": (80, 130), "A": (280, 62), "B": (280, 198), "T": (470, 130)}
    edges = [("S", "A", "10", -16, 12), ("S", "B", "1", 16, -14),
             ("B", "A", "1", 0, 16), ("A", "T", "1", -16, -12)]
    for a, c, w, oy, ox in edges:
        x1, y1 = nodes[a]
        x2, y2 = nodes[c]
        b.append(node_arrow(x1, y1, x2, y2, 21))
        b.append(label((x1 + x2) / 2 + ox, (y1 + y2) / 2 + oy, w,
                       color="var(--accent)", size=13, font=MONO, weight="700"))
    for n, (x, y) in nodes.items():
        b.append(f'<circle cx="{x}" cy="{y}" r="21" fill="var(--panel)" '
                 f'stroke="var(--line)" stroke-width="1.5"/>')
        b.append(label(x, y + 5, n, color="var(--ink)", size=13, font=MONO, weight="600"))
    b.append(label(275, 254, "Shortest S→T is S→B→A→T, cost 3. The direct S→A edge "
                   "costs 10.", color="var(--muted)", size=11))

    b.append(f'<rect x="530" y="44" width="230" height="88" rx="6" fill="var(--code)" '
             f'stroke="var(--bad)"/>')
    b.append(label(546, 68, "visited on PUSH", color="var(--bad)", size=12,
                   anchor="start", weight="700"))
    b.append(label(546, 90, "A is locked at 10 the moment", color="var(--bad)",
                   size=11, anchor="start"))
    b.append(label(546, 106, "the S→A edge is first seen", color="var(--bad)",
                   size=11, anchor="start"))
    b.append(label(546, 126, "dist[T] = 11   ✗", color="var(--bad)", size=12,
                   anchor="start", font=MONO, weight="700"))

    b.append(f'<rect x="530" y="146" width="230" height="88" rx="6" fill="var(--code)" '
             f'stroke="var(--good)"/>')
    b.append(label(546, 170, "finalised on POP", color="var(--good)", size=12,
                   anchor="start", weight="700"))
    b.append(label(546, 192, "the (2, A) entry pops before", color="var(--good)",
                   size=11, anchor="start"))
    b.append(label(546, 208, "the (10, A) entry ever does", color="var(--good)",
                   size=11, anchor="start"))
    b.append(label(546, 228, "dist[T] = 3    ✓", color="var(--good)", size=12,
                   anchor="start", font=MONO, weight="700"))
    return svg(776, 272, "".join(b),
               "The smallest graph that breaks visited-on-push: with weights, the "
               "first time you SEE a node is not the cheapest way to reach it. "
               "This is your number-of-ways-to-arrive-at-destination bug in four edges.")


def kahn_direction() -> str:
    b = [ARROWHEADS]
    b.append(label(230, 30, '"to take B you must first take A"',
                   color="var(--ink)", size=13, weight="600"))
    b.append(f'<circle cx="150" cy="96" r="24" fill="var(--panel)" '
             f'stroke="var(--line)" stroke-width="1.5"/>')
    b.append(label(150, 101, "A", color="var(--ink)", size=14, font=MONO, weight="600"))
    b.append(f'<circle cx="330" cy="96" r="24" fill="var(--panel)" '
             f'stroke="var(--accent)" stroke-width="2.5"/>')
    b.append(label(330, 101, "B", color="var(--ink)", size=14, font=MONO, weight="600"))
    b.append(arrow(176, 96, 304, 96, "var(--accent)", "ah-a", 2))
    b.append(label(150, 142, "tail", color="var(--muted)", size=11))
    b.append(label(240, 78, "A before B", color="var(--accent)", size=11))
    b.append(label(330, 142, "head", color="var(--accent)", size=11, weight="600"))
    b.append(label(330, 162, "indegree[B]++", color="var(--accent)", size=12, font=MONO,
                   weight="700"))

    b.append(f'<rect x="418" y="56" width="330" height="52" rx="6" fill="var(--code)" '
             f'stroke="var(--good)"/>')
    b.append(label(434, 78, "adj[A].add(B);", color="var(--good)", size=12,
                   anchor="start", font=MONO))
    b.append(label(434, 98, "indegree[B]++;", color="var(--good)", size=12,
                   anchor="start", font=MONO))
    b.append(f'<rect x="418" y="122" width="330" height="52" rx="6" fill="var(--code)" '
             f'stroke="var(--bad)"/>')
    b.append(label(434, 144, "adj[B].add(A);", color="var(--bad)", size=12,
                   anchor="start", font=MONO))
    b.append(label(434, 164, "indegree[A]++;   ← your recurring bug",
                   color="var(--bad)", size=12, anchor="start", font=MONO))
    return svg(760, 196, "".join(b),
               "Say the prerequisite out loud. The course you name <em>second</em> is "
               "the head of the edge, and the head is the one whose indegree goes up. "
               "This one rule would have prevented three separate "
               "course-schedule-ii failures across 15 months.")


def bfs_layers() -> str:
    b = [ARROWHEADS]
    layers = [["S"], ["a", "b"], ["c", "d", "e"], ["T"]]
    pos = {}
    for li, layer in enumerate(layers):
        x = 90 + li * 170
        for ni, n in enumerate(layer):
            y = 130 + (ni - (len(layer) - 1) / 2) * 62
            pos[n] = (x, y)
    for a, c in [("S", "a"), ("S", "b"), ("a", "c"), ("a", "d"), ("b", "d"),
                 ("b", "e"), ("c", "T"), ("d", "T"), ("e", "T")]:
        x1, y1 = pos[a]
        x2, y2 = pos[c]
        b.append(line(x1 + 20, y1, x2 - 20, y2, "var(--line)", 1.2))
    for li, layer in enumerate(layers):
        x = 90 + li * 170
        b.append(f'<rect x="{x - 42}" y="14" width="84" height="232" rx="8" '
                 f'fill="var(--code)" opacity="0.55"/>')
        b.append(label(x, 34, f"dist {li}", color="var(--accent)", size=11, weight="600"))
        for n in layer:
            nx, ny = pos[n]
            b.append(f'<circle cx="{nx}" cy="{ny}" r="19" fill="var(--panel)" '
                     f'stroke="var(--line)" stroke-width="1.5"/>')
            b.append(label(nx, ny + 5, n, color="var(--ink)", size=12, font=MONO))
    return svg(700, 262, "".join(b),
               "BFS expands in complete layers — every node in layer <em>k</em> is at "
               "distance <em>k</em>. On an unweighted graph the first arrival IS the "
               "shortest, which is why marking visited at enqueue time is both correct "
               "and necessary.")


# ==========================================================================
# range-structures
# ==========================================================================

def bit_coverage() -> str:
    b = []
    n, cell, ox, oy = 8, 70, 130, 92
    b.append(label(ox - 14, 44, "a[ ]", color="var(--muted)", size=11, anchor="end",
                   font=MONO))
    for i in range(n):
        b.append(box(ox + i * cell, 26, cell - 8, 28, f"a{i + 1}", fill="var(--code)",
                     size=12))
    for i in range(1, n + 1):
        span = i & -i
        start_at = i - span
        x = ox + start_at * cell
        w = span * cell - 8
        y = oy + (i - 1) * 26
        b.append(f'<rect x="{x}" y="{y}" width="{w}" height="20" rx="3" '
                 f'fill="var(--panel)" stroke="var(--accent)" stroke-width="1.3"/>')
        text = f"a{start_at + 1}…a{i}" if span > 1 else f"a{i}"
        if span > 1:                       # room inside the block
            b.append(label(x + w / 2, y + 14, text, color="var(--accent)", size=11,
                           font=MONO))
        else:                              # too narrow -- caption it to the right
            b.append(label(x + w + 6, y + 14, text, color="var(--accent)", size=11,
                           anchor="start", font=MONO))
        b.append(label(ox - 14, y + 14, f"tree[{i}]", color="var(--muted)", size=11,
                       anchor="end", font=MONO))
        b.append(label(ox + n * cell + 14, y + 14, f"i &amp; -i = {span}",
                       color="var(--muted)", size=10, anchor="start", font=MONO))
    return svg(770, 320, "".join(b),
               "<code>tree[i]</code> holds a <em>block</em> ending at <code>i</code>, of "
               "length <code>i &amp; -i</code>. It never holds <code>a[i]</code>. A "
               "Fenwick tree is an encoding of the array, not a copy of it — which is "
               "why <code>add()</code> is the only way data gets in, and why "
               "<code>tree = dist</code> cannot work.")


def segment_tree_shape() -> str:
    b = [ARROWHEADS]
    levels = [
        [("[0,8)", 380)],
        [("[0,4)", 200), ("[4,8)", 560)],
        [("[0,2)", 110), ("[2,4)", 290), ("[4,6)", 470), ("[6,8)", 650)],
    ]
    ys = [40, 116, 192]
    for li, level in enumerate(levels):
        for text, x in level:
            b.append(box(x - 46, ys[li], 92, 30, text, fill="var(--panel)", size=12))
            if li:
                parent_x = min((p[1] for p in levels[li - 1]),
                               key=lambda px: abs(px - x))
                b.append(line(x, ys[li], parent_x, ys[li - 1] + 30, "var(--line)", 1.2))
    for i in range(8):
        x = 65 + i * 90
        b.append(box(x - 32, 268, 64, 30, f"a{i}", fill="var(--code)", size=12))
        parent_x = min((p[1] for p in levels[2]), key=lambda px: abs(px - x))
        b.append(line(x, 268, parent_x, 222, "var(--line)", 1.2))
    return svg(760, 318, "".join(b),
               "Each node stores <code>merge(left, right)</code>, and any query splits "
               "into O(log n) of these nodes — never more. <code>merge</code> must be "
               "associative with an identity; that is the <em>only</em> requirement, "
               "which is why one tree serves sum, min, max or gcd. Half-open "
               "[l, r) throughout, the same convention as binary search.")


# ==========================================================================
# windows
# ==========================================================================

def sliding_window() -> str:
    b = [ARROWHEADS]
    arr = [1, 3, 3, 2, 5, 1, 4, 2]
    cell, ox = 70, 130
    rows = [(0, 2, "extend: right++", "var(--accent)", "window still valid"),
            (0, 4, "extend again", "var(--bad)", "invariant broken"),
            (2, 4, "shrink: while(!valid) left++", "var(--good)", "valid again — record now")]
    for i, v in enumerate(arr):
        b.append(box(ox + i * cell, 24, cell - 8, 30, str(v), fill="var(--code)", size=12))
        b.append(label(ox + i * cell + 31, 70, str(i), color="var(--muted)", size=10,
                       font=MONO))
    for k, (lo, hi, note, colour, verdict) in enumerate(rows):
        y = 96 + k * 62
        b.append(f'<rect x="{ox + lo * cell - 5}" y="{y}" '
                 f'width="{(hi - lo + 1) * cell - 2}" height="34" rx="5" fill="none" '
                 f'stroke="{colour}" stroke-width="2.5"/>')
        for i in range(lo, hi + 1):
            b.append(box(ox + i * cell, y + 2, cell - 8, 30, str(arr[i]),
                         fill="var(--panel)", size=12))
        b.append(label(ox + lo * cell + 6, y + 50, "L", color=colour, size=10,
                       font=MONO, weight="700"))
        b.append(label(ox + hi * cell + 56, y + 50, "R", color=colour, size=10,
                       font=MONO, weight="700"))
        b.append(label(24, y + 14, note, color="var(--muted)", size=11, anchor="start"))
        b.append(label(24, y + 30, verdict, color=colour, size=11, anchor="start",
                       weight="600"))
    return svg(760, 284, "".join(b),
               'The invariant here is "at most 2 distinct values in the window". Each '
               "index enters once and leaves once, so the nested loop is still O(n) — "
               "and the shrink is a <code>while</code>, because one removal may not be "
               "enough.")


# ==========================================================================
# recursion
# ==========================================================================

def backtracking_tree() -> str:
    b = [ARROWHEADS]
    nodes = {
        "[]": (380, 44), "[1]": (180, 122), "[2]": (380, 122), "[3]": (580, 122),
        "[1,2]": (100, 200), "[1,3]": (260, 200), "[2,3]": (380, 200),
    }
    edges = [("[]", "[1]"), ("[]", "[2]"), ("[]", "[3]"),
             ("[1]", "[1,2]"), ("[1]", "[1,3]"), ("[2]", "[2,3]")]
    for a, c in edges:
        x1, y1 = nodes[a]
        x2, y2 = nodes[c]
        b.append(arrow(x1, y1 + 16, x2, y2 - 16, "var(--good)", "ah-g", 1.3))
        b.append(curve(x2 - 14, y2 - 16, x1 - 14, y1 + 16, -22, "var(--bad)", "ah-b",
                       "3 3"))
    for n, (x, y) in nodes.items():
        b.append(box(x - 36, y - 16, 72, 32, n, fill="var(--panel)", size=12))
    b.append(f'<rect x="600" y="176" width="150" height="30" rx="5" '
             f'fill="var(--code)" stroke="var(--good)"/>')
    b.append(label(616, 196, "do:   path.add(x)", color="var(--good)", size=11,
                   anchor="start", font=MONO))
    b.append(f'<rect x="600" y="212" width="150" height="30" rx="5" '
             f'fill="var(--code)" stroke="var(--bad)"/>')
    b.append(label(616, 232, "undo: path.remove()", color="var(--bad)", size=11,
                   anchor="start", font=MONO))
    return svg(760, 258, "".join(b),
               "One <code>path</code> object is reused for the whole search: the solid "
               "arrow adds, the dashed one undoes. Every mutation on the way down needs "
               "its mirror on the way back up — and collected results must be "
               "<em>copied</em>, because <code>path</code> keeps changing after you "
               "store it.")


def record_vs_return() -> str:
    b = [ARROWHEADS]
    nodes = {"n": (380, 60), "L": (270, 160), "R": (490, 160)}
    for c in ("L", "R"):
        b.append(line(380, 82, nodes[c][0], nodes[c][1] - 22, "var(--line)"))
    for n, (x, y) in nodes.items():
        b.append(f'<circle cx="{x}" cy="{y}" r="22" fill="var(--panel)" '
                 f'stroke="var(--line)" stroke-width="1.5"/>')
        b.append(label(x, y + 5, n, color="var(--ink)", size=13, font=MONO))
    b.append(f'<path d="M 270 138 Q 380 30 490 138" fill="none" stroke="var(--accent)" '
             f'stroke-width="2.5"/>')
    b.append(label(380, 22, "RECORD: uses both children — a path through n",
                   color="var(--accent)", size=12, weight="600"))
    b.append(arrow(380, 38, 380, -2, "var(--good)", "ah-g", 2.5))
    b.append(f'<path d="M 270 138 Q 320 100 372 78" fill="none" stroke="var(--good)" '
             f'stroke-width="2.5"/>')
    b.append(label(150, 206, "RETURN: one child only —", color="var(--good)", size=12,
                   anchor="start", weight="600"))
    b.append(label(150, 224, "a path that can still extend upward",
                   color="var(--good)", size=12, anchor="start"))
    b.append(label(150, 250, "best = max(best, n + L + R);", color="var(--accent)",
                   size=12, anchor="start", font=MONO))
    b.append(label(150, 270, "return  n + max(L, R);", color="var(--good)", size=12,
                   anchor="start", font=MONO))
    b.append(label(560, 250, "Conflating these two is the", color="var(--muted)",
                   size=11, anchor="start"))
    b.append(label(560, 268, "classic bug on tree-DP problems.", color="var(--muted)",
                   size=11, anchor="start"))
    return svg(760, 288, "".join(b),
               "A recursive call returns one thing and records another. Say which, "
               "precisely, before writing the body.")


# ==========================================================================
# complexity-budget
# ==========================================================================

def growth_curves() -> str:
    b = []
    ox, oy, w, h = 80, 250, 560, 210
    b.append(line(ox, oy, ox + w, oy, "var(--muted)", 1.5))
    b.append(line(ox, oy, ox, oy - h, "var(--muted)", 1.5))
    b.append(label(ox + w / 2, oy + 34, "input size n", size=12))
    b.append(f'<text x="24" y="{oy - h / 2}" text-anchor="middle" font-family="{SANS}" '
             f'font-size="12" fill="var(--muted)" '
             f'transform="rotate(-90 24 {oy - h / 2})">operations</text>')
    b.append(line(ox, oy - h + 20, ox + w, oy - h + 20, "var(--bad)", 1.2, "5 4"))
    b.append(label(ox + w - 4, oy - h + 12, "10⁸ — the budget", color="var(--bad)",
                   size=11, anchor="end"))

    import math
    curves = [
        ("log n", lambda t: math.log2(1 + t * 60) / 8, "var(--good)"),
        ("n", lambda t: t, "var(--good)"),
        ("n log n", lambda t: t * math.log2(2 + t * 30) / 5.2, "var(--accent)"),
        ("n²", lambda t: t * t, "var(--bad)"),
        ("2ⁿ", lambda t: (2 ** (t * 9) - 1) / 511, "var(--bad)"),
    ]
    for name, fn, colour in curves:
        pts = []
        for i in range(81):
            t = i / 80
            v = min(fn(t), 1.06)
            pts.append(f"{ox + t * w:.1f},{oy - v * (h - 20):.1f}")
            if v >= 1.06:
                break
        b.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{colour}" '
                 f'stroke-width="2"/>')
        lx, ly = pts[-1].split(",")
        b.append(label(float(lx) + 6, float(ly) + 4, name, color=colour, size=12,
                       anchor="start", font=MONO, weight="600"))
    return svg(700, 286, "".join(b),
               "Where a curve crosses the dashed line is the largest <em>n</em> that "
               "algorithm can handle. Only the shape matters: n² is comfortable at "
               "n = 10⁴ and hopeless at n = 10⁶. Read n off the constraints, then read "
               "the curve.")


def two_heaps() -> str:
    b = [ARROWHEADS]
    lo_vals, hi_vals = [7, 5, 2], [9, 12, 15]
    b.append(f'<rect x="40" y="46" width="270" height="150" rx="8" fill="var(--code)" '
             f'stroke="var(--line)"/>')
    b.append(label(175, 70, "lo — max-heap, smaller half", color="var(--muted)",
                   size=12, weight="600"))
    for i, v in enumerate(lo_vals):
        x = 175 if i == 0 else 105 + (i - 1) * 140
        y = 100 if i == 0 else 154
        colour = "var(--accent)" if i == 0 else "var(--line)"
        b.append(f'<circle cx="{x}" cy="{y}" r="21" fill="var(--panel)" '
                 f'stroke="{colour}" stroke-width="{2.5 if not i else 1.5}"/>')
        b.append(label(x, y + 5, str(v), color="var(--ink)", size=13, font=MONO))
        if i:
            b.append(line(x, y - 21, 175, 121, "var(--line)", 1.2))

    b.append(f'<rect x="390" y="46" width="270" height="150" rx="8" fill="var(--code)" '
             f'stroke="var(--line)"/>')
    b.append(label(525, 70, "hi — min-heap, larger half", color="var(--muted)",
                   size=12, weight="600"))
    for i, v in enumerate(hi_vals):
        x = 525 if i == 0 else 455 + (i - 1) * 140
        y = 100 if i == 0 else 154
        colour = "var(--accent)" if i == 0 else "var(--line)"
        b.append(f'<circle cx="{x}" cy="{y}" r="21" fill="var(--panel)" '
                 f'stroke="{colour}" stroke-width="{2.5 if not i else 1.5}"/>')
        b.append(label(x, y + 5, str(v), color="var(--ink)", size=13, font=MONO))
        if i:
            b.append(line(x, y - 21, 525, 121, "var(--line)", 1.2))

    b.append(f'<path d="M 200 100 Q 350 30 500 100" fill="none" stroke="var(--accent)" '
             f'stroke-width="1.6" stroke-dasharray="4 3" marker-end="url(#ah-a)"/>')
    b.append(label(350, 30, "the median lives at these two roots",
                   color="var(--accent)", size=12, weight="600"))
    b.append(label(350, 224, "lo.size() == hi.size(), or exactly one more — "
                   "restored on every add()", color="var(--muted)", size=12))
    b.append(label(350, 248, "findMedian() reads two roots. O(1). No copying, no draining.",
                   color="var(--good)", size=12, font=MONO))
    return svg(700, 266, "".join(b),
               "Your find-median-from-data-stream rewrite drained a heap per query. "
               "The invariant makes that unnecessary.")


# ==========================================================================
# comparators
# ==========================================================================

def treeset_collapse() -> str:
    b = [ARROWHEADS]
    b.append(label(380, 26, 'comparing intervals by start only: (a, b) -> a[0] - b[0]',
                   color="var(--ink)", size=13, font=MONO, weight="600"))
    items = [("[1, 4]", "var(--good)"), ("[1, 9]", "var(--bad)"), ("[3, 5]", "var(--good)")]
    for i, (t, c) in enumerate(items):
        b.append(box(70 + i * 130, 58, 104, 34, t, fill="var(--code)", color=c))
    b.append(label(220, 116, "add() all three", color="var(--muted)", size=12))
    b.append(arrow(380, 74, 448, 74, "var(--ink)"))

    b.append(f'<rect x="470" y="46" width="240" height="118" rx="8" fill="var(--panel)" '
             f'stroke="var(--line)"/>')
    b.append(label(590, 70, "TreeSet contents", color="var(--muted)", size=12,
                   weight="600"))
    b.append(box(510, 84, 160, 30, "[1, 4]", fill="var(--code)", color="var(--good)"))
    b.append(box(510, 122, 160, 30, "[3, 5]", fill="var(--code)", color="var(--good)"))
    b.append(label(590, 182, "[1, 9] was silently dropped", color="var(--bad)", size=12,
                   weight="700"))
    b.append(label(590, 202, "compare(...) == 0 means SAME ELEMENT",
                   color="var(--bad)", size=11, font=MONO))
    b.append(label(220, 150, "equals() is never called.", color="var(--bad)", size=12))
    b.append(label(220, 172, "add() returns false and", color="var(--bad)", size=12))
    b.append(label(220, 192, "throws nothing.", color="var(--bad)", size=12))
    b.append(label(380, 236,
                   "Fix: make the comparator total — tie-break on every field that "
                   "distinguishes two elements.",
                   color="var(--good)", size=12))
    b.append(label(380, 258, "(a, b) -> a[0] != b[0] ? a[0] - b[0] : a[1] - b[1]",
                   color="var(--good)", size=12, font=MONO))
    return svg(760, 276, "".join(b),
               "A sorted collection has no separate notion of equality. Ordering IS "
               "identity.")


def comparator_overflow() -> str:
    b = [ARROWHEADS]
    b.append(label(380, 28, "(a, b) -> a - b     with a = 2,000,000,000, b = -2,000,000,000",
                   color="var(--ink)", size=13, font=MONO, weight="600"))
    b.append(box(60, 58, 200, 36, "true order: a > b", fill="var(--code)",
                 stroke="var(--good)", color="var(--good)"))
    b.append(arrow(268, 76, 320, 76, "var(--ink)"))
    b.append(box(330, 58, 250, 36, "a - b = 4,000,000,000", fill="var(--code)", size=12))
    b.append(arrow(588, 76, 630, 76, "var(--bad)", "ah-b"))
    b.append(box(640, 58, 108, 36, "wraps", fill="var(--panel)", stroke="var(--bad)",
                 color="var(--bad)"))
    b.append(label(380, 124, "= -294,967,296   →  negative  →  \"a comes BEFORE b\"",
                   color="var(--bad)", size=13, font=MONO, weight="700"))
    b.append(f'<rect x="60" y="146" width="688" height="60" rx="6" fill="var(--code)" '
             f'stroke="var(--bad)"/>')
    b.append(label(76, 170, "The comparator now contradicts itself. Java's TimSort "
                   "detects this and throws:", color="var(--bad)", size=12,
                   anchor="start"))
    b.append(label(76, 192, 'IllegalArgumentException: Comparison method violates its '
                   'general contract!', color="var(--bad)", size=11, anchor="start",
                   font=MONO))
    b.append(label(380, 234, "Integer.compare(a, b)   —  branches instead of subtracting. "
                   "Always correct, same length.",
                   color="var(--good)", size=12, font=MONO))
    return svg(800, 252, "".join(b),
               "Subtraction in a comparator is a latent overflow with a loud, "
               "confusing failure mode.")



# ==========================================================================
# dynamic-programming
# ==========================================================================

def dp_grid_dependency() -> str:
    b = [ARROWHEADS]
    cell, ox, oy = 62, 150, 60
    cols, rows = 6, 4
    for r in range(rows):
        for c in range(cols):
            filled = r < 2 or (r == 2 and c < 3)
            b.append(box(ox + c * cell, oy + r * cell, cell - 6, cell - 6, "",
                         fill="var(--code)" if filled else "var(--panel)"))
    tr, tc = 2, 3
    tx, ty = ox + tc * cell, oy + tr * cell
    b.append(box(tx, ty, cell - 6, cell - 6, "?", fill="var(--panel)",
                 stroke="var(--accent)", color="var(--accent)", weight="700"))
    for dr, dc, colour in ((-1, -1, "var(--good)"), (-1, 0, "var(--good)"),
                           (0, -1, "var(--good)")):
        sx, sy = ox + (tc + dc) * cell + (cell - 6) / 2, oy + (tr + dr) * cell + (cell - 6) / 2
        b.append(arrow(sx, sy, tx + (cell - 6) / 2 - dc * 22, ty + (cell - 6) / 2 - dr * 22,
                       colour, "ah-g", 1.8))
    b.append(label(ox - 16, oy + 26, "i-1", color="var(--muted)", size=11, anchor="end",
                   font=MONO))
    b.append(label(88, oy + 2 * cell + 26, "i", color="var(--accent)", size=11,
                   anchor="end", font=MONO, weight="700"))
    b.append(label(ox + 2 * cell + 28, oy - 14, "j-1", color="var(--muted)", size=11,
                   font=MONO))
    b.append(label(ox + 3 * cell + 28, oy - 14, "j", color="var(--accent)", size=11,
                   font=MONO, weight="700"))
    b.append(label(560, 96, "dp[i][j] depends only on", color="var(--ink)", size=12,
                   anchor="start", weight="600"))
    b.append(label(560, 118, "dp[i-1][j-1], dp[i-1][j], dp[i][j-1]",
                   color="var(--good)", size=11, anchor="start", font=MONO))
    b.append(label(560, 148, "so rows ascending, columns", color="var(--muted)",
                   size=12, anchor="start"))
    b.append(label(560, 168, "ascending is a legal fill order.", color="var(--muted)",
                   size=12, anchor="start"))
    b.append(label(560, 198, "And only row i-1 is ever read,", color="var(--accent)",
                   size=12, anchor="start"))
    b.append(label(560, 218, "so two rows suffice: O(n) space.", color="var(--accent)",
                   size=12, anchor="start"))
    b.append(label(150, 322, "shaded = already computed", color="var(--muted)", size=11,
                   anchor="start"))
    return svg(880, 340, "".join(b),
               "Two-sequence DP (LCS, edit distance, wildcard matching). The "
               "<em>dependency direction</em> is what dictates the loop order — derive "
               "it, never guess it.")


def knapsack_loop_direction() -> str:
    b = [ARROWHEADS]
    cell, ox = 66, 190
    caps = [0, 1, 2, 3, 4, 5, 6]

    def strip(y, title, arrow_dir, note, colour):
        out = [label(24, y + 22, title, color="var(--ink)", size=12, anchor="start",
                     weight="600")]
        for i, c in enumerate(caps):
            out.append(box(ox + i * cell, y, cell - 8, 34, str(c), fill="var(--code)",
                           size=12))
        x1 = ox + 4 if arrow_dir > 0 else ox + len(caps) * cell - 12
        x2 = ox + len(caps) * cell - 12 if arrow_dir > 0 else ox + 4
        out.append(arrow(x1, y + 52, x2, y + 52, colour,
                         "ah-g" if colour == "var(--good)" else "ah-a", 2))
        out.append(label(24, y + 44, note, color=colour, size=11, anchor="start"))
        return "".join(out)

    b.append(label(400, 26, "same table, same recurrence — only the inner loop direction "
                   "differs", color="var(--muted)", size=12))
    b.append(strip(46, "0/1 knapsack", -1,
                   "descending: dp[w-wt] is still the PREVIOUS item's row",
                   "var(--good)"))
    b.append(strip(148, "unbounded knapsack", +1,
                   "ascending: dp[w-wt] is already THIS item's row — reuse is intended",
                   "var(--accent)"))
    b.append(f'<rect x="24" y="228" width="800" height="66" rx="6" fill="var(--code)" '
             f'stroke="var(--line)"/>')
    b.append(label(40, 252, "for (int w = cap; w >= wt; w--)   dp[w] = max(dp[w], dp[w-wt] + val);   "
                   "// each item once", color="var(--good)", size=11, anchor="start",
                   font=MONO))
    b.append(label(40, 278, "for (int w = wt; w <= cap; w++)   dp[w] = max(dp[w], dp[w-wt] + val);   "
                   "// unlimited copies", color="var(--accent)", size=11, anchor="start",
                   font=MONO))
    return svg(848, 312, "".join(b),
               "The single most useful fact in knapsack DP: one loop direction gives "
               "you 0/1, the other gives you unbounded. Nothing else changes.")


def coin_change_nesting() -> str:
    b = []
    b.append(f'<rect x="20" y="30" width="390" height="230" rx="8" fill="var(--code)" '
             f'stroke="var(--good)"/>')
    b.append(label(215, 56, "coins OUTSIDE  →  combinations", color="var(--good)",
                   size=13, weight="700"))
    b.append(label(40, 84, "for (int c : coins)", color="var(--good)", size=12,
                   anchor="start", font=MONO))
    b.append(label(58, 104, "for (int a = c; a <= amt; a++)", color="var(--good)",
                   size=12, anchor="start", font=MONO))
    b.append(label(76, 124, "dp[a] += dp[a - c];", color="var(--good)", size=12,
                   anchor="start", font=MONO))
    b.append(label(215, 158, "amount 3, coins {1, 2}", color="var(--muted)", size=12))
    b.append(label(215, 182, "1+1+1     1+2", color="var(--ink)", size=13, font=MONO))
    b.append(label(215, 212, "answer: 2", color="var(--good)", size=13, font=MONO,
                   weight="700"))
    b.append(label(215, 240, "coin-change-ii asks for this", color="var(--muted)",
                   size=11))

    b.append(f'<rect x="430" y="30" width="390" height="230" rx="8" fill="var(--code)" '
             f'stroke="var(--accent)"/>')
    b.append(label(625, 56, "amount OUTSIDE  →  permutations", color="var(--accent)",
                   size=13, weight="700"))
    b.append(label(450, 84, "for (int a = 1; a <= amt; a++)", color="var(--accent)",
                   size=12, anchor="start", font=MONO))
    b.append(label(468, 104, "for (int c : coins) if (c <= a)", color="var(--accent)",
                   size=12, anchor="start", font=MONO))
    b.append(label(486, 124, "dp[a] += dp[a - c];", color="var(--accent)", size=12,
                   anchor="start", font=MONO))
    b.append(label(625, 158, "amount 3, coins {1, 2}", color="var(--muted)", size=12))
    b.append(label(625, 182, "1+1+1   1+2   2+1", color="var(--ink)", size=13, font=MONO))
    b.append(label(625, 212, "answer: 3", color="var(--accent)", size=13, font=MONO,
                   weight="700"))
    b.append(label(625, 240, "combination-sum-iv asks for this", color="var(--muted)",
                   size=11))
    return svg(840, 278, "".join(b),
               "Identical bodies, opposite answers. Which loop is outside decides "
               "whether order counts — read the problem statement for the word "
               "\"combination\" and check it means what you think.")


def dp_state_machine() -> str:
    b = [ARROWHEADS]
    nodes = {"HOLD": (200, 96), "FREE": (560, 96), "COOL": (380, 220)}
    for n, (x, y) in nodes.items():
        colour = "var(--accent)" if n == "HOLD" else "var(--line)"
        b.append(f'<rect x="{x - 56}" y="{y - 24}" width="112" height="48" rx="24" '
                 f'fill="var(--panel)" stroke="{colour}" stroke-width="2"/>')
        b.append(label(x, y + 5, n, color="var(--ink)", size=13, font=MONO, weight="600"))
    b.append(curve(256, 84, 504, 84, 34, "var(--good)", "ah-g"))
    b.append(label(380, 44, "sell:  free = hold + price", color="var(--good)", size=11,
                   font=MONO))
    b.append(node_arrow(520, 118, 240, 118, 56, "var(--accent)", "ah-a"))
    b.append(label(380, 140, "buy:  hold = free − price", color="var(--accent)", size=11,
                   font=MONO))
    b.append(f'<path d="M 152 76 A 34 34 0 1 0 152 116" fill="none" stroke="var(--muted)" '
             f'stroke-width="1.6" marker-end="url(#ah)"/>')
    b.append(label(74, 96, "hold", color="var(--muted)", size=11, font=MONO))
    b.append(f'<path d="M 608 76 A 34 34 0 1 1 608 116" fill="none" stroke="var(--muted)" '
             f'stroke-width="1.6" marker-end="url(#ah)"/>')
    b.append(label(690, 96, "wait", color="var(--muted)", size=11, font=MONO))
    b.append(label(380, 268, "add a COOL state and the same code solves the "
                   "with-cooldown variant", color="var(--muted)", size=12))
    b.append(label(380, 290, "add a transaction counter and it solves best-time-iii "
                   "and -iv", color="var(--muted)", size=12))
    return svg(760, 308, "".join(b),
               "State-machine DP: name the states, name the transitions, and the "
               "recurrence writes itself. Every best-time-to-buy-and-sell-stock "
               "variant is this diagram with states added.")


def interval_dp_order() -> str:
    b = [ARROWHEADS]
    n, cell, ox, oy = 6, 50, 200, 56
    for i in range(n):
        b.append(label(ox + i * cell + 22, oy - 12, str(i), color="var(--muted)",
                       size=10, font=MONO))
        b.append(label(ox - 14, oy + i * cell + 28, str(i), color="var(--muted)",
                       size=10, anchor="end", font=MONO))
    for i in range(n):
        for j in range(n):
            if j < i:
                continue
            length = j - i
            shade = ("var(--code)" if length < 2 else
                     "var(--panel)")
            stroke = "var(--accent)" if length == 2 else "var(--line)"
            b.append(box(ox + j * cell, oy + i * cell, cell - 5, cell - 5,
                         str(length + 1), fill=shade, stroke=stroke,
                         color="var(--accent)" if length == 2 else "var(--muted)",
                         size=11))
    b.append(label(ox + n * cell + 24, oy + 40, "length 1, 2 — the base cases",
                   color="var(--muted)", size=11, anchor="start"))
    b.append(label(ox + n * cell + 24, oy + 74, "length 3 — computed next, and it",
                   color="var(--accent)", size=11, anchor="start"))
    b.append(label(ox + n * cell + 24, oy + 92, "reads only shorter intervals",
                   color="var(--accent)", size=11, anchor="start"))
    b.append(label(ox + n * cell + 24, oy + 126, "cell [i][j] = the answer for the",
                   color="var(--muted)", size=11, anchor="start"))
    b.append(label(ox + n * cell + 24, oy + 144, "subarray a[i..j]; the number shown",
                   color="var(--muted)", size=11, anchor="start"))
    b.append(label(ox + n * cell + 24, oy + 162, "is its length", color="var(--muted)",
                   size=11, anchor="start"))
    b.append(label(320, 386, "for (int len = 2; len <= n; len++)", color="var(--good)",
                   size=12, font=MONO))
    b.append(label(320, 406, "for (int i = 0; i + len <= n; i++) { int j = i + len - 1; ... }",
                   color="var(--good)", size=12, font=MONO))
    return svg(800, 424, "".join(b),
               "Interval DP fills by increasing length, not by row — a longer interval "
               "always depends on shorter ones. Loop over <code>len</code>, derive "
               "<code>j</code>. This is burst-balloons and matrix-chain.")


def lis_patience() -> str:
    b = [ARROWHEADS]
    seq = [10, 9, 2, 5, 3, 7, 101, 18]
    tails = ["[10]", "[9]", "[2]", "[2,5]", "[2,3]", "[2,3,7]", "[2,3,7,101]",
             "[2,3,7,18]"]
    acts = ["append", "replace 10", "replace 9", "append", "replace 5", "append",
            "append", "replace 101"]
    b.append(label(60, 34, "x", color="var(--muted)", size=11, anchor="start", font=MONO))
    b.append(label(150, 34, "action", color="var(--muted)", size=11, anchor="start"))
    b.append(label(330, 34, "tails[] — smallest possible tail of an increasing run of "
                   "each length", color="var(--muted)", size=11, anchor="start"))
    for i, (x, t, a) in enumerate(zip(seq, tails, acts)):
        y = 58 + i * 30
        grow = a == "append"
        b.append(label(60, y + 14, str(x), color="var(--ink)", size=12, anchor="start",
                       font=MONO))
        b.append(label(150, y + 14, a,
                       color="var(--good)" if grow else "var(--accent)", size=11,
                       anchor="start"))
        b.append(label(330, y + 14, t, color="var(--ink)", size=12, anchor="start",
                       font=MONO))
    b.append(f'<rect x="40" y="300" width="720" height="60" rx="6" fill="var(--code)" '
             f'stroke="var(--line)"/>')
    b.append(label(56, 324, "answer = tails.length = 4.  tails is NOT the LIS — "
                   "[2,3,7,18] happens to be one here, but in general it is not.",
                   color="var(--muted)", size=11, anchor="start"))
    b.append(label(56, 346, "Each x does one binary search: O(n log n) instead of the "
                   "O(n²) pairwise DP.", color="var(--good)", size=11, anchor="start"))
    return svg(800, 376, "".join(b),
               "Longest increasing subsequence by patience sorting. The array being "
               "binary searched is <em>tails</em>, which is always sorted — that is the "
               "whole reason this works.")



# ==========================================================================
# heaps
# ==========================================================================

def heap_layout() -> str:
    b = [ARROWHEADS]
    vals = [2, 5, 3, 9, 7, 4, 8]
    pos = {0: (400, 60), 1: (250, 140), 2: (550, 140),
           3: (180, 220), 4: (320, 220), 5: (480, 220), 6: (620, 220)}
    for i in range(1, 7):
        p = (i - 1) // 2
        b.append(line(pos[i][0], pos[i][1] - 20, pos[p][0], pos[p][1] + 20,
                      "var(--line)", 1.3))
    for i, (x, y) in pos.items():
        b.append(f'<circle cx="{x}" cy="{y}" r="20" fill="var(--panel)" '
                 f'stroke="{"var(--accent)" if i == 0 else "var(--line)"}" '
                 f'stroke-width="{2.5 if i == 0 else 1.5}"/>')
        b.append(label(x, y + 5, str(vals[i]), color="var(--ink)", size=13, font=MONO))
        b.append(label(x, y + 36, f"[{i}]", color="var(--muted)", size=10, font=MONO))
    b.append(label(400, 30, "heap property: every parent ≤ both children",
                   color="var(--muted)", size=12))

    cell, ox, oy = 76, 130, 280
    for i, v in enumerate(vals):
        b.append(box(ox + i * cell, oy, cell - 8, 32, str(v),
                     fill="var(--code)",
                     stroke="var(--accent)" if i == 0 else "var(--line)"))
        b.append(label(ox + i * cell + 34, oy + 48, str(i), color="var(--muted)",
                       size=10, font=MONO))
    b.append(label(ox - 16, oy + 21, "array", color="var(--muted)", size=11,
                   anchor="end", font=MONO))
    b.append(label(400, 358, "left = 2i+1     right = 2i+2     parent = (i-1)/2",
                   color="var(--good)", size=13, font=MONO, weight="600"))
    return svg(800, 378, "".join(b),
               "A binary heap is a complete tree stored as a flat array — no nodes, no "
               "pointers. It is <em>partially</em> ordered: the root is the minimum, and "
               "nothing else is in any particular order.")


def heap_top_k() -> str:
    b = [ARROWHEADS]
    b.append(label(400, 28, "k = 3 largest of  [5, 1, 9, 3, 7, 2, 8]",
                   color="var(--ink)", size=13, font=MONO, weight="600"))
    b.append(f'<rect x="40" y="52" width="330" height="150" rx="8" fill="var(--code)" '
             f'stroke="var(--bad)"/>')
    b.append(label(205, 76, "sort everything", color="var(--bad)", size=12, weight="700"))
    b.append(label(205, 104, "O(n log n) time", color="var(--bad)", size=12, font=MONO))
    b.append(label(205, 128, "O(n) extra space", color="var(--bad)", size=12, font=MONO))
    b.append(label(205, 160, "and it computes a full ordering", color="var(--muted)",
                   size=11))
    b.append(label(205, 180, "you then throw away", color="var(--muted)", size=11))

    b.append(f'<rect x="430" y="52" width="330" height="150" rx="8" fill="var(--code)" '
             f'stroke="var(--good)"/>')
    b.append(label(595, 76, "MIN-heap capped at k", color="var(--good)", size=12,
                   weight="700"))
    b.append(label(595, 104, "O(n log k) time", color="var(--good)", size=12, font=MONO))
    b.append(label(595, 128, "O(k) extra space", color="var(--good)", size=12, font=MONO))
    b.append(label(595, 160, "the root is the SMALLEST of the", color="var(--muted)",
                   size=11))
    b.append(label(595, 180, "k best — so it is what to evict", color="var(--muted)",
                   size=11))

    b.append(f'<rect x="40" y="222" width="720" height="60" rx="6" fill="var(--panel)" '
             f'stroke="var(--line)"/>')
    b.append(label(56, 246, "pq.offer(x);", color="var(--good)", size=12, anchor="start",
                   font=MONO))
    b.append(label(56, 268, "if (pq.size() > k) pq.poll();   // evict the weakest",
                   color="var(--good)", size=12, anchor="start", font=MONO))
    b.append(label(400, 304, "k largest → MIN-heap.   k smallest → MAX-heap.   "
                   "The direction is always the surprising one.",
                   color="var(--accent)", size=12, weight="600"))
    return svg(800, 322, "".join(b),
               "The heap holds the answer set and its root is the candidate to drop. "
               "Getting the direction backwards keeps the wrong k and passes small "
               "tests.")


# ==========================================================================
# monotonic-stack
# ==========================================================================

def monotonic_stack_trace() -> str:
    b = [ARROWHEADS]
    arr = [2, 1, 2, 4, 3]
    cell, ox = 66, 250
    steps = [
        (0, "push 0", "[0]", "—"),
        (1, "2 > 1, pop nothing; push", "[0,1]", "—"),
        (2, "1 < 2 → pop 1, ans[1]=2; push", "[0,2]", "ans[1] = 2"),
        (3, "2 < 4 → pop 2, ans[2]=4;", "[0,3]", "ans[2] = 4"),
        (4, "  2 < 4 → pop 0, ans[0]=4; push", "[3]", "ans[0] = 4"),
    ]
    for i, v in enumerate(arr):
        b.append(box(ox + i * cell, 26, cell - 8, 30, str(v), fill="var(--code)", size=12))
        b.append(label(ox + i * cell + 29, 72, str(i), color="var(--muted)", size=10,
                       font=MONO))
    b.append(label(ox - 16, 47, "nums", color="var(--muted)", size=11, anchor="end",
                   font=MONO))
    b.append(label(40, 100, "i", color="var(--muted)", size=11, anchor="start", font=MONO))
    b.append(label(80, 100, "what happens", color="var(--muted)", size=11, anchor="start"))
    b.append(label(430, 100, "stack (indices)", color="var(--muted)", size=11,
                   anchor="start"))
    b.append(label(600, 100, "recorded", color="var(--muted)", size=11, anchor="start"))
    for k, (i, what, stack, rec) in enumerate(steps):
        y = 124 + k * 28
        b.append(label(40, y, str(i), color="var(--ink)", size=11, anchor="start",
                       font=MONO))
        b.append(label(80, y, what, color="var(--ink)", size=11, anchor="start"))
        b.append(label(430, y, stack, color="var(--accent)", size=11, anchor="start",
                       font=MONO))
        b.append(label(600, y, rec, color="var(--good)" if rec != "—" else "var(--muted)",
                       size=11, anchor="start", font=MONO))
    b.append(f'<rect x="40" y="278" width="700" height="60" rx="6" fill="var(--code)" '
             f'stroke="var(--line)"/>')
    b.append(label(56, 302, "The stack holds indices whose answer is still UNKNOWN, "
                   "kept in decreasing value order.", color="var(--muted)", size=11,
                   anchor="start"))
    b.append(label(56, 324, "An element is popped exactly when its answer arrives — so "
                   "each index is pushed once and popped once: O(n).",
                   color="var(--good)", size=11, anchor="start"))
    return svg(780, 356, "".join(b),
               "next-greater-element, traced. Anything left on the stack at the end has "
               "no answer — that is where the sentinel from lesson 3 goes.")


# ==========================================================================
# strings
# ==========================================================================

def palindrome_expand() -> str:
    b = [ARROWHEADS]
    s = "a b a b d"
    chars = s.split()
    cell, ox, oy = 64, 220, 70
    for i, c in enumerate(chars):
        b.append(box(ox + i * cell, oy, cell - 8, 34, c, fill="var(--code)", size=13))
        b.append(label(ox + i * cell + 28, oy + 54, str(i), color="var(--muted)",
                       size=10, font=MONO))

    b.append(label(150, oy + 22, "odd centre", color="var(--good)", size=12,
                   anchor="end", weight="600"))
    cx = ox + 2 * cell + 28
    b.append(f'<circle cx="{cx}" cy="{oy + 17}" r="5" fill="var(--good)"/>')
    b.append(curve(cx - 8, oy - 6, cx - 64, oy - 6, 22, "var(--good)", "ah-g"))
    b.append(curve(cx + 8, oy - 6, cx + 64, oy - 6, 22, "var(--good)", "ah-g"))
    b.append(label(cx, oy - 34, "expand outward while s[l] == s[r]", color="var(--good)",
                   size=11))

    b.append(label(150, oy + 130, "even centre", color="var(--accent)", size=12,
                   anchor="end", weight="600"))
    ex = ox + 2 * cell
    b.append(f'<circle cx="{ex}" cy="{oy + 125}" r="5" fill="var(--accent)"/>')
    b.append(curve(ex - 8, oy + 140, ex - 60, oy + 140, -20, "var(--accent)", "ah-a"))
    b.append(curve(ex + 8, oy + 140, ex + 60, oy + 140, -20, "var(--accent)", "ah-a"))
    b.append(label(ex, oy + 176, "the gap between two cells is a centre too",
                   color="var(--accent)", size=11))
    b.append(f'<rect x="40" y="290" width="700" height="82" rx="6" fill="var(--code)" '
             f'stroke="var(--line)"/>')
    b.append(label(56, 314, "for (int i = 0; i < n; i++) {", color="var(--good)",
                   size=12, anchor="start", font=MONO))
    b.append(label(72, 334, "expand(i, i);      // 2n-1 centres, not n --",
                   color="var(--good)", size=12, anchor="start", font=MONO))
    b.append(label(72, 354, "expand(i, i + 1);  // forgetting the even ones is THE bug",
                   color="var(--good)", size=12, anchor="start", font=MONO))
    return svg(780, 390, "".join(b),
               "Expand around centre: O(n²) time, O(1) space, and no DP table. A string "
               "of length n has 2n−1 possible centres.")


# ==========================================================================
# intervals
# ==========================================================================

def interval_sweep() -> str:
    b = [ARROWHEADS]
    ivs = [(1, 4), (2, 6), (8, 10), (9, 12), (15, 18)]
    unit, ox, oy = 38, 90, 66
    b.append(line(ox, oy - 18, ox + 19 * unit, oy - 18, "var(--muted)", 1.2))
    for t in range(0, 19, 2):
        b.append(line(ox + t * unit, oy - 22, ox + t * unit, oy - 14, "var(--muted)", 1))
        b.append(label(ox + t * unit, oy - 28, str(t), color="var(--muted)", size=10,
                       font=MONO))
    for k, (a, c) in enumerate(ivs):
        y = oy + k * 30
        b.append(f'<rect x="{ox + a * unit}" y="{y}" width="{(c - a) * unit}" '
                 f'height="20" rx="4" fill="var(--panel)" stroke="var(--line)"/>')
        b.append(label(ox + (a + c) / 2 * unit, y + 14, f"[{a},{c}]", color="var(--ink)",
                       size=11, font=MONO))
    merged = [(1, 6), (8, 12), (15, 18)]
    y = oy + 5 * 30 + 14
    for a, c in merged:
        b.append(f'<rect x="{ox + a * unit}" y="{y}" width="{(c - a) * unit}" '
                 f'height="24" rx="4" fill="var(--code)" stroke="var(--good)" '
                 f'stroke-width="2"/>')
        b.append(label(ox + (a + c) / 2 * unit, y + 16, f"[{a},{c}]",
                       color="var(--good)", size=11, font=MONO))
    b.append(label(ox - 16, y + 16, "merged", color="var(--good)", size=11, anchor="end",
                   font=MONO))
    b.append(f'<rect x="40" y="250" width="760" height="82" rx="6" fill="var(--code)" '
             f'stroke="var(--line)"/>')
    b.append(label(56, 274, "sort by START, then sweep once:", color="var(--muted)",
                   size=11, anchor="start"))
    b.append(label(56, 296, "if (cur[1] >= next[0]) cur[1] = max(cur[1], next[1]);  "
                   "// overlap -- EXTEND, do not overwrite", color="var(--good)",
                   size=11, anchor="start", font=MONO))
    b.append(label(56, 318, "else { out.add(cur); cur = next; }                     "
                   "// disjoint -- emit and move on", color="var(--good)", size=11,
                   anchor="start", font=MONO))
    return svg(820, 350, "".join(b),
               "<code>max(cur[1], next[1])</code> is the line people get wrong: an "
               "interval can be entirely swallowed by the one before it, and plain "
               "assignment would shrink the merge.")


# ==========================================================================
# linked-list
# ==========================================================================

def floyd_cycle() -> str:
    b = [ARROWHEADS]
    tail = [(90, 130), (180, 130), (270, 130)]
    ring = [(390, 80), (480, 60), (550, 130), (480, 200), (390, 180)]
    for i in range(len(tail) - 1):
        b.append(node_arrow(*tail[i], *tail[i + 1], 18))
    b.append(node_arrow(*tail[-1], *ring[0], 18))
    for i in range(len(ring)):
        b.append(node_arrow(*ring[i], *ring[(i + 1) % len(ring)], 18, "var(--accent)",
                            "ah-a"))
    for x, y in tail:
        b.append(f'<circle cx="{x}" cy="{y}" r="18" fill="var(--panel)" '
                 f'stroke="var(--line)" stroke-width="1.5"/>')
    for i, (x, y) in enumerate(ring):
        stroke = "var(--good)" if i == 0 else "var(--accent)"
        b.append(f'<circle cx="{x}" cy="{y}" r="18" fill="var(--panel)" '
                 f'stroke="{stroke}" stroke-width="{2.5 if i == 0 else 1.5}"/>')
    b.append(label(90, 100, "head", color="var(--muted)", size=11, font=MONO))
    b.append(label(390, 52, "cycle entry", color="var(--good)", size=11, weight="600"))
    b.append(f'<rect x="600" y="52" width="238" height="76" rx="6" fill="var(--code)" '
             f'stroke="var(--line)"/>')
    b.append(label(616, 76, "slow = slow.next;", color="var(--ink)", size=12,
                   anchor="start", font=MONO))
    b.append(label(616, 98, "fast = fast.next.next;", color="var(--ink)", size=12,
                   anchor="start", font=MONO))
    b.append(label(616, 120, "they meet ⇒ a cycle exists", color="var(--muted)",
                   size=11, anchor="start"))
    b.append(f'<rect x="600" y="142" width="238" height="76" rx="6" fill="var(--code)" '
             f'stroke="var(--good)"/>')
    b.append(label(616, 166, "then reset slow = head,", color="var(--good)", size=11,
                   anchor="start"))
    b.append(label(616, 186, "advance both ONE step at a", color="var(--good)", size=11,
                   anchor="start"))
    b.append(label(616, 206, "time — they meet at the entry", color="var(--good)",
                   size=11, anchor="start"))
    return svg(860, 240, "".join(b),
               "Floyd's cycle detection. <code>fast.next.next</code> needs BOTH "
               "<code>fast</code> and <code>fast.next</code> non-null — checking only "
               "<code>fast</code> is the classic NullPointerException here. The second "
               "phase is not a trick to memorise blindly: the distance from head to the "
               "entry equals the distance from the meeting point to the entry, going "
               "forward.")



# ==========================================================================
# number-theory
# ==========================================================================

def sieve() -> str:
    b = []
    cell, ox, oy, per = 46, 60, 76, 15
    marks = {}
    for p in (2, 3, 5):
        for m in range(p * p, 31, p):
            marks.setdefault(m, p)
    colours = {2: "var(--bad)", 3: "var(--accent)", 5: "var(--warn)"}
    for n in range(2, 32):
        k = n - 2
        x, y = ox + (k % per) * cell, oy + (k // per) * (cell + 26)
        prime = n not in marks
        stroke = "var(--good)" if prime else colours.get(marks[n], "var(--line)")
        b.append(box(x, y, cell - 6, 32, str(n), fill="var(--code)", stroke=stroke,
                     color="var(--good)" if prime else "var(--muted)", size=12,
                     weight="700" if prime else "400"))
        if not prime:
            b.append(label(x + 20, y + 46, f"×{marks[n]}", color=colours[marks[n]],
                           size=10, font=MONO))
    b.append(label(ox - 14, 44, "start crossing out at p·p — everything below it was "
                   "already crossed out by a smaller prime",
                   color="var(--muted)", size=12, anchor="start"))
    b.append(f'<rect x="40" y="196" width="700" height="82" rx="6" fill="var(--code)" '
             f'stroke="var(--line)"/>')
    b.append(label(56, 220, "for (int p = 2; (long) p * p <= n; p++)", color="var(--good)",
                   size=12, anchor="start", font=MONO))
    b.append(label(72, 240, "if (isPrime[p])", color="var(--good)", size=12,
                   anchor="start", font=MONO))
    b.append(label(88, 260, "for (int m = p * p; m <= n; m += p) isPrime[m] = false;",
                   color="var(--good)", size=12, anchor="start", font=MONO))
    return svg(760, 296, "".join(b),
               "Sieve of Eratosthenes, O(n log log n). Starting the inner loop at "
               "<code>2p</code> instead of <code>p·p</code> is not wrong, only wasteful; "
               "looping <code>p</code> past <code>√n</code> is pure waste.")


# --------------------------------------------------------------------------

# ==========================================================================
# added for the section-structure pass: the lessons that were carrying only
# one figure across five or six subsections
# ==========================================================================

def answer_space() -> str:
    """Binary search on the answer: the predicate is monotone over the range."""
    b = [ARROWHEADS]
    y, x0, x1 = 96, 60, 700
    split = 400
    b.append(f'<rect x="{x0}" y="{y - 18}" width="{split - x0}" height="36" rx="4" '
             f'fill="var(--panel)" stroke="var(--bad)" stroke-width="1.5"/>')
    b.append(f'<rect x="{split}" y="{y - 18}" width="{x1 - split}" height="36" rx="4" '
             f'fill="var(--panel)" stroke="var(--good)" stroke-width="1.5"/>')
    b.append(label((x0 + split) / 2, y + 5, "P(x) = false", "var(--bad)", 14, font=MONO))
    b.append(label((split + x1) / 2, y + 5, "P(x) = true", "var(--good)", 14, font=MONO))
    b.append(label(x0, y + 42, "lo = smallest conceivable answer", "var(--muted)", 11,
                   anchor="start"))
    b.append(label(x1, y + 42, "hi = largest conceivable answer", "var(--muted)", 11,
                   anchor="end"))
    b.append(arrow(split, y + 66, split, y + 26, "var(--accent)"))
    b.append(label(split, y + 84, "the answer: the first x where P(x) holds",
                   "var(--accent)", 12))
    b.append(label(380, 42, "feasibility check P(x): can it be done with budget x?",
                   "var(--muted)", 12))
    b.append(label(380, 22, "the search runs over the ANSWER, not over the array",
                   "var(--ink)", 13, weight="600"))
    return svg(760, 210, "".join(b),
               "Binary search on the answer works whenever the feasibility check is "
               "monotone: once a budget is large enough, every larger budget is too. "
               "You never sort the input and the input need not be sorted — the "
               "ordering that matters is over the candidate answers.",
               "Monotone predicate over the answer range")


def window_negatives() -> str:
    """Why a sliding window needs non-negative values to shrink meaningfully."""
    b = [ARROWHEADS]
    vals = [4, -3, 5, -2, 6]
    w, x0, y = 92, 90, 92
    for i, v in enumerate(vals):
        x = x0 + i * w
        b.append(box(x, y, w - 10, 44, str(v), size=16,
                     color="var(--bad)" if v < 0 else "var(--ink)"))
    b.append(label(400, 60, "sum of the whole window = 10", "var(--ink)", 13, weight="600"))
    b.append(arrow(x0 + 4, y + 74, x0 + 4, y + 52, "var(--accent)"))
    b.append(label(x0 + 4, y + 92, "shrink from the left", "var(--accent)", 11))
    b.append(label(400, y + 122, "drop the 4 and the sum becomes 6 — smaller, as expected",
                   "var(--muted)", 12))
    b.append(label(400, y + 144, "drop the 4 and then the -3 and it becomes 9 — LARGER",
                   "var(--bad)", 12, weight="600"))
    return svg(760, 268, "".join(b),
               "A window is only valid when shrinking it moves the quantity in one "
               "direction. With a negative element present, removing a prefix can "
               "increase the sum, so \u201cshrink until the sum is small enough\u201d "
               "never terminates correctly. Prefix sums plus a hash map replace the "
               "window here.",
               "Why negative values break a sliding window")


def string_concat_cost() -> str:
    """s += c copies the whole string every iteration."""
    b = [ARROWHEADS]
    y = 76
    for i, n in enumerate((1, 2, 3, 4)):
        x = 70 + i * 168
        b.append(label(x + 60, y - 14, f"iteration {i + 1}", "var(--muted)", 11))
        for k in range(n):
            b.append(f'<rect x="{x + k * 22}" y="{y}" width="20" height="26" rx="3" '
                     f'fill="var(--code)" stroke="var(--line)"/>')
        b.append(f'<rect x="{x + n * 22}" y="{y}" width="20" height="26" rx="3" '
                 f'fill="var(--panel)" stroke="var(--accent)" stroke-width="1.5"/>')
        b.append(label(x + 60, y + 52, f"copies {n} char" + ("s" if n != 1 else ""),
                       "var(--bad)", 11))
    b.append(label(400, 190, "1 + 2 + 3 + ... + n  =  n(n+1)/2  =  O(n\u00b2)",
                   "var(--bad)", 15, font=MONO, weight="600"))
    b.append(label(400, 222,
                   "StringBuilder appends into a buffer it already owns: O(1) amortised",
                   "var(--good)", 12))
    b.append(label(400, 36, "s += c  inside a loop", "var(--ink)", 14, font=MONO,
                   weight="600"))
    return svg(760, 248, "".join(b),
               "A Java String is immutable, so every += allocates a new string and "
               "copies everything written so far. The grey cells are the copy; only "
               "the outlined cell is new work. This is the single most common way an "
               "O(n) loop becomes O(n\u00b2).",
               "Quadratic cost of string concatenation in a loop")


def fast_slow_pointers() -> str:
    """One pass gives the middle, the k-th from the end, and cycle detection."""
    b = [ARROWHEADS]
    y, r, x0, gap = 118, 19, 78, 84
    n = 7
    for i in range(n):
        x = x0 + i * gap
        b.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="var(--panel)" '
                 f'stroke="var(--line)" stroke-width="1.5"/>')
        b.append(label(x, y + 5, str(i + 1), "var(--ink)", 12, font=MONO))
        if i < n - 1:
            b.append(arrow(x + r, y, x + gap - r - 3, y, "var(--line)"))
    slow, fast = x0 + 3 * gap, x0 + 6 * gap
    b.append(arrow(slow, y + 62, slow, y + r + 6, "var(--accent)"))
    b.append(label(slow, y + 80, "slow: +1 per step", "var(--accent)", 11))
    b.append(arrow(fast, y - 62, fast, y - r - 6, "var(--good)"))
    b.append(label(fast, y - 72, "fast: +2 per step", "var(--good)", 11))
    b.append(label(400, 30, "after 3 steps: fast is at the end, slow is at the middle",
                   "var(--ink)", 13, weight="600"))
    return svg(760, 232, "".join(b),
               "Because fast moves twice as far, slow lands on the middle exactly when "
               "fast reaches the end. The same idea with a fixed k-gap instead of a "
               "speed difference gives the k-th node from the end, and on a cyclic "
               "list the two pointers are guaranteed to meet.",
               "Fast and slow pointers over a linked list")


def interval_sort_choice() -> str:
    """Sort by start to merge; sort by end to schedule."""
    b = [ARROWHEADS]
    ivs = [(0, 5), (1, 2), (3, 4), (4, 6)]
    unit, x0 = 52, 100
    def strip(top, order, colour, keep):
        out = [label(x0 - 24, top + 16, order, "var(--ink)", 12, anchor="end",
                     weight="600")]
        for row, idx in enumerate(keep["order"]):
            a, bb = ivs[idx]
            y = top + row * 26
            good = idx in keep["taken"]
            out.append(f'<rect x="{x0 + a * unit}" y="{y}" width="{(bb - a) * unit}" '
                       f'height="18" rx="3" fill="var(--panel)" '
                       f'stroke="{colour if good else "var(--line)"}" stroke-width="1.5"/>')
            out.append(label(x0 + a * unit + (bb - a) * unit / 2, y + 13,
                             f"[{a},{bb})", colour if good else "var(--muted)", 10,
                             font=MONO))
        return "".join(out)
    b.append(label(400, 30, "the same four intervals, two different sort keys",
                   "var(--ink)", 13, weight="600"))
    b.append(strip(56, "by start", "var(--accent)",
                   {"order": [0, 1, 2, 3], "taken": {0, 1, 2, 3}}))
    b.append(label(400, 172, "merging: sweep left to right, extend the current end",
                   "var(--muted)", 11))
    b.append(strip(200, "by end", "var(--good)",
                   {"order": [1, 2, 0, 3], "taken": {1, 2, 3}}))
    b.append(label(400, 316,
                   "scheduling: take [1,2), then [3,4), then [4,6) — three of four",
                   "var(--muted)", 11))
    return svg(760, 340, "".join(b),
               "Sorting by start makes overlaps adjacent, which is what merging needs. "
               "Sorting by end makes the greedy \u201ckeep whatever finishes soonest\u201d "
               "optimal, which is what scheduling needs — the grey interval is the one "
               "the greedy correctly rejects. Sorting by start and taking greedily "
               "would have picked [0,5) and kept only one.",
               "Sort by start to merge, by end to schedule")


def guard_order() -> str:
    """&& short-circuits left to right, so the bounds test must come first."""
    b = [ARROWHEADS]
    def lane(y, cond, first, second, ok):
        colour = "var(--good)" if ok else "var(--bad)"
        out = [label(70, y - 22, cond, "var(--ink)", 13, anchor="start", font=MONO)]
        out.append(box(70, y, 250, 40, first, stroke=colour))
        out.append(arrow(326, y + 20, 384, y + 20, colour,
                         "ah-g" if ok else "ah-b"))
        out.append(box(390, y, 250, 40, second, stroke=colour))
        out.append(label(660, y + 25, "safe" if ok else "throws", colour, 12,
                         anchor="start", weight="600"))
        return "".join(out)
    b.append(lane(64, "if (inBounds(r, c) &amp;&amp; grid[r][c] == 1)",
                  "evaluate inBounds(r, c)", "only then read grid[r][c]", True))
    b.append(lane(180, "if (grid[r][c] == 1 &amp;&amp; inBounds(r, c))",
                  "read grid[r][c] FIRST", "inBounds never runs", False))
    b.append(label(400, 272,
                   "&amp;&amp; evaluates left to right and stops early — that ordering IS the guard",
                   "var(--muted)", 12))
    return svg(760, 296, "".join(b),
               "Java's &amp;&amp; is short-circuiting, so the left operand is the only "
               "thing protecting the right one. Writing the array read first means the "
               "bounds test is dead code: the exception is thrown while the condition "
               "is still being evaluated.",
               "Short-circuit order in a bounds guard")


def euclid_steps() -> str:
    """gcd by repeated remainder, traced."""
    b = [ARROWHEADS]
    steps = [(252, 105, 42), (105, 42, 21), (42, 21, 0)]
    y0 = 76
    for i, (a, m, r) in enumerate(steps):
        y = y0 + i * 56
        b.append(label(96, y + 5, f"gcd({a}, {m})", "var(--ink)", 14, anchor="start",
                       font=MONO))
        b.append(arrow(250, y, 316, y, "var(--muted)"))
        b.append(label(283, y - 10, f"{a} % {m}", "var(--muted)", 11, font=MONO))
        nxt = f"gcd({m}, {r})"
        b.append(label(330, y + 5, nxt, "var(--ink)" if r else "var(--good)", 14,
                       anchor="start", font=MONO))
        if r == 0:
            b.append(label(500, y + 5, "\u2190 remainder 0, so the answer is 21",
                           "var(--good)", 12, anchor="start", weight="600"))
    b.append(label(400, 36, "each step replaces (a, b) with (b, a % b)", "var(--ink)",
                   13, weight="600"))
    b.append(label(400, 260,
                   "the second argument at least halves every two steps, so it is O(log n)",
                   "var(--muted)", 12))
    b.append(label(400, 288, "int gcd(int a, int b) { return b == 0 ? a : gcd(b, a % b); }",
                   "var(--accent)", 13, font=MONO))
    return svg(760, 312, "".join(b),
               "Euclid's algorithm is the whole of gcd: replace the pair with the "
               "smaller number and the remainder until the remainder is zero. The "
               "identity element is 0 — gcd(x, 0) is x — which is why folding gcd "
               "across an array starts at 0 and not at 1.",
               "Euclid's algorithm, traced on gcd(252, 105)")


def submit_loop() -> str:
    """A compile error costs an attempt and returns no information."""
    b = [ARROWHEADS]
    def lane(y, boxes, colour, head, verdict, note):
        out = []
        x = 62
        for i, t in enumerate(boxes):
            w = 148
            out.append(box(x, y, w, 42, t, stroke=colour, size=12, font=SANS))
            if i < len(boxes) - 1:
                out.append(arrow(x + w + 4, y + 21, x + w + 40, y + 21, colour, head))
            x += w + 44
        out.append(label(x + 4, y + 26, verdict, colour, 12, anchor="start",
                         weight="600"))
        out.append(label(62, y + 66, note, "var(--muted)", 11, anchor="start"))
        return "".join(out)
    b.append(label(400, 34, "the same edit, submitted two ways", "var(--ink)", 13,
                   weight="600"))
    b.append(lane(58, ["edit", "submit", "Compile Error"], "var(--bad)", "ah-b",
                  "attempt spent",
                  "you are back in the editor knowing nothing about the algorithm"))
    b.append(lane(168, ["edit", "javac", "submit"], "var(--good)", "ah-g",
                  "real verdict",
                  "whatever comes back is now information about the logic"))
    b.append(label(400, 274,
                   "242 of 5,212 submissions in this export took the top path",
                   "var(--bad)", 13, weight="600"))
    return svg(760, 298, "".join(b),
               "A Compile Error verdict is the judge acting as your compiler. It costs "
               "the same attempt as a wrong answer and tells you nothing you could not "
               "have learned locally in under a second.",
               "What a compile error actually costs")


def emit_on_transition() -> str:
    """Why a run-length scan silently drops its last group."""
    b = [ARROWHEADS]
    chars = "aaabbcc"
    x0, w = 90, 62
    for i, c in enumerate(chars):
        last = i >= 5
        b.append(box(x0 + i * w, 56, w - 6, 40, c,
                     fill="var(--code)" if last else "var(--panel)",
                     stroke="var(--bad)" if last else "var(--line)"))
        b.append(label(x0 + i * w + w / 2 - 3, 48, str(i), "var(--muted)", 11))
    # the two transitions the loop can see
    for i, out in ((3, "a3"), (5, "b2")):
        x = x0 + i * w - 3
        b.append(line(x, 50, x, 102, "var(--accent)", 2, "3 3"))
        b.append(arrow(x, 128, x, 106, "var(--accent)", "ah-a"))
        b.append(label(x, 146, f"emit {out}", "var(--accent)", 12, weight="600"))
    b.append(label(x0 + 5.9 * w, 196, "no transition here — the array ends",
                   "var(--bad)", 12, anchor="end", weight="600"))
    b.append(arrow(x0 + 6.1 * w, 190, x0 + 6.4 * w, 106, "var(--bad)", "ah-b"))
    b.append(label(400, 236,
                   "the loop emits on change, and the last group never changes",
                   "var(--ink)", 13, weight="600"))
    b.append(label(400, 260, "c2 is missing from the output unless you emit it "
                   "after the loop", "var(--muted)", 12))
    return svg(800, 284, "".join(b),
               "A scan that writes a group out when it sees the next one different "
               "is correct for every group but the last, which has no next one. The "
               "same hole swallows a leftover carry, a half-full buffer and the "
               "final interval of a merge.",
               "Emit-on-transition drops the final group")


def counting_array_zero() -> str:
    """0 in a frequency table means absent, and absent always wins a minimum."""
    b = [ARROWHEADS]
    freq = [0, 2, 0, 0, 1, 0, 3, 0, 0, 0]
    x0, w = 96, 58
    for d, n in enumerate(freq):
        present = n > 0
        b.append(box(x0 + d * w, 60, w - 6, 38, str(n),
                     fill="var(--panel)" if present else "var(--code)",
                     stroke="var(--line)",
                     color="var(--ink)" if present else "var(--muted)"))
        b.append(label(x0 + d * w + w / 2 - 3, 50, str(d), "var(--muted)", 11))
    b.append(label(72, 84, "freq", "var(--muted)", 12, anchor="end", font=MONO))
    # the naive minimum lands on digit 0
    b.append(arrow(x0 + 26, 132, x0 + 26, 104, "var(--bad)", "ah-b"))
    b.append(label(x0 + 26, 152, "min over all 10", "var(--bad)", 12, weight="600"))
    b.append(label(x0 + 26, 170, "answer: 0", "var(--bad)", 12))
    b.append(label(x0 + 26, 188, "a digit that is not there", "var(--muted)", 11))
    # the guarded minimum lands on digit 4
    b.append(arrow(x0 + 4 * w + 26, 132, x0 + 4 * w + 26, 104, "var(--good)", "ah-g"))
    b.append(label(x0 + 4 * w + 26, 152, "min over freq[d] &gt; 0",
                   "var(--good)", 12, weight="600"))
    b.append(label(x0 + 4 * w + 26, 170, "answer: 4", "var(--good)", 12))
    b.append(label(400, 224,
                   "an empty bucket and a bucket holding zero are the same value",
                   "var(--ink)", 13, weight="600"))
    return svg(800, 244, "".join(b),
               "A counting array cannot distinguish &ldquo;never appeared&rdquo; from "
               "&ldquo;appeared zero times&rdquo;, so any minimum, any argmin and any "
               "even/odd test over the whole table is decided by the buckets that "
               "hold nothing. Skip them explicitly.",
               "The zero bucket wins every minimum")


def index_spaces() -> str:
    """Two loops, two index spaces, one variable used in both."""
    b = [ARROWHEADS]
    b.append(label(60, 44, "i runs over CHARACTER POSITIONS  (0..7)",
                   "var(--accent)", 12, anchor="start", weight="600"))
    for k in range(8):
        b.append(box(60 + k * 46, 56, 40, 34, str(k), fill="var(--panel)"))
    b.append(label(60, 154, "j runs over BANK ENTRIES  (0..3)",
                   "var(--good)", 12, anchor="start", weight="600"))
    for k in range(4):
        b.append(box(60 + k * 92, 166, 86, 34, f"bank[{k}]", fill="var(--panel)",
                     size=12))
    # the crossing read
    b.append(arrow(198, 96, 198, 160, "var(--bad)", "ah-b"))
    b.append(label(214, 132, "bank[i]", "var(--bad)", 13, anchor="start",
                   font=MONO, weight="600"))
    b.append(label(292, 132, "— i is a position, not an entry",
                   "var(--muted)", 12, anchor="start"))
    b.append(label(60, 240, "It compiles. It runs. It reads a real element every "
                   "time — just never the one you meant.",
                   "var(--ink)", 13, anchor="start", weight="600"))
    b.append(label(60, 264, "Both spaces are small integers, so the type system "
                   "has nothing to say about it.",
                   "var(--muted)", 12, anchor="start"))
    return svg(760, 284, "".join(b),
               "Every index in a nested scan belongs to exactly one space. Naming "
               "both of them <code>i</code> and <code>j</code> hides which is "
               "which; naming them for what they range over makes the wrong pairing "
               "visible as you type it.",
               "One variable, two index spaces")


def guard_short_circuit() -> str:
    """Why && and || are not interchangeable in a null guard."""
    b = [ARROWHEADS]
    b.append(label(30, 30, "head == null && head.next == null",
                   "var(--bad)", 14, anchor="start", font=MONO, weight="600"))
    b.append(label(30, 52, "input: an empty list, head is null",
                   "var(--muted)", 12, anchor="start"))
    b.append(box(30, 66, 150, 34, "head == null", fill="var(--panel)"))
    b.append(label(114, 122, "true", "var(--muted)", 11, anchor="start"))
    b.append(arrow(105, 100, 105, 126, "var(--bad)", "ah-b"))
    b.append(box(30, 132, 150, 34, "&& evaluates", fill="var(--panel)", size=12))
    b.append(arrow(180, 149, 226, 149, "var(--bad)", "ah-b"))
    b.append(box(232, 132, 168, 34, "head.next", fill="var(--panel)",
                 stroke="var(--bad)"))
    b.append(label(316, 190, "crash", "var(--bad)", 13, weight="600"))
    b.append(arrow(316, 166, 316, 178, "var(--bad)", "ah-b"))

    b.append(label(430, 30, "head == null || head.next == null",
                   "var(--good)", 14, anchor="start", font=MONO, weight="600"))
    b.append(label(430, 52, "same input, same first operand",
                   "var(--muted)", 12, anchor="start"))
    b.append(box(430, 66, 150, 34, "head == null", fill="var(--panel)"))
    b.append(label(514, 122, "true", "var(--muted)", 11, anchor="start"))
    b.append(arrow(505, 100, 505, 126, "var(--good)", "ah-g"))
    b.append(box(430, 132, 150, 34, "|| short-circuits", fill="var(--panel)",
                 size=12))
    b.append(line(580, 149, 626, 149, "var(--line)", 1.5, "4 3"))
    b.append(box(632, 132, 168, 34, "head.next", fill="var(--code)",
                 stroke="var(--line)", color="var(--muted)"))
    b.append(label(716, 190, "never evaluated", "var(--good)", 13, weight="600"))

    b.append(label(30, 232, "The guard exists to stop the second operand from "
                   "running.", "var(--ink)", 13, anchor="start", weight="600"))
    b.append(label(30, 254, "&amp;&amp; makes running it the condition for the "
                   "guard to fire.", "var(--ink)", 13, anchor="start",
                   weight="600"))
    return svg(830, 272, "".join(b),
               "Both lines read as &ldquo;the list is empty or has one "
               "node&rdquo;. Only one of them is a guard: <code>||</code> stops "
               "at the first true operand, <code>&amp;&amp;</code> must reach "
               "the second to decide &mdash; which is the exact dereference the "
               "guard was written to prevent.",
               "&& versus || in a null guard")


def case_space() -> str:
    """A case analysis with a hole in it."""
    b = []
    xs = [40, 210, 380, 550]
    names = [("i == 0", "left edge"), ("0 &lt; i &lt; n-1", "interior"),
             ("i == n-1", "right edge"), ("n == 1", "both at once")]
    for k, (x, (cond, what)) in enumerate(zip(xs, names)):
        missing = k == 3
        b.append(box(x, 60, 150, 46, cond,
                     fill="var(--panel)" if not missing else "var(--code)",
                     stroke="var(--line)" if not missing else "var(--bad)",
                     color="var(--ink)" if not missing else "var(--bad)"))
        b.append(label(x + 75, 126, what,
                       "var(--muted)" if not missing else "var(--bad)", 12))
        b.append(label(x + 75, 146, "written" if not missing else "not written",
                       "var(--good)" if not missing else "var(--bad)", 12,
                       weight="600"))
    b.append(label(40, 36, "the case space, as the code partitions it",
                   "var(--muted)", 12, anchor="start"))
    b.append(label(40, 186, "Three branches cover every index a two-element array "
                   "can have.", "var(--ink)", 13, anchor="start", weight="600"))
    b.append(label(40, 208, "The bug is the input that has no index at all.",
                   "var(--ink)", 13, anchor="start", weight="600"))
    b.append(label(40, 232, "Overlapping cases are redundant. A gap is wrong, "
                   "and silent.", "var(--muted)", 12, anchor="start"))
    return svg(720, 248, "".join(b),
               "A branch you did not write produces no error and no warning "
               "&mdash; control simply falls past it into whatever came next. "
               "Enumerate the cases before writing any of them, and check that "
               "they tile the input space with no overlap and no hole.",
               "A case analysis with a gap in it")


def aliased_write() -> str:
    """Writing into the row you are still reading."""
    b = [ARROWHEADS]
    vals = ["2", "3", "5", "7"]
    b.append(label(40, 34, "a[i] = a[i-1] * a[i]   scanning left to right",
                   "var(--bad)", 13, anchor="start", font=MONO, weight="600"))
    for k, v in enumerate(vals):
        done = k < 2
        b.append(box(40 + k * 92, 50, 82, 38,
                     "6" if k == 1 else v,
                     fill="var(--panel)",
                     stroke="var(--bad)" if done else "var(--line)",
                     color="var(--bad)" if done else "var(--ink)"))
        b.append(label(81 + k * 92, 106, f"a[{k}]", "var(--muted)", 11))
    b.append(label(40, 136, "a[1] now holds a product, not the original 3. "
                   "a[2] reads it and compounds the error.",
                   "var(--muted)", 12, anchor="start"))
    b.append(arrow(122, 69, 152, 69, "var(--bad)", "ah-b"))

    b.append(label(40, 184, "prefix[i] = prefix[i-1] * a[i]   two arrays",
                   "var(--good)", 13, anchor="start", font=MONO, weight="600"))
    for k, v in enumerate(vals):
        b.append(box(40 + k * 92, 200, 82, 38, v, fill="var(--code)",
                     stroke="var(--line)", color="var(--muted)"))
        b.append(label(81 + k * 92, 256, f"a[{k}]", "var(--muted)", 11))
    b.append(label(430, 200, "a is never written.", "var(--good)", 13,
                   anchor="start", weight="600"))
    b.append(label(430, 222, "Every read returns what the", "var(--muted)", 12,
                   anchor="start"))
    b.append(label(430, 240, "algorithm assumed it would.", "var(--muted)", 12,
                   anchor="start"))
    return svg(720, 274, "".join(b),
               "An algorithm derived on paper reads the input. Reusing the "
               "input array as the output buffer keeps that derivation valid "
               "only if every read happens strictly before the write that "
               "lands on it &mdash; a property nothing in the code states and "
               "nothing checks.",
               "Reading a buffer you have already written")


def _selfcheck() -> None:
    """Render every diagram and assert nothing escapes its own viewBox.

    Text overflow is the failure mode here: SVG does not wrap or clip, so a
    label that is too long for its box just runs off the edge and is silently
    cut by the figure's overflow. Estimating the extent from character count is
    crude but catches the real bug -- a caption centred at x=300 that is 700px
    wide.
    """
    import inspect
    import re
    import sys

    fns = [(n, f) for n, f in sorted(globals().items())
           if callable(f) and not n.startswith("_")
           and inspect.isfunction(f) and not inspect.signature(f).parameters]
    assert fns, "no diagrams found"

    bad = []
    for name, fn in fns:
        out = fn()
        vb = re.search(r'viewBox="0 0 (\d+) (\d+)"', out)
        assert vb, f"{name}: no viewBox"
        w, h = int(vb.group(1)), int(vb.group(2))
        for m in re.finditer(
                r'<text x="([\d.-]+)" y="([\d.-]+)" text-anchor="(\w+)"(?![^>]*transform)'
                r'[^>]*?font-size="([\d.]+)"[^>]*>(.*?)</text>', out):
            x, y, anchor, size, txt = (float(m.group(1)), float(m.group(2)),
                                       m.group(3), float(m.group(4)),
                                       re.sub(r"<[^>]+>|&\w+;", "x", m.group(5)))
            span = len(txt) * size * 0.56
            left = {"middle": x - span / 2, "start": x, "end": x - span}[anchor]
            right = left + span
            if left < -2 or right > w + 2 or y < 0 or y > h:
                bad.append(f"{name}: {txt[:40]!r} spans "
                           f"{left:.0f}..{right:.0f} y={y:.0f} in {w}x{h}")
    if bad:
        print("\n".join(bad), file=sys.stderr)
        raise AssertionError(f"{len(bad)} label(s) outside the viewBox")
    print(f"diagrams ok: {len(fns)} figures, no overflow")


if __name__ == "__main__":
    _selfcheck()
