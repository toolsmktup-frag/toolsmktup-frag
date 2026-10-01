#!/usr/bin/env python3
"""Gera dark_mode.svg e light_mode.svg do README de perfil (estilo neofetch).

Uso:
  python3 build.py            # monta os SVGs com ascii.txt + CONFIG + stats do GitHub
  python3 build.py --ascii    # refaz o ascii.txt a partir de foto.jpeg (precisa de Pillow)

Stats: lê GH_TOKEN / GITHUB_TOKEN do ambiente. Sem token, reaproveita stats.json.
"""
import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent

# ─────────────────────────── edite aqui ───────────────────────────
LOGIN = "toolsmktup-frag"
TITLE = "lucas@carli"
BIRTHDAY = date(1995, 11, 21)  # None -> usa AGE_FALLBACK fixo
AGE_FALLBACK = "30 years"

# (chave, valor) vira linha pontilhada | "" = linha vazia | "- Texto" = título de seção
LINES = [
    ("OS", "macOS 15, Linux (VPS)"),
    ("Uptime", "{uptime}"),
    ("Host", "Brasil"),
    ("Kernel", "Automações, integrações e agentes de IA"),
    ("Background", "desde 2012: infra, redes, telecom"),
    ("Background.Ex", "Oi Telecom, Copel Fibra, Sicoob"),
    ".",
    ("Automation", "n8n, APIs REST, webhooks, JSON"),
    ("Integrations", "CRM, ERP, WhatsApp API, Supabase"),
    ("AI.Assisted", "Claude, Codex, Cursor, Antigravity"),
    ("AI.Builders", "Lovable, Dyad"),
    ("Marketing", "automação de marketing, growth hacking"),
    ("Sales", "operações de vendas, funis e CRM"),
    "",
    "- Building",
    ("Agents", "agentes de WhatsApp p/ advocacia bancária"),
    ("SaaS", "conciliação contábil com IA"),
    ("Commerce", "e-commerce próprio"),
    "",
    "- Contact",
    ("GitHub", LOGIN),
    ("Instagram", "carli.lucas"),
    ("LinkedIn", "lucas-carli-1a692174"),
    "",
    "- GitHub Stats",
    "{stats}",
]
# ──────────────────────────────────────────────────────────────────

# Geometria. Consolas é mais estreita que as outras monoespaçadas; o @font-face
# abaixo estica ela pra ~0.6em, então a conta de largura vale em Windows, Mac e Linux.
CHAR_W = 0.602
ASCII_COLS, ASCII_ROWS, ASCII_FS, ASCII_LH = 64, 42, 10, 12
INFO_FS, INFO_LH, INFO_COLS = 16, 20, 58
PAD = 15
INFO_X = PAD + round(ASCII_COLS * ASCII_FS * CHAR_W) + PAD
WIDTH = INFO_X + round(INFO_COLS * INFO_FS * CHAR_W) + PAD
HEIGHT = max(530, 30 + len(LINES) * INFO_LH + 20)  # cresce sozinho com o número de linhas

THEMES = {
    "dark_mode.svg": dict(bg="#161b22", fg="#c9d1d9", key="#ffa657", value="#a5d6ff", cc="#616e7f"),
    "light_mode.svg": dict(bg="#f6f8fa", fg="#24292f", key="#953800", value="#0a3069", cc="#c2cfde"),
}

RAMP = " .`',:;!|*ijlkmwpg%HNM@"


