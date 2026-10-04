"""FIBA Champions League komandų sekimas nacionaliniuose čempionatuose (Flashscore).
Pritaikyta iš Eurocup scraper.py. Paleidimas: python scraper.py
Jei Flashscore pakeis struktūrą, taisyk selektorius viršuje.
"""
import json, re, time, hashlib, pathlib, datetime
from collections import Counter
from playwright.sync_api import sync_playwright
from build_site import build

BASE = "https://www.flashscore.com"
COMP = BASE + "/basketball/europe/champions-league/"
TITLE = "FIBA Champions League 2026-2027"
OUT = pathlib.Path(".")          # index.html, data.json ir logos/ rašomi į repo šaknį
LOGOS = OUT / "logos"
DELAY = 2.5

LEAGUE_OVERRIDES = {}
INTL = {"europe", "world"}
SKIP_SLUG = ("cup", "friendl", "copa", "coupe", "pokal", "coppa", "beker")

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
            "venue": "H" if mine_home else "A"}


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
                     "record": "", "last5": [], "next": None, "note": ""}
            try:
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
                    entry["league"] = "Azerbaidžanas (lygos Flashscore nėra)"
                    entry["note"] = ""
                    data["teams"].append(entry)
                    continue
                entry["league"] = league_name

                res = [team_result(m, t["name"]) for m in res_m
                       if m["comp"] and m["comp"]["href"] == league_href and season_ok(m["time"])]
                entry["last5"] = [r for r in res if r][:5]
                started = bool(entry["last5"])

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
