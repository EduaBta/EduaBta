"""Desenha a "Galáxia de Contribuições": cada estrela é um dia do último ano.

Uso: python3 contrib_galaxy.py <usuario> <saida.svg>   (precisa de GITHUB_TOKEN no ambiente)
Só usa a biblioteca padrão, para rodar direto no runner do GitHub Actions.
"""
import json
import math
import os
import random
import sys
import urllib.request
from datetime import date
from html import escape

QUERY = """query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar {
  totalContributions weeks { contributionDays { date contributionCount contributionLevel } } } } } }"""

FONT = "'Segoe UI','Helvetica Neue',Arial,sans-serif"
LEVELS = {  # raio, cor, halo?
    "NONE": (1.4, "#7465C8", False),
    "FIRST_QUARTILE": (2.3, "#5B7BFF", False),
    "SECOND_QUARTILE": (3.0, "#9D7BFF", True),
    "THIRD_QUARTILE": (3.8, "#00D8FF", True),
    "FOURTH_QUARTILE": (4.8, "#00F7FF", True),
}


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "contrib-galaxy"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if body.get("errors"):
        raise SystemExit(f"GraphQL error: {body['errors']}")
    cal = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    return cal["totalContributions"], days


def streaks(days):
    counts = [d["contributionCount"] for d in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    i = len(counts) - 1
    if counts and counts[i] == 0:  # hoje ainda pode não ter commit
        i -= 1
    current = 0
    while i >= 0 and counts[i]:
        current += 1
        i -= 1
    return current, longest


def f(x):
    return f"{x:.1f}".rstrip("0").rstrip(".")


def br(n):
    return f"{n:,}".replace(",", ".")


def br_date(iso):
    y, m, d = iso.split("-")
    return f"{d}/{m}/{y}"


def render(login, total, days):
    rng = random.Random(42)
    W, H = 1200, 460
    gx, gy, R = 380, 235, 300
    current, longest = streaks(days)
    active = sum(1 for d in days if d["contributionCount"])
    best = max(days, key=lambda d: d["contributionCount"])

    # fundo de estrelas
    bg_stars = []
    for _ in range(170):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        r = rng.uniform(.35, 1.1) if rng.random() > .1 else rng.uniform(1.2, 1.8)
        bg_stars.append(f'<circle class="tw tw{rng.randrange(4)}" cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="#FFF" opacity="{rng.uniform(.25, .8):.2f}"/>')

    # poeira decorativa: um pouco no disco e a maior parte desenhando os braços da espiral
    arms, n = 3, len(days)
    dust = []
    for _ in range(140):
        r = abs(rng.gauss(0, R * .35))
        a = rng.uniform(0, 2 * math.pi)
        dust.append(f'<circle cx="{f(r * math.cos(a))}" cy="{f(r * math.sin(a))}" r="{f(rng.uniform(.6, 1.5))}" '
                    f'fill="#8F6BFF" opacity="{rng.uniform(.1, .3):.2f}"/>')
    for k in range(600):
        t = rng.random() ** .85
        rad = 26 + t * (R - 26)
        ang = (k % arms) * 2 * math.pi / arms + t * 2.4 * math.pi + rng.gauss(0, .1)
        jit = 5 + 12 * t
        x, y = rad * math.cos(ang) + rng.gauss(0, jit), rad * math.sin(ang) + rng.gauss(0, jit)
        col = rng.choice(["#7FE9FF", "#9D7BFF", "#C77DFF", "#5B7BFF"]) if t > .25 else "#D8FBFF"
        dust.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rng.uniform(.5, 1.4))}" fill="{col}" opacity="{rng.uniform(.15, .5):.2f}"/>')

    # um dia = uma estrela; os dias mais antigos ficam no núcleo, os recentes nas pontas dos braços
    halos, stars = [], []
    for i, d in enumerate(days):
        t = i / max(n - 1, 1)
        rad = 26 + t * (R - 26)
        ang = (i % arms) * 2 * math.pi / arms + t * 2.4 * math.pi
        jit = 2 + 7 * t
        x = rad * math.cos(ang) + rng.gauss(0, jit)
        y = rad * math.sin(ang) + rng.gauss(0, jit)
        size, col, halo = LEVELS.get(d["contributionLevel"], LEVELS["NONE"])
        label = f'{br_date(d["date"])}: {d["contributionCount"]} contribuições'
        if halo:
            halos.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(size * 2.8)}" fill="{col}" opacity=".18"/>')
        tw = f' class="tw tw{i % 4}"' if d["contributionCount"] else ""
        core = f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(size * .45)}" fill="#FFF"/>' if size >= 3.8 else ""
        stars.append(f'<g{tw}><title>{label}</title><circle cx="{f(x)}" cy="{f(y)}" r="{f(size)}" fill="{col}"/>{core}</g>')

    tiles = [
        (br(total), "contribuições no último ano"),
        (br(active), "dias com estrelas acesas"),
        (f"{current} {'dia' if current == 1 else 'dias'}", "sequência atual"),
        (f"{longest} {'dia' if longest == 1 else 'dias'}", "maior sequência"),
    ]
    px, tw_, th, gap = 742, 200, 92, 16
    tile_svg = []
    for k, (num, lab) in enumerate(tiles):
        x = px + (k % 2) * (tw_ + gap)
        y = 148 + (k // 2) * (th + gap)
        tile_svg.append(
            f'<rect x="{x}" y="{y}" width="{tw_}" height="{th}" rx="14" fill="#140C3A" fill-opacity=".72" stroke="#7B5CFF" stroke-opacity=".35"/>'
            f'<text x="{x + 18}" y="{y + 46}" font-size="30" font-weight="800" fill="url(#txt)">{escape(num)}</text>'
            f'<text x="{x + 18}" y="{y + 72}" font-size="13" fill="#B7AEF0">{escape(lab)}</text>')

    legend = "".join(
        f'<circle cx="{px + 54 + j * 22}" cy="395" r="{LEVELS[l][0]}" fill="{LEVELS[l][1]}"/>'
        for j, l in enumerate(LEVELS))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
<title id="t">Galáxia de contribuições de {escape(login)}</title>
<desc id="d">{br(total)} contribuições no último ano, {active} dias ativos, sequência atual de {current} dias e maior sequência de {longest} dias.</desc>
<style>
@keyframes twinkle {{ from {{ opacity: 1 }} to {{ opacity: .3 }} }}
@keyframes spin {{ to {{ transform: rotate(360deg) }} }}
@keyframes pulse {{ from {{ transform: scale(1); opacity: .8 }} to {{ transform: scale(1.2); opacity: 1 }} }}
@keyframes breathe {{ from {{ opacity: .6 }} to {{ opacity: 1 }} }}
.core {{ transform-box: fill-box; transform-origin: center }}
@media (prefers-reduced-motion: no-preference) {{
  .tw0 {{ animation: twinkle 2.8s ease-in-out infinite alternate }}
  .tw1 {{ animation: twinkle 3.6s ease-in-out .9s infinite alternate }}
  .tw2 {{ animation: twinkle 4.4s ease-in-out 1.7s infinite alternate }}
  .tw3 {{ animation: twinkle 5.4s ease-in-out .3s infinite alternate }}
  .spin {{ animation: spin 160s linear infinite }}
  .core {{ animation: pulse 4s ease-in-out infinite alternate }}
  .nebula {{ animation: breathe 14s ease-in-out infinite alternate }}
}}
</style>
<defs>
  <radialGradient id="bg" cx="35%" cy="50%" r="85%">
    <stop offset="0" stop-color="#170B45"/><stop offset=".55" stop-color="#08041F"/><stop offset="1" stop-color="#02000D"/>
  </radialGradient>
  <filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="45"/></filter>
  <filter id="disk" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="34"/></filter>
  <radialGradient id="coreG">
    <stop offset="0" stop-color="#FFF"/><stop offset=".2" stop-color="#C9FCFF"/>
    <stop offset=".45" stop-color="#00F7FF" stop-opacity=".5"/><stop offset="1" stop-color="#7B2FF7" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="txt" x1="0" x2="1" y1="0" y2="0">
    <stop offset="0" stop-color="#00F7FF"/><stop offset=".55" stop-color="#C77DFF"/><stop offset="1" stop-color="#FF7AD9"/>
  </linearGradient>
  <clipPath id="frame"><rect width="{W}" height="{H}" rx="18"/></clipPath>
</defs>
<g clip-path="url(#frame)" font-family="{FONT}">
  <rect width="{W}" height="{H}" fill="url(#bg)"/>
  <g filter="url(#blur)" class="nebula">
    <ellipse cx="300" cy="120" rx="300" ry="130" fill="#7B2FF7" opacity=".38"/>
    <ellipse cx="520" cy="400" rx="280" ry="100" fill="#FF4FD8" opacity=".16"/>
    <ellipse cx="1050" cy="80" rx="260" ry="110" fill="#3A5BFF" opacity=".28"/>
  </g>
  {"".join(bg_stars)}
  <g transform="translate({gx} {gy}) rotate(-16) scale(1 .52)">
    <circle r="230" fill="#6A4BFF" opacity=".16" filter="url(#disk)"/>
    <g class="spin">{"".join(dust)}{"".join(halos)}{"".join(stars)}</g>
  </g>
  <circle class="core" cx="{gx}" cy="{gy}" r="60" fill="url(#coreG)"/>
  <text x="{px}" y="78" font-size="22" font-weight="800" letter-spacing="2.5" fill="url(#txt)">GALÁXIA DE CONTRIBUIÇÕES</text>
  <text x="{px}" y="106" font-size="14" fill="#B7AEF0">Cada estrela é um dia do último ano.</text>
  <text x="{px}" y="126" font-size="14" fill="#B7AEF0">Quanto mais commits, mais ela brilha. ✦</text>
  {"".join(tile_svg)}
  <text x="{px}" y="399" font-size="12" fill="#B7AEF0">menos</text>{legend}<text x="{px + 54 + 5 * 22}" y="399" font-size="12" fill="#B7AEF0">mais</text>
  <text x="{px}" y="430" font-size="12" fill="#8C82C8">Melhor dia: {br_date(best["date"])} com {best["contributionCount"]} contribuições · atualizado em {date.today().strftime("%d/%m/%Y")}</text>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="#7B5CFF" stroke-opacity=".35"/>
</svg>
"""


def main():
    login, out = sys.argv[1], sys.argv[2]
    token = os.environ.get("GITHUB_TOKEN") or sys.exit("GITHUB_TOKEN não definido")
    total, days = fetch(login, token)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render(login, total, days))
    print(f"{out}: {total} contribuições, {len(days)} dias")


if __name__ == "__main__":
    main()
