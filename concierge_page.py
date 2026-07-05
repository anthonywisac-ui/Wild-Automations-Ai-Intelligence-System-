"""Self-contained mobile-first AI Concierge page (served at GET /concierge)."""

CONCIERGE_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<title>Wild Automations — AI Concierge</title>
<style>
  :root{
    --bg:#0a0a0b; --surface:#141416; --surface2:#1b1b1f; --line:#2a2a30;
    --text:#f4f2ea; --muted:#9a978c; --gold:#e9c766; --gold2:#c9a13a;
    --radius:16px; --pad:18px;
  }
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  body{margin:0;background:var(--bg);color:var(--text);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    padding:0 var(--pad) 120px;max-width:520px;margin:0 auto;font-size:16px}
  header{position:sticky;top:0;background:linear-gradient(180deg,var(--bg) 70%,transparent);
    padding:16px 0 12px;z-index:20;display:flex;align-items:center;gap:10px}
  .logo{width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,var(--gold),var(--gold2));
    display:grid;place-items:center;color:#000;font-weight:800}
  header h1{font-size:17px;margin:0;letter-spacing:.3px}
  header .sub{font-size:12px;color:var(--muted)}
  .live{width:8px;height:8px;border-radius:50%;background:#39d353;box-shadow:0 0 8px #39d353;margin-left:auto}
  h2{font-size:14px;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);margin:22px 4px 12px}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  .persona{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
    padding:18px 14px;text-align:left;cursor:pointer;transition:.18s;min-height:96px}
  .persona:active{transform:scale(.97)}
  .persona.sel{border-color:var(--gold);box-shadow:0 0 0 1px var(--gold),0 8px 24px rgba(233,199,102,.12)}
  .persona .ic{font-size:26px}
  .persona .nm{font-weight:700;margin-top:8px;font-size:15px}
  .persona .ds{font-size:12px;color:var(--muted);margin-top:3px;line-height:1.35}
  .card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:16px;margin:12px 0}
  label{display:block;font-size:13px;color:var(--muted);margin:12px 0 6px}
  input,textarea,select{width:100%;background:var(--surface2);border:1px solid var(--line);
    color:var(--text);border-radius:12px;padding:14px;font-size:16px;min-height:50px}
  textarea{min-height:110px;resize:vertical}
  .btn{width:100%;min-height:52px;border:none;border-radius:14px;font-size:16px;font-weight:700;
    cursor:pointer;margin-top:16px;background:linear-gradient(135deg,var(--gold),var(--gold2));color:#000;
    box-shadow:0 6px 20px rgba(233,199,102,.25)}
  .btn:active{transform:scale(.98)}
  .btn.ghost{background:transparent;border:1px solid var(--gold);color:var(--gold);box-shadow:none}
  .res{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:14px;margin:10px 0}
  .res .t{font-weight:700;font-size:15px}
  .res .m{font-size:13px;color:var(--muted);margin-top:4px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
  .chip{background:rgba(233,199,102,.14);color:var(--gold);border-radius:999px;padding:3px 9px;font-size:12px;font-weight:600}
  .res a{color:var(--gold);text-decoration:none;font-size:13px}
  .muted{color:var(--muted);font-size:14px}
  .spin{display:inline-block;width:18px;height:18px;border:2px solid var(--line);border-top-color:var(--gold);
    border-radius:50%;animation:sp .8s linear infinite;vertical-align:middle}
  @keyframes sp{to{transform:rotate(360deg)}}
  /* chat dock */
  .dock{position:fixed;left:0;right:0;bottom:0;max-width:520px;margin:0 auto;background:var(--surface);
    border-top:1px solid var(--line);padding:10px 14px calc(10px + env(safe-area-inset-bottom));display:flex;gap:8px;z-index:30}
  .dock input{min-height:46px}
  .dock .btn{width:auto;margin:0;padding:0 18px;min-height:46px}
  #chatlog{margin:10px 0}
  .bubble{max-width:85%;padding:10px 13px;border-radius:14px;margin:6px 0;font-size:14px;line-height:1.4}
  .bubble.ai{background:var(--surface2);border:1px solid var(--line)}
  .bubble.me{background:linear-gradient(135deg,var(--gold),var(--gold2));color:#000;margin-left:auto}
  @media(min-width:560px){ .grid{grid-template-columns:1fr 1fr 1fr 1fr} }
</style>
</head>
<body>
<header>
  <div class="logo">W</div>
  <div><h1>AI Concierge</h1><div class="sub">Wild Automations</div></div>
  <div class="live"></div>
</header>

<h2>What do you need?</h2>
<div class="grid" id="personas"></div>
<button class="btn ghost" style="margin-top:12px" onclick="helpChoose()">🤔 Not sure? Let AI help me choose</button>

<div id="intake"></div>
<div id="results"></div>

<h2 style="margin-top:26px">Ask anything</h2>
<div id="chatlog"></div>

<input type="file" id="cvfile" accept=".pdf,.doc,.docx,.txt" style="display:none" onchange="uploadCV(this)"/>
<div class="dock">
  <button class="btn ghost" style="padding:0 14px" onclick="document.getElementById('cvfile').click()" title="Upload CV">📎</button>
  <input id="chatin" placeholder="Tell me what you need…" autocomplete="off"/>
  <button class="btn" onclick="sendChat()">Send</button>
</div>

<script>
let PERSONAS=[], selected=null, lastRun=null;

async function j(url,opts){const r=await fetch(url,opts);return r.json();}

async function loadPersonas(){
  const d=await j('/api/concierge/personas');
  PERSONAS=d.personas||[];
  document.getElementById('personas').innerHTML=PERSONAS.map(p=>
    `<div class="persona" data-id="${p.id}" onclick="pick('${p.id}')">
       <div class="ic">${p.icon}</div><div class="nm">${p.label}</div>
       <div class="ds">${p.intro}</div></div>`).join('');
}

function pick(id){
  selected=PERSONAS.find(p=>p.id===id);
  document.querySelectorAll('.persona').forEach(e=>e.classList.toggle('sel',e.dataset.id===id));
  document.getElementById('results').innerHTML='';
  const q=selected.questions.map(qq=>{
    const req=qq.required===false?' <span class="muted">(optional)</span>':'';
    if(qq.type==='textarea') return `<label>${qq.label}${req}</label><textarea id="f_${qq.key}" placeholder="${qq.example||''}"></textarea>`;
    if(qq.type==='select') return `<label>${qq.label}${req}</label><select id="f_${qq.key}">`+
      (qq.options||[]).map(o=>`<option>${o}</option>`).join('')+`</select>`;
    return `<label>${qq.label}${req}</label><input id="f_${qq.key}" placeholder="${qq.example||''}"/>`+sugChips(selected.id,qq.key);
  }).join('');
  document.getElementById('intake').innerHTML=
    `<div class="card"><div style="font-weight:700">${selected.icon} ${selected.label}</div>
     ${q}<button class="btn" onclick="runIt()" id="runbtn">Find matches ▶</button></div>`;
  document.getElementById('intake').scrollIntoView({behavior:'smooth'});
}

// tap-able suggestions so users who don't know exact info can just pick
const SUGG={
  student:{country:['United Kingdom','USA','Canada','Germany','Australia','UAE'],
           field:['Computer Science','Business','Engineering','Medicine','Data Science','Law']},
  job_seeker:{role:['Software Engineer','Accountant','Marketing Manager','Nurse','Sales Executive','Civil Engineer'],
              location:['Dubai','Abu Dhabi','Remote','London','Riyadh']},
  travel_agent:{nationality:['India','Pakistan','Nigeria','Philippines','Egypt'],
                destination:['Canada','United Kingdom','Germany','Australia','UAE']},
  car_dealer:{make:['Toyota','BMW','Mercedes','Honda','Nissan','Audi'],
              model:['Camry','Corolla','X5','Civic','Patrol']}
};
function sugChips(pid,key){
  const s=(SUGG[pid]||{})[key];if(!s)return '';
  return `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px">`+
    s.map(v=>`<span class="chip" style="cursor:pointer" onclick="fillF('${key}','${v.replace(/'/g,"")}')">${v}</span>`).join('')+`</div>`;
}
function fillF(key,val){const el=document.getElementById('f_'+key);if(el)el.value=val;}

async function helpChoose(){
  bubble("I'm not sure what I need — help me choose.","me");
  const d=await j('/api/concierge/chat',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({message:"I'm not sure what I need. Ask me 1-2 short questions to help me choose between Student/Admission, Job Seeker, Travel Agent, or Car Dealer, then tell me which to tap."})});
  bubble(d.reply||'Tell me: are you looking to study, find a job, travel/visa, or buy/sell cars?','ai');
  document.getElementById('chatin').scrollIntoView({behavior:'smooth'});
}

function answers(){const a={};selected.questions.forEach(q=>{const el=document.getElementById('f_'+q.key);if(el)a[q.key]=el.value;});return a;}

async function runIt(){
  const b=document.getElementById('runbtn'); b.innerHTML='<span class="spin"></span> Searching…'; b.disabled=true;
  const d=await j('/api/concierge/run',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({persona:selected.id,answers:answers()})});
  b.innerHTML='Find matches ▶'; b.disabled=false;
  lastRun={persona:selected.id,requirement:d.requirement,matches:d.matches};
  const R=document.getElementById('results');
  if(d.error){R.innerHTML=`<div class="card muted">Error: ${d.error}</div>`;return;}
  const list=(d.matches||[]).map(m=>{
    const md=m.metadata||{};const loc=m.location||md.country||'';
    const sc=m._match_score!=null?`<span class="chip">${Math.round(m._match_score*100)}% match</span>`:'';
    const link=m.source_url?`<a href="${m.source_url}" target="_blank">Open ↗</a>`:'';
    return `<div class="res"><div class="t">${(m.title||'').slice(0,90)}</div>
      <div class="m">${loc?'📍 '+loc:''} ${sc} ${link}</div></div>`;}).join('');
  R.innerHTML=`<h2>${d.total||0} matches</h2>${list||'<div class="card muted">No strong matches — widen the criteria.</div>'}
    ${(d.matches||[]).length?`<button class="btn ghost" onclick="deliverIt()" id="delbtn">📲 Send top 5 to WhatsApp</button>`:''}`;
  R.scrollIntoView({behavior:'smooth'});
}

