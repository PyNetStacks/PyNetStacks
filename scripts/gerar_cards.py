#!/usr/bin/env python3
"""Gera os cards SVG do perfil (stats, linguagens, streak, atividade, troféus)
usando a API GraphQL do GitHub. Roda dentro da GitHub Action."""
import os, json, datetime as dt, urllib.request
from html import escape

USER = os.environ.get("GH_USER", "PyNetStacks")
OUT = "assets/gerados"
RED, BG, TXT, MUT, DIM = "#FF1E1E", "#0A0A0A", "#F2F2F2", "#8A8A8A", "#1C1C1C"
FONT = "'JetBrains Mono','Cascadia Code',Consolas,'Courier New',monospace"

QUERY = """
query($login:String!){ user(login:$login){
  followers{totalCount}
  pullRequests{totalCount}
  issues{totalCount}
  repositories(ownerAffiliations:OWNER, isFork:false, first:100, privacy:PUBLIC){
    totalCount
    nodes{ stargazerCount
      languages(first:10, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name } } } }
  }
  contributionsCollection{
    totalCommitContributions
    contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } }
  }
}}"""


def fetch():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": "bearer " + os.environ["GITHUB_TOKEN"],
                 "Content-Type": "application/json", "User-Agent": "perfil-cards"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    if "errors" in d:
        raise SystemExit(d["errors"])
    return d["data"]["user"]


def frame(w, h, title, body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="{FONT}"><defs>{defs}</defs>'
            f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="10" fill="{BG}" stroke="{RED}" stroke-width="1.5"/>'
            f'<rect x="1" y="14" width="5" height="{h-28}" fill="{RED}"/>'
            f'<text x="26" y="34" fill="{RED}" font-size="13" font-weight="700" letter-spacing="3">{escape(title)}</text>'
            f'{body}</svg>')


