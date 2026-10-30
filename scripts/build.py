#!/usr/bin/env python3
"""Builds the SVGs for the jonbttt profile README.

  python scripts/build.py static        card, buttons, section headers, project rows
  python scripts/build.py live          GitHub stats + recent PRs (needs GITHUB_TOKEN)
  python scripts/build.py live --mock   same, with sample data (local preview only)

Edit the CONFIG block to change what the card says.
"""
import base64, datetime as dt, io, json, os, re, sys, urllib.request
from xml.sax.saxutils import escape
from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")

# ------------------------------------------------------------------ CONFIG
LOGIN = "jonbttt"
INFO = [  # (label, value). Empty label = continuation line.
    ("Education", "BSc CS (Security Eng.), UNSW"),
    ("Experience", "SWE @ The Golfer Network"),
    ("", "AI Eng @ PT Wide Technologies"),
    ("Focus", "Linux kernel, eBPF, systems"),
    ("Upstream", "bpf-next, canonical/netplan"),
    ("Languages", "C, Go, Rust, Python, Bash"),
    ("OS", "Fedora 44 + Windows (dual boot)"),
    ("WM", "Hyprland"),
    ("Editor", "VSCode"),
]
PROJECTS = [  # (file id, name, description, tags, url)
    ("ward-xdp", "Ward-XDP", "eBPF/XDP inline IPS with a Go control plane, ~51 ns per packet",
     "C · Go · eBPF", "https://github.com/jonbttt/ward-xdp"),
    ("rk-veil", "rk-veil", "Linux kernel module rootkit + detector, presented at SCONES 2026",
     "C · Python", "https://github.com/jonbttt/rk-veil"),
    ("kernel", "selftests/bpf wq fix", "Upstream Linux kernel patch to bpf-next, flaky selftest fix",
     "C · kernel", "https://lore.kernel.org/bpf/?q=f%3Athamrin"),
]
BUTTONS = [("portfolio", "portfolio"), ("linkedin", "linkedin")]  # (file id, label)
EXCLUDE_OWN_REPOS = True  # hide PRs to your own repos in "recent PRs"
N_PRS = 5

# ------------------------------------------------------------------ THEME
# pulled from the Hyprland rice (look.lua + kitty.conf)
BG, PANEL, BORDER = "#14121a", "#1f1c27", "#3a3350"      # bg, color0, selection
TEXT, DIM, FAINT = "#dcd6e8", "#8a8299", "#4a4458"       # fg, waybar dim, inactive border
# role names kept for the code below
PINK, VIOLET, CYAN = "#cfc2ee", "#b8a7e0", "#9aaee0"     # color13, primary, color4
GREEN, AMBER = "#a6c9a0", "#e3c99a"                      # color2, color3
ANSI = ["#e09a9a", "#a6c9a0", "#e3c99a", "#9aaee0", "#b8a7e0", "#9ccfd8", "#dcd6e8", "#4a4458"]
STATE = {"OPEN": ("#a6c9a0", "open"), "MERGED": ("#b8a7e0", "merged"), "CLOSED": ("#e09a9a", "closed")}
CW = 0.6  # JetBrains Mono advance width per 1px of font size
W = 860   # every SVG shares this width so they line up stacked in the README

_FONTS = {}


def font_css(text, bold=False):
    """Subset JetBrains Mono to the glyphs used and inline it, so alignment is
    identical on every machine (an <img> SVG cannot load web fonts)."""
    name = "Bold" if bold else "Regular"
    path = os.path.join(A, "fonts", f"JetBrainsMono-{name}.ttf")
    opts = subset.Options(); opts.flavor = "woff2"; opts.layout_features = []
    font = TTFont(path)
    sub = subset.Subsetter(opts); sub.populate(text=text + " "); sub.subset(font)
    buf = io.BytesIO(); font.flavor = "woff2"; font.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    weight = 700 if bold else 400
    return (f"@font-face{{font-family:'JBM';font-weight:{weight};"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}")


def svg(w, h, body, text_reg="", text_bold="", extra_css=""):
    css = ""
    if text_reg:
        css += font_css(text_reg)
    if text_bold:
        css += font_css(text_bold, bold=True)
    css += ("text{font-family:'JBM','JetBrains Mono',ui-monospace,Menlo,Consolas,monospace;"
            "white-space:pre}" + extra_css)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}"><style>{css}</style>{body}</svg>')