def make_ascii():
    """foto.jpeg -> ascii.txt. Corrige a luz lateral dividindo pela iluminação borrada."""
    from PIL import Image, ImageFilter, ImageOps

    im = Image.open(ROOT / "foto.jpeg").convert("L")
    w, h = im.size
    target = (ASCII_COLS * ASCII_FS * CHAR_W) / (ASCII_ROWS * ASCII_LH)
    cw = min(w, h * target)
    ch = cw / target
    im = im.crop((int((w - cw) / 2), 0, int((w + cw) / 2), int(ch)))
    base = ImageOps.autocontrast(im, cutoff=(1, 1))
    blur = base.filter(ImageFilter.GaussianBlur(45))
    src, light = base.load(), blur.load()
    out = Image.new("L", base.size)
    dst = out.load()
    for y in range(base.size[1]):
        for x in range(base.size[0]):
            v = src[x, y]
            if v < 20:  # fundo preto continua vazio
                continue
            local = v / (light[x, y] + 30) * 150
            dst[x, y] = max(0, min(255, int(0.65 * local + 0.35 * v)))
    out = ImageOps.autocontrast(out, cutoff=(0, 1))
    out = out.filter(ImageFilter.UnsharpMask(radius=4, percent=120))
    out = out.resize((ASCII_COLS, ASCII_ROWS), Image.LANCZOS)
    rows = [
        "".join(RAMP[min(len(RAMP) - 1, out.getpixel((x, y)) * len(RAMP) // 256)] for x in range(ASCII_COLS)).rstrip()
        for y in range(ASCII_ROWS)
    ]
    (ROOT / "ascii.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def uptime():
    if not BIRTHDAY:
        return AGE_FALLBACK
    today = date.today()
    years = today.year - BIRTHDAY.year - ((today.month, today.day) < (BIRTHDAY.month, BIRTHDAY.day))
    last = date(BIRTHDAY.year + years, BIRTHDAY.month, BIRTHDAY.day)
    months = (today.year - last.year) * 12 + today.month - last.month - (today.day < last.day)
    anchor_m = (last.month - 1 + months) % 12 + 1
    anchor_y = last.year + (last.month - 1 + months) // 12
    days = (today - date(anchor_y, anchor_m, min(last.day, 28))).days
    return f"{years} years, {months} months, {max(days, 0)} days"


def fetch_stats():
    """Com o GITHUB_TOKEN do Actions só enxerga o que é público; com um PAT seu, conta os privados."""
    cache = ROOT / "stats.json"
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        query = """query($login:String!){user(login:$login){
          followers{totalCount}
          all:repositories(ownerAffiliations:OWNER){totalCount}
          public:repositories(ownerAffiliations:OWNER,privacy:PUBLIC){totalCount}
          contributionsCollection{contributionCalendar{totalContributions}}}}"""
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": query, "variables": {"login": LOGIN}}).encode(),
            headers={"Authorization": f"bearer {token}", "User-Agent": LOGIN},
        )
        try:
            user = json.load(urllib.request.urlopen(req, timeout=30))["data"]["user"]
            stats = {
                "repos": user["all"]["totalCount"],
                "public": user["public"]["totalCount"],
                "contributions": user["contributionsCollection"]["contributionCalendar"]["totalContributions"],
                "followers": user["followers"]["totalCount"],
            }
            cache.write_text(json.dumps(stats, indent=2) + "\n")
            return stats
        except Exception as err:  # API fora do ar não pode quebrar o card
            print(f"aviso: stats não atualizados ({err}); usando stats.json", file=sys.stderr)
    return json.loads(cache.read_text())


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def key_svg(key):
    return ".".join(f'<tspan class="key">{esc(part)}</tspan>' for part in key.split("."))


def kv(key, value, width):
    """'Key: ....... value' ocupando exatamente `width` colunas."""
    dots = width - len(key) - len(value) - 3
    if dots < 1:
        sys.exit(f"linha estoura {width} colunas: {key}: {value}")
    return f'{key_svg(key)}:<tspan class="cc"> {"." * dots} </tspan><tspan class="value">{esc(value)}</tspan>'


def rule(label):
    return f'{esc(label)} -{"—" * (INFO_COLS - len(label) - 5)}-—-'


def info_lines(stats):
    out = [rule(TITLE)]
    for item in LINES:
        if item == "":
            out.append("")
        elif item == ".":
            out.append('<tspan class="cc">. </tspan>')
        elif item == "{stats}":
            if stats["repos"] > stats["public"]:
                left = kv("Repos", f'{stats["repos"]} {{Public: {stats["public"]}}}', 26)
            else:  # sem PAT a API só enxerga os públicos
                left = kv("Repos.Public", str(stats["public"]), 26)
            right = kv("Contributions.Year", f'{stats["contributions"]:,}', INFO_COLS - 2 - 26 - 3)
            out.append(f'<tspan class="cc">. </tspan>{left} | {right}')
        elif isinstance(item, str):
            out.append(rule(item))
        else:
            key, value = item
            out.append('<tspan class="cc">. </tspan>' + kv(key, value.format(uptime=uptime()), INFO_COLS - 2))
    return out


def render(theme, art, info):
    svg = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f'<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,Menlo,\'DejaVu Sans Mono\',monospace" '
        f'width="{WIDTH}px" height="{HEIGHT}px" viewBox="0 0 {WIDTH} {HEIGHT}" font-size="{INFO_FS}px">',
        "<style>",
        "@font-face {src: local('Consolas'), local('Consolas Bold'); font-family: 'ConsolasFallback'; "
        "font-display: swap; -webkit-size-adjust: 109%; size-adjust: 109%;}",
        f".key {{fill: {theme['key']};}}",
        f".value {{fill: {theme['value']};}}",
        f".cc {{fill: {theme['cc']};}}",
        "text, tspan {white-space: pre;}",
        "</style>",
        f'<rect width="{WIDTH}px" height="{HEIGHT}px" fill="{theme["bg"]}" rx="15"/>',
        f'<g fill="{theme["fg"]}" font-size="{ASCII_FS}px">',
    ]
    top = (HEIGHT - ASCII_ROWS * ASCII_LH) // 2 + ASCII_LH - 2
    svg += [f'<text x="{PAD}" y="{top + i * ASCII_LH}" xml:space="preserve">{esc(row)}</text>' for i, row in enumerate(art) if row]
    svg += ["</g>", f'<g fill="{theme["fg"]}">']
    svg += [f'<text x="{INFO_X}" y="{30 + i * INFO_LH}" xml:space="preserve">{line}</text>' for i, line in enumerate(info) if line]
    svg += ["</g>", "</svg>"]
    return "\n".join(svg) + "\n"


def main():
    if "--ascii" in sys.argv:
        make_ascii()
    art = (ROOT / "ascii.txt").read_text(encoding="utf-8").split("\n")
    info = info_lines(fetch_stats())
    for name, theme in THEMES.items():
        (ROOT / name).write_text(render(theme, art, info), encoding="utf-8")
    print(f"ok: {WIDTH}x{HEIGHT}px, {len(info)} linhas")


if __name__ == "__main__":
    main()
