"""Render a "top languages" card for the profile README.

Sums language bytes across the user's public, non-fork repositories via the
GitHub API and writes light and dark SVG cards. Runs in the profile workflow,
so the README never depends on a third-party stats server.
"""
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

API = "https://api.github.com"
TOP = 6
COLORS = ["#a78bfa", "#60a5fa", "#34d399", "#fbbf24", "#f472b6", "#94a3b8"]
THEMES = {
    "light": {"bg": "#ffffff", "border": "#d0d7de", "title": "#1f2328", "text": "#59636e"},
    "dark": {"bg": "#0d1117", "border": "#30363d", "title": "#e6edf3", "text": "#8b949e"},
}
WIDTH = 420


def get(path):
    req = urllib.request.Request(API + path, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def collect(user):
    totals = {}
    page = 1
    while True:
        repos = get(f"/users/{user}/repos?type=owner&per_page=100&page={page}")
        if not repos:
            break
        for repo in repos:
            if repo["fork"] or repo["archived"]:
                continue
            for lang, size in get(f"/repos/{repo['full_name']}/languages").items():
                totals[lang] = totals.get(lang, 0) + size
        page += 1
    return totals


def render(totals, theme):
    t = THEMES[theme]
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:TOP]
    total = sum(size for _, size in top)
    rows = (len(top) + 1) // 2
    height = 84 + rows * 26 if top else 100
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}">',
        '<style>.t{font:600 15px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}'
        '.l{font:400 12px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}</style>',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="12" fill="{t["bg"]}" stroke="{t["border"]}"/>',
        f'<text x="24" y="36" class="t" fill="{t["title"]}">top languages</text>',
    ]
    if not top:
        out.append(f'<text x="24" y="72" class="l" fill="{t["text"]}">no public code yet — soon.</text>')
    else:
        out.append(f'<clipPath id="bar"><rect x="24" y="52" width="{WIDTH - 48}" height="8" rx="4"/></clipPath><g clip-path="url(#bar)">')
        x = 24.0
        for i, (_, size) in enumerate(top):
            w = (WIDTH - 48) * size / total
            out.append(f'<rect x="{x:.2f}" y="52" width="{w + 0.5:.2f}" height="8" fill="{COLORS[i]}"/>')
            x += w
        out.append("</g>")
        for i, (lang, size) in enumerate(top):
            cx = 24 + (i % 2) * 190
            cy = 88 + (i // 2) * 26
            out.append(f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{COLORS[i]}"/>')
            out.append(
                f'<text x="{cx + 18}" y="{cy}" class="l" fill="{t["text"]}">'
                f'{escape(lang)} {100 * size / total:.1f}%</text>'
            )
    out.append("</svg>")
    return "\n".join(out)


def main():
    user, out_dir = sys.argv[1], sys.argv[2]
    totals = json.load(sys.stdin) if user == "-" else collect(user)
    os.makedirs(out_dir, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(out_dir, f"languages-{theme}.svg"), "w") as f:
            f.write(render(totals, theme))


if __name__ == "__main__":
    main()
