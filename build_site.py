"""Sugeneruoja tamsų interaktyvų dashboard (index.html) iš data.json.
Veikia ir Eurocup (eurocup_logo), ir BCL (comp_logo) duomenims.
Paleidimas atskirai: python build_site.py   (arba build("site") / build("."))"""

import json
import pathlib
from html import escape as e

CSS = r"""
:root{
  --bg:#07111f;--bg2:#0b1728;--card:#101f33;--card2:#14263d;
  --border:rgba(255,255,255,.09);--text:#f4f7fb;--muted:#8fa2b8;
  --accent:#35d07f;--accent2:#55a8ff;--danger:#ff5f6d;--warning:#ffc857;
  --shadow:0 16px 40px rgba(0,0,0,.22);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  background:radial-gradient(circle at top right,rgba(53,208,127,.08),transparent 30%),
  radial-gradient(circle at top left,rgba(85,168,255,.08),transparent 30%),var(--bg);
  color:var(--text);min-height:100vh}
body.lock{overflow:hidden}
button,input,select{font:inherit}
button{cursor:pointer}
.topbar{position:sticky;top:0;z-index:50;backdrop-filter:blur(18px);background:rgba(7,17,31,.82);border-bottom:1px solid var(--border)}
.topbar-inner{max-width:1200px;margin:auto;padding:14px 18px;display:flex;align-items:center;justify-content:space-between;gap:16px}
.brand{display:flex;align-items:center;gap:12px;min-width:0}
.brand-logo{width:46px;height:46px;object-fit:contain;border-radius:12px;background:rgba(255,255,255,.05);padding:5px}
.brand-title{font-size:18px;font-weight:800;line-height:1.1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.brand-subtitle{color:var(--muted);font-size:12px;margin-top:3px}
.updated{color:var(--muted);font-size:11px;white-space:nowrap}
main{max-width:1200px;margin:auto;padding:22px 18px 50px}
.hero{display:grid;grid-template-columns:1.5fr 1fr;gap:16px;margin-bottom:18px}
.hero-main,.hero-hot{background:linear-gradient(135deg,rgba(255,255,255,.06),rgba(255,255,255,.015));
  border:1px solid var(--border);border-radius:22px;padding:24px;box-shadow:var(--shadow)}
.hero-main{position:relative;overflow:hidden}
.hero-main:after{content:"";position:absolute;width:230px;height:230px;right:-80px;top:-100px;background:rgba(53,208,127,.10);border-radius:50%;filter:blur(5px)}
.eyebrow{color:var(--accent);text-transform:uppercase;font-size:11px;font-weight:800;letter-spacing:.12em}
.hero h1{font-size:34px;line-height:1.05;margin:8px 0 10px;max-width:650px}
.hero p{margin:0;color:var(--muted);line-height:1.5;max-width:650px}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin-top:20px;position:relative;z-index:1}
.stat{background:rgba(255,255,255,.045);border:1px solid var(--border);border-radius:14px;padding:10px 14px;min-width:100px}
.stat-number{font-size:21px;font-weight:850}
.stat-label{color:var(--muted);font-size:11px;margin-top:2px}
.hero-hot{display:flex;flex-direction:column;justify-content:center}
.hot-title{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.1em;font-weight:800;margin-bottom:12px}
.hot-team{display:flex;align-items:center;gap:12px;cursor:pointer}
.hot-team img,.hot-ph{width:54px;height:54px;object-fit:contain;border-radius:14px;background:rgba(255,255,255,.06);padding:5px;flex:none}
.hot-name{font-size:19px;font-weight:800}
.hot-league{color:var(--muted);font-size:12px;margin-top:2px}
.hot-form{display:flex;gap:4px;margin-top:7px}
.controls{display:grid;grid-template-columns:1fr auto auto;gap:10px;margin-bottom:14px}
.search{width:100%;background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:14px;padding:13px 15px;outline:none}
.search:focus{border-color:rgba(53,208,127,.55);box-shadow:0 0 0 3px rgba(53,208,127,.08)}
.select{background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:14px;padding:0 13px;min-width:155px;outline:none}
.favorite-toggle{border:1px solid var(--border);background:var(--card);color:var(--text);border-radius:14px;padding:0 16px;font-weight:700}
.favorite-toggle.active{border-color:rgba(255,200,87,.35);color:var(--warning)}
.filters{display:flex;gap:7px;overflow-x:auto;padding-bottom:5px;margin-bottom:18px;scrollbar-width:none}
.filters::-webkit-scrollbar{display:none}
.filter{flex:0 0 auto;border:1px solid var(--border);background:rgba(255,255,255,.035);color:var(--muted);padding:8px 12px;border-radius:999px;font-size:12px;font-weight:700}
.filter.active{background:rgba(53,208,127,.13);border-color:rgba(53,208,127,.35);color:var(--accent)}
.league{margin-bottom:24px}
.league-header{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:20px 0 9px}
.league-title{display:flex;align-items:center;gap:10px;min-width:0}
.league-title img{width:32px;height:32px;object-fit:contain;border-radius:9px;background:rgba(255,255,255,.05);padding:3px}
.league-name{font-size:17px;font-weight:850}
.league-count{color:var(--muted);font-size:11px}
.teams{display:grid;gap:7px}
.team{position:relative;display:grid;grid-template-columns:42px minmax(150px,1fr) 46px 76px 100px;align-items:center;gap:10px;
  background:linear-gradient(135deg,rgba(255,255,255,.045),rgba(255,255,255,.02));border:1px solid var(--border);border-radius:15px;
  padding:9px 34px 9px 11px;transition:.18s ease;cursor:pointer}
.team:hover,.team:focus-visible{transform:translateY(-1px);border-color:rgba(255,255,255,.18);background:var(--card2);outline:none}
.team-logo{width:38px;height:38px;object-fit:contain;border-radius:10px;background:rgba(255,255,255,.05);padding:4px}
.team-name-wrap{min-width:0}
.team-name{font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.team-note{color:var(--warning);font-size:10px;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rank{font-size:16px;font-weight:900;text-align:center}
.record{color:var(--muted);font-size:12px;text-align:center}
.form{display:flex;justify-content:flex-end;gap:3px}
.f{width:20px;height:20px;border-radius:6px;display:inline-flex;align-items:center;justify-content:center;font-size:10px;font-weight:900;color:#fff}
.W{background:var(--accent);color:#062315}
.L{background:var(--danger)}
.favorite{position:absolute;right:7px;top:6px;width:24px;height:24px;border:0;background:transparent;color:#53657b;font-size:17px;padding:0;z-index:2}
.favorite:hover,.favorite.active{color:var(--warning)}
.no-results{padding:35px;text-align:center;color:var(--muted);background:var(--card);border:1px solid var(--border);border-radius:16px}
.footer{text-align:center;color:var(--muted);font-size:11px;padding:20px 0 0}
.modal-backdrop{display:none;position:fixed;inset:0;z-index:100;background:rgba(0,0,0,.7);backdrop-filter:blur(7px);padding:18px;align-items:center;justify-content:center}
.modal-backdrop.open{display:flex}
.modal{width:min(620px,100%);max-height:90vh;overflow:auto;background:#0c1a2c;border:1px solid var(--border);border-radius:24px;box-shadow:0 30px 80px rgba(0,0,0,.5);animation:pop .18s ease}
@keyframes pop{from{opacity:0;transform:translateY(10px) scale(.98)}to{opacity:1;transform:none}}
.modal-head{padding:20px;display:flex;align-items:center;justify-content:space-between;gap:14px;border-bottom:1px solid var(--border)}
.modal-team{display:flex;align-items:center;gap:14px;min-width:0}
.modal-team img,.modal-ph{width:58px;height:58px;object-fit:contain;border-radius:15px;background:rgba(255,255,255,.06);padding:6px;flex:none}
.modal-name{font-size:21px;font-weight:850;line-height:1.1}
.modal-league{color:var(--muted);font-size:12px;margin-top:4px}
.close{width:38px;height:38px;border-radius:12px;border:1px solid var(--border);background:rgba(255,255,255,.05);color:var(--text);font-size:18px;flex:none}
.close:hover{background:rgba(255,255,255,.1)}
.modal-body{padding:20px}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:18px}
.kpi{background:rgba(255,255,255,.045);border:1px solid var(--border);border-radius:14px;padding:12px;text-align:center}
.kpi b{display:block;font-size:22px;font-weight:900}
.kpi span{color:var(--muted);font-size:11px}
.section-title{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.1em;font-weight:800;margin:16px 0 8px}
.next-card{background:linear-gradient(135deg,rgba(85,168,255,.12),rgba(85,168,255,.03));border:1px solid rgba(85,168,255,.22);border-radius:14px;padding:13px 15px}
.next-card b{display:block;font-size:15px}
.next-card span{color:var(--muted);font-size:12px}
.game{display:grid;grid-template-columns:24px 1fr auto;gap:10px;align-items:center;padding:9px 0;border-bottom:1px solid var(--border)}
.game:last-child{border-bottom:0}
.game .f{width:24px;height:24px}
.game-opp{font-weight:700}
.game-venue{color:var(--muted);font-size:11px;margin-top:1px}
.game-score{font-weight:850;font-variant-numeric:tabular-nums}
.modal-note{margin-top:14px;color:var(--warning);font-size:12px}
.muted{color:var(--muted)}
@media(max-width:820px){
  .hero{grid-template-columns:1fr}
  .hero h1{font-size:27px}
  .controls{grid-template-columns:1fr 1fr}
  .search{grid-column:1/-1}
  .select{min-height:44px}
  .favorite-toggle{min-height:44px}
  .updated{display:none}
}
@media(max-width:560px){
  main{padding:16px 12px 40px}
  .team{grid-template-columns:36px minmax(0,1fr) 34px 52px auto;gap:8px;padding:9px 30px 9px 9px}
  .team-logo{width:34px;height:34px}
  .f{width:17px;height:17px;font-size:9px;border-radius:5px}
  .form{gap:2px}
  .kpis{gap:7px}
}
"""

