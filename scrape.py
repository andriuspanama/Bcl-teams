import json, re, sys, datetime, urllib.parse
from playwright.sync_api import sync_playwright

BASE = "https://www.flashscore.com"
cfg = json.load(open("teams.json", encoding="utf-8"))
std_cache = {}

def find_team(page, name):
    page.goto(f"{BASE}/search/?q={urllib.parse.quote(name)}", wait_until="domcontentloaded")
    try:
        page.wait_for_selector('a[href*="/team/"]', timeout=15000)
    except Exception:
        return None
    return page.eval_on_selector('a[href*="/team/"]', "e=>e.getAttribute('href')").strip("/")

def rows(page, hdr):
    """Grąžina (data, namai, svečiai, balai) tik iš pageidaujamos lygos antraštės."""
    out, cur = [], ""
    for el in page.query_selector_all('[class*="event__title"], div.event__match'):
        cls = el.get_attribute("class") or ""
        if "event__title" in cls:
            cur = el.inner_text().replace("\n", " ")
        elif hdr.lower() in cur.lower() and "cup" not in cur.lower():
            g = lambda s: (el.query_selector(s).inner_text().strip() if el.query_selector(s) else "")
            out.append((g(".event__time"), g(".event__homeParticipant"), g(".event__awayParticipant"),
                        g(".event__score--home"), g(".event__score--away")))
    return out

def position(page, hdr, team):
    link = None
    if hdr in std_cache:
        return std_cache[hdr].get(team)
    # lygos nuoroda paimama iš antraštės
    for a in page.query_selector_all('[class*="event__title"] a'):
        if hdr.lower() in (a.evaluate("e=>e.closest('[class*=event__title]').innerText") or "").lower().replace("\n", " "):
            link = a.get_attribute("href"); break
    std_cache[hdr] = {}
    if link:
        page.goto(BASE + link.rstrip("/") + "/standings/", wait_until="domcontentloaded")
        try: page.wait_for_selector(".ui-table__row", timeout=15000)
        except Exception: return None
        for r in page.query_selector_all(".ui-table__row"):
            n = r.query_selector(".tableCellParticipant__name"); k = r.query_selector(".tableCellRank")
            if n and k: std_cache[hdr][n.inner_text().strip()] = int(re.sub(r"\D", "", k.inner_text()) or 0)
    return std_cache[hdr].get(team)

def norm(s): return re.sub(r"[^a-z0-9]", "", s.lower())

def run():
    res = {"updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), "competition": cfg["competition"], "leagues": []}
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_page(locale="en-GB")
        for lg in cfg["leagues"]:
            L = {"league": lg["league"], "teams": []}
            for t in lg["teams"]:
                item = {"name": t["name"], "g": t["g"], "logo": None, "pos": None, "rec": None, "form": [], "next": None}
                try:
                    fs = t.get("fs") or find_team(page, t["name"])
                    if fs:
                        item["url"] = f"{BASE}/{fs}/"
                        page.goto(f"{BASE}/{fs}/results/", wait_until="domcontentloaded")
                        page.wait_for_selector("div.event__match", timeout=15000)
                        logo = page.query_selector("img.heading__logo")
                        item["logo"] = logo.get_attribute("src") if logo else None
                        h = page.query_selector("h2.heading__name, .heading__name")
                        me = norm(h.inner_text()) if h else norm(t["name"])
                        w = l = 0
                        for d, home, away, sh, sa in rows(page, lg["hdr"]):
                            if not sh.isdigit(): continue
                            ishome = norm(home) in me or me in norm(home)
                            won = (int(sh) > int(sa)) == ishome
                            w += won; l += (not won)
                            item["form"].append("W" if won else "L")
                        item["form"] = item["form"][:5]
                        item["rec"] = f"{w}-{l}" if (w + l) else None
                        item["pos"] = position(page, lg["hdr"], h.inner_text().strip() if h else t["name"])
                        page.goto(f"{BASE}/{fs}/fixtures/", wait_until="domcontentloaded")
                        page.wait_for_selector("div.event__match", timeout=15000)
                        fx = rows(page, lg["hdr"])
                        if fx:
                            d, home, away, *_ = fx[0]
                            opp = away if norm(home) in me or me in norm(home) else home
                            item["next"] = f"{d} prieš {opp}"
                except Exception as e:
                    print("KLAIDA", t["name"], e, file=sys.stderr)
                L["teams"].append(item)
            res["leagues"].append(L)
        b.close()
    json.dump(res, open("data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

run()