def t(x, y, s, size, fill, bold=False, anchor="start"):
    w = ' font-weight="700"' if bold else ""
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}"{w}{a}>{escape(s)}</text>'


def save(name, content):
    with open(os.path.join(A, name), "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", name, f"({len(content)//1024} KB)")


def fit(s, max_chars):
    return s if len(s) <= max_chars else s[: max_chars - 1] + "…"

# ------------------------------------------------------------------ CARD


def portrait_dots(x0, y0, pitch, r):
    """Braille cells -> real dots. Each U+2800 cell is a 2x4 dot grid."""
    bits = [(0, 0, 0x01), (0, 1, 0x02), (0, 2, 0x04), (1, 0, 0x08),
            (1, 1, 0x10), (1, 2, 0x20), (0, 3, 0x40), (1, 3, 0x80)]
    lines = open(os.path.join(A, "portrait.txt"), encoding="utf-8").read().splitlines()
    d = []
    for row, line in enumerate(lines):
        for col, ch in enumerate(line):
            v = ord(ch) - 0x2800
            if not 0 < v < 256:
                continue
            for dx, dy, b in bits:
                if v & b:
                    cx = x0 + (col * 2 + dx) * pitch
                    cy = y0 + (row * 4 + dy) * pitch
                    d.append(f"M{cx - r:.1f} {cy:.1f}a{r} {r} 0 1 0 {2*r} 0a{r} {r} 0 1 0 {-2*r} 0")
    cols = max(len(l) for l in lines) * 2
    return "".join(d), cols * pitch, len(lines) * 4 * pitch


def build_card():
    pitch, r, pad = 4.3, 1.1, 34
    dots, pw, ph = portrait_dots(pad + 8, pad + 6, pitch, r)
    h = int(ph + pad * 2 + 6)

    fs, lh = 15, 25
    tx = int(pad + pw + 44)
    vx = tx + int(max(len(l) for l, _ in INFO) * fs * CW) + 34
    n_lines = 2 + len(INFO) + 2
    ty = int((h - n_lines * lh) / 2) + lh - 4

    reg = bold = ""
    b = [f'<rect x="1" y="1" width="{W-2}" height="{h-2}" rx="14" fill="{BG}" stroke="{BORDER}"/>',
         f'<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" y1="{pad}" x2="0" y2="{pad+ph}">'
         f'<stop offset="0" stop-color="{PINK}"/><stop offset=".5" stop-color="{VIOLET}"/>'
         f'<stop offset="1" stop-color="{CYAN}"/></linearGradient></defs>',
         f'<path d="{dots}" fill="url(#g)"/>']

    # header: user@host + blinking cursor
    u, at, host = LOGIN, "@", "github"
    b.append(f'<text x="{tx}" y="{ty}" font-size="{fs+1}" font-weight="700">'
             f'<tspan fill="{PINK}">{u}</tspan><tspan fill="{DIM}">{at}</tspan>'
             f'<tspan fill="{GREEN}">{host}</tspan></text>')
    bold += u + at + host
    cur_x = tx + (len(u + at + host) + 0.4) * (fs + 1) * CW
    b.append(f'<rect x="{cur_x:.1f}" y="{ty-13}" width="8" height="16" fill="{PINK}">'
             f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" '
             f'dur="1.1s" repeatCount="indefinite"/></rect>')
    y = ty + lh - 8
    b.append(f'<line x1="{tx}" y1="{y}" x2="{W-pad}" y2="{y}" stroke="{FAINT}"/>')
    y += lh - 2

    for label, value in INFO:
        if label:
            b.append(t(tx, y, label, fs, GREEN, bold=True)); bold += label
            lx = tx + len(label) * fs * CW + 8
            lx = tx + 6 * (int((lx - tx) / 6) + 1)  # snap dots to one shared grid
            b.append(f'<line x1="{lx:.0f}" y1="{y-4}" x2="{vx-10}" y2="{y-4}" stroke="{FAINT}" '
                     f'stroke-width="1.6" stroke-dasharray="0 6" stroke-linecap="round"/>')
        b.append(t(vx, y, value, fs, TEXT)); reg += value
        y += lh

    # neofetch colour blocks
    y += 4
    for i, c in enumerate(ANSI):
        b.append(f'<rect x="{tx + i*30}" y="{y-14}" width="24" height="14" rx="3" fill="{c}"/>')

    save("card.svg", svg(W, h, "".join(b), reg, bold))

