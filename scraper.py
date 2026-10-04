"""FIBA Champions League komandų sekimas nacionaliniuose čempionatuose (Flashscore).
Papildyta: visų sezono rungtynių taškai (games), ABA / Lat-EST lygos, Sabah Baku iš Sofascore.
Paleidimas: python scraper.py
"""
import json, re, time, hashlib, pathlib, datetime
from collections import Counter
from playwright.sync_api import sync_playwright
from build_site import build

BASE = "https://www.flashscore.com"
COMP = BASE + "/basketball/europe/champions-league/"
TITLE = "FIBA Champions League 2026-2027"
OUT = pathlib.Path(".")
LOGOS = OUT / "logos"
DELAY = 2.5

LEAGUE_OVERRIDES = {}
INTL = {"europe", "world"}
SKIP_SLUG = ("cup", "friendl", "copa", "coupe", "pokal", "coppa", "beker")

# Jungtinės lygos atpažįstamos pagal Flashscore nuorodos pavadinimą (europe/<slug>).
# Jei kuri nors neatpažįstama, žurnale prie komandos ("lygos=[...]") matysi tikrą nuorodą, ir pataisyk joint_name().
def joint_name(href):
    parts = (href or "").strip("/").split("/")
    if len(parts) < 3 or parts[1] != "europe":
        return None
    s = parts[2]
    if s.endswith("-2") or "women" in s:
        return None
    if s.startswith(("aba-league", "adriatic")):
        return "Adrijos lyga"
    if "bnxt" in s:
        return "BNXT lyga"
    if any(k in s for k in ("latvian", "estonian", "baltic")):
        return "Lat-EST lyga"
    return None


# Sabah Baku: Sofascore (unique-tournament ID iš tavo nuorodos)
SOFA_ID = 24261
SOFA_TEAM = "sabah"

JS_MATCHES = r"""()=>{
 const out=[];let cur=null;
 const re=/^\/basketball\/[a-z0-9-]+\/[a-z0-9-]+\/?$/;
 document.querySelectorAll('.event__match, a[href^="/basketball/"]').forEach(el=>{
  if(el.classList.contains('event__match')){
   const q=s=>{const e=el.querySelector(s);return e?e.innerText.trim():''};
   out.push({comp:cur,home:q('.event__homeParticipant'),away:q('.event__awayParticipant'),
     hs:q('.event__score--home'),as:q('.event__score--away'),time:q('.event__time')||((el.innerText||'').match(/\b\d{1,2}\.\d{1,2}\.(?:\d{2,4})?(?:\s*\d{1,2}:\d{2})?/)||[''])[0]});
  } else if(!el.closest('.event__match')){
   const h=el.getAttribute('href')||'';
   if(!re.test(h)) return;
   const t=(el.innerText||'').replace(/\s+/g,' ').trim();
   if(!t && cur && cur.href===h) return;
   cur={href:h,name:t};
  }});
 return out;}"""

JS_STANDINGS = """()=>[...document.querySelectorAll('.ui-table__row')].map(r=>{
 const a=r.querySelector('a.tableCellParticipant__name');
 const img=r.querySelector('img');
 return {name:a?a.innerText.trim():'',href:a?a.getAttribute('href'):'',
         rank:(r.querySelector('.tableCellRank')||{}).innerText||'',
         logo:img?img.src:'',
         cells:[...r.querySelectorAll('.table__cell--value')].map(c=>c.innerText.trim())};
}).filter(x=>x.name)"""

JS_LINKS = r"""(c)=>{const re=/^\/basketball\/[a-z0-9-]+\/[a-z0-9-]+\/?$/;
 return [...new Set([...document.querySelectorAll('a[href^="/basketball/'+c+'/"]')]
  .map(a=>a.getAttribute('href')).filter(h=>re.test(h)))];}"""


def nh(h):
    return "/" + h.split("?")[0].strip("/") + "/"


def open_page(page, url):
    time.sleep(DELAY)
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    try:
        page.click("#onetrust-accept-btn-handler", timeout=2500)
    except Exception:
        pass
    page.wait_for_timeout(1500)


def save_logo(page, url):
    if not url or url.startswith("data:"):
        return ""
    ext = pathlib.Path(url.split("?")[0]).suffix or ".png"
    name = hashlib.md5(url.encode()).hexdigest()[:12] + ext
    path = LOGOS / name
    if not path.exists():
        try:
            path.write_bytes(page.request.get(url).body())
        except Exception:
            return ""
    return "logos/" + name


def page_logo(page):
    for sel in ["img.heading__logo", ".heading img", "img[class*=logo]"]:
        el = page.query_selector(sel)
        if el:
            return el.get_attribute("src") or ""
    return ""


def get_matches(page, url):
    open_page(page, url)
    try:
        page.wait_for_selector(".event__match", timeout=8000)
    except Exception:
        return []
    return page.evaluate(JS_MATCHES)


