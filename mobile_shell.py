"""
Dedicated mobile-first shell for the Wild Automations CRM.

Injected into the dashboard page before </body>. Shown only <=768px; on mobile the
desktop `.layout` is hidden and this purpose-built touch UI takes over. Same
black+gold identity, typography, radius, glow. Plain string (NOT an f-string) so
all { } are literal — no escaping.

UX: minimal content-first dashboard — Header (logo + Filter/Stats icons) · source
chips · ONE swipeable scraper card per screen (snap carousel + dots) · bottom nav ·
floating Run-All. Filters & stats live in animated bottom sheets. Schema-driven
filters per category.
"""

MOBILE_SHELL = r"""
<style>
#m-shell{display:none}
@media (max-width:768px){
  /* hand the phone entirely to the mobile shell; desktop layout untouched */
  .layout{display:none!important}
  .m-bottomnav,.m-runfab,.m-scrim{display:none!important}
  #wc-fab{bottom:150px!important;right:16px!important;z-index:160}
  #m-shell{display:flex;flex-direction:column;min-height:100vh;min-height:100dvh;
    background:var(--bg,#0a0a0b);color:var(--white,#f4f2ea);
    font-family:var(--font,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif)}
}
:root{--ms-gold:#E2B404;--ms-gborder:rgba(226,180,4,.25);--ms-gdim:rgba(226,180,4,.10);
  --ms-card:#141416;--ms-line:#26262c;--ms-sec:#9a978c;--ms-bg:#0a0a0b}

.ms-head{position:sticky;top:0;z-index:40;display:flex;align-items:center;gap:12px;
  padding:14px 16px;background:rgba(10,10,11,.82);backdrop-filter:blur(16px);
  border-bottom:1px solid var(--ms-line)}
.ms-logo{width:34px;height:34px;border-radius:9px;flex-shrink:0;
  background:linear-gradient(135deg,#E2B404,#8a6c00);display:grid;place-items:center;
  color:#050505;font-weight:900;font-size:17px}
.ms-title{line-height:1.15;font-weight:700;font-size:15px}
.ms-title span{display:block;font-size:10.5px;color:var(--ms-sec);font-weight:500;letter-spacing:.3px}
.ms-ic{width:40px;height:40px;border-radius:11px;border:1px solid var(--ms-gborder);
  background:var(--ms-gdim);color:var(--ms-gold);display:grid;place-items:center;cursor:pointer;flex-shrink:0}
.ms-ic svg{width:18px;height:18px;stroke:var(--ms-gold);fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.ms-ic:first-of-type{margin-left:auto}

.ms-chips{display:flex;gap:8px;overflow-x:auto;padding:14px 16px 6px;scrollbar-width:none}
.ms-chips::-webkit-scrollbar{display:none}
.ms-chip{flex-shrink:0;padding:8px 14px;border-radius:999px;border:1px solid var(--ms-line);
  background:var(--ms-card);color:var(--ms-sec);font-size:12.5px;font-weight:600;white-space:nowrap;cursor:pointer;transition:.15s}
.ms-chip.on{border-color:var(--ms-gold);color:var(--ms-gold);background:var(--ms-gdim);
  box-shadow:0 0 14px rgba(226,180,4,.12)}

.ms-carousel{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;
  scrollbar-width:none;padding:8px 0 6px}
.ms-carousel::-webkit-scrollbar{display:none}
.ms-slide{flex:0 0 100%;scroll-snap-align:center;padding:8px 16px}
.ms-card{background:var(--ms-card);border:1px solid var(--ms-gborder);border-radius:18px;
  padding:20px;min-height:340px;display:flex;flex-direction:column;
  box-shadow:0 2px 20px rgba(0,0,0,.5),0 0 26px rgba(226,180,4,.05)}
.ms-card-top{display:flex;align-items:center;gap:12px}
.ms-card-emoji{width:46px;height:46px;border-radius:12px;background:var(--ms-gdim);
  border:1px solid var(--ms-gborder);display:grid;place-items:center;font-size:22px;flex-shrink:0}
.ms-card-name{font-weight:700;font-size:16px;line-height:1.25}
.ms-card-bot{font-size:12px;color:var(--ms-sec);margin-top:2px}
.ms-pill{display:inline-flex;align-self:flex-start;margin-top:12px;padding:4px 11px;border-radius:999px;
  border:1px solid var(--ms-gborder);background:var(--ms-gdim);color:var(--ms-gold);font-size:11px;font-weight:600}
.ms-card-body{flex:1;margin-top:16px;overflow:hidden}
.ms-res{border-top:1px solid var(--ms-line);padding:11px 0;font-size:13px;color:var(--white,#f4f2ea)}
.ms-res .r2{color:var(--ms-sec);font-size:11.5px;margin-top:2px}
.ms-card-run{margin-top:14px;min-height:48px;border:none;border-radius:13px;font-weight:700;font-size:15px;
  color:#050505;cursor:pointer;background:linear-gradient(135deg,#F0C838,#B8860B);
  box-shadow:0 6px 18px rgba(226,180,4,.28)}
.ms-card-run.busy{opacity:.7}
.ms-count{color:var(--ms-gold);font-weight:700}

.ms-dots{display:flex;justify-content:center;gap:6px;padding:6px 0 4px;flex-wrap:wrap}
.ms-dot{width:6px;height:6px;border-radius:50%;background:var(--ms-line);transition:.2s}
.ms-dot.on{background:var(--ms-gold);width:18px;border-radius:3px;box-shadow:0 0 8px rgba(226,180,4,.5)}

.ms-run{position:fixed;left:50%;transform:translateX(-50%);bottom:82px;z-index:45;
  display:inline-flex;align-items:center;gap:8px;padding:13px 28px;border:none;border-radius:999px;
  font-family:inherit;font-size:15px;font-weight:700;color:#050505;cursor:pointer;
  background:linear-gradient(135deg,#F0C838,#B8860B);
  box-shadow:0 12px 30px rgba(226,180,4,.42),0 0 0 1px rgba(226,180,4,.55)}
.ms-run svg{width:14px;height:14px;fill:#050505}
.ms-run:active{transform:translateX(-50%) scale(.96)}

.ms-nav{position:fixed;left:0;right:0;bottom:0;z-index:44;height:66px;display:flex;justify-content:space-around;
  align-items:center;background:rgba(8,8,9,.92);backdrop-filter:blur(18px);border-top:1px solid var(--ms-gborder);
  box-shadow:0 -6px 24px rgba(0,0,0,.5);padding-bottom:env(safe-area-inset-bottom)}
.ms-nav-i{display:flex;flex-direction:column;align-items:center;gap:3px;background:none;border:none;
  color:var(--ms-sec);font-size:9.5px;font-weight:600;cursor:pointer;padding:6px 4px;min-width:52px}
.ms-nav-i .ic{font-size:19px;line-height:1;opacity:.8}
.ms-nav-i.on{color:var(--ms-gold)}
.ms-nav-i.on .ic{opacity:1}

/* bottom sheets */
.ms-scrim{position:fixed;inset:0;background:rgba(3,3,4,.62);backdrop-filter:blur(3px);z-index:60;
  opacity:0;pointer-events:none;transition:opacity .28s}
.ms-scrim.on{opacity:1;pointer-events:auto}
.ms-sheet{position:fixed;left:0;right:0;bottom:0;z-index:70;background:var(--ms-card);
  border-top:1px solid var(--ms-gborder);border-radius:22px 22px 0 0;padding:8px 18px calc(24px + env(safe-area-inset-bottom));
  transform:translateY(102%);transition:transform .34s cubic-bezier(.16,1,.3,1);max-height:82vh;overflow-y:auto;
  box-shadow:0 -20px 60px rgba(0,0,0,.6)}
.ms-sheet.on{transform:translateY(0)}
.ms-grip{width:40px;height:4px;border-radius:2px;background:var(--ms-line);margin:6px auto 14px}
.ms-sheet h3{margin:0 0 4px;font-size:17px}
.ms-sheet .sub{color:var(--ms-sec);font-size:12.5px;margin-bottom:14px}
.ms-field{margin-bottom:12px}
.ms-field label{display:block;font-size:12px;color:var(--ms-sec);margin-bottom:6px}
.ms-field input,.ms-field select{width:100%;min-height:48px;background:#1b1b1f;border:1px solid var(--ms-line);
  color:var(--white,#f4f2ea);border-radius:12px;padding:12px;font-size:16px}
.ms-apply{width:100%;min-height:52px;border:none;border-radius:14px;margin-top:8px;font-weight:700;font-size:16px;
  color:#050505;cursor:pointer;background:linear-gradient(135deg,#F0C838,#B8860B)}
.ms-stats{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:6px}
.ms-stat{background:#1b1b1f;border:1px solid var(--ms-line);border-radius:14px;padding:16px}
.ms-stat .v{font-size:26px;font-weight:800;color:var(--ms-gold)}
.ms-stat .l{font-size:11.5px;color:var(--ms-sec);margin-top:4px;text-transform:uppercase;letter-spacing:.6px}
</style>

<div id="m-shell">
  <div class="ms-head">
    <div class="ms-logo">W</div>
    <div class="ms-title">Wild Automations<span>Scraper CRM</span></div>
    <button class="ms-ic" onclick="msOpen('filter')" aria-label="Filters">
      <svg viewBox="0 0 24 24"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg></button>
    <button class="ms-ic" onclick="msOpen('stats')" aria-label="Statistics">
      <svg viewBox="0 0 24 24"><line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="14"/></svg></button>
  </div>

  <div class="ms-chips" id="ms-chips"></div>
  <div class="ms-carousel" id="ms-car"></div>
  <div class="ms-dots" id="ms-dots"></div>

  <button class="ms-run" onclick="msRunAll()" id="ms-runall">
    <svg viewBox="0 0 24 24"><polygon points="6 3 20 12 6 21 6 3"/></svg><span>Run All</span></button>

  <nav class="ms-nav" id="ms-nav"></nav>

  <div class="ms-scrim" id="ms-scrim" onclick="msClose()"></div>
  <div class="ms-sheet" id="ms-filter">
    <div class="ms-grip"></div>
    <h3>Filters</h3><div class="sub" id="ms-filter-sub">Refine this category</div>
    <div id="ms-filter-fields"></div>
    <button class="ms-apply" onclick="msApply()">Apply filters</button>
  </div>
  <div class="ms-sheet" id="ms-stats">
    <div class="ms-grip"></div>
    <h3>Statistics</h3><div class="sub">This session</div>
    <div class="ms-stats" id="ms-stats-body"></div>
  </div>
</div>

<script>
(function(){
  var CAT_META={Jobs:{ic:'💼',l:'Jobs'},University:{ic:'🎓',l:'Edu'},
    Visa:{ic:'🛂',l:'Visa'},Automobiles:{ic:'🚗',l:'Cars'},Leads:{ic:'🧲',l:'Leads'}};
  var FILTER_SCHEMA={
    Jobs:[{k:'country',l:'Country',t:'select',o:['Any','UAE','USA','UK','Canada','Germany','Australia']},
          {k:'role',l:'Role',t:'text'},{k:'salary',l:'Min Salary',t:'number'},
          {k:'experience',l:'Experience',t:'select',o:['Any','Entry','Mid','Senior']},
          {k:'jobtype',l:'Job Type',t:'select',o:['Any','Full-time','Part-time','Remote','Contract']}],
    University:[{k:'country',l:'Country',t:'text'},{k:'university',l:'University',t:'text'},
          {k:'ranking',l:'Ranking',t:'select',o:['Any','Top 100','Top 500','Top 1000']},
          {k:'scholarship',l:'Scholarship',t:'select',o:['Any','Yes','No']},
          {k:'degree',l:'Degree',t:'select',o:['Any','Bachelor','Master','PhD']}],
    Visa:[{k:'country',l:'Country',t:'text'},{k:'visatype',l:'Visa Type',t:'text'},
          {k:'sponsor',l:'Sponsor',t:'select',o:['Any','Yes','No']},{k:'occupation',l:'Occupation',t:'text'}],
    Automobiles:[{k:'brand',l:'Brand',t:'text'},{k:'model',l:'Model',t:'text'},
          {k:'price',l:'Max Price',t:'number'},{k:'year',l:'Year',t:'number'}],
    Leads:[{k:'industry',l:'Industry',t:'text'},{k:'location',l:'Location',t:'text'}]
  };
  var ALL=[], CATS=[], cat=null, items=[], filters={}, stats={rows:0,pass:0,fail:0,lat:[]};

  function $(id){return document.getElementById(id);}
  function esc(s){return (s||'').replace(/[<>&]/g,function(c){return {'<':'&lt;','>':'&gt;','&':'&amp;'}[c];});}

  fetch('/api/scrapers').then(function(r){return r.json();}).then(function(d){
    ALL=d.scrapers||[]; CATS=(d.categories||[]).filter(function(c){return ALL.some(function(s){return s.category===c;});});
    renderNav(); selectCat(CATS[0]);
  }).catch(function(){});

  function renderNav(){
    $('ms-nav').innerHTML=CATS.map(function(c){var m=CAT_META[c]||{ic:'•',l:c};
      return '<button class="ms-nav-i" data-c="'+c+'" onclick="msCat(\''+c+'\')"><span class="ic">'+m.ic+'</span>'+m.l+'</button>';}).join('');
  }
  window.msCat=function(c){selectCat(c);};

  function selectCat(c){
    cat=c; items=ALL.filter(function(s){return s.category===c;});
    document.querySelectorAll('.ms-nav-i').forEach(function(n){n.classList.toggle('on',n.getAttribute('data-c')===c);});
    $('ms-chips').innerHTML=items.map(function(s,i){
      return '<div class="ms-chip'+(i===0?' on':'')+'" data-i="'+i+'" onclick="msGo('+i+')">'+esc(s.name)+'</div>';}).join('');
    $('ms-car').innerHTML=items.map(function(s,i){
      return '<div class="ms-slide"><div class="ms-card">'+
        '<div class="ms-card-top"><div class="ms-card-emoji">'+(s.emoji||'🔎')+'</div>'+
        '<div><div class="ms-card-name">'+esc(s.name)+'</div><div class="ms-card-bot">'+esc(s.bot)+'</div></div></div>'+
        '<span class="ms-pill">'+esc(s.mode||'')+'</span>'+
        '<div class="ms-card-body" id="ms-body-'+i+'"><div class="ms-card-bot">Tap Run to fetch live results.</div></div>'+
        '<button class="ms-card-run" id="ms-run-'+i+'" onclick="msRun('+i+')">Run source ▶</button>'+
        '</div></div>';}).join('');
    renderDots(); $('ms-car').scrollLeft=0;
  }

  function renderDots(){
    $('ms-dots').innerHTML=items.map(function(_,i){return '<div class="ms-dot'+(i===0?' on':'')+'"></div>';}).join('');
  }
  function activeIndex(){var w=$('ms-car').clientWidth||1;return Math.round($('ms-car').scrollLeft/w);}
  $('ms-car')&&$('ms-car').addEventListener('scroll',function(){
    var i=activeIndex();
    document.querySelectorAll('.ms-dot').forEach(function(d,k){d.classList.toggle('on',k===i);});
    document.querySelectorAll('.ms-chip').forEach(function(c,k){c.classList.toggle('on',k===i);});
    var chip=document.querySelectorAll('.ms-chip')[i]; if(chip)chip.scrollIntoView({inline:'center',block:'nearest',behavior:'smooth'});
  },{passive:true});
  window.msGo=function(i){var w=$('ms-car').clientWidth;$('ms-car').scrollTo({left:i*w,behavior:'smooth'});};

  function matchFilter(rec){
    var vals=Object.keys(filters).map(function(k){return (filters[k]||'').toString().toLowerCase();})
      .filter(function(v){return v && v!=='any' && v!=='0';});
    if(!vals.length) return true;
    var hay=((rec.title||'')+' '+(rec.description||'')+' '+(rec.location||'')+' '+JSON.stringify(rec.metadata||{})).toLowerCase();
    return vals.every(function(v){return hay.indexOf(v)>=0;});
  }

  window.msRun=function(i){
    var s=items[i]; if(!s)return;
    var b=$('ms-run-'+i); b.classList.add('busy'); b.textContent='Running…';
    var t0=Date.now();
    fetch('/api/run/'+s.index).then(function(r){return r.json();}).then(function(d){
      var el=((Date.now()-t0)/1000);
      var ok=d.status==='ok'; stats.lat.push(d.elapsed||el);
      if(ok){stats.pass++;} else {stats.fail++;}
      var res=(d.results||[]).filter(matchFilter);
      stats.rows+=res.length;
      var body=res.slice(0,4).map(function(r){
        var loc=(r.location||(r.metadata||{}).country||'');
        return '<div class="ms-res">'+esc((r.title||'').slice(0,70))+(loc?'<div class="r2">📍 '+esc(loc)+'</div>':'')+'</div>';}).join('');
      $('ms-body-'+i).innerHTML='<div class="ms-card-bot"><span class="ms-count">'+res.length+'</span> results · '+(d.elapsed||el.toFixed(1))+'s</div>'+body;
      b.classList.remove('busy'); b.textContent='Run again ↻';
    }).catch(function(){b.classList.remove('busy'); b.textContent='Retry';});
  };

  window.msRunAll=function(){
    var rb=$('ms-runall'); rb.querySelector('span').textContent='Running…';
    var idx=0; (function next(){ if(idx>=items.length){rb.querySelector('span').textContent='Run All'; return;}
      var i=idx++; msRun(i); setTimeout(next, 1200); })();
  };

  // bottom sheets
  window.msOpen=function(which){
    if(which==='filter'){
      $('ms-filter-sub').textContent='Refine '+ (CAT_META[cat]?CAT_META[cat].l:cat);
      var sc=FILTER_SCHEMA[cat]||[];
      $('ms-filter-fields').innerHTML=sc.map(function(f){
        if(f.t==='select') return '<div class="ms-field"><label>'+f.l+'</label><select id="mf_'+f.k+'">'+
          (f.o||[]).map(function(o){return '<option>'+o+'</option>';}).join('')+'</select></div>';
        return '<div class="ms-field"><label>'+f.l+'</label><input id="mf_'+f.k+'" type="'+(f.t||'text')+'" placeholder="'+f.l+'"/></div>';
      }).join('');
      $('ms-filter').classList.add('on');
    } else { renderStats(); $('ms-stats').classList.add('on'); }
    $('ms-scrim').classList.add('on');
  };
  window.msClose=function(){$('ms-scrim').classList.remove('on');$('ms-filter').classList.remove('on');$('ms-stats').classList.remove('on');};
  window.msApply=function(){
    filters={}; (FILTER_SCHEMA[cat]||[]).forEach(function(f){var el=$('mf_'+f.k); if(el)filters[f.k]=el.value;});
    msClose();
  };
  function renderStats(){
    var avg=stats.lat.length?(stats.lat.reduce(function(a,b){return a+b;},0)/stats.lat.length):0;
    $('ms-stats-body').innerHTML=
      '<div class="ms-stat"><div class="v">'+stats.rows+'</div><div class="l">Rows Extracted</div></div>'+
      '<div class="ms-stat"><div class="v">'+stats.pass+'</div><div class="l">Sources Passed</div></div>'+
      '<div class="ms-stat"><div class="v">'+stats.fail+'</div><div class="l">Sources Failed</div></div>'+
      '<div class="ms-stat"><div class="v">'+avg.toFixed(1)+'s</div><div class="l">Avg Latency</div></div>';
  }
})();
</script>
"""