async function deliverIt(){
  const b=document.getElementById('delbtn'); b.innerHTML='<span class="spin"></span> Sending…'; b.disabled=true;
  const d=await j('/api/concierge/deliver',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(lastRun)});
  b.innerHTML = d.sent ? '✅ Sent to WhatsApp' : ('⚠️ '+(d.reason||'not configured'));
  b.disabled = d.sent;
}

let CHAT=[];  // conversation history so the assistant never re-asks a known answer
let CTX='';   // profile + jobs already shown → so follow-ups ('why is this good for me') work
function esc(s){return String(s==null?'':s).replace(/[<>&]/g,function(c){return {'<':'&lt;','>':'&gt;','&':'&amp;'}[c];});}
function bubble(t,cls){const el=document.createElement('div');el.className='bubble '+cls;el.innerHTML=(t||'').replace(/\*\*(.+?)\*\*/g,'<b>$1</b>');
  document.getElementById('chatlog').appendChild(el);el.scrollIntoView({behavior:'smooth'});}
async function sendChat(){
  const inp=document.getElementById('chatin');const msg=inp.value.trim();if(!msg)return;
  inp.value='';bubble(msg,'me');CHAT.push({role:'user',content:msg});
  const d=await j('/api/concierge/chat',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({message:msg,history:CHAT,context:CTX})});
  const reply=d.reply||d.error||'…';bubble(reply,'ai');CHAT.push({role:'assistant',content:reply});
  if(d.action){runFromChat(d.action);}
}
async function runFromChat(action){
  bubble('🔎 Searching…','ai');
  const d=await j('/api/concierge/run',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(action)});
  if(d.error){bubble('Sorry — '+d.error,'ai');return;}
  const n=(d.matches||[]).length;
  CTX='Search: '+JSON.stringify(action.answers||{})+'\nJobs shown:\n'+(d.matches||[]).slice(0,8).map(function(m,i){var md=m.metadata||{};return (i+1)+'. '+m.title+' @ '+(md.company||'')+' ('+m.location+') — '+(md.why||'');}).join('\n');
  bubble(n?('Found '+d.total+' results — top '+n+' below 👇'):'No strong matches — try a different city or role.','ai');
  const R=document.getElementById('results');
  R.innerHTML='<h2>'+(d.total||0)+' matches</h2>'+(d.matches||[]).map(function(m){
    const md=m.metadata||{};const loc=m.location||md.country||'';
    const sc=m._match_score!=null?'<span class="chip">'+Math.round(m._match_score*100)+'% match</span>':'';
    const link=m.source_url?'<a href="'+m.source_url+'" target="_blank">Open ↗</a>':'';
    return '<div class="res"><div class="t">'+(m.title||'').slice(0,90)+'</div><div class="m">'+(loc?'📍 '+loc:'')+' '+sc+' '+link+'</div></div>';}).join('');
  R.scrollIntoView({behavior:'smooth'});
}
async function uploadCV(input){
  const f=input.files&&input.files[0];if(!f)return;input.value='';
  bubble('📎 '+f.name,'me');bubble('Reading your CV…','ai');
  const fd=new FormData();fd.append('file',f);
  try{
    const r=await fetch('/api/cv/upload',{method:'POST',body:fd});const d=await r.json();
    if(d.error){bubble('Could not read the CV: '+d.error+'. You can paste the text instead.','ai');return;}
    window.CVTEXT=d.cv_text||'';
    bubble('Read your full CV — **'+(d.role||'candidate')+'**'+
      (d.seniority?' · '+d.seniority:'')+(d.years?' · ~'+d.years+' yrs':'')+
      (d.domain?' · '+esc(d.domain):'')+
      (d.summary?'<br><span style="color:var(--muted)">'+esc(d.summary)+'</span>':'')+
      (d.skills&&d.skills.length?'<br><span style="color:var(--muted)">Skills: '+d.skills.slice(0,8).map(esc).join(', ')+'</span>':'')+
      (d.education?'<br><span style="color:var(--muted)">🎓 '+esc(d.education)+'</span>':'')+
      (d.certifications&&d.certifications.length?'<br><span style="color:var(--muted)">📜 '+d.certifications.slice(0,5).map(esc).join(', ')+'</span>':'')+
      '<br>Now matching roles that **truly fit your experience** (reading each job description)…','ai');
    let m;
    try{
      m=await j('/api/cv/match',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({cv_text:d.cv_text||'',role:d.role||'',skills:d.skills||[]})});
    }catch(e2){bubble('Search hit a snag — say "search '+(d.role||'jobs')+' remote" and I\'ll retry.','ai');return;}
    try{renderCVJobs(m);}catch(e3){bubble('Got matches but couldn\'t render them — reload and try again.','ai');}
  }catch(e){bubble('Upload failed. Try pasting your CV text.','ai');}
}
function renderCVJobs(m){
  const n=(m.jobs||[]).length;
  window.CVJOBS=m.jobs||[];
  CTX='Candidate profile: '+(m.role||'')+'. Skills: '+((m.skills||[]).join(', '))+'.\nJobs shown:\n'+
    (m.jobs||[]).slice(0,8).map(function(x,i){return (i+1)+'. '+x.title+' @ '+x.company+' ('+x.location+') — '+(x.why_match||'')+(x.salary&&x.salary!=='—'?' · '+x.salary:'');}).join('\n');
  bubble(n?('Found '+n+' remote roles matching your profile 👇'):'No fully-remote, no-visa matches right now for '+(m.role||'your profile')+'. Try again shortly (sources rotate).','ai');
  const R=document.getElementById('results');
  R.innerHTML='<h2>'+n+' remote matches · '+esc(m.role||'')+'</h2>'+(m.jobs||[]).map(function(x,i){
    var f=x.fit||{};
    var fitRow=(f.skill||f.seniority||f.domain)?
      '<div style="font-size:12px;margin-top:6px;display:flex;flex-wrap:wrap;gap:6px">'+
      (f.skill?'<span class="chip" title="Skills fit">🧩 '+esc(f.skill)+'</span>':'')+
      (f.seniority?'<span class="chip" title="Seniority fit">📈 '+esc(f.seniority)+'</span>':'')+
      (f.domain?'<span class="chip" title="Domain fit">🏢 '+esc(f.domain)+'</span>':'')+
      '</div>':
      '<div style="font-size:12px;color:var(--muted);margin-top:4px">'+esc(x.why_match)+'</div>';
    var tools=window.CVTEXT?
      '<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">'+
      '<button class="chip" style="cursor:pointer;border:0" onclick="gapJob('+i+')">🧩 Gap check</button>'+
      '<button class="chip" style="cursor:pointer;border:0" onclick="tailorJob('+i+')">✍️ Tailor CV</button>'+
      '</div>':'';
    return '<div class="res"><div class="t">'+esc(x.title)+'</div>'+
      '<div class="m"><span class="chip">'+Math.round(x.match*100)+'% match</span> '+esc(x.company)+' · 📍 '+esc(x.location)+'</div>'+
      '<div style="font-size:12px;color:var(--muted);margin-top:6px">🌍 '+esc(x.remote_policy)+' · ✅ '+esc(x.visa)+(x.salary&&x.salary!=='—'?' · 💰 '+esc(x.salary):'')+'</div>'+
      fitRow+
      (x.url?'<div style="margin-top:6px"><a class="chip" style="text-decoration:none" href="'+x.url+'" target="_blank">Apply ↗</a></div>':'')+
      tools+
      '<div id="tool-'+i+'" style="margin-top:8px"></div>'+
      '</div>';}).join('');
  R.scrollIntoView({behavior:'smooth'});
}
async function gapJob(i){
  var x=(window.CVJOBS||[])[i];if(!x)return;
  var box=document.getElementById('tool-'+i);box.innerHTML='<span style="color:var(--muted);font-size:12px">Analyzing gap…</span>';
  try{
    var d=await j('/api/cv/gap',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({cv_text:window.CVTEXT||'',job_description:x.description||'',job_title:x.title||''})});
    if(d.error||(!d.matched.length&&!d.missing.length)){box.innerHTML='<span style="color:var(--muted);font-size:12px">'+esc(d.note||'No gap data.')+'</span>';return;}
    box.innerHTML='<div style="font-size:12px;border-top:1px solid rgba(255,255,255,.06);padding-top:6px">'+
      (d.matched.length?'<div>✅ <b>You have:</b> '+d.matched.map(esc).join(', ')+'</div>':'')+
      (d.missing.length?'<div style="margin-top:4px;color:#f0a">➖ <b>Missing:</b> '+d.missing.map(esc).join(', ')+'</div>':'')+
      (d.suggestions&&d.suggestions.length?'<div style="margin-top:4px;color:var(--muted)">💡 '+d.suggestions.map(esc).join('<br>💡 ')+'</div>':'')+
      '</div>';
  }catch(e){box.innerHTML='<span style="color:var(--muted);font-size:12px">Gap check failed — try again.</span>';}
}
async function tailorJob(i){
  var x=(window.CVJOBS||[])[i];if(!x)return;
  var box=document.getElementById('tool-'+i);box.innerHTML='<span style="color:var(--muted);font-size:12px">Tailoring your CV…</span>';
  try{
    var d=await j('/api/cv/tailor',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({cv_text:window.CVTEXT||'',job_description:x.description||'',job_title:x.title||''})});
    if(d.error||(!d.summary&&!(d.bullets||[]).length)){box.innerHTML='<span style="color:var(--muted);font-size:12px">'+esc(d.note||'No tailoring data.')+'</span>';return;}
    box.innerHTML='<div style="font-size:12px;border-top:1px solid rgba(255,255,255,.06);padding-top:6px">'+
      (d.summary?'<div><b>Summary:</b> '+esc(d.summary)+'</div>':'')+
      ((d.bullets||[]).length?'<ul style="margin:6px 0 0 16px;padding:0">'+d.bullets.map(function(b){return '<li>'+esc(b)+'</li>';}).join('')+'</ul>':'')+
      '</div>';
  }catch(e){box.innerHTML='<span style="color:var(--muted);font-size:12px">Tailoring failed — try again.</span>';}
}
document.getElementById('chatin').addEventListener('keydown',e=>{if(e.key==='Enter')sendChat();});
loadPersonas();
</script>
</body></html>"""
