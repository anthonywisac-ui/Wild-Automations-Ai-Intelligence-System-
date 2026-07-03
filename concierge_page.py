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

<div class="dock">
  <input id="chatin" placeholder="Ask the assistant…" autocomplete="off"/>
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

function bubble(t,cls){const el=document.createElement('div');el.className='bubble '+cls;el.textContent=t;
  document.getElementById('chatlog').appendChild(el);el.scrollIntoView({behavior:'smooth'});}
async function sendChat(){
  const inp=document.getElementById('chatin');const msg=inp.value.trim();if(!msg)return;
  inp.value='';bubble(msg,'me');
  const d=await j('/api/concierge/chat',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({message:msg})});
  bubble(d.reply||d.error||'…','ai');
}
document.getElementById('chatin').addEventListener('keydown',e=>{if(e.key==='Enter')sendChat();});
loadPersonas();
</script>
</body></html>"""