def streaks(days):
    counts = [d["contributionCount"] for d in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    i = len(counts) - 1
    if i >= 0 and counts[i] == 0:  # hoje ainda sem contribuição não quebra a sequência
        i -= 1
    cur = 0
    while i >= 0 and counts[i] > 0:
        cur += 1
        i -= 1
    return cur, longest


def card_stats(u, commits):
    items = [("Contribuições (1 ano)", u["contributionsCollection"]["contributionCalendar"]["totalContributions"]),
             ("Commits (1 ano)", commits),
             ("Repositórios públicos", u["repositories"]["totalCount"]),
             ("Estrelas recebidas", sum(n["stargazerCount"] for n in u["repositories"]["nodes"])),
             ("Pull requests", u["pullRequests"]["totalCount"]),
             ("Issues", u["issues"]["totalCount"])]
    b = ""
    for i, (lab, val) in enumerate(items):
        x, y = 28 + (i // 3) * 235, 78 + (i % 3) * 38
        b += (f'<text x="{x}" y="{y}" fill="{TXT}" font-size="22" font-weight="700">{val}</text>'
              f'<text x="{x}" y="{y+16}" fill="{MUT}" font-size="11">{escape(lab)}</text>')
    return frame(495, 195, "GITHUB STATS", b)


def card_langs(u):
    tot = {}
    for n in u["repositories"]["nodes"]:
        for e in n["languages"]["edges"]:
            tot[e["node"]["name"]] = tot.get(e["node"]["name"], 0) + e["size"]
    top = sorted(tot.items(), key=lambda kv: -kv[1])[:5]
    s = sum(tot.values()) or 1
    b = ""
    if not top:
        b = f'<text x="28" y="100" fill="{MUT}" font-size="13">Sem dados ainda.</text>'
    for i, (name, size) in enumerate(top):
        y, pct = 62 + i * 25, size / s * 100
        w = max(3, 300 * pct / 100)
        op = 1 - i * 0.14
        b += (f'<text x="28" y="{y+11}" fill="{TXT}" font-size="12">{escape(name)}</text>'
              f'<rect x="130" y="{y}" width="300" height="12" rx="6" fill="{DIM}"/>'
              f'<rect x="130" y="{y}" width="0" height="12" rx="6" fill="{RED}" opacity="{op:.2f}">'
              f'<animate attributeName="width" from="0" to="{w:.1f}" dur="1.2s" fill="freeze"/></rect>'
              f'<text x="440" y="{y+11}" fill="{MUT}" font-size="12" text-anchor="end">{pct:.1f}%</text>')
    return frame(495, 195, "TOP LINGUAGENS", b)


def card_streak(days, total):
    cur, longest = streaks(days)
    b = ""
    for cx, num, lab in ((85, total, "Contribuições\n(último ano)"), (410, longest, "Maior\nsequência")):
        l1, l2 = lab.split("\n")
        b += (f'<text x="{cx}" y="108" fill="{TXT}" font-size="30" font-weight="700" text-anchor="middle">{num}</text>'
              f'<text x="{cx}" y="140" fill="{MUT}" font-size="11" text-anchor="middle">{l1}</text>'
              f'<text x="{cx}" y="155" fill="{MUT}" font-size="11" text-anchor="middle">{l2}</text>')
    b += (f'<circle cx="247" cy="105" r="42" fill="none" stroke="{DIM}" stroke-width="7"/>'
          f'<circle cx="247" cy="105" r="42" fill="none" stroke="{RED}" stroke-width="7" stroke-linecap="round" '
          f'stroke-dasharray="264" stroke-dashoffset="264" transform="rotate(-90 247 105)">'
          f'<animate attributeName="stroke-dashoffset" from="264" to="{264*(1-min(cur,30)/30):.1f}" dur="1.4s" fill="freeze"/></circle>'
          f'<text x="247" y="114" fill="{TXT}" font-size="28" font-weight="700" text-anchor="middle">{cur}</text>'
          f'<text x="247" y="168" fill="{RED}" font-size="11" font-weight="700" text-anchor="middle" letter-spacing="1">SEQUÊNCIA ATUAL</text>')
    return frame(495, 195, "STREAK", b)


def card_activity(days):
    d = days[-30:]
    W, H, x0, y0, gw, gh = 900, 230, 40, 60, 820, 120
    mx = max([x["contributionCount"] for x in d] + [1])
    pts = [(x0 + i * gw / max(len(d) - 1, 1), y0 + gh - x["contributionCount"] / mx * gh) for i, x in enumerate(d)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{x0},{y0+gh} {line} {x0+gw},{y0+gh}"
    grid = "".join(f'<line x1="{x0}" x2="{x0+gw}" y1="{y0+gh*k/3:.0f}" y2="{y0+gh*k/3:.0f}" stroke="{DIM}"/>' for k in range(4))
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{TXT}"/>' for (x, y), v in zip(pts, d) if v["contributionCount"] > 0)
    b = (grid + f'<polygon points="{area}" fill="url(#g)"/>'
         f'<polyline points="{line}" fill="none" stroke="{RED}" stroke-width="2.5" stroke-linejoin="round"/>{dots}'
         f'<text x="{x0}" y="{y0+gh+24}" fill="{MUT}" font-size="11">{d[0]["date"]}</text>'
         f'<text x="{x0+gw}" y="{y0+gh+24}" fill="{MUT}" font-size="11" text-anchor="end">{d[-1]["date"]}</text>'
         f'<text x="{W-26}" y="34" fill="{MUT}" font-size="11" text-anchor="end">pico: {mx} contrib./dia · últimos 30 dias</text>')
    g = (f'<linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{RED}" stop-opacity=".45"/>'
         f'<stop offset="1" stop-color="{RED}" stop-opacity="0"/></linearGradient>')
    return frame(W, H, "ATIVIDADE", b, g)


def card_trophies(u, commits, longest, nlangs):
    stars = sum(n["stargazerCount"] for n in u["repositories"]["nodes"])
    t = [("COMMITS", commits, (10, 100, 500, 1000)), ("REPOS", u["repositories"]["totalCount"], (1, 5, 15, 30)),
         ("ESTRELAS", stars, (1, 10, 50, 200)), ("SEGUIDORES", u["followers"]["totalCount"], (1, 10, 50, 200)),
         ("SEQUÊNCIA", longest, (3, 7, 30, 100)), ("LINGUAGENS", nlangs, (1, 3, 5, 8))]
    b = ""
    for i, (name, val, th) in enumerate(t):
        lvl = sum(val >= x for x in th)
        x = 28 + i * 140
        col = RED if lvl else "#444"
        b += (f'<rect x="{x}" y="58" width="124" height="104" rx="8" fill="#111" stroke="{col}" stroke-width="1.2"/>'
              f'<text x="{x+62}" y="108" fill="{col}" font-size="42" font-weight="700" text-anchor="middle">{"CBAS"[lvl-1] if lvl else "—"}</text>'
              f'<text x="{x+62}" y="132" fill="{TXT}" font-size="12" font-weight="700" text-anchor="middle">{escape(name)}</text>'
              f'<text x="{x+62}" y="150" fill="{MUT}" font-size="11" text-anchor="middle">{val}</text>')
    return frame(868, 182, "TROFÉUS", b)


def main():
    u = fetch()
    cc = u["contributionsCollection"]
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    today = dt.date.today().isoformat()
    days = [d for d in days if d["date"] <= today]
    langs = {e["node"]["name"] for n in u["repositories"]["nodes"] for e in n["languages"]["edges"]}
    commits = cc["totalCommitContributions"]
    total = cc["contributionCalendar"]["totalContributions"]
    _, longest = streaks(days)
    os.makedirs(OUT, exist_ok=True)
    files = {"stats": card_stats(u, commits), "langs": card_langs(u), "streak": card_streak(days, total),
             "activity": card_activity(days), "trofeus": card_trophies(u, commits, longest, len(langs))}
    for k, v in files.items():
        with open(f"{OUT}/{k}.svg", "w", encoding="utf-8") as f:
            f.write(v)
    print("ok:", ", ".join(files))


if __name__ == "__main__":
    main()