def tid(href):
    return href.split("?")[0].strip("/").split("/")[-1]


def same(a, b):
    a, b = a.lower().strip(), b.lower().strip()
    return bool(a and b) and (a == b or a in b or b in a)


def league_ok(c):
    if not c or not c.get("href"):
        return False
    if joint_name(c["href"]):
        return True
    parts = c["href"].strip("/").split("/")
    return parts[1] not in INTL and not any(s in parts[2] for s in SKIP_SLUG)


def season_ok(tstr):
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})?", tstr or "")
    if not m:
        return False
    d, mo = int(m.group(1)), int(m.group(2))
    today = datetime.date.today()
    ystart = today.year if today.month >= 8 else today.year - 1
    if m.group(3):
        y = int(m.group(3))
        y = y + 2000 if y < 100 else y
    else:
        y = ystart if mo >= 8 else ystart + 1
    try:
        dt = datetime.date(y, mo, d)
    except ValueError:
        return False
    return datetime.date(ystart, 8, 1) <= dt <= today


def clean_name(n):
    return re.sub(r"\s*[-–]\s*(play[- ]?offs?|regular season|relegation.*|round.*|group.*|final.*)$",
                  "", n.strip(), flags=re.I)


def team_result(m, team):
    h, a_, t = m["home"].lower(), m["away"].lower(), team.lower()
    mine_home = h == t or (a_ != t and same(h, t))
    try:
        a, b = int(m["hs"]), int(m["as"])
    except ValueError:
        return None
    me, opp = (a, b) if mine_home else (b, a)
    return {"wl": "W" if me > opp else "L", "score": f"{a}:{b}",
            "opponent": m["away"] if mine_home else m["home"],
            "venue": "H" if mine_home else "A",
            "date": m["time"], "pf": me, "pa": opp}


# ---------- Sabah Baku (Sofascore) ----------
def api_json(page, url):
    time.sleep(DELAY)
    r = page.goto(url, wait_until="domcontentloaded", timeout=45000)
    if not r or r.status != 200:
        raise RuntimeError(f"HTTP {r.status if r else '?'}")
    return json.loads(page.inner_text("body"))


def fill_sabah(page, entry):
    api = f"https://api.sofascore.com/api/v1/unique-tournament/{SOFA_ID}"
    games, rank = [], None
    try:
        season = api_json(page, api + "/seasons")["seasons"][0]
        sid = season["id"]
        entry["note"] = f"Sofascore sezonas: {season.get('year', '?')}"
        found = []
        for pg in range(10):
            d = api_json(page, f"{api}/season/{sid}/events/last/{pg}")
            for e in d.get("events", []):
                hn, an = e["homeTeam"]["name"], e["awayTeam"]["name"]
                if SOFA_TEAM in (hn + an).lower() and e.get("status", {}).get("type") == "finished":
                    found.append(e)
            if not d.get("hasNextPage"):
                break
        found.sort(key=lambda e: e["startTimestamp"], reverse=True)
        for e in found:
            home = SOFA_TEAM in e["homeTeam"]["name"].lower()
            a, b = e["homeScore"]["current"], e["awayScore"]["current"]
            me, opp = (a, b) if home else (b, a)
            dt = datetime.datetime.fromtimestamp(e["startTimestamp"])
            games.append({"wl": "W" if me > opp else "L", "score": f"{a}:{b}",
                          "opponent": e["awayTeam"]["name"] if home else e["homeTeam"]["name"],
                          "venue": "H" if home else "A", "date": dt.strftime("%d.%m."),
                          "pf": me, "pa": opp})
        try:
            st = api_json(page, f"{api}/season/{sid}/standings/total")
            for row in st["standings"][0]["rows"]:
                if SOFA_TEAM in row["team"]["name"].lower():
                    rank = row["position"]
        except Exception:
            pass
    except Exception as ex:
        entry["note"] = f"Sofascore nepavyko ({ex}); naudojamas manual/sabah.json"
    manual = pathlib.Path("manual/sabah.json")
    if not games and manual.exists():
        for g in json.loads(manual.read_text(encoding="utf-8")).get("games", []):
            games.append({"wl": "W" if g["pf"] > g["pa"] else "L", "score": f"{g['pf']}:{g['pa']}",
                          "opponent": g.get("opponent", ""), "venue": g.get("venue", ""),
                          "date": g.get("date", ""), "pf": g["pf"], "pa": g["pa"]})
    w = sum(1 for g in games if g["wl"] == "W")
    entry.update(league="Azerbaidžano lyga", rank=rank, games=games, last5=games[:5],
                 record=f"{w}-{len(games) - w}" if games else "")