# ------------------------------------------------------------------ SMALL PIECES


def build_section(file_id, cmd):
    h = 44
    body = (t(4, 28, "$ ", 15, GREEN, bold=True)
            + t(4 + 2 * 15 * CW, 28, cmd, 15, TEXT, bold=True)
            + f'<line x1="{4 + (len(cmd)+3)*15*CW:.0f}" y1="23" x2="{W}" y2="23" stroke="{FAINT}"/>')
    save(f"sec-{file_id}.svg", svg(W, h, body, "", "$ " + cmd))


def build_button(file_id, label):
    fs = 14
    parts = [("[ ", DIM), (label, CYAN), (" ↗", PINK), (" ]", DIM)]
    n = sum(len(x) for x, _ in parts)
    w = int(n * fs * CW + 28)
    x = (w - n * fs * CW) / 2
    body = f'<rect x="1" y="1" width="{w-2}" height="36" rx="8" fill="{BG}" stroke="{BORDER}"/>'
    for s, c in parts:
        body += t(round(x, 1), 24, s, fs, c, bold=True)
        x += len(s) * fs * CW
    save(f"btn-{file_id}.svg", svg(w, 38, body, "", "".join(x for x, _ in parts)))


def row_frame(h, accent):
    return (f'<rect x="1" y="1" width="{W-2}" height="{h-2}" rx="10" fill="{BG}" stroke="{BORDER}"/>'
            f'<rect x="1" y="12" width="3" height="{h-24}" rx="1.5" fill="{accent}"/>')


def build_project(file_id, name, desc, tags, accent):
    h = 66
    body = (row_frame(h, accent)
            + t(22, 29, name, 16, accent, bold=True)
            + t(22, 50, fit(desc, 74), 13, DIM)
            + t(W - 20, 29, tags, 12, FAINT if False else DIM, anchor="end")
            + t(W - 20, 50, "↗", 15, PINK, bold=True, anchor="end"))
    save(f"proj-{file_id}.svg", svg(W, h, body, desc + tags, name + "↗"))


def build_static():
    build_card()
    for fid, label in BUTTONS:
        build_button(fid, label)
    build_section("projects", "ls ~/projects")
    build_section("activity", f"gh pr list --author {LOGIN}")
    accents = [PINK, VIOLET, CYAN, GREEN, AMBER]
    for i, (fid, name, desc, tags, _) in enumerate(PROJECTS):
        build_project(fid, name, desc, tags, accents[i % len(accents)])

# ------------------------------------------------------------------ LIVE STATS


QUERY = """
query($login:String!, $own:String!, $merged:String!, $recent:String!){
  user(login:$login){
    followers{totalCount}
    repositories(ownerAffiliations:OWNER, privacy:PUBLIC, first:100, isFork:false){
      totalCount nodes{stargazerCount}}
    contributionsCollection{totalCommitContributions}
    pullRequests{totalCount}
  }
  merged: search(query:$merged, type:ISSUE){issueCount}
  recent: search(query:$recent, type:ISSUE, first:20){
    nodes{... on PullRequest{title number url state createdAt
      repository{nameWithOwner owner{login}}}}}
}"""