BODY = r"""
<header class="topbar"><div class="topbar-inner">
  <div class="brand">__LOGO__<div style="min-width:0"><div class="brand-title">__TITLE__</div>
  <div class="brand-subtitle">Komandos nacionaliniuose čempionatuose</div></div></div>
  <div class="updated">Atnaujinta __UPDATED__</div>
</div></header>
<main>
  <section class="hero">
    <div class="hero-main">
      <div class="eyebrow">Sezono apžvalga</div>
      <h1>Kaip sekasi komandoms savo lygose</h1>
      <p>Vieta lentelėje, balansas, paskutinių rungtynių forma ir artimiausios rungtynės. Paspausk komandą, kad pamatytum daugiau.</p>
      <div class="stats" id="stats"></div>
    </div>
    <div class="hero-hot"><div class="hot-title">Geriausia forma</div><div id="hot"></div></div>
  </section>
  <div class="controls">
    <input class="search" id="q" type="search" placeholder="Ieškoti komandos ar lygos…" aria-label="Paieška">
    <select class="select" id="sort" aria-label="Rikiavimas">
      <option value="rank">Pagal vietą lygoje</option>
      <option value="name">Pagal pavadinimą</option>
      <option value="form">Pagal formą</option>
    </select>
    <button class="favorite-toggle" id="favOnly">★ Mėgstamos</button>
  </div>
  <div class="filters" id="filters"></div>
  <div id="list"></div>
  <div class="footer">Duomenys: Flashscore · atnaujinta __UPDATED__</div>
</main>
<div class="modal-backdrop" id="modal" aria-hidden="true">
  <div class="modal" role="dialog" aria-modal="true" id="modalBox"></div>
</div>
"""

