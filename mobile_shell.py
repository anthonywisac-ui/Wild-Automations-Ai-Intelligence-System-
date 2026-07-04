"""
Dedicated mobile-first shell for the Wild Automations CRM.

Injected before </body>; active only <=768px (desktop .layout hidden). Plain
string (NOT an f-string) so every { } is literal — no escaping. Same black+gold
identity, typography, radius, glow, card style as the desktop.

Layout (per user feedback):
  - Slide-in SIDEBAR drawer (hamburger) exactly like the desktop sidebar, incl.
    a Statistics item; NO bottom navigation.
  - Header: hamburger + brand + Filter icon (opens filter bottom sheet).
  - Content: "All" shows one horizontal card SLIDER per category; a single
    category shows a snap carousel + dots. Tap a card -> full-screen detail popup
    (UK-Licensed-Sponsors style) with the source's live results.
  - Floating round Run-All button stacked above the chat button.
"""

MOBILE_SHELL = r"""
<style>
#m-shell{display:none}
@media (max-width:768px){
  .layout{display:none!important}
  .m-bottomnav,.m-runfab,.m-scrim{display:none!important}
  #wc-fab{bottom:24px!important;right:16px!important;z-index:150}
  #m-shell{display:block;min-height:100vh;min-height:100dvh;background:var(--bg,#0a0a0b);
    color:var(--white,#f4f2ea);font-family:var(--font,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif)}
}
:root{--g:#E2B404;--gb:rgba(226,180,4,.25);--gd:rgba(226,180,4,.10);--gg:rgba(226,180,4,.12);
  --card:#141416;--card2:#1b1b1f;--line:#26262c;--sec:#9a978c;--bgc:#0a0a0b}

/* ── Sidebar drawer (matches desktop sidebar) ── */
.ms-scrim{position:fixed;inset:0;background:rgba(3,3,4,.6);backdrop-filter:blur(3px);z-index:180;
  opacity:0;pointer-events:none;transition:opacity .28s}
body.ms-nav .ms-scrim{opacity:1;pointer-events:auto}
.ms-side{position:fixed;top:0;left:0;height:100vh;height:100dvh;width:80%;max-width:290px;z-index:190;
  background:#010000;border-right:1px solid var(--line);display:flex;flex-direction:column;
  transform:translateX(-104%);transition:transform .28s cubic-bezier(.16,1,.3,1);box-shadow:0 0 60px rgba(0,0,0,.8)}
body.ms-nav .ms-side{transform:translateX(0)}
.ms-brand{padding:24px 20px 16px;display:flex;flex-direction:column;align-items:center;gap:10px;border-bottom:1px solid var(--line)}
.ms-brand .l{width:50px;height:50px;border-radius:12px;background:linear-gradient(135deg,#E2B404,#8a6c00);
  display:grid;place-items:center;font-size:24px;font-weight:900;color:#050505}
.ms-brand .n{font-size:11px;font-weight:700;letter-spacing:2.5px;color:#fff}
.ms-snav{padding:14px 10px;display:flex;flex-direction:column;gap:2px;flex:1;overflow-y:auto}
.ms-sitem{display:flex;align-items:center;gap:11px;padding:11px 14px;border-radius:10px;cursor:pointer;
  color:var(--sec);font-size:13.5px;font-weight:500;background:none;border:none;width:100%;text-align:left}
.ms-sitem svg{width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;opacity:.7;flex-shrink:0}
.ms-sitem.on{background:var(--gg);color:#fff;box-shadow:0 0 18px rgba(226,180,4,.08)}
.ms-sitem.on svg{stroke:var(--g);opacity:1}
.ms-sdiv{height:1px;background:var(--line);margin:10px 6px}
.ms-art{display:flex;align-items:center;justify-content:center;padding:6px 0}
.ms-prof{display:flex;align-items:center;gap:10px;padding:12px 16px 16px;border-top:1px solid var(--line)}
.ms-prof .av{width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,#E2B404,#7a5800);
  display:grid;place-items:center;font-size:11px;font-weight:700;color:#050505}
.ms-prof .nm{font-size:12.5px;font-weight:600;color:#fff}
.ms-prof .em{font-size:10.5px;color:var(--sec)}

/* ── Header ── */
.ms-head{position:sticky;top:0;z-index:40;display:flex;align-items:center;gap:12px;padding:14px 16px;
  background:rgba(10,10,11,.82);backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}
.ms-ham,.ms-ic{width:44px;height:44px;min-width:44px;min-height:44px;border-radius:12px;border:1px solid var(--gb);
  background:var(--gd);color:var(--g);display:grid;place-items:center;cursor:pointer;flex-shrink:0}
.ms-ham svg,.ms-ic svg{width:18px;height:18px;stroke:var(--g);fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.ms-logo{width:32px;height:32px;border-radius:9px;background:linear-gradient(135deg,#E2B404,#8a6c00);
  display:grid;place-items:center;color:#050505;font-weight:900;font-size:16px;flex-shrink:0}
.ms-htitle{line-height:1.15;font-weight:700;font-size:14.5px}
.ms-htitle span{display:block;font-size:10px;color:var(--sec);font-weight:500}
.ms-ic{margin-left:auto}

.ms-content{padding-bottom:110px}

/* ── Category section (All view) ── */
.ms-sec{margin-top:18px}
.ms-sec-h{display:flex;align-items:center;gap:8px;padding:0 16px 10px;font-size:13px;font-weight:700;color:#fff}
.ms-sec-h .c{font-size:11px;color:var(--g);border:1px solid var(--gb);background:var(--gd);border-radius:999px;padding:2px 9px}
.ms-row{display:flex;gap:12px;overflow-x:auto;padding:0 16px 4px;scroll-snap-type:x mandatory;scrollbar-width:none}
.ms-row::-webkit-scrollbar{display:none}
.ms-row .ms-card{flex:0 0 82%;scroll-snap-align:start}

/* ── Single-category carousel ── */
.ms-chips{display:flex;gap:8px;overflow-x:auto;padding:14px 16px 6px;scrollbar-width:none;
  -webkit-mask-image:linear-gradient(to right,#000 90%,transparent);mask-image:linear-gradient(to right,#000 90%,transparent)}
.ms-chips::-webkit-scrollbar{display:none}
.ms-row{-webkit-mask-image:linear-gradient(to right,#000 92%,transparent);mask-image:linear-gradient(to right,#000 92%,transparent)}
.ms-chip{flex-shrink:0;padding:8px 14px;border-radius:999px;border:1px solid var(--line);background:var(--card);
  color:var(--sec);font-size:12.5px;font-weight:600;white-space:nowrap;cursor:pointer;transition:.15s}
.ms-chip.on{border-color:var(--g);color:var(--g);background:var(--gd);box-shadow:0 0 14px rgba(226,180,4,.12)}
.ms-car{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;padding:8px 0 6px}
.ms-car::-webkit-scrollbar{display:none}
.ms-slide{flex:0 0 100%;scroll-snap-align:center;padding:8px 16px}
.ms-dots{display:flex;justify-content:center;gap:6px;padding:4px 0;flex-wrap:wrap}
.ms-dot{width:6px;height:6px;border-radius:50%;background:var(--line);transition:.2s}
.ms-dot.on{background:var(--g);width:18px;border-radius:3px;box-shadow:0 0 8px rgba(226,180,4,.5)}

/* ── Source card ── */
.ms-card{background:var(--card);border:1px solid var(--gb);border-radius:18px;padding:18px;cursor:pointer;
  box-shadow:0 2px 20px rgba(0,0,0,.5),0 0 26px rgba(226,180,4,.05);
  transition:transform .2s,box-shadow .2s,border-color .2s}
.ms-card:active{transform:scale(.985)}
.ms-card-top{display:flex;align-items:center;gap:12px}
.ms-emoji{width:46px;height:46px;border-radius:12px;background:var(--gd);border:1px solid var(--gb);
  display:grid;place-items:center;font-size:22px;flex-shrink:0}
.ms-name{font-weight:700;font-size:15.5px;line-height:1.25}
.ms-bot{font-size:12px;color:var(--sec);margin-top:2px}
.ms-pill{display:inline-flex;margin-top:12px;padding:4px 11px;border-radius:999px;border:1px solid var(--gb);
  background:var(--gd);color:var(--g);font-size:11px;font-weight:600}
.ms-meta{display:flex;align-items:center;gap:8px;margin-top:12px;font-size:12px;color:var(--sec);flex-wrap:wrap}
.ms-open{display:flex;align-items:center;justify-content:space-between;margin-top:14px;padding-top:12px;
  border-top:1px solid var(--line);font-size:12.5px;color:var(--g);font-weight:600}

/* ── Floating round buttons (Run All above chat) ── */
.ms-run{position:fixed;right:16px;bottom:88px;z-index:150;width:56px;height:56px;border-radius:50%;border:none;
  background:linear-gradient(135deg,#F0C838,#B8860B);color:#050505;display:grid;place-items:center;cursor:pointer;
  box-shadow:0 10px 26px rgba(226,180,4,.4),0 0 0 1px rgba(226,180,4,.5)}
.ms-run svg{width:22px;height:22px;fill:#050505}
.ms-run:active{transform:scale(.94)}

/* ── Bottom sheets ── */
.ms-sheet{position:fixed;left:0;right:0;bottom:0;z-index:200;background:var(--card);border-top:1px solid var(--gb);
  border-radius:22px 22px 0 0;padding:8px 18px calc(24px + env(safe-area-inset-bottom));
  transform:translateY(102%);transition:transform .34s cubic-bezier(.16,1,.3,1);max-height:82vh;overflow-y:auto;
  box-shadow:0 -20px 60px rgba(0,0,0,.6)}
.ms-sheet.on{transform:translateY(0)}
.ms-grip{width:40px;height:4px;border-radius:2px;background:var(--line);margin:6px auto 14px}
.ms-sheet h3{margin:0 0 4px;font-size:17px}
.ms-sheet .sub{color:var(--sec);font-size:12.5px;margin-bottom:14px}
.ms-field{margin-bottom:12px}
.ms-field label{display:block;font-size:12px;color:var(--sec);margin-bottom:6px}
.ms-field input,.ms-field select{width:100%;min-height:48px;background:var(--card2);border:1px solid var(--line);
  color:#f4f2ea;border-radius:12px;padding:12px;font-size:16px}
.ms-apply{width:100%;min-height:52px;border:none;border-radius:14px;margin-top:8px;font-weight:700;font-size:16px;
  color:#050505;cursor:pointer;background:linear-gradient(135deg,#F0C838,#B8860B)}
.ms-stats{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:6px}
.ms-stat{background:var(--card2);border:1px solid var(--line);border-radius:14px;padding:16px}
.ms-stat .v{font-size:26px;font-weight:800;color:var(--g)}
.ms-stat .l{font-size:11.5px;color:var(--sec);margin-top:4px;text-transform:uppercase;letter-spacing:.6px}

/* ── Detail popup (UK-Licensed-Sponsors style) ── */
.ms-detail{position:fixed;inset:0;z-index:210;background:var(--bgc);overflow-y:auto;
  transform:translateY(100%);transition:transform .34s cubic-bezier(.16,1,.3,1)}
.ms-detail.on{transform:translateY(0)}
.ms-d-wrap{padding:16px 16px 120px;max-width:640px;margin:0 auto}
.ms-d-close{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:8px;padding:12px 0;
  background:linear-gradient(180deg,var(--bgc) 75%,transparent);color:var(--g);font-weight:600;cursor:pointer;font-size:14px}
.ms-d-head{display:flex;gap:14px;align-items:flex-start;margin-top:6px}
.ms-d-badge{width:66px;height:66px;border-radius:16px;border:1px solid var(--gb);background:linear-gradient(135deg,var(--gd),transparent);
  display:grid;place-items:center;font-size:24px;font-weight:800;color:var(--g);flex-shrink:0}
.ms-d-title{font-size:24px;font-weight:800;line-height:1.15}
.ms-d-sub{font-size:12.5px;color:var(--sec);margin-top:6px}
.ms-d-official{display:inline-flex;align-items:center;gap:6px;margin-top:10px;padding:6px 12px;border-radius:999px;
  border:1px solid var(--gb);background:var(--gd);color:var(--g);font-size:12px;font-weight:600}
.ms-d-info{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:16px;padding:14px 16px;
  background:var(--card);border:1px solid var(--line);border-radius:14px}
.ms-d-info .big{font-size:15px;font-weight:700}.ms-d-info .big b{color:var(--g)}
.ms-d-info .r{text-align:right;font-size:11.5px;color:var(--sec)}
.ms-d-search{display:flex;gap:10px;margin-top:14px}
.ms-d-search input{flex:1;min-height:50px;background:var(--card);border:1px solid var(--line);border-radius:13px;
  color:#f4f2ea;padding:0 16px;font-size:15px}
.ms-d-refresh{min-height:50px;padding:0 18px;border-radius:13px;border:1px solid var(--gb);background:var(--gd);
  color:var(--g);font-weight:600;font-size:13px;cursor:pointer;white-space:nowrap}
.ms-d-filters{display:flex;gap:8px;overflow-x:auto;margin-top:12px;scrollbar-width:none}
.ms-d-filters::-webkit-scrollbar{display:none}
.ms-d-fpill{flex-shrink:0;display:flex;align-items:center;gap:6px;padding:10px 14px;border-radius:12px;
  border:1px solid var(--line);background:var(--card);color:var(--sec);font-size:12.5px;font-weight:500}
.ms-rcard{display:flex;align-items:center;gap:14px;margin-top:12px;padding:16px;background:var(--card);
  border:1px solid var(--line);border-radius:16px;transition:transform .2s,border-color .2s}
.ms-rcard:active{transform:scale(.99)}
.ms-rcard .ic{width:52px;height:52px;border-radius:12px;border:1px solid var(--line);background:var(--card2);
  display:grid;place-items:center;font-size:22px;flex-shrink:0}
.ms-rcard .nm{font-size:15px;font-weight:700;line-height:1.2}
.ms-rbadge{display:inline-flex;align-items:center;gap:5px;margin-top:6px;padding:3px 9px;border-radius:999px;
  background:rgba(52,211,120,.12);border:1px solid rgba(52,211,120,.3);color:#5fd38a;font-size:11px;font-weight:600}
.ms-rcard .mt{font-size:11.5px;color:var(--sec);margin-top:6px}
.ms-rcard .vd{margin-left:auto;color:var(--g);font-size:12px;font-weight:600;white-space:nowrap;align-self:center}
.ms-loadmore{width:100%;min-height:54px;margin-top:18px;border:none;border-radius:14px;font-weight:700;font-size:15px;
  color:#050505;cursor:pointer;background:linear-gradient(135deg,#F0C838,#B8860B);
  box-shadow:0 10px 26px rgba(226,180,4,.3);display:flex;align-items:center;justify-content:center;gap:8px}
.ms-empty{padding:40px 16px;text-align:center;color:var(--sec)}
.ms-spin{display:inline-block;width:20px;height:20px;border:2px solid var(--line);border-top-color:var(--g);
  border-radius:50%;animation:mssp .8s linear infinite;vertical-align:middle}
@keyframes mssp{to{transform:rotate(360deg)}}
</style>

<div id="m-shell">
  <!-- drawer -->
  <div class="ms-scrim" onclick="msNav(false)"></div>
  <aside class="ms-side">
    <div class="ms-brand"><div class="l">W</div><div class="n">WILD AUTOMATIONS</div></div>
    <nav class="ms-snav" id="ms-snav"></nav>
    <div class="ms-art">
      <svg width="120" height="120" viewBox="0 0 130 130" fill="none">
        <circle cx="65" cy="65" r="58" stroke="rgba(226,180,4,.2)" stroke-width="1"/>
        <circle cx="65" cy="65" r="46" stroke="rgba(226,180,4,.14)" stroke-width="1"/>
        <circle cx="65" cy="65" r="34" stroke="rgba(226,180,4,.1)" stroke-width="1"/>
        <text x="65" y="72" text-anchor="middle" font-size="30" font-weight="900" fill="rgba(226,180,4,.6)">W</text></svg>
    </div>
    <div class="ms-prof"><div class="av">WA</div><div><div class="nm">Wild Admin</div><div class="em">admin@wild.com</div></div></div>
  </aside>

  <!-- header -->
  <div class="ms-head">
    <button class="ms-ham" onclick="msNav(true)" aria-label="Menu"><svg viewBox="0 0 24 24"><line x1="3" x2="21" y1="6" y2="6"/><line x1="3" x2="21" y1="12" y2="12"/><line x1="3" x2="21" y1="18" y2="18"/></svg></button>
    <div class="ms-logo">W</div>
    <div class="ms-htitle">Wild Automations<span id="ms-cur">All Sources</span></div>
    <button class="ms-ic" onclick="msOpen('filter')" aria-label="Filters"><svg viewBox="0 0 24 24"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg></button>
  </div>

  <div class="ms-content" id="ms-content"><div class="ms-empty"><span class="ms-spin"></span><div style="margin-top:12px">Loading sources…</div></div></div>

  <button class="ms-run" onclick="msRunAll()" id="ms-runall" aria-label="Run All"><svg viewBox="0 0 24 24"><polygon points="6 3 20 12 6 21 6 3"/></svg></button>

  <!-- sheets -->
  <div class="ms-sheet" id="ms-filter"><div class="ms-grip"></div><h3>Filters</h3>
    <div class="sub" id="ms-filter-sub">Refine this category</div>
    <div id="ms-filter-fields"></div><button class="ms-apply" onclick="msApply()">Apply filters</button></div>
  <div class="ms-sheet" id="ms-statsheet"><div class="ms-grip"></div><h3>Statistics</h3>
    <div class="sub">This session</div><div class="ms-stats" id="ms-stats-body"></div></div>

  <!-- detail popup -->
  <div class="ms-detail" id="ms-detail"><div class="ms-d-wrap" id="ms-detail-body"></div></div>
</div>

<script>
(function(){
  var CAT_META={all:{ic:'▦',l:'All'},Jobs:{ic:'💼',l:'Jobs'},University:{ic:'🎓',l:'Edu'},
    Visa:{ic:'🛂',l:'Visa'},Automobiles:{ic:'🚗',l:'Cars'},Leads:{ic:'🧲',l:'Leads'}};
  var NAV_SVG={
    all:'<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
    Jobs:'<path d="M16 6V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><rect width="20" height="14" x="2" y="6" rx="2"/>',
    University:'<path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
    Visa:'<rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/>',
    Automobiles:'<path d="M5 10H2a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1h20a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1h-3"/><path d="m21 8-2 2-1.5-3.7A2 2 0 0 0 15.646 5H8.4a2 2 0 0 0-1.903 1.257L5 10"/>',
    Leads:'<path d="M17 6.1H3"/><path d="M21 12.1H3"/><path d="M15.1 18H3"/>',
    AI:'<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    Stats:'<line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="14"/>',
    Health:'<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>',
    Config:'<circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'
  };
  var FILTER_SCHEMA={
    Jobs:[{k:'country',l:'Country',t:'select',o:['Any','UAE','USA','UK','Canada','Germany','Australia']},{k:'role',l:'Role',t:'text'},{k:'salary',l:'Min Salary',t:'number'},{k:'experience',l:'Experience',t:'select',o:['Any','Entry','Mid','Senior']},{k:'jobtype',l:'Job Type',t:'select',o:['Any','Full-time','Part-time','Remote','Contract']}],
    University:[{k:'country',l:'Country',t:'text'},{k:'university',l:'University',t:'text'},{k:'ranking',l:'Ranking',t:'select',o:['Any','Top 100','Top 500','Top 1000']},{k:'scholarship',l:'Scholarship',t:'select',o:['Any','Yes','No']},{k:'degree',l:'Degree',t:'select',o:['Any','Bachelor','Master','PhD']}],
    Visa:[{k:'country',l:'Country',t:'text'},{k:'visatype',l:'Visa Type',t:'text'},{k:'sponsor',l:'Sponsor',t:'select',o:['Any','Yes','No']},{k:'occupation',l:'Occupation',t:'text'}],
    Automobiles:[{k:'brand',l:'Brand',t:'text'},{k:'model',l:'Model',t:'text'},{k:'price',l:'Max Price',t:'number'},{k:'year',l:'Year',t:'number'}],
    Leads:[{k:'industry',l:'Industry',t:'text'},{k:'location',l:'Location',t:'text'}]
  };
  var ALL=[],CATS=[],cat='all',filters={},stats={rows:0,pass:0,fail:0,lat:[]},cache={};
  function $(id){return document.getElementById(id);}
  function esc(s){return (s||'').replace(/[<>&]/g,function(c){return {'<':'&lt;','>':'&gt;','&':'&amp;'}[c];});}

  function loadScrapers(){
    $('ms-content').innerHTML='<div class="ms-empty"><span class="ms-spin"></span><div style="margin-top:12px">Loading sources…</div></div>';
    fetch('/api/scrapers').then(function(r){return r.json();}).then(function(d){
      ALL=d.scrapers||[]; CATS=(d.categories||[]).filter(function(c){return ALL.some(function(s){return s.category===c;});});
      if(!ALL.length){$('ms-content').innerHTML='<div class="ms-empty">No sources registered.</div>';return;}
      renderNav(); selectCat('all');
    }).catch(function(){
      $('ms-content').innerHTML='<div class="ms-empty"><div style="font-size:30px">⚡</div>'+
        '<div style="margin-top:8px;color:#f4f2ea;font-weight:600">Couldn\'t load sources</div>'+
        '<div style="margin-top:4px">Check your connection.</div>'+
        '<button class="ms-apply" style="max-width:180px;margin:16px auto 0" onclick="msReload()">Retry</button></div>';
    });
  }
  window.msReload=loadScrapers;
  loadScrapers();

  function navBtn(key,label,fn,active){
    return '<button class="ms-sitem'+(active?' on':'')+'" onclick="'+fn+'"><svg viewBox="0 0 24 24">'+(NAV_SVG[key]||'')+'</svg>'+label+'</button>';
  }
  function renderNav(){
    var h=navBtn('all','All',"msPick('all')",cat==='all');
    CATS.forEach(function(c){h+=navBtn(c,(CAT_META[c]||{}).l||c,"msPick('"+c+"')",cat===c);});
    h+='<div class="ms-sdiv"></div>';
    h+=navBtn('AI','AI Analyzer',"msConcierge()",false);
    h+=navBtn('Stats','Statistics',"msOpen('stats')",false);
    h+='<div class="ms-sdiv"></div>';
    h+=navBtn('Health','Health','void 0',false)+navBtn('Config','Config','void 0',false);
    $('ms-snav').innerHTML=h;
  }
  window.msNav=function(open){document.body.classList.toggle('ms-nav',open);};
  window.msConcierge=function(){msNav(false); if(window.wcOpen)wcOpen();};
  window.msPick=function(c){
    if(c==='Jobs'){location.href='/jobs';return;}
    cat=c; msNav(false); renderNav();
    $('ms-cur').textContent=c==='all'?'All Sources':((CAT_META[c]||{}).l||c);
    renderContent();};

  function sourceCard(s,cls){
    return '<div class="ms-card '+(cls||'')+'" onclick="msDetail('+s.index+')">'+
      '<div class="ms-card-top"><div class="ms-emoji">'+(s.emoji||'🔎')+'</div>'+
      '<div><div class="ms-name">'+esc(s.name)+'</div><div class="ms-bot">'+esc(s.bot)+'</div></div></div>'+
      '<span class="ms-pill">'+esc(s.mode||'')+'</span>'+
      '<div class="ms-open"><span>Tap to view results</span><span>→</span></div></div>';
  }

  function renderContent(){
    var C=$('ms-content');
    if(cat==='all'){
      var h='';
      CATS.forEach(function(c){
        var items=ALL.filter(function(s){return s.category===c;}); if(!items.length)return;
        h+='<div class="ms-sec"><div class="ms-sec-h">'+((CAT_META[c]||{}).ic||'')+' '+((CAT_META[c]||{}).l||c)+'<span class="c">'+items.length+'</span></div>'+
           '<div class="ms-row">'+items.map(function(s){return sourceCard(s);}).join('')+'</div></div>';
      });
      C.innerHTML=h; return;
    }
    var items=ALL.filter(function(s){return s.category===cat;});
    C.innerHTML='<div class="ms-chips" id="ms-chips">'+items.map(function(s,i){return '<div class="ms-chip'+(i===0?' on':'')+'" onclick="msGo('+i+')">'+esc(s.name)+'</div>';}).join('')+'</div>'+
      '<div class="ms-car" id="ms-car">'+items.map(function(s){return '<div class="ms-slide">'+sourceCard(s)+'</div>';}).join('')+'</div>'+
      '<div class="ms-dots" id="ms-dots">'+items.map(function(_,i){return '<div class="ms-dot'+(i===0?' on':'')+'"></div>';}).join('')+'</div>';
    var car=$('ms-car');
    car.addEventListener('scroll',function(){var i=Math.round(car.scrollLeft/(car.clientWidth||1));
      document.querySelectorAll('#ms-dots .ms-dot').forEach(function(d,k){d.classList.toggle('on',k===i);});
      document.querySelectorAll('#ms-chips .ms-chip').forEach(function(c,k){c.classList.toggle('on',k===i);});},{passive:true});
    window.msGo=function(i){car.scrollTo({left:i*car.clientWidth,behavior:'smooth'});};
  }

  // ── Detail popup (screenshot-2 style) ──
  window.msDetail=function(index){
    var s=ALL.filter(function(x){return x.index===index;})[0]||ALL[index]; if(!s)return;
    var D=$('ms-detail-body');
    D.innerHTML='<div class="ms-d-close" onclick="msDetailClose()">‹ Back</div>'+detailHead(s)+
      '<div class="ms-empty"><span class="ms-spin"></span> Fetching live results…</div>';
    $('ms-detail').classList.add('on');
    var render=function(res,elapsed){
      var body=res.length?res.map(resultCard).join(''):'<div class="ms-empty">No results returned.</div>';
      D.innerHTML='<div class="ms-d-close" onclick="msDetailClose()">‹ Back</div>'+detailHead(s,res.length,elapsed)+
        '<div class="ms-d-search"><input placeholder="Search '+esc(s.name)+'…" oninput="msFilterDetail(this.value)"/>'+
        '<button class="ms-d-refresh" onclick="msDetail('+index+')">↻ Refresh</button></div>'+
        detailFilters(s.category)+'<div id="ms-rlist">'+body+'</div>'+
        (res.length>=5?'<button class="ms-loadmore" onclick="void 0">✦ Load More Results →</button>':'');
      window._msres=res;
    };
    if(cache[index]){render(cache[index].res,cache[index].el);return;}
    fetch('/api/run/'+index).then(function(r){return r.json();}).then(function(d){
      var res=(d.results||[]); cache[index]={res:res,el:d.elapsed};
      stats.lat.push(d.elapsed||0); (d.status==='ok'?stats.pass++:stats.fail++); stats.rows+=res.length;
      render(res,d.elapsed);
    }).catch(function(){D.innerHTML+='<div class="ms-empty">Failed to load.</div>';});
  };
  function detailHead(s,count,elapsed){
    return '<div class="ms-d-head"><div class="ms-d-badge">'+(s.emoji||'🔎')+'</div>'+
      '<div><div class="ms-d-title">'+esc(s.name)+'</div>'+
      '<div class="ms-d-sub">'+esc(s.bot)+' • '+esc(s.mode||'')+'</div>'+
      '<div class="ms-d-official">🛡 Official Source</div></div></div>'+
      (count!=null?'<div class="ms-d-info"><div class="big">Showing <b>'+count+'</b> results</div>'+
      '<div class="r">Fetched<br>'+(elapsed||0)+'s ago</div></div>':'');
  }
  function detailFilters(category){
    var sc=(FILTER_SCHEMA[category]||[]).slice(0,4);
    return '<div class="ms-d-filters">'+sc.map(function(f){return '<div class="ms-d-fpill">'+f.l+' ▾</div>';}).join('')+'</div>';
  }
  function resultCard(r){
    var md=r.metadata||{}; var loc=r.location||md.country||''; var cat2=md.type||md.category||'';
    var url=r.source_url||'';
    return '<div class="ms-rcard" onclick="'+(url?"window.open('"+url+"','_blank')":'void 0')+'">'+
      '<div class="ic">🏢</div><div style="flex:1;min-width:0">'+
      '<div class="nm">'+esc((r.title||'').slice(0,60))+'</div>'+
      (md.status||md.type?'<span class="ms-rbadge">◇ '+esc(md.status||md.type)+'</span>':'')+
      '<div class="mt">'+(loc?'📍 '+esc(loc):'')+(cat2?'  ·  '+esc(cat2):'')+'</div></div>'+
      (url?'<span class="vd">View →</span>':'')+'</div>';
  }
  window.msFilterDetail=function(q){q=(q||'').toLowerCase();
    var res=(window._msres||[]).filter(function(r){return JSON.stringify(r).toLowerCase().indexOf(q)>=0;});
    $('ms-rlist').innerHTML=res.length?res.map(resultCard).join(''):'<div class="ms-empty">No match.</div>';};
  window.msDetailClose=function(){$('ms-detail').classList.remove('on');};

  window.msRunAll=function(){
    var items=(cat==='all'?ALL:ALL.filter(function(s){return s.category===cat;}));
    if(items.length){msDetail(items[0].index);}
  };

  // sheets
  window.msOpen=function(which){msNav(false);
    if(which==='filter'){var use=(cat==='all'?'Jobs':cat);
      $('ms-filter-sub').textContent='Refine '+((CAT_META[use]||{}).l||use);
      var sc=FILTER_SCHEMA[use]||[];
      $('ms-filter-fields').innerHTML=sc.map(function(f){
        if(f.t==='select')return '<div class="ms-field"><label>'+f.l+'</label><select id="mf_'+f.k+'">'+(f.o||[]).map(function(o){return '<option>'+o+'</option>';}).join('')+'</select></div>';
        return '<div class="ms-field"><label>'+f.l+'</label><input id="mf_'+f.k+'" type="'+(f.t||'text')+'" placeholder="'+f.l+'"/></div>';}).join('');
      $('ms-filter').classList.add('on');
    } else { renderStats(); $('ms-statsheet').classList.add('on'); }
  };
  window.msApply=function(){filters={}; (FILTER_SCHEMA[cat==='all'?'Jobs':cat]||[]).forEach(function(f){var el=$('mf_'+f.k);if(el)filters[f.k]=el.value;});
    $('ms-filter').classList.remove('on');};
  function renderStats(){var avg=stats.lat.length?(stats.lat.reduce(function(a,b){return a+b;},0)/stats.lat.length):0;
    $('ms-stats-body').innerHTML=
      '<div class="ms-stat"><div class="v">'+stats.rows+'</div><div class="l">Rows Extracted</div></div>'+
      '<div class="ms-stat"><div class="v">'+stats.pass+'</div><div class="l">Sources Passed</div></div>'+
      '<div class="ms-stat"><div class="v">'+stats.fail+'</div><div class="l">Sources Failed</div></div>'+
      '<div class="ms-stat"><div class="v">'+avg.toFixed(1)+'s</div><div class="l">Avg Latency</div></div>';}
  // tap scrim/sheets to close
  document.addEventListener('click',function(e){
    if(e.target.classList&&e.target.classList.contains('ms-sheet'))e.target.classList.remove('on');});
})();
</script>
"""