def fetch_live():
    token = os.environ["GITHUB_TOKEN"]
    variables = {"login": LOGIN, "own": LOGIN,
                 "merged": f"author:{LOGIN} type:pr is:merged",
                 "recent": f"author:{LOGIN} type:pr sort:created-desc"}
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req))
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    d = data["data"]; u = d["user"]
    prs = [p for p in d["recent"]["nodes"] if p
           and not (EXCLUDE_OWN_REPOS and p["repository"]["owner"]["login"].lower() == LOGIN.lower())]
    return {
        "repos": u["repositories"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "followers": u["followers"]["totalCount"],
        "commits": u["contributionsCollection"]["totalCommitContributions"],
        "prs": u["pullRequests"]["totalCount"],
        "merged": d["merged"]["issueCount"],
        "recent": [{"title": p["title"], "num": p["number"], "url": p["url"], "state": p["state"],
                    "repo": p["repository"]["nameWithOwner"], "date": p["createdAt"][:10]}
                   for p in prs[:N_PRS]],
    }


def mock_live():
    return {"repos": 14, "stars": 9, "followers": 21, "commits": 412, "prs": 6, "merged": 2,
            "recent": [
                {"title": "SAMPLE: fix silently dropped address when label exceeds 15 chars",
                 "num": 512, "url": "#", "state": "OPEN", "repo": "canonical/netplan", "date": "2026-10-20"},
                {"title": "SAMPLE: docs typo", "num": 1801, "url": "#", "state": "MERGED",
                 "repo": "example/project", "date": "2026-10-02"},
                {"title": "SAMPLE: closed experiment", "num": 77, "url": "#", "state": "CLOSED",
                 "repo": "example/other", "date": "2026-09-14"}]}


def build_stats(s):
    h = 112
    cells = [("repos", s["repos"], PINK), ("stars", s["stars"], AMBER),
             ("followers", s["followers"], VIOLET), (f"commits {dt.date.today().year}", s["commits"], CYAN),
             ("pull requests", s["prs"], GREEN), ("merged", s["merged"], VIOLET)]
    colw = (W - 40) / 3
    b = [f'<rect x="1" y="1" width="{W-2}" height="{h-2}" rx="12" fill="{BG}" stroke="{BORDER}"/>']
    reg = bold = ""
    for i, (label, val, col) in enumerate(cells):
        x = 26 + (i % 3) * colw
        y = 44 + (i // 3) * 42
        v = f"{val:,}"
        b.append(t(x, y, v, 20, col, bold=True)); bold += v
        b.append(t(x + len(v) * 20 * CW + 10, y, label, 13, DIM)); reg += label
    save("stats.svg", svg(W, h, "".join(b), reg, bold))


def build_pr(i, p):
    h = 56
    col, word = STATE[p["state"]]
    pill_w = len(word) * 12 * CW + 18
    num = f"#{p['num']}"
    right = p["date"]
    room = int((W - 40 - pill_w - 12 - len(right) * 12 * CW - 20) / (13 * CW))
    title = fit(p["title"], room - len(p["repo"]) - len(num) - 3)
    body = (row_frame(h, col)
            + f'<rect x="20" y="17" width="{pill_w:.0f}" height="22" rx="11" fill="{col}" fill-opacity=".16" stroke="{col}"/>'
            + t(20 + pill_w / 2, 32, word, 12, col, bold=True, anchor="middle")
            + f'<text x="{20 + pill_w + 12:.0f}" y="33" font-size="13">'
              f'<tspan fill="{CYAN}">{escape(p["repo"])}</tspan>'
              f'<tspan fill="{DIM}"> {num} </tspan><tspan fill="{TEXT}">{escape(title)}</tspan></text>'
            + t(W - 20, 33, right, 12, DIM, anchor="end"))
    save(f"pr-{i}.svg", svg(W, h, body, p["repo"] + num + title + right, word))


def build_live(mock=False):
    s = mock_live() if mock else fetch_live()
    build_stats(s)
    for f in os.listdir(A):
        if re.fullmatch(r"pr-\d+\.svg", f):
            os.remove(os.path.join(A, f))
    lines = ['<img src="assets/stats.svg" width="100%" alt="GitHub stats">', ""]
    for i, p in enumerate(s["recent"], 1):
        build_pr(i, p)
        lines.append(f'<a href="{p["url"]}"><img src="assets/pr-{i}.svg" width="100%" '
                     f'alt="{escape(p["repo"])} #{p["num"]}: {escape(p["title"])}"></a>')
    if not s["recent"]:
        lines.append("<sub>no public PRs yet</sub>")
    readme = os.path.join(ROOT, "README.md")
    txt = open(readme, encoding="utf-8").read()
    block = "<!-- LIVE:START -->\n" + "\n".join(lines) + "\n<!-- LIVE:END -->"
    txt = re.sub(r"<!-- LIVE:START -->.*?<!-- LIVE:END -->", block, txt, flags=re.S)
    open(readme, "w", encoding="utf-8").write(txt)
    print("README live block updated")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "static"
    if mode == "static":
        build_static()
    elif mode == "live":
        build_live(mock="--mock" in sys.argv)
    else:
        sys.exit(__doc__)