def main():
    LOGOS.mkdir(exist_ok=True)
    league_cache, country_cache = {}, {}
    data = {"title": TITLE, "updated": time.strftime("%Y-%m-%d %H:%M"), "comp_logo": "", "teams": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(locale="en-US").new_page()

        open_page(page, COMP + "standings/")
        data["comp_logo"] = save_logo(page, page_logo(page))
        try:
            page.wait_for_selector(".ui-table__row", timeout=10000)
        except Exception:
            pass
        seen, teams = set(), []
        for t in page.evaluate(JS_STANDINGS):
            if t["href"] not in seen:
                seen.add(t["href"]); teams.append(t)
        print(f"Champions League komandų rasta: {len(teams)}")

        for t in teams:
            entry = {"name": t["name"], "logo": save_logo(page, t["logo"]),
                     "league": None, "league_logo": "", "rank": None,
                     "record": "", "last5": [], "games": [], "next": None, "note": ""}
            try:
                if SOFA_TEAM in t["name"].lower():
                    fill_sabah(page, entry)
                    print(entry["name"], "->", entry["league"], entry["rank"], entry["note"])
                    data["teams"].append(entry)
                    continue

                url = BASE + t["href"]
                res_m = get_matches(page, url + "results/")
                fx_m = get_matches(page, url + "fixtures/")
                allm = res_m + fx_m
                found = sorted({m["comp"]["href"] for m in allm if m["comp"]})
                print(f"  [diag] {t['name']}: rezultatų={len(res_m)}, būsimų={len(fx_m)}, lygos={found[:4]}")

                dom = [m for m in allm if league_ok(m["comp"])]
                pool = [m for m in dom if season_ok(m["time"])] or dom
                league_href = LEAGUE_OVERRIDES.get(t["name"])
                league_name = league_href.strip("/").split("/")[-1].upper() if league_href else ""
                if not league_href and pool:
                    joint = [m for m in pool if m["comp"] and joint_name(m["comp"]["href"])]
                    if joint:  # komanda žaidžia jungtinėje lygoje -> ji ir rodoma
                        league_href = joint[0]["comp"]["href"]
                        league_name = joint_name(league_href)
                    else:
                        league_href = Counter(m["comp"]["href"] for m in pool).most_common(1)[0][0]
                        names = [m["comp"]["name"] for m in pool
                                 if m["comp"]["href"] == league_href and m["comp"]["name"]]
                        league_name = clean_name(names[0]) if names else league_href.strip("/").split("/")[-1].upper()
                if not league_href:
                    countries = [m["comp"]["href"].strip("/").split("/")[1] for m in allm
                                 if m["comp"] and m["comp"]["href"].strip("/").split("/")[1] not in INTL]
                    if countries:
                        country = Counter(countries).most_common(1)[0][0]
                        if country not in country_cache:
                            open_page(page, f"{BASE}/basketball/{country}/")
                            links = page.evaluate(JS_LINKS, country)
                            country_cache[country] = next((h for h in links if league_ok({"href": h})), "")
                        league_href = country_cache[country]
                        if league_href:
                            league_name = league_href.strip("/").split("/")[-1].replace("-", " ").title()
                if not league_href:
                    entry["league"] = "Nežinoma"
                    data["teams"].append(entry)
                    continue
                entry["league"] = league_name

                res = [team_result(m, t["name"]) for m in res_m
                       if m["comp"] and m["comp"]["href"] == league_href and season_ok(m["time"])]
                entry["games"] = [r for r in res if r]
                entry["last5"] = entry["games"][:5]
                started = bool(entry["games"])

                fx = [m for m in fx_m if m["time"]]
                fx = [m for m in fx if m["comp"] and m["comp"]["href"] == league_href] or fx
                if fx:
                    m = fx[0]
                    home = same(m["home"], t["name"])
                    entry["next"] = {"date": m["time"], "opponent": m["away"] if home else m["home"]}

                if league_href not in league_cache:
                    open_page(page, BASE + league_href.rstrip("/") + "/standings/")
                    logo = save_logo(page, page_logo(page))
                    try:
                        page.wait_for_selector(".ui-table__row", timeout=8000)
                    except Exception:
                        pass
                    league_cache[league_href] = (page.evaluate(JS_STANDINGS), logo)
                rows, entry["league_logo"] = league_cache[league_href]
                row = next((r for r in rows if tid(r["href"]) == tid(t["href"])), None)
                if row:
                    entry["rank"] = int(re.sub(r"\D", "", row["rank"]) or 0) or None
                    c = row["cells"]
                    entry["record"] = f"{c[1]}-{c[2]}" if len(c) > 2 else ""
                else:
                    entry["note"] = ("Komanda lygos lentelėje nerasta" if started
                                     else "Lygos sezonas dar nepradėtas")
            except Exception as e:
                entry["note"] = f"Klaida: {type(e).__name__}"
            print(entry["name"], "->", entry["league"], entry["rank"], entry["note"])
            data["teams"].append(entry)

        browser.close()

    (OUT / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    build(str(OUT))
    print("Paruošta: index.html")


if __name__ == "__main__":
    main()
             