JS = r"""
const D=__DATA__;
const T=(D.teams||[]).map(t=>({...t,last5:t.last5||[],league:t.league||"Lyga nenustatyta"}));
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const LS="dash:"+location.pathname;
const S={q:"",league:"all",sort:"rank",favOnly:false,fav:[]};
try{S.fav=JSON.parse(localStorage.getItem(LS)||"[]")}catch(e){}
const saveFav=()=>{try{localStorage.setItem(LS,JSON.stringify(S.fav))}catch(e){}};
const wl=t=>{const m=(t.record||"").match(/(\d+)-(\d+)/);return m?[+m[1],+m[2]]:[0,0]};
const formW=t=>t.last5.filter(r=>r.wl==="W").length;
const byRank=(a,b)=>(a.rank==null)-(b.rank==null)||(a.rank||0)-(b.rank||0)||a.name.localeCompare(b.name);
const sorters={rank:byRank,name:(a,b)=>a.name.localeCompare(b.name),
  form:(a,b)=>formW(b)-formW(a)||byRank(a,b)};
const logo=(t,cls,ph)=>t.logo?`<img class="${cls}" src="${esc(t.logo)}" alt="" loading="lazy">`:`<span class="${ph}"></span>`;
const formHTML=t=>t.last5.map(r=>`<span class="f ${r.wl}" title="${esc(r.opponent)} ${esc(r.score)}">${r.wl}</span>`).join("");

function renderStats(){
  const leagues=new Set(T.filter(t=>t.league!=="Lyga nenustatyta").map(t=>t.league));
  let w=0,l=0;T.forEach(t=>{const [a,b]=wl(t);w+=a;l+=b});
  const pct=w+l?Math.round(100*w/(w+l))+"%":"–";
  const items=[[T.length,"Komandų"],[leagues.size,"Lygų"],[w+l,"Sužaista rungtynių"],[pct,"Pergalių dalis"]];
  $("#stats").innerHTML=items.map(([n,k])=>`<div class="stat"><div class="stat-number">${n}</div><div class="stat-label">${k}</div></div>`).join("");
}
function renderHot(){
  const c=T.filter(t=>t.last5.length).sort((a,b)=>formW(b)-formW(a)||byRank(a,b))[0];
  $("#hot").innerHTML=c?`<div class="hot-team" data-open="${esc(c.name)}">${logo(c,"","hot-ph")}
    <div><div class="hot-name">${esc(c.name)}</div><div class="hot-league">${esc(c.league)}${c.rank?` · ${c.rank} vieta`:""}</div>
    <div class="hot-form">${formHTML(c)}</div></div></div>`
    :`<div class="muted">Sezonas dar prasideda: rungtynių duomenų kol kas nėra.</div>`;
}
function renderFilters(){
  const ls=[...new Set(T.map(t=>t.league))].sort((a,b)=>a.localeCompare(b));
  $("#filters").innerHTML=[["all","Visos"],...ls.map(l=>[l,l])].map(([v,n])=>
    `<button class="filter${S.league===v?" active":""}" data-league="${esc(v)}">${esc(n)}</button>`).join("");
}
function teamHTML(t){
  const f=S.fav.includes(t.name);
  return `<div class="team" data-open="${esc(t.name)}" tabindex="0" role="button">
    ${logo(t,"team-logo","team-logo")}
    <div class="team-name-wrap"><div class="team-name">${esc(t.name)}</div>${t.note?`<div class="team-note">${esc(t.note)}</div>`:""}</div>
    <div class="rank">${t.rank==null?"–":t.rank}</div><div class="record">${esc(t.record)}</div><div class="form">${formHTML(t)}</div>
    <button class="favorite${f?" active":""}" data-fav="${esc(t.name)}" aria-label="Mėgstama">★</button></div>`;
}
function renderList(){
  const q=S.q.toLowerCase();
  const ts=T.filter(t=>(S.league==="all"||t.league===S.league)&&(!S.favOnly||S.fav.includes(t.name))&&
    (!q||(t.name+" "+t.league).toLowerCase().includes(q)));
  const m={};ts.forEach(t=>(m[t.league]=m[t.league]||[]).push(t));
  const h=Object.keys(m).sort((a,b)=>a.localeCompare(b)).map(l=>{
    const arr=m[l].sort(sorters[S.sort]),lg=(arr.find(t=>t.league_logo)||{}).league_logo;
    return `<section class="league"><div class="league-header"><div class="league-title">${lg?`<img src="${esc(lg)}" alt="">`:""}
      <div class="league-name">${esc(l)}</div></div><div class="league-count">${arr.length} kom.</div></div>
      <div class="teams">${arr.map(teamHTML).join("")}</div></section>`}).join("");
  $("#list").innerHTML=h||`<div class="no-results">Nieko nerasta</div>`;
}
function openModal(name){
  const t=T.find(x=>x.name===name);if(!t)return;
  const [w,l]=wl(t);
  const games=t.last5.length?t.last5.map(r=>`<div class="game"><span class="f ${r.wl}">${r.wl}</span>
    <div><div class="game-opp">${esc(r.opponent)}</div><div class="game-venue">${r.venue==="H"?"Namie":"Išvykoje"}</div></div>
    <div class="game-score">${esc(r.score)}</div></div>`).join(""):`<div class="muted">Šį sezoną rungtynių dar nėra.</div>`;
  const nx=t.next?`<div class="next-card"><b>prieš ${esc(t.next.opponent)}</b><span>${esc(t.next.date)}</span></div>`:`<div class="muted">Kitų rungtynių duomenų nėra.</div>`;
  $("#modalBox").innerHTML=`<div class="modal-head"><div class="modal-team">${logo(t,"","modal-ph")}
    <div><div class="modal-name">${esc(t.name)}</div><div class="modal-league">${esc(t.league)}</div></div></div>
    <button class="close" data-close aria-label="Uždaryti">✕</button></div>
    <div class="modal-body"><div class="kpis"><div class="kpi"><b>${t.rank==null?"–":t.rank}</b><span>Vieta</span></div>
    <div class="kpi"><b>${w}-${l}</b><span>Balansas</span></div><div class="kpi"><b>${formW(t)}/${t.last5.length}</b><span>Pergalės formoje</span></div></div>
    <div class="section-title">Kitos rungtynės</div>${nx}
    <div class="section-title">Paskutinės rungtynės</div>${games}
    ${t.note?`<div class="modal-note">${esc(t.note)}</div>`:""}</div>`;
  $("#modal").classList.add("open");$("#modal").setAttribute("aria-hidden","false");document.body.classList.add("lock");
}
function closeModal(){$("#modal").classList.remove("open");$("#modal").setAttribute("aria-hidden","true");document.body.classList.remove("lock")}

document.addEventListener("click",ev=>{
  const f=ev.target.closest("[data-fav]");
  if(f){ev.stopPropagation();const n=f.dataset.fav;
    S.fav=S.fav.includes(n)?S.fav.filter(x=>x!==n):[...S.fav,n];saveFav();renderList();return}
  const fl=ev.target.closest("[data-league]");
  if(fl){S.league=fl.dataset.league;renderFilters();renderList();return}
  if(ev.target.closest("#favOnly")){S.favOnly=!S.favOnly;$("#favOnly").classList.toggle("active",S.favOnly);renderList();return}
  if(ev.target.closest("[data-close]")||ev.target.id==="modal"){closeModal();return}
  const o=ev.target.closest("[data-open]");if(o)openModal(o.dataset.open);
});
document.addEventListener("keydown",ev=>{
  if(ev.key==="Escape")closeModal();
  if((ev.key==="Enter"||ev.key===" ")&&ev.target.classList&&ev.target.classList.contains("team")){ev.preventDefault();openModal(ev.target.dataset.open)}
});
$("#q").addEventListener("input",ev=>{S.q=ev.target.value.trim();renderList()});
$("#sort").addEventListener("change",ev=>{S.sort=ev.target.value;renderList()});
renderStats();renderHot();renderFilters();renderList();
"""


def build(path="site"):
    p = pathlib.Path(path)
    d = json.loads((p / "data.json").read_text(encoding="utf-8"))
    title = d.get("title") or "EuroCup 2026–2027"
    logo_url = d.get("eurocup_logo") or d.get("comp_logo") or ""
    logo = f'<img class="brand-logo" src="{e(logo_url)}" alt="">' if logo_url else ""
    data_json = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
    body = (BODY.replace("__LOGO__", logo)
                .replace("__TITLE__", e(title))
                .replace("__UPDATED__", e(d.get("updated", ""))))
    html = ('<!doctype html><html lang="lt"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="theme-color" content="#07111f">'
            f'<title>{e(title)} · komandos savo lygose</title><style>{CSS}</style></head><body>'
            f'{body}<script>{JS.replace("__DATA__", data_json)}</script></body></html>')
    (p / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    build()
