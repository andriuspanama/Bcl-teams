"""Sugeneruoja index.html iš data.json. Galima paleisti atskirai: python build_site.py"""
import json, pathlib
from html import escape as e

CSS = """
body{font-family:system-ui,sans-serif;margin:0;background:#fafafa;color:#222}
header{display:flex;align-items:center;gap:12px;padding:16px;background:#fff;border-bottom:1px solid #ddd}
header img{height:44px} h1{font-size:20px;margin:0} small{color:#777}
main{max-width:860px;margin:0 auto;padding:12px}
h2{display:flex;align-items:center;gap:8px;font-size:16px;margin:22px 0 6px}
h2 img{height:26px}
.row{display:flex;align-items:center;gap:10px;background:#fff;border:1px solid #e3e3e3;
 border-radius:6px;padding:8px 10px;margin-bottom:4px;flex-wrap:wrap}
.row img{height:26px;width:26px;object-fit:contain}
.name{flex:1;min-width:140px;font-weight:600}
.pos{width:34px;font-weight:700;text-align:center}
.rec{width:56px;color:#555}
.f{display:inline-block;width:20px;height:20px;line-height:20px;text-align:center;
 border-radius:3px;color:#fff;font-size:11px;font-weight:700;margin-right:2px}
.W{background:#2e9e4f}.L{background:#d33b3b}
.next{font-size:12px;color:#666;width:100%}
.note{color:#b36b00;font-size:12px}
"""


def row(t):
    img = f'<img src="{e(t["logo"])}" alt="">' if t.get("logo") else "<span></span>"
    form = "".join(
        f'<span class="f {r["wl"]}" title="{e(r["opponent"])} {e(r["score"])}">{r["wl"]}</span>'
        for r in t["last5"])
    nxt = ""
    if t.get("next"):
        nxt = f'<div class="next">Kitos rungtynės: {e(t["next"]["date"])} prieš {e(t["next"]["opponent"])}</div>'
    note = f'<span class="note">{e(t["note"])}</span>' if t.get("note") else ""
    pos = t["rank"] if t.get("rank") else "-"
    return (f'<div class="row">{img}<span class="name">{e(t["name"])}</span>'
            f'<span class="pos">{pos}</span><span class="rec">{e(t["record"])}</span>'
            f'<span>{form}</span>{note}{nxt}</div>')


def build(path="."):
    p = pathlib.Path(path)
    d = json.loads((p / "data.json").read_text(encoding="utf-8"))
    title = d.get("title", "Komandos savo lygose")
    groups = {}
    for t in d["teams"]:
        groups.setdefault(t.get("league") or "Lyga nenustatyta", []).append(t)
    body = []
    for league in sorted(groups):
        ts = sorted(groups[league], key=lambda t: (t["rank"] is None, t["rank"] or 0))
        logo = next((t["league_logo"] for t in ts if t.get("league_logo")), "")
        lg = f'<img src="{e(logo)}" alt="">' if logo else ""
        body.append(f"<h2>{lg}{e(league)}</h2>" + "".join(row(t) for t in ts))
    logo = f'<img src="{e(d["comp_logo"])}" alt="">' if d.get("comp_logo") else ""
    html = (f'<!doctype html><html lang="lt"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(title)}</title><style>{CSS}</style></head><body>'
            f'<header>{logo}<div><h1>{e(title)}: komandos savo lygose</h1>'
            f'<small>Atnaujinta {e(d["updated"])} · duomenys: Flashscore</small></div></header>'
            f'<main>{"".join(body)}</main></body></html>')
    (p / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    build()
