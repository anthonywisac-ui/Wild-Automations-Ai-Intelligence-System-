"""
Jobs Dashboard — aggregated jobs from every Jobs scraper in one table + a
Job Details side panel. Served at /jobs. Recreates the provided reference
(black + gold Wild Automations) pixel-close, responsive desktop/tablet/mobile.
Real company logos are fetched (Clearbit -> letter avatar fallback), no generic
icons. Plain string (no f-string) so every { } is literal.
"""

JOBS_HTML = r"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>Jobs Scrapers — Wild Automations</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{--bg:#0b0b0c;--panel:#0f0f11;--card:#151517;--card2:#1a1a1e;--line:#222226;
  --text:#f2f1ec;--sec:#84827a;--g:#E2B404;--gb:rgba(226,180,4,.30);--gd:rgba(226,180,4,.08);
  --font:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--font);font-size:14px}
a{color:inherit;text-decoration:none}
.wrap{display:flex;height:100vh;height:100dvh;overflow:hidden}
/* sidebar */
.side{width:186px;min-width:186px;background:#010000;border-right:1px solid var(--line);display:flex;flex-direction:column;flex-shrink:0}
.brand{padding:22px 18px 16px;display:flex;flex-direction:column;align-items:center;gap:9px;border-bottom:1px solid var(--line)}
.brand .l{width:48px;height:48px;border-radius:12px;background:linear-gradient(135deg,#E2B404,#8a6c00);display:grid;place-items:center;font-weight:900;font-size:23px;color:#050505}
.brand .n{font-size:10.5px;font-weight:700;letter-spacing:2.4px;color:#fff}
.nav{padding:12px 10px;display:flex;flex-direction:column;gap:2px;flex:1;overflow-y:auto}
.ni{display:flex;align-items:center;gap:11px;padding:10px 13px;border-radius:10px;color:var(--sec);font-size:13px;font-weight:500;cursor:pointer}
.ni svg{width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:2;opacity:.7}
.ni.on{background:var(--gd);color:#fff;box-shadow:0 0 18px rgba(226,180,4,.08)}
.ni.on svg{stroke:var(--g);opacity:1}
.prof{display:flex;align-items:center;gap:10px;padding:12px 14px 16px;border-top:1px solid var(--line)}
.prof .av{width:30px;height:30px;border-radius:8px;background:linear-gradient(135deg,#E2B404,#7a5800);display:grid;place-items:center;font-size:10px;font-weight:700;color:#050505}
.prof .nm{font-size:12px;font-weight:600}.prof .em{font-size:10px;color:var(--sec)}
/* main */
.main{flex:1;display:flex;flex-direction:column;min-width:0;overflow:hidden}
.hdr{display:flex;align-items:center;gap:14px;padding:16px 24px;border-bottom:1px solid var(--line)}
.hdr .dot{width:8px;height:8px;border-radius:50%;background:#39d353;box-shadow:0 0 9px #39d353}
.hdr h1{margin:0;font-size:22px;font-weight:800;letter-spacing:-.4px}
.hdr .sub{font-size:12px;color:var(--sec);margin-top:2px}
.hdr .pill{margin-left:auto;padding:8px 15px;border:1px solid var(--line);border-radius:9px;font-size:12.5px;color:var(--text);background:var(--card)}
.runbtn{display:inline-flex;align-items:center;gap:8px;padding:10px 18px;border:none;border-radius:9px;font-family:var(--font);
  font-weight:700;font-size:13px;color:#050505;cursor:pointer;background:linear-gradient(135deg,#F5CE3E,#C99A26)}
.runbtn svg{width:12px;height:12px;fill:#050505}
.hdr .last{font-size:11.5px;color:var(--sec)}
.hicon{width:38px;height:38px;border-radius:10px;border:1px solid var(--line);background:none;color:var(--sec);display:grid;place-items:center;cursor:pointer}
.hicon svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.havatar{width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#E2B404,#7a5800);display:grid;place-items:center;font-size:12px;font-weight:700;color:#050505}
/* search + filters */
.searchrow{display:flex;align-items:center;gap:10px;padding:14px 24px 6px;flex-wrap:wrap}
.selbox{display:flex;align-items:center;gap:7px;padding:10px 14px;background:var(--card);border:1px solid var(--line);border-radius:10px;font-size:13px;color:var(--sec);white-space:nowrap}
.searchrow .inp{flex:1;min-width:180px;display:flex;align-items:center;gap:9px;padding:10px 15px;background:var(--card);border:1px solid var(--line);border-radius:10px}
.searchrow .inp input{flex:1;background:none;border:none;color:var(--text);font-size:14px;outline:none;font-family:var(--font)}
.searchbtn{padding:11px 22px;border:1px solid var(--gb);border-radius:10px;background:var(--gd);color:var(--g);font-weight:700;font-size:13px;cursor:pointer;font-family:var(--font)}
.chips2{display:flex;gap:8px;padding:8px 24px 10px;flex-wrap:wrap}
.f2{padding:8px 14px;border:1px solid var(--line);border-radius:9px;background:var(--card);color:var(--sec);font-size:12.5px;cursor:pointer}
.f2.sort{margin-left:auto;color:var(--text)}
/* stats */
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);background:var(--panel)}
.stat{display:flex;align-items:center;gap:16px;padding:16px 24px;border-right:1px solid var(--line)}
.stat .ring{width:44px;height:44px;border-radius:50%;border:1px solid var(--gb);background:rgba(226,180,4,.05);display:grid;place-items:center;flex-shrink:0}
.stat .ring svg{width:18px;height:18px;stroke:var(--g);fill:none;stroke-width:1.6}
.stat .v{font-size:30px;font-weight:800;letter-spacing:-1px;line-height:1}
.stat .k{font-size:9.5px;font-weight:600;color:var(--sec);text-transform:uppercase;letter-spacing:1.3px;margin-top:5px;min-height:2.2em;display:flex;align-items:flex-start}
/* source chips */
.srcbar{display:flex;align-items:center;gap:8px;padding:11px 24px;border-bottom:1px solid var(--line);overflow-x:auto;
  -webkit-mask-image:linear-gradient(to right,#000 94%,transparent);mask-image:linear-gradient(to right,#000 94%,transparent)}
.srcbar::-webkit-scrollbar{display:none}
.srcbar .lbl{font-size:11px;color:var(--sec);white-space:nowrap;margin-right:4px}
.src{display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border:1px solid var(--gb);border-radius:999px;background:var(--gd);color:var(--g);font-size:11.5px;font-weight:600;white-space:nowrap}
.src .ok{width:6px;height:6px;border-radius:50%;background:#39d353}
/* body: table + details */
.body{flex:1;display:flex;min-height:0;overflow:hidden}
.tablewrap{flex:1;overflow-y:auto;min-width:0}
table{width:100%;border-collapse:collapse}
thead th{text-align:left;font-size:11px;font-weight:600;color:var(--sec);text-transform:capitalize;padding:14px 20px;position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);z-index:2}
tbody tr{border-bottom:1px solid var(--line);cursor:pointer;transition:background .12s}
tbody tr:hover{background:rgba(226,180,4,.035)}
tbody tr.sel{background:rgba(226,180,4,.06);box-shadow:inset 3px 0 0 var(--g)}
td{padding:14px 20px;font-size:13.5px;vertical-align:middle}
.team{display:flex;align-items:center;gap:11px}
.logo{width:34px;height:34px;border-radius:9px;object-fit:cover;flex-shrink:0;background:var(--card2);border:1px solid var(--line)}
.logo-fb{width:34px;height:34px;border-radius:9px;flex-shrink:0;display:grid;place-items:center;font-weight:800;font-size:14px;color:#050505}
.team .co{font-weight:600}
.pos .t{font-weight:600}.pos .l{font-size:11.5px;color:var(--sec);margin-top:2px}
.muted{color:var(--sec)}
.star{width:34px;text-align:center;color:var(--sec);font-size:16px}
.star.on{color:var(--g)}
.srctag{font-size:10px;color:var(--sec);border:1px solid var(--line);border-radius:6px;padding:2px 7px;margin-top:4px;display:inline-block}
.vbadge{display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:600;color:#5fd38a;border:1px solid rgba(52,211,120,.3);background:rgba(52,211,120,.1);border-radius:6px;padding:2px 7px;margin-top:4px;margin-left:5px}
.d-verif{margin:16px 0;padding:14px;border:1px solid rgba(52,211,120,.3);background:rgba(52,211,120,.07);border-radius:12px}
.d-verif .h{display:flex;align-items:center;gap:7px;color:#5fd38a;font-weight:700;font-size:13px}
.d-verif .r{margin-top:8px;font-size:12px;color:#cfccc2}
.d-notv{margin:16px 0;padding:12px 14px;border:1px solid var(--line);background:var(--card);border-radius:12px;color:var(--sec);font-size:12.5px}
.d-scores{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}
.d-score{flex:1;min-width:90px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px}
.d-score .v{font-size:17px;font-weight:800;color:var(--g)}
.d-score .k{font-size:9.5px;color:var(--sec);text-transform:uppercase;letter-spacing:.5px;margin-top:2px}
.d-ev{font-size:11.5px;color:var(--sec);line-height:1.5;margin-top:6px}
/* details panel */
.details{width:390px;min-width:390px;border-left:1px solid var(--line);background:var(--panel);display:flex;flex-direction:column;overflow:hidden}
.details.empty{align-items:center;justify-content:center;color:var(--sec);text-align:center;padding:30px}
.d-top{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--line)}
.d-top h2{margin:0;font-size:16px}
.d-close{background:none;border:none;color:var(--sec);font-size:20px;cursor:pointer}
.d-scroll{flex:1;overflow-y:auto;padding:20px}
.d-co{display:flex;align-items:center;gap:11px}
.d-co .nm{font-weight:600}
.d-title{font-size:20px;font-weight:800;margin:14px 0 4px;line-height:1.2}
.d-loc{color:var(--sec);font-size:13px}
.d-meta{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin:16px 0;padding:14px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.d-meta .k{font-size:10px;color:var(--sec);text-transform:uppercase;letter-spacing:.5px}
.d-meta .v{font-size:13px;font-weight:600;margin-top:3px}
.d-h{font-size:14px;font-weight:700;margin:18px 0 8px}
.d-p{font-size:13px;color:#cfccc2;line-height:1.55;margin:0 0 10px}
.d-li{display:flex;gap:9px;font-size:13px;color:#cfccc2;line-height:1.5;margin-bottom:8px}
.d-li .c{color:var(--g);flex-shrink:0}
.d-foot{display:flex;align-items:center;gap:10px;padding:14px 20px;border-top:1px solid var(--line)}
.d-saved{display:flex;align-items:center;gap:6px;color:var(--g);font-size:13px;font-weight:600}
.btn-ghost{margin-left:auto;padding:10px 18px;border:1px solid var(--line);border-radius:9px;background:none;color:var(--text);font-weight:600;cursor:pointer;font-family:var(--font)}
.btn-gold{padding:10px 20px;border:none;border-radius:9px;background:linear-gradient(135deg,#F0C838,#B8860B);color:#050505;font-weight:700;cursor:pointer;font-family:var(--font)}
/* pagination */
.pager{display:flex;align-items:center;gap:10px;padding:14px 24px;border-top:1px solid var(--line);font-size:12.5px;color:var(--sec)}
.pg{width:30px;height:30px;border-radius:8px;border:1px solid var(--line);background:none;color:var(--sec);cursor:pointer;font-family:var(--font)}
.pg.on{border-color:var(--gb);background:var(--gd);color:var(--g)}
.pager .right{margin-left:auto;display:flex;gap:8px;align-items:center}
.spin{display:inline-block;width:20px;height:20px;border:2px solid var(--line);border-top-color:var(--g);border-radius:50%;animation:sp .8s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
.center{display:grid;place-items:center;height:100%;color:var(--sec);gap:12px}
.m-only{display:none}
/* ── responsive ── */
@media(max-width:1100px){.details{width:340px;min-width:340px}}
/* mobile chrome (2nd-image Job Board look) */
.jham,.jbell,.jfilt{display:none;width:40px;height:40px;border-radius:11px;border:1px solid var(--line);background:none;color:var(--sec);align-items:center;justify-content:center;cursor:pointer;flex-shrink:0}
.jham svg,.jbell svg,.jfilt svg{width:19px;height:19px;stroke:currentColor;fill:none;stroke-width:2}
.jcount{display:none;align-items:center;justify-content:space-between;padding:12px 16px 6px;font-size:13px}
.jcount b{font-size:15px}.jcount .sort{color:var(--sec)}
.jscrim{position:fixed;inset:0;background:rgba(3,3,4,.6);backdrop-filter:blur(3px);z-index:180;opacity:0;pointer-events:none;transition:opacity .25s}
body.jnav .jscrim{opacity:1;pointer-events:auto}
.jsheet{position:fixed;left:0;right:0;bottom:0;z-index:220;background:var(--panel);border-top:1px solid var(--gb);border-radius:22px 22px 0 0;padding:8px 18px calc(24px + env(safe-area-inset-bottom));transform:translateY(103%);transition:transform .34s cubic-bezier(.16,1,.3,1);max-height:82vh;overflow-y:auto}
.jsheet.on{transform:translateY(0)}
.jgrip{width:40px;height:4px;border-radius:2px;background:var(--line);margin:6px auto 14px}
.jsheet h3{margin:0 0 14px;font-size:17px}
.jf-field{margin-bottom:12px}
.jf-field label{display:block;font-size:12px;color:var(--sec);margin-bottom:6px}
.jf-field select,.jf-field input{width:100%;min-height:46px;background:var(--card2);border:1px solid var(--line);color:var(--text);border-radius:11px;padding:12px;font-size:15px}
.jf-toggle{display:flex;align-items:center;gap:10px;padding:12px;background:var(--card2);border:1px solid var(--line);border-radius:11px;margin-bottom:10px;cursor:pointer;font-size:14px}
.jf-toggle input{width:18px;height:18px}
.jf-apply{width:100%;min-height:50px;border:none;border-radius:13px;margin-top:6px;font-weight:700;font-size:16px;color:#050505;cursor:pointer;background:linear-gradient(135deg,#F0C838,#B8860B)}
.drawer-extra{display:none;padding:12px 14px;border-top:1px solid var(--line)}
.drawer-extra .runbtn2{width:100%;justify-content:center;margin-bottom:12px;display:flex;align-items:center;gap:8px;padding:12px;border:none;border-radius:11px;font-weight:700;color:#050505;background:linear-gradient(135deg,#F0C838,#B8860B);cursor:pointer;font-family:var(--font)}

@media(max-width:900px){
  .side{position:fixed;top:0;left:0;height:100vh;height:100dvh;width:82%;max-width:300px;z-index:190;transform:translateX(-104%);transition:transform .28s cubic-bezier(.16,1,.3,1);display:flex;box-shadow:0 0 60px rgba(0,0,0,.8)}
  body.jnav .side{transform:translateX(0)}
  .drawer-extra{display:block}
  .details{position:fixed;inset:0;width:100%;min-width:0;z-index:210;transform:translateX(100%);transition:transform .3s cubic-bezier(.16,1,.3,1)}
  .details.show{transform:translateX(0)}
  .hdr{gap:10px;padding:14px 16px}
  .hdr .dot,.hdr .sub,.hdr .pill,.hdr .runbtn,.hdr .last,.hdr .hicon,.hdr .havatar{display:none!important}
  .hdr h1{font-size:19px}
  .jham,.jbell{display:flex}
  .searchrow{padding:10px 16px 4px;gap:8px}
  .searchrow .selbox{display:none}
  .jfilt{display:flex}
  .chips2,.stats,.srcbar{display:none}
  .jcount{display:flex}
  thead{display:none}
  table,tbody,tr,td{display:block;width:100%}
  tbody tr{padding:14px 16px;position:relative}
  td{padding:0;border:none}
  td.pos,td.emp,td.sal,td.star{display:inline-block;width:auto}
  td.emp,td.sal{font-size:12px;color:var(--sec);margin-top:8px;margin-right:14px}
  td.posted{display:none}
  td.star{position:absolute;right:14px;top:14px}
  .m-only{display:flex}
}
</style></head><body>
<div class="jscrim" onclick="jNav(false)"></div>
<div class="wrap">
  <aside class="side">
    <div class="brand"><div class="l">W</div><div class="n">WILD AUTOMATIONS</div></div>
    <nav class="nav" id="side-nav"></nav>
    <div class="drawer-extra">
      <button class="runbtn2" onclick="jNav(false);runJobs()"><svg viewBox="0 0 24 24" width="13" height="13" fill="#050505"><polygon points="6 3 20 12 6 21 6 3"/></svg> Run Jobs</button>
      <div id="drawer-src" style="font-size:11.5px;color:var(--sec)"></div>
    </div>
    <div class="prof"><div class="av">WA</div><div><div class="nm">Wild Admin</div><div class="em">admin@wild.com</div></div></div>
  </aside>
  <div class="main">
    <div class="hdr">
      <button class="jham" onclick="jNav(true)" aria-label="Menu"><svg viewBox="0 0 24 24"><line x1="3" x2="21" y1="6" y2="6"/><line x1="3" x2="21" y1="12" y2="12"/><line x1="3" x2="21" y1="18" y2="18"/></svg></button>
      <span class="dot"></span>
      <div><h1>Jobs Scrapers</h1><div class="sub">Wild Automations · <span id="agents">20</span> agents registered across 4 categories</div></div>
      <button class="jbell" aria-label="Notifications"><svg viewBox="0 0 24 24"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg></button>
      <span class="pill">Jobs</span>
      <button class="runbtn" onclick="runJobs()" id="runbtn"><svg viewBox="0 0 24 24"><polygon points="6 3 20 12 6 21 6 3"/></svg> Run Jobs</button>
      <span class="last" id="last">Ready</span>
      <button class="hicon" aria-label="Theme"><svg viewBox="0 0 24 24"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg></button>
      <button class="hicon" aria-label="Notifications"><svg viewBox="0 0 24 24"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg></button>
      <div class="havatar">WA</div>
    </div>
    <div class="searchrow">
      <div class="selbox"><svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="16" rx="2"/></svg> Jobs <span style="opacity:.6">▾</span></div>
      <div class="inp"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="var(--sec)" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg> <input id="q" placeholder="Search by Job Title, Company, Location, and More" oninput="applyFilter()"/></div>
      <div class="selbox everywhere"><svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21s-7-6-7-11a7 7 0 0 1 14 0c0 5-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg> Everywhere <span style="opacity:.6">▾</span></div>
      <button class="jfilt" onclick="jFilterOpen()" aria-label="Filters"><svg viewBox="0 0 24 24"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg></button>
      <button class="searchbtn" onclick="applyFilter()">Search</button>
    </div>
    <div class="jcount"><b id="jcount-n">0</b> Jobs Found <span class="sort">Most Relevant ▾</span></div>
    <div class="chips2">
      <span class="f2">Easy apply</span><span class="f2">Salary Range ▾</span><span class="f2">Company Rating ▾</span>
      <span class="f2">Date posted ▾</span><span class="f2">All Filters</span>
      <span class="f2 sort">Most Relevant ▾</span>
    </div>
    <div class="stats">
      <div class="stat"><div class="ring"><svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18"/></svg></div><div><div class="v" id="s-found">0</div><div class="k">Jobs Found</div></div></div>
      <div class="stat"><div class="ring"><svg viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h10"/></svg></div><div><div class="v" id="s-rows">0</div><div class="k">Sponsors Indexed</div></div></div>
      <div class="stat"><div class="ring"><svg viewBox="0 0 24 24"><path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="9"/></svg></div><div><div class="v" id="s-pass">0</div><div class="k">Verified Sponsors</div></div></div>
      <div class="stat"><div class="ring"><svg viewBox="0 0 24 24"><path d="M13 2 3 14h7l-1 8 10-12h-7z"/></svg></div><div><div class="v" id="s-lat">0s</div><div class="k">Avg Latency</div></div></div>
    </div>
    <div class="srcbar" id="srcbar"><span class="lbl">Sources</span></div>
    <div class="body">
      <div class="tablewrap">
        <table><thead><tr><th>Team</th><th>Position</th><th>Employee</th><th>Salary</th><th>Posted</th><th></th></tr></thead>
        <tbody id="tbody"><tr><td colspan="6"><div class="center" style="padding:60px 0"><span class="spin"></span><div>Loading jobs…</div></div></td></tr></tbody></table>
        <div class="pager"><span id="pginfo">—</span><div class="right"><button class="pg" onclick="pg(-1)">‹</button><span id="pgnum">1</span><button class="pg" onclick="pg(1)">›</button></div></div>
      </div>
      <aside class="details empty" id="details"><div><div style="font-size:30px">🗂</div><div style="margin-top:8px">Select a job to see details</div></div></aside>
    </div>
  </div>
</div>
<div class="jsheet" id="jsheet"><div class="jgrip"></div><h3>Filters</h3>
  <div class="jf-field"><label>Keyword</label><input id="jf-q" placeholder="Title, company, skill…"/></div>
  <div class="jf-field"><label>Country</label><select id="jf-country"><option value="">Any</option><option>United Kingdom</option><option>United States</option><option>UAE</option><option>Canada</option><option>Germany</option><option>Australia</option><option>India</option><option>Pakistan</option></select></div>
  <div class="jf-field"><label>Job type</label><select id="jf-type"><option value="">Any</option><option value="remote">Remote</option><option value="hybrid">Hybrid</option><option value="onsite">Onsite</option></select></div>
  <label class="jf-toggle"><input type="checkbox" id="jf-verified"/> Visa-Verified sponsors only</label>
  <label class="jf-toggle"><input type="checkbox" id="jf-salary"/> Has salary listed</label>
  <button class="jf-apply" onclick="jFilterApply()">Apply filters</button>
</div>
<script>
(function(){
  var NAV=[['all','All'],['Jobs','Jobs'],['University','Edu'],['Visa','Visa'],['Automobiles','Cars'],['Leads','Leads'],['sep'],['AI','AI Analyzer'],['Health','Health'],['Config','Config']];
  document.getElementById('side-nav').innerHTML=NAV.map(function(x){
    if(x[0]==='sep')return '<div style="height:1px;background:var(--line);margin:10px 6px"></div>';
    var href=x[0]==='Jobs'?'/jobs':(x[0]==='AI'?'/concierge':'/');
    return '<a class="ni'+(x[0]==='Jobs'?' on':'')+'" href="'+href+'"><svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/></svg>'+x[1]+'</a>';
  }).join('');

  var JOBS=[],VIEW=[],page=1,per=10,saved={},sel=null;
  var COLORS=['#E2B404','#4267B2','#1DB954','#E1306C','#FF5700','#6e5494','#00AB6C','#FF9900'];
  function esc(s){return (s||'').replace(/[<>&]/g,function(c){return {'<':'&lt;','>':'&gt;','&':'&amp;'}[c];});}
  function domain(co){return (co||'').toLowerCase().replace(/[^a-z0-9]/g,'')+'.com';}
  function letterLogo(co,i){var c=COLORS[(co||'').length%COLORS.length];
    return '<div class="logo-fb" style="background:'+c+'">'+((co||'?')[0]||'?').toUpperCase()+'</div>';}
  function logo(co,i){if(!co)return letterLogo('?',i);
    return '<img class="logo" src="https://logo.clearbit.com/'+domain(co)+'" '+
      'onerror="this.outerHTML=window.__lf('+JSON.stringify(co).replace(/"/g,'&quot;')+','+i+')"/>';}
  window.__lf=function(co,i){return letterLogo(co,i);};

  function load(){
    document.getElementById('tbody').innerHTML='<tr><td colspan="6"><div class="center" style="padding:60px 0"><span class="spin"></span><div>Loading jobs…</div></div></td></tr>';
    fetch('/api/jobs/all').then(function(r){return r.json();}).then(function(d){
      JOBS=d.jobs||[]; VIEW=JOBS.slice();
      var lat=(d.sources||[]).map(function(s){return s.elapsed||0;});
      var avg=lat.length?(lat.reduce(function(a,b){return a+b;},0)/lat.length):0;
      document.getElementById('s-found').textContent=JOBS.length;
      document.getElementById('s-rows').textContent=(d.sponsor_index&&d.sponsor_index.sponsors_indexed||0).toLocaleString();
      document.getElementById('s-pass').textContent=d.verified_sponsors||0;
      document.getElementById('s-lat').textContent=avg.toFixed(1)+'s';
      document.getElementById('last').textContent='Last run '+new Date().toLocaleTimeString();
      var srcHtml=(d.sources||[]).map(function(s){return '<span class="src"><span class="ok"></span>'+esc(s.name)+' ('+(s.count||0)+')</span>';}).join('');
      document.getElementById('srcbar').innerHTML='<span class="lbl">'+(d.sources||[]).length+' sources</span>'+srcHtml;
      var de=document.getElementById('drawer-src');if(de)de.innerHTML='<div style="font-weight:600;color:var(--text);margin-bottom:8px">Sources</div>'+srcHtml+'<div style="margin-top:12px">✓ '+(d.verified_sponsors||0)+' verified sponsors · '+((d.sponsor_index&&d.sponsor_index.sponsors_indexed)||0).toLocaleString()+' indexed</div>';
      page=1; render();
      jBootExtra();
    }).catch(function(){document.getElementById('tbody').innerHTML='<tr><td colspan="6"><div class="center" style="padding:50px"><div style="font-size:28px">⚡</div><div>Couldn\'t load jobs</div><button class="searchbtn" style="margin-top:10px" onclick="location.reload()">Retry</button></div></td></tr>';});
  }
  // after the fast first paint, pull the FULL multi-source engine in the
  // background (Himalayas/WWR/boards/Adzuna/…) and merge into the table
  var BOOTED=false;
  function jBootExtra(){
    if(BOOTED)return; BOOTED=true;
    var sb=document.getElementById('srcbar');
    if(sb)sb.innerHTML+='<span class="src"><span class="spin" style="width:10px;height:10px"></span> loading more sources…</span>';
    fetch('/api/jobs/search?q=&type=remote').then(function(r){return r.json();}).then(function(d){
      var added=0,keys={};
      JOBS.forEach(function(j){keys[((j.position||'')+'|'+(j.company||'')).toLowerCase()]=1;});
      (d.jobs||[]).forEach(function(j){
        var k=((j.position||'')+'|'+(j.company||'')).toLowerCase();
        if(!keys[k]){keys[k]=1;JOBS.push(j);added++;}
      });
      if(added){document.getElementById('s-found').textContent=JOBS.length;applyFilter();}
      if(sb)sb.innerHTML=sb.innerHTML.replace(/<span class="src"><span class="spin"[^<]*<\/span> loading more sources…<\/span>/,
        added?'<span class="src"><span class="ok"></span>Global engine (+'+added+')</span>':'');
    }).catch(function(){});
  }
  window.runJobs=function(){var b=document.getElementById('runbtn');b.innerHTML='<span class="spin" style="width:13px;height:13px"></span> Running…';b.disabled=true;
    fetch('/api/jobs/all').then(function(r){return r.json();}).then(function(){b.innerHTML='<svg viewBox="0 0 24 24"><polygon points="6 3 20 12 6 21 6 3"/></svg> Run Jobs';b.disabled=false;load();})
    .catch(function(){b.innerHTML='Run Jobs';b.disabled=false;});};

  var FILT={q:'',country:'',type:'',verified:false,salary:false};
  window.applyFilter=function(){
    var q=((document.getElementById('q').value||'')||FILT.q).toLowerCase();
    VIEW=JOBS.filter(function(j){
      if(q&&JSON.stringify(j).toLowerCase().indexOf(q)<0)return false;
      if(FILT.country&&(j.location||'').toLowerCase().indexOf(FILT.country.toLowerCase())<0)return false;
      if(FILT.type==='remote'&&!j.remote&&(j.location||'').toLowerCase().indexOf('remote')<0)return false;
      if(FILT.type==='onsite'&&(j.remote||(j.location||'').toLowerCase().indexOf('remote')>=0))return false;
      if(FILT.verified&&!j.sponsor_verified)return false;
      if(FILT.salary&&(!j.salary||j.salary==='—'))return false;
      return true;});
    page=1;render();};
  window.jNav=function(open){document.body.classList.toggle('jnav',open);};
  window.jFilterOpen=function(){
    document.getElementById('jf-q').value=FILT.q||document.getElementById('q').value||'';
    document.getElementById('jf-country').value=FILT.country;document.getElementById('jf-type').value=FILT.type;
    document.getElementById('jf-verified').checked=FILT.verified;document.getElementById('jf-salary').checked=FILT.salary;
    document.getElementById('jsheet').classList.add('on');};
  window.jFilterApply=function(){
    FILT.q=document.getElementById('jf-q').value;FILT.country=document.getElementById('jf-country').value;
    FILT.type=document.getElementById('jf-type').value;FILT.verified=document.getElementById('jf-verified').checked;
    FILT.salary=document.getElementById('jf-salary').checked;
    var qi=document.getElementById('q');if(qi)qi.value=FILT.q;
    document.getElementById('jsheet').classList.remove('on');applyFilter();
    jFetchFresh();};
  // live search: filters also FETCH new jobs matching them (not just re-filter cache)
  window.jFetchFresh=function(){
    if(!(FILT.q||FILT.country||FILT.type))return;
    var pg=document.getElementById('pginfo');var old=pg?pg.textContent:'';
    if(pg)pg.textContent=old+' · searching fresh jobs…';
    fetch('/api/jobs/search?q='+encodeURIComponent(FILT.q)+'&country='+encodeURIComponent(FILT.country)+'&type='+encodeURIComponent(FILT.type))
      .then(function(r){return r.json();})
      .then(function(d){
        var added=0,keys={};
        JOBS.forEach(function(j){keys[((j.position||'')+'|'+(j.company||'')).toLowerCase()]=1;});
        (d.jobs||[]).forEach(function(j){
          var k=((j.position||'')+'|'+(j.company||'')).toLowerCase();
          if(!keys[k]){keys[k]=1;JOBS.push(j);added++;}
        });
        if(added)applyFilter();
        if(pg&&added)pg.textContent=pg.textContent.replace(' · searching fresh jobs…',' · +'+added+' fresh');
        else if(pg)pg.textContent=pg.textContent.replace(' · searching fresh jobs…','');
      })
      .catch(function(){if(pg)pg.textContent=pg.textContent.replace(' · searching fresh jobs…','');});};

  function render(){
    var tb=document.getElementById('tbody');
    if(!VIEW.length){tb.innerHTML='<tr><td colspan="6"><div class="center" style="padding:60px 0">No jobs found.</div></td></tr>';document.getElementById('pginfo').textContent='0 results';return;}
    var start=(page-1)*per,slice=VIEW.slice(start,start+per);
    tb.innerHTML=slice.map(function(j,k){var idx=start+k;
      return '<tr onclick="openJob('+idx+',this)" class="'+(sel===idx?'sel':'')+'">'+
        '<td class="team"><div class="team">'+logo(j.company,idx)+'<div><div class="co">'+esc(j.company||'—')+'</div><div><span class="srctag">'+esc(j.source||'')+'</span>'+(j.sponsor_verified?'<span class="vbadge">✓ Visa Verified'+(j.visa_routes&&j.visa_routes.length?' · '+esc(j.visa_routes[0]):'')+'</span>':'')+'</div></div></div></td>'+
        '<td class="pos"><div class="t">'+esc((j.position||'').slice(0,60))+'</div><div class="l">'+esc(j.location||'')+'</div></td>'+
        '<td class="emp muted">'+esc(j.employees||'—')+'</td>'+
        '<td class="sal">'+esc(j.salary||'—')+'</td>'+
        '<td class="posted muted">'+esc(j.posted||'—')+'</td>'+
        '<td class="star'+(saved[idx]?' on':'')+'" onclick="event.stopPropagation();toggleSave('+idx+',this)">'+(saved[idx]?'★':'☆')+'</td></tr>';
    }).join('');
    var tot=VIEW.length,to=Math.min(start+per,tot);
    document.getElementById('pginfo').textContent='Showing '+(start+1)+' to '+to+' of '+tot+' results';
    document.getElementById('pgnum').textContent=page;
    var jc=document.getElementById('jcount-n');if(jc)jc.textContent=tot;
  }
  window.pg=function(d){var max=Math.ceil(VIEW.length/per)||1;page=Math.min(max,Math.max(1,page+d));render();};
  window.toggleSave=function(i,el){saved[i]=!saved[i];el.textContent=saved[i]?'★':'☆';el.classList.toggle('on',saved[i]);};

  function sponsorBlock(j){
    if(j.sponsor_verified){
      var routes=(j.visa_routes||[]).map(esc).join(', ')||'Skilled Worker';
      return '<div class="d-verif"><div class="h">🛡 Visa Sponsor — Verified</div>'+
        '<div class="r"><b>'+esc(j.company)+'</b> is on the official UK Register of Licensed Sponsors.<br>'+
        'Routes: '+routes+'</div>'+
        '<div class="d-ev">Source: UK Gov Register of Licensed Sponsors (Workers)</div></div>';
    }
    return '<div class="d-notv">⚪ Sponsorship: <b>'+esc(j.sponsor_status||'Not Verified')+'</b> — no matching licence in the official register.</div>';
  }
  function intelBlock(j){
    var ig=j.intelligence||{}; if(!ig.summary)return '';
    function pc(x){return Math.round((x||0)*100);}
    var ev=(ig.evidence||[]).map(function(e){return '• '+esc(e.detail||'');}).join('<br>');
    return '<div class="d-h">AI Intelligence</div>'+
      '<div class="d-scores">'+
      '<div class="d-score"><div class="v">'+pc(ig.ai_score)+'</div><div class="k">AI Score</div></div>'+
      '<div class="d-score"><div class="v">'+pc(ig.visa_score)+'</div><div class="k">Visa</div></div>'+
      '<div class="d-score"><div class="v">'+pc(ig.salary_score)+'</div><div class="k">Salary</div></div>'+
      '<div class="d-score"><div class="v">'+pc(ig.confidence)+'</div><div class="k">Confidence</div></div></div>'+
      '<p class="d-p">'+esc(ig.summary)+'</p>'+
      (ev?'<div class="d-ev"><b style="color:var(--sec)">Evidence</b><br>'+ev+'</div>':'');
  }
  window.openJob=function(i,row){sel=i;var j=VIEW[i];if(!j)return;
    document.querySelectorAll('tbody tr').forEach(function(r){r.classList.remove('sel');});if(row)row.classList.add('sel');
    var desc=esc(j.description||'');var parts=desc.split(/[.!?]\s/).filter(Boolean);
    var about=parts.slice(0,2).join('. ');var role=parts.slice(2,4).join('. ');
    var bullets=parts.slice(4,8);
    var d=document.getElementById('details');d.classList.remove('empty');d.classList.add('show');
    d.innerHTML='<div class="d-top"><h2>Job Details</h2><button class="d-close" onclick="closeJob()">✕</button></div>'+
      '<div class="d-scroll"><div class="d-co">'+logo(j.company,i)+'<div class="nm">'+esc(j.company||'—')+'</div></div>'+
      '<div class="d-title">'+esc(j.position||'')+'</div><div class="d-loc">'+esc(j.location||'')+'</div>'+
      '<div class="d-meta"><div><div class="k">Employee</div><div class="v">'+esc(j.employees||'—')+'</div></div>'+
      '<div><div class="k">Salary</div><div class="v">'+esc(j.salary||'—')+'</div></div>'+
      '<div><div class="k">Posted</div><div class="v">'+esc(j.posted||'—')+'</div></div></div>'+
      sponsorBlock(j)+intelBlock(j)+
      (about?'<div class="d-h">About '+esc(j.company||'the role')+'</div><p class="d-p">'+about+'.</p>':'')+
      (role?'<div class="d-h">What\'s the role?</div><p class="d-p">'+role+'.</p>':'')+
      (bullets.length?'<div class="d-h">In this role you will…</div>'+bullets.map(function(b){return '<div class="d-li"><span class="c">✓</span>'+b+'.</div>';}).join(''):'')+
      (!about&&!role?'<p class="d-p">'+(desc||'No description available for this listing.')+'</p>':'')+
      '<div id="d-full"></div></div>'+
      '<div class="d-foot"><span class="d-saved">'+(saved[i]?'★ Saved':'☆ Save')+'</span>'+
      '<button class="btn-ghost">Share</button>'+
      (j.url?'<a class="btn-gold" href="'+j.url+'" target="_blank">Apply Now</a>':'<button class="btn-gold">Apply Now</button>')+'</div>';
    // lazy deep-fetch the full description from the source page
    if(j.url){var fd=document.getElementById('d-full');fd.innerHTML='<div class="d-h">Full description</div><p class="d-p muted"><span class="spin" style="width:14px;height:14px"></span> Loading from source…</p>';
      fetch('/api/jobs/detail?url='+encodeURIComponent(j.url)).then(function(r){return r.json();}).then(function(dd){
        if(dd.description&&dd.description.length>(j.description||'').length){
          fd.innerHTML='<div class="d-h">Full description <span class="muted" style="font-size:10px">· from source</span></div><p class="d-p">'+esc(dd.description)+'</p>';
        } else {fd.innerHTML='';}
      }).catch(function(){fd.innerHTML='';});}
  };
  window.closeJob=function(){var d=document.getElementById('details');d.classList.remove('show');d.classList.add('empty');
    d.innerHTML='<div><div style="font-size:30px">🗂</div><div style="margin-top:8px">Select a job to see details</div></div>';
    sel=null;document.querySelectorAll('tbody tr').forEach(function(r){r.classList.remove('sel');});};
  load();
})();
</script></body></html>"""
