"""
Jobs Dashboard — Wild Automations premium SaaS redesign.
Card-based layout, KPI sparklines, Linear/Stripe inspired.
DO NOT modify API endpoints or business logic.
"""

JOBS_HTML = r"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>Jobs Scrapers — Wild Automations</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#09090B;--surface:#111214;--surface-2:#17181C;
  --border:rgba(255,255,255,.06);--border-solid:#23252B;
  --primary:#F5C842;--primary-hover:#FFD95A;
  --success:#22C55E;--danger:#EF4444;--warning:#F59E0B;--info:#3B82F6;
  --text:#FFFFFF;--text-secondary:#A1A1AA;--text-muted:#71717A;
  --font:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  --radius-card:18px;--radius-btn:14px;--radius-input:16px;--radius-tag:999px;--radius-search:20px;
  --shadow:0 8px 30px rgba(0,0,0,.18);
  --transition:200ms ease;
}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{background:var(--bg);color:var(--text);font-family:var(--font);font-size:16px;line-height:1.5;overflow:hidden;height:100vh}
a{color:inherit;text-decoration:none}
button{font-family:var(--font);cursor:pointer}
::-webkit-scrollbar{width:8px;background:transparent}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,.12);border-radius:4px}

/* ── Layout ── */
.wrap{display:flex;height:100vh;overflow:hidden}

/* ── Sidebar ── */
.side{
  width:250px;min-width:250px;background:#0D0D0F;
  border-right:1px solid var(--border-solid);
  display:flex;flex-direction:column;flex-shrink:0;overflow:hidden;
}
.brand{
  display:flex;align-items:center;gap:12px;
  padding:24px 20px 20px;border-bottom:1px solid var(--border-solid);
}
.brand-logo{
  width:36px;height:36px;border-radius:10px;flex-shrink:0;
  background:linear-gradient(135deg,#F5C842,#B8860B);
  display:grid;place-items:center;font-size:16px;font-weight:700;color:#000;
}
.brand-name{font-size:12px;font-weight:700;letter-spacing:2px;color:var(--text);text-transform:uppercase}
.brand-sub{font-size:11px;color:var(--text-muted);margin-top:1px}
.nav{padding:12px 10px;flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:2px}
.nav-section{font-size:11px;font-weight:600;color:var(--text-muted);letter-spacing:1px;text-transform:uppercase;padding:12px 14px 6px}
.ni{
  display:flex;align-items:center;gap:10px;
  padding:0 14px;height:44px;border-radius:10px;
  font-size:14px;font-weight:500;color:var(--text-secondary);
  cursor:pointer;transition:background var(--transition);position:relative;
}
.ni:hover{background:rgba(255,255,255,.04)}
.ni.on{background:rgba(245,200,66,.06);color:var(--text)}
.ni.on::before{content:'';position:absolute;left:-10px;top:50%;transform:translateY(-50%);width:3px;height:22px;background:var(--primary);border-radius:0 3px 3px 0}
.ni.on svg{stroke:var(--primary)}
.ni svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:1.75;flex-shrink:0}
.nav-sep{height:1px;background:var(--border-solid);margin:8px 10px}
.prof{
  display:flex;align-items:center;gap:12px;
  padding:16px 20px;border-top:1px solid var(--border-solid);
}
.prof-av{
  width:32px;height:32px;border-radius:8px;flex-shrink:0;
  background:linear-gradient(135deg,#F5C842,#7a5800);
  display:grid;place-items:center;font-size:11px;font-weight:700;color:#000;
}
.prof-info{flex:1;min-width:0}
.prof-name{font-size:13px;font-weight:600;color:var(--text)}
.prof-email{font-size:12px;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.prof-upgrade{font-size:11px;color:var(--text-muted);cursor:pointer;transition:color var(--transition)}
.prof-upgrade:hover{color:var(--primary)}

/* ── Main ── */
.main{flex:1;display:flex;flex-direction:column;min-width:0;overflow:hidden}

/* ── Top Nav ── */
.topnav{
  display:flex;align-items:center;gap:16px;
  padding:0 24px;height:72px;min-height:72px;
  border-bottom:1px solid var(--border-solid);background:transparent;
}
.topnav-left{display:flex;align-items:center;gap:10px;flex:1}
.topnav-status{width:8px;height:8px;border-radius:50%;background:var(--success);box-shadow:0 0 8px var(--success);flex-shrink:0}
.topnav-title{font-size:18px;font-weight:600;color:var(--text)}
.topnav-sub{font-size:13px;color:var(--text-muted);margin-left:4px}
.topnav-right{display:flex;align-items:center;gap:8px}
.topnav-pill{
  padding:6px 12px;border-radius:var(--radius-tag);
  background:var(--surface);border:1px solid var(--border-solid);
  font-size:12px;color:var(--text-secondary);white-space:nowrap;
}
.topnav-last{font-size:12px;color:var(--text-muted);white-space:nowrap}
.icon-btn{
  width:36px;height:36px;border-radius:10px;background:none;
  border:1px solid var(--border-solid);color:var(--text-muted);
  display:grid;place-items:center;transition:all var(--transition);
}
.icon-btn:hover{border-color:rgba(255,255,255,.12);color:var(--text)}
.icon-btn svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:1.75}
.run-btn{
  display:inline-flex;align-items:center;gap:8px;
  padding:8px 20px;border:none;border-radius:var(--radius-btn);
  background:var(--primary);color:#000;font-size:14px;font-weight:600;
  transition:all var(--transition);white-space:nowrap;
}
.run-btn:hover{background:var(--primary-hover);transform:scale(1.02)}
.run-btn svg{width:12px;height:12px;fill:#000}
.avatar-btn{
  width:36px;height:36px;border-radius:10px;
  background:linear-gradient(135deg,#F5C842,#7a5800);
  display:grid;place-items:center;font-size:12px;font-weight:700;color:#000;
  flex-shrink:0;
}

/* ── Search Bar ── */
.searchrow{
  display:flex;align-items:center;gap:12px;
  padding:16px 24px 8px;
}
.search-bar{
  flex:1;height:56px;display:flex;align-items:center;gap:0;
  background:var(--surface);border:1px solid var(--border-solid);
  border-radius:var(--radius-search);overflow:hidden;
  transition:border-color var(--transition);
}
.search-bar:focus-within{border-color:rgba(245,200,66,.4)}
.search-bar-icon{padding:0 16px;flex-shrink:0}
.search-bar-icon svg{width:18px;height:18px;stroke:var(--text-muted);fill:none;stroke-width:1.75;display:block}
.search-bar input{
  flex:1;background:none;border:none;color:var(--text);
  font-size:15px;font-family:var(--font);outline:none;min-width:0;
}
.search-bar input::placeholder{color:var(--text-muted)}
.search-divider{width:1px;height:28px;background:var(--border-solid);flex-shrink:0}
.search-location{
  display:flex;align-items:center;gap:8px;padding:0 16px;
  font-size:14px;color:var(--text-secondary);white-space:nowrap;cursor:pointer;flex-shrink:0;
}
.search-location svg{width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:1.75}
.search-btn{
  height:56px;padding:0 24px;border:none;border-radius:0 var(--radius-search) var(--radius-search) 0;
  background:var(--primary);color:#000;font-size:14px;font-weight:600;
  transition:background var(--transition);flex-shrink:0;
}
.search-btn:hover{background:var(--primary-hover)}
.search-filter-btn{
  display:none;width:56px;height:56px;border-radius:var(--radius-input);
  background:var(--surface);border:1px solid var(--border-solid);
  color:var(--text-muted);align-items:center;justify-content:center;flex-shrink:0;
}
.search-filter-btn svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:1.75}

/* ── Filter chips ── */
.chips{display:flex;align-items:center;gap:8px;padding:4px 24px 12px;flex-wrap:wrap}
.chip{
  display:inline-flex;align-items:center;gap:6px;
  padding:6px 14px;border-radius:var(--radius-tag);
  border:1px solid var(--border-solid);background:var(--surface);
  font-size:13px;color:var(--text-secondary);cursor:pointer;
  transition:all var(--transition);white-space:nowrap;
}
.chip:hover{border-color:rgba(255,255,255,.12);color:var(--text)}
.chip-sort{margin-left:auto}

/* ── KPI Cards ── */
.kpis{
  display:grid;grid-template-columns:repeat(4,1fr);
  border-top:1px solid var(--border-solid);border-bottom:1px solid var(--border-solid);
}
.kpi{
  display:flex;align-items:center;justify-content:space-between;
  padding:20px 24px;border-right:1px solid var(--border-solid);
  cursor:default;transition:background var(--transition);
}
.kpi:last-child{border-right:none}
.kpi:hover{background:rgba(255,255,255,.02)}
.kpi-left{display:flex;align-items:center;gap:14px}
.kpi-icon{
  width:40px;height:40px;border-radius:10px;flex-shrink:0;
  background:rgba(245,200,66,.08);border:1px solid rgba(245,200,66,.15);
  display:grid;place-items:center;
}
.kpi-icon svg{width:18px;height:18px;stroke:var(--primary);fill:none;stroke-width:1.75}
.kpi-num{font-size:28px;font-weight:700;line-height:1;color:var(--text);letter-spacing:-1px}
.kpi-label{font-size:12px;color:var(--text-muted);margin-top:4px;font-weight:500;text-transform:uppercase;letter-spacing:.5px}
.kpi-trend{font-size:12px;font-weight:600;color:var(--success);margin-top:2px}
.kpi-trend.down{color:var(--danger)}
.kpi-chart{flex-shrink:0;opacity:.7}

/* ── Source Pills ── */
.srcbar{
  display:flex;align-items:center;gap:8px;
  padding:12px 24px;border-bottom:1px solid var(--border-solid);
  overflow-x:auto;-webkit-overflow-scrolling:touch;
}
.srcbar::-webkit-scrollbar{display:none}
.src-pill{
  display:inline-flex;align-items:center;gap:6px;
  padding:6px 14px;border-radius:var(--radius-tag);
  border:1px solid var(--border-solid);background:var(--surface);
  font-size:13px;font-weight:500;color:var(--text-secondary);
  cursor:pointer;white-space:nowrap;transition:all var(--transition);flex-shrink:0;
}
.src-pill:hover{border-color:rgba(255,255,255,.12);color:var(--text)}
.src-pill.active{background:var(--primary);border-color:var(--primary);color:#000;font-weight:600}
.src-pill .dot{width:6px;height:6px;border-radius:50%;background:var(--success);flex-shrink:0}
.src-sort{margin-left:auto;flex-shrink:0;display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border-radius:var(--radius-tag);border:1px solid var(--border-solid);background:var(--surface);font-size:13px;color:var(--text-secondary);cursor:pointer;white-space:nowrap}

/* ── Body ── */
.body{flex:1;display:flex;min-height:0;overflow:hidden}
.jobs-wrap{flex:1;overflow-y:auto;padding:0}

/* ── Job Cards ── */
.jobs-list{display:flex;flex-direction:column;gap:0}
.job-card{
  display:flex;align-items:center;gap:16px;
  padding:16px 24px;min-height:80px;
  border-bottom:1px solid var(--border-solid);
  cursor:pointer;transition:all var(--transition);
  position:relative;
}
.job-card:hover{background:rgba(255,255,255,.025);transform:translateY(-1px)}
.job-card.sel{background:rgba(245,200,66,.05)}
.job-card.sel::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--primary);border-radius:0 3px 3px 0}
.job-logo{width:44px;height:44px;border-radius:12px;object-fit:cover;flex-shrink:0;background:var(--surface-2);border:1px solid var(--border-solid)}
.logo-fb{
  width:44px;height:44px;border-radius:12px;flex-shrink:0;
  display:grid;place-items:center;font-size:17px;font-weight:700;color:#000;border:1px solid var(--border-solid);
}
.job-body{flex:1;min-width:0;display:flex;flex-direction:column;gap:4px}
.job-top{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.job-company{font-size:14px;font-weight:600;color:var(--text)}
.job-source{font-size:11px;color:var(--text-muted);padding:2px 8px;border-radius:var(--radius-tag);background:var(--surface-2);border:1px solid var(--border-solid)}
.tag-visa{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:600;color:var(--success);background:rgba(34,197,94,.1);border-radius:var(--radius-tag);padding:2px 8px}
.tag-remote{font-size:11px;font-weight:600;color:var(--info);background:rgba(59,130,246,.1);border-radius:var(--radius-tag);padding:2px 8px}
.tag-ai{font-size:11px;font-weight:600;color:var(--primary);background:rgba(245,200,66,.1);border-radius:var(--radius-tag);padding:2px 8px}
.job-title{font-size:15px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.job-meta{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.job-meta-item{display:flex;align-items:center;gap:5px;font-size:13px;color:var(--text-secondary)}
.job-meta-item svg{width:14px;height:14px;stroke:currentColor;fill:none;stroke-width:1.75;flex-shrink:0}
.job-right{display:flex;flex-direction:column;align-items:flex-end;gap:8px;flex-shrink:0}
.job-posted{font-size:12px;color:var(--text-muted)}
.bookmark-btn{
  background:none;border:none;color:var(--text-muted);font-size:18px;
  transition:color var(--transition);line-height:1;padding:4px;
}
.bookmark-btn.on{color:var(--primary)}
.bookmark-btn:hover{color:var(--text)}
.job-salary{font-size:13px;font-weight:600;color:var(--text);white-space:nowrap}

/* ── Empty / Loading / Error ── */
.center-msg{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:12px;color:var(--text-muted);padding:60px}
.spin{display:inline-block;width:20px;height:20px;border:2px solid var(--border-solid);border-top-color:var(--primary);border-radius:50%;animation:sp .8s linear infinite}
.spin-lg{width:36px;height:36px;border-width:3px}
@keyframes sp{to{transform:rotate(360deg)}}

/* ── Pagination ── */
.pager{
  display:flex;align-items:center;gap:10px;
  padding:14px 24px;border-top:1px solid var(--border-solid);
  font-size:13px;color:var(--text-muted);
}
.pager-info{flex:1}
.pg-btn{
  width:32px;height:32px;border-radius:8px;
  border:1px solid var(--border-solid);background:none;
  color:var(--text-muted);font-size:14px;
  transition:all var(--transition);display:grid;place-items:center;
}
.pg-btn:hover{border-color:rgba(255,255,255,.12);color:var(--text)}
.pg-num{font-size:13px;color:var(--text-secondary);padding:0 8px}

/* ── Details Panel ── */
.details{
  width:380px;min-width:380px;flex-shrink:0;
  border-left:1px solid var(--border-solid);
  background:var(--surface);display:flex;flex-direction:column;overflow:hidden;
}
.details.empty{align-items:center;justify-content:center;color:var(--text-muted);text-align:center;gap:12px}
.d-empty-icon{width:48px;height:48px;border-radius:14px;background:var(--surface-2);border:1px solid var(--border-solid);display:grid;place-items:center;margin:0 auto}
.d-empty-icon svg{width:22px;height:22px;stroke:var(--text-muted);fill:none;stroke-width:1.75}
.d-header{
  display:flex;align-items:center;justify-content:space-between;
  padding:16px 20px;border-bottom:1px solid var(--border-solid);flex-shrink:0;
}
.d-header h2{font-size:16px;font-weight:600;color:var(--text)}
.d-close{
  background:none;border:none;color:var(--text-muted);
  width:32px;height:32px;border-radius:8px;display:grid;place-items:center;
  transition:all var(--transition);
}
.d-close:hover{background:rgba(255,255,255,.06);color:var(--text)}
.d-close svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:2}
.d-scroll{flex:1;overflow-y:auto;padding:20px}
.d-company-row{display:flex;align-items:center;gap:12px;margin-bottom:16px}
.d-co-logo{width:48px;height:48px;border-radius:14px;object-fit:cover;background:var(--surface-2);border:1px solid var(--border-solid);flex-shrink:0}
.d-co-logo-fb{width:48px;height:48px;border-radius:14px;flex-shrink:0;display:grid;place-items:center;font-size:19px;font-weight:700;color:#000;border:1px solid var(--border-solid)}
.d-co-name{font-size:15px;font-weight:600;color:var(--text)}
.d-co-badge{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:600;color:var(--primary);background:rgba(245,200,66,.1);border-radius:var(--radius-tag);padding:2px 8px;margin-top:2px}
.d-co-badge svg{width:12px;height:12px;stroke:currentColor;fill:none;stroke-width:2}
.d-rating{display:flex;align-items:center;gap:4px;font-size:12px;color:var(--text-secondary);margin-top:4px}
.d-stars{color:var(--warning);font-size:13px;letter-spacing:1px}
.d-title{font-size:22px;font-weight:700;color:var(--text);line-height:1.2;margin-bottom:6px;letter-spacing:-.3px}
.d-location{font-size:14px;color:var(--text-secondary);display:flex;align-items:center;gap:6px}
.d-location svg{width:14px;height:14px;stroke:currentColor;fill:none;stroke-width:1.75}
.d-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:16px 0;padding:16px 0;border-top:1px solid var(--border-solid);border-bottom:1px solid var(--border-solid)}
.d-meta-item .k{font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;font-weight:500}
.d-meta-item .v{font-size:14px;font-weight:600;color:var(--text);margin-top:4px}
.d-section-title{font-size:14px;font-weight:600;color:var(--text);margin:18px 0 10px;display:flex;align-items:center;gap:6px}
.d-section-title svg{width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:1.75;color:var(--text-muted)}
.d-sponsor-ok{
  padding:14px;border-radius:var(--radius-card);margin-bottom:14px;
  background:rgba(34,197,94,.07);border:1px solid rgba(34,197,94,.2);
}
.d-sponsor-ok .h{display:flex;align-items:center;gap:8px;font-size:14px;font-weight:600;color:var(--success);margin-bottom:6px}
.d-sponsor-ok .h svg{width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:2}
.d-sponsor-ok .r{font-size:13px;color:var(--text-secondary);line-height:1.5}
.d-sponsor-no{
  padding:12px 14px;border-radius:12px;margin-bottom:14px;
  background:var(--surface-2);border:1px solid var(--border-solid);
  font-size:13px;color:var(--text-muted);
}
.d-scores{display:flex;gap:10px;margin-bottom:16px}
.d-score{
  flex:1;background:var(--surface-2);border:1px solid var(--border-solid);
  border-radius:12px;padding:12px;
}
.d-score .v{font-size:22px;font-weight:700;color:var(--primary);line-height:1}
.d-score .k{font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;margin-top:4px}
.d-progress-row{margin-bottom:12px}
.d-progress-label{display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;color:var(--text-secondary)}
.d-progress-label span:last-child{font-weight:600;color:var(--text)}
.d-progress{height:8px;border-radius:999px;background:var(--surface-2);overflow:hidden}
.d-progress-bar{height:100%;border-radius:999px;background:linear-gradient(90deg,#22C55E,#16a34a);transition:width .6s ease}
.d-p{font-size:14px;color:var(--text-secondary);line-height:1.6;margin-bottom:12px}
.d-bullet{display:flex;gap:10px;font-size:13px;color:var(--text-secondary);line-height:1.5;margin-bottom:8px}
.d-bullet-dot{color:var(--primary);flex-shrink:0;margin-top:2px}
.d-evidence{font-size:12px;color:var(--text-muted);line-height:1.5;padding:10px 12px;background:var(--surface-2);border-radius:8px;border:1px solid var(--border-solid);margin-top:8px}
.d-footer{
  display:flex;align-items:center;gap:8px;
  padding:14px 20px;border-top:1px solid var(--border-solid);flex-shrink:0;
}
.d-save-btn{
  display:flex;align-items:center;gap:6px;font-size:13px;font-weight:600;
  color:var(--text-muted);background:none;border:1px solid var(--border-solid);
  border-radius:var(--radius-btn);padding:8px 14px;
  transition:all var(--transition);
}
.d-save-btn:hover{border-color:rgba(255,255,255,.12);color:var(--text)}
.d-share-btn{
  display:flex;align-items:center;gap:6px;font-size:13px;font-weight:600;
  color:var(--text-secondary);background:none;border:1px solid var(--border-solid);
  border-radius:var(--radius-btn);padding:8px 14px;transition:all var(--transition);
}
.d-share-btn:hover{border-color:rgba(255,255,255,.12);color:var(--text)}
.d-apply-btn{
  flex:1;display:flex;align-items:center;justify-content:center;gap:8px;
  padding:10px 20px;border:none;border-radius:var(--radius-btn);
  background:var(--primary);color:#000;font-size:14px;font-weight:600;
  transition:all var(--transition);
}
.d-apply-btn:hover{background:var(--primary-hover);transform:scale(1.02)}
.d-apply-btn svg{width:14px;height:14px;stroke:#000;fill:none;stroke-width:2.5}

/* ── Mobile Overlay ── */
.mob-scrim{position:fixed;inset:0;background:rgba(9,9,11,.7);backdrop-filter:blur(4px);z-index:180;opacity:0;pointer-events:none;transition:opacity var(--transition)}
body.jnav .mob-scrim{opacity:1;pointer-events:auto}

/* ── Mobile Sheet ── */
.jsheet{
  position:fixed;left:0;right:0;bottom:0;z-index:220;
  background:var(--surface);border-top:1px solid var(--border-solid);
  border-radius:22px 22px 0 0;padding:8px 20px calc(24px + env(safe-area-inset-bottom));
  transform:translateY(103%);transition:transform .34s cubic-bezier(.16,1,.3,1);
  max-height:82vh;overflow-y:auto;
}
.jsheet.on{transform:translateY(0)}
.jgrip{width:40px;height:4px;border-radius:2px;background:var(--border-solid);margin:8px auto 16px}
.jsheet h3{font-size:18px;font-weight:600;margin-bottom:16px}
.jf-field{margin-bottom:14px}
.jf-field label{display:block;font-size:12px;color:var(--text-muted);margin-bottom:6px;font-weight:500;text-transform:uppercase;letter-spacing:.5px}
.jf-field select,.jf-field input{
  width:100%;min-height:48px;background:var(--surface-2);
  border:1px solid var(--border-solid);color:var(--text);
  border-radius:var(--radius-input);padding:12px 14px;font-size:15px;font-family:var(--font);
}
.jf-toggle{
  display:flex;align-items:center;gap:12px;padding:12px 14px;
  background:var(--surface-2);border:1px solid var(--border-solid);
  border-radius:12px;margin-bottom:10px;cursor:pointer;font-size:14px;
}
.jf-toggle input{width:18px;height:18px;accent-color:var(--primary)}
.jf-apply{
  width:100%;min-height:52px;border:none;border-radius:var(--radius-btn);
  margin-top:8px;font-weight:600;font-size:16px;color:#000;cursor:pointer;
  background:var(--primary);font-family:var(--font);
  transition:background var(--transition);
}
.jf-apply:hover{background:var(--primary-hover)}

/* ── Drawer extra ── */
.drawer-extra{display:none;padding:14px 16px;border-top:1px solid var(--border-solid)}
.drawer-run{
  width:100%;display:flex;align-items:center;justify-content:center;gap:8px;
  padding:14px;border:none;border-radius:var(--radius-btn);
  background:var(--primary);color:#000;font-size:15px;font-weight:600;
  cursor:pointer;font-family:var(--font);margin-bottom:14px;
}
.drawer-run svg{width:13px;height:13px;fill:#000}

/* ── Mobile header ── */
.mob-btn{
  display:none;width:40px;height:40px;border-radius:11px;
  border:1px solid var(--border-solid);background:none;
  color:var(--text-secondary);align-items:center;justify-content:center;flex-shrink:0;
}
.mob-btn svg{width:19px;height:19px;stroke:currentColor;fill:none;stroke-width:1.75}
.mob-count{display:none;align-items:center;justify-content:space-between;padding:10px 20px 4px;font-size:14px}
.mob-count b{font-size:16px;font-weight:700}
.mob-count span{color:var(--text-muted);font-size:13px}

/* ── Responsive ── */
@media(max-width:1100px){.details{width:340px;min-width:340px}}
@media(max-width:900px){
  .side{
    position:fixed;top:0;left:0;height:100vh;width:82%;max-width:300px;
    z-index:190;transform:translateX(-104%);transition:transform .28s cubic-bezier(.16,1,.3,1);
    box-shadow:var(--shadow);
  }
  body.jnav .side{transform:translateX(0)}
  .drawer-extra{display:block}
  .details{
    position:fixed;inset:0;width:100%;min-width:0;
    z-index:210;transform:translateX(100%);
    transition:transform .3s cubic-bezier(.16,1,.3,1);
  }
  .details.show{transform:translateX(0)}
  .topnav{padding:0 16px;height:60px;min-height:60px}
  .topnav-status,.topnav-sub,.topnav-pill,.topnav-last,.icon-btn,.run-btn,.avatar-btn{display:none!important}
  .topnav-title{font-size:17px}
  .mob-btn{display:flex}
  .searchrow{padding:10px 16px 4px;gap:8px}
  .search-filter-btn{display:flex}
  .search-location{display:none}
  .search-divider{display:none}
  .chips,.kpis,.srcbar{display:none}
  .mob-count{display:flex}
  .job-card{padding:14px 16px}
  .pager{padding:12px 16px}
}
</style></head><body>

<div class="mob-scrim" onclick="jNav(false)"></div>
<div class="wrap">

  <!-- Sidebar -->
  <aside class="side">
    <div class="brand">
      <div class="brand-logo">W</div>
      <div>
        <div class="brand-name">Wild Automations</div>
        <div class="brand-sub">AI-Powered Platform</div>
      </div>
    </div>
    <nav class="nav" id="side-nav"></nav>
    <div class="drawer-extra">
      <button class="drawer-run" onclick="jNav(false);runJobs()">
        <svg viewBox="0 0 24 24"><polygon points="6 3 20 12 6 21 6 3"/></svg>Run Jobs
      </button>
      <div id="drawer-src" style="font-size:12px;color:var(--text-muted)"></div>
    </div>
    <div class="prof">
      <div class="prof-av">WA</div>
      <div class="prof-info">
        <div class="prof-name">Wild Admin</div>
        <div class="prof-email">admin@wild.com</div>
      </div>
      <div class="prof-upgrade">⬆</div>
    </div>
  </aside>

  <!-- Main content -->
  <div class="main">

    <!-- Top nav -->
    <header class="topnav">
      <button class="mob-btn" onclick="jNav(true)" aria-label="Menu">
        <svg viewBox="0 0 24 24"><line x1="3" x2="21" y1="6" y2="6"/><line x1="3" x2="21" y1="12" y2="12"/><line x1="3" x2="21" y1="18" y2="18"/></svg>
      </button>
      <div class="topnav-left">
        <span class="topnav-status"></span>
        <div>
          <span class="topnav-title">Jobs Scrapers</span>
          <span class="topnav-sub">· <span id="agents">20</span> agents across 4 categories</span>
        </div>
      </div>
      <div class="topnav-right">
        <span class="mob-btn" style="display:none" id="mob-bell">
          <svg viewBox="0 0 24 24"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
        </span>
        <span class="topnav-pill">Jobs</span>
        <span class="topnav-last" id="last">Ready</span>
        <button class="icon-btn" aria-label="Theme"><svg viewBox="0 0 24 24"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg></button>
        <button class="icon-btn" aria-label="Notifications"><svg viewBox="0 0 24 24"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg></button>
        <button class="run-btn" onclick="runJobs()" id="runbtn">
          <svg viewBox="0 0 24 24"><polygon points="6 3 20 12 6 21 6 3"/></svg>Run Jobs
        </button>
        <div class="avatar-btn">WA</div>
      </div>
    </header>

    <!-- Search -->
    <div class="searchrow">
      <div class="search-bar">
        <div class="search-bar-icon"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg></div>
        <input id="q" placeholder="Search jobs, companies, skills, locations…" oninput="applyFilter()"/>
        <div class="search-divider"></div>
        <div class="search-location">
          <svg viewBox="0 0 24 24"><path d="M12 21s-7-6-7-11a7 7 0 0 1 14 0c0 5-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>
          Dubai, UAE
        </div>
        <button class="search-btn" onclick="applyFilter()">Search</button>
      </div>
      <button class="search-filter-btn" onclick="jFilterOpen()">
        <svg viewBox="0 0 24 24"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
      </button>
    </div>

    <!-- Filter chips -->
    <div class="chips">
      <span class="chip">Easy apply</span>
      <span class="chip">Salary Range ▾</span>
      <span class="chip">Company Rating ▾</span>
      <span class="chip">Date posted ▾</span>
      <span class="chip">All Filters</span>
      <span class="chip chip-sort">Most Relevant ▾</span>
    </div>

    <!-- KPI cards -->
    <div class="kpis">
      <div class="kpi">
        <div class="kpi-left">
          <div class="kpi-icon"><svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18"/></svg></div>
          <div>
            <div class="kpi-num" id="s-found">0</div>
            <div class="kpi-label">Jobs Found</div>
            <div class="kpi-trend" id="kpi-trend-jobs">+18%</div>
          </div>
        </div>
        <svg class="kpi-chart" width="64" height="32" viewBox="0 0 64 32">
          <defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#22C55E" stop-opacity=".3"/><stop offset="100%" stop-color="#22C55E" stop-opacity="0"/></linearGradient></defs>
          <path d="M0,24 C8,22 16,12 24,14 C32,16 40,6 48,8 C56,10 60,4 64,2" fill="none" stroke="#22C55E" stroke-width="1.5"/>
          <path d="M0,24 C8,22 16,12 24,14 C32,16 40,6 48,8 C56,10 60,4 64,2 L64,32 L0,32Z" fill="url(#g1)"/>
        </svg>
      </div>
      <div class="kpi">
        <div class="kpi-left">
          <div class="kpi-icon"><svg viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h10"/></svg></div>
          <div>
            <div class="kpi-num" id="s-rows">0</div>
            <div class="kpi-label">Sponsors Indexed</div>
            <div class="kpi-trend" id="kpi-trend-sponsors">+12.6%</div>
          </div>
        </div>
        <svg class="kpi-chart" width="64" height="32" viewBox="0 0 64 32">
          <defs><linearGradient id="g2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#3B82F6" stop-opacity=".3"/><stop offset="100%" stop-color="#3B82F6" stop-opacity="0"/></linearGradient></defs>
          <path d="M0,20 C10,18 20,22 30,16 C40,10 50,14 64,8" fill="none" stroke="#3B82F6" stroke-width="1.5"/>
          <path d="M0,20 C10,18 20,22 30,16 C40,10 50,14 64,8 L64,32 L0,32Z" fill="url(#g2)"/>
        </svg>
      </div>
      <div class="kpi">
        <div class="kpi-left">
          <div class="kpi-icon"><svg viewBox="0 0 24 24"><path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="9"/></svg></div>
          <div>
            <div class="kpi-num" id="s-pass">0</div>
            <div class="kpi-label">Verified Sponsors</div>
            <div class="kpi-trend">+2 new today</div>
          </div>
        </div>
        <svg class="kpi-chart" width="64" height="32" viewBox="0 0 64 32">
          <defs><linearGradient id="g3" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#F5C842" stop-opacity=".3"/><stop offset="100%" stop-color="#F5C842" stop-opacity="0"/></linearGradient></defs>
          <path d="M0,28 C8,24 16,20 24,18 C32,16 40,10 48,8 C56,6 60,4 64,2" fill="none" stroke="#F5C842" stroke-width="1.5"/>
          <path d="M0,28 C8,24 16,20 24,18 C32,16 40,10 48,8 C56,6 60,4 64,2 L64,32 L0,32Z" fill="url(#g3)"/>
        </svg>
      </div>
      <div class="kpi">
        <div class="kpi-left">
          <div class="kpi-icon"><svg viewBox="0 0 24 24"><path d="M13 2 3 14h7l-1 8 10-12h-7z"/></svg></div>
          <div>
            <div class="kpi-num" id="s-lat">0s</div>
            <div class="kpi-label">Avg Latency</div>
            <div class="kpi-trend down" id="kpi-trend-lat">-0.4s vs yesterday</div>
          </div>
        </div>
        <svg class="kpi-chart" width="64" height="32" viewBox="0 0 64 32">
          <defs><linearGradient id="g4" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#EF4444" stop-opacity=".3"/><stop offset="100%" stop-color="#EF4444" stop-opacity="0"/></linearGradient></defs>
          <path d="M0,8 C8,12 16,10 24,16 C32,22 40,18 48,20 C56,22 60,24 64,26" fill="none" stroke="#EF4444" stroke-width="1.5"/>
          <path d="M0,8 C8,12 16,10 24,16 C32,22 40,18 48,20 C56,22 60,24 64,26 L64,32 L0,32Z" fill="url(#g4)"/>
        </svg>
      </div>
    </div>

    <!-- Source pills -->
    <div class="srcbar" id="srcbar">
      <span class="src-pill active" onclick="filterSource('')">All Sources</span>
      <div class="src-sort">Most Relevant ▾</div>
    </div>

    <!-- Mobile count -->
    <div class="mob-count"><b id="jcount-n">0</b><span>Jobs Found &nbsp;·&nbsp; Most Relevant ▾</span></div>

    <!-- Body: cards + details -->
    <div class="body">
      <div class="jobs-wrap">
        <div class="jobs-list" id="jobs-list">
          <div class="center-msg"><span class="spin spin-lg"></span><span>Loading jobs…</span></div>
        </div>
        <div class="pager">
          <span class="pager-info" id="pginfo">—</span>
          <button class="pg-btn" onclick="pg(-1)">‹</button>
          <span class="pg-num" id="pgnum">1</span>
          <button class="pg-btn" onclick="pg(1)">›</button>
        </div>
      </div>

      <!-- Details panel -->
      <aside class="details empty" id="details">
        <div class="d-empty-icon">
          <svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M7 15h4"/></svg>
        </div>
        <div style="font-size:14px;color:var(--text-secondary);margin-top:8px">Select a job to view details</div>
        <div style="font-size:13px;color:var(--text-muted);margin-top:4px">Click any job card to get started</div>
      </aside>
    </div>

  </div><!-- end .main -->
</div><!-- end .wrap -->

<!-- Mobile filter sheet -->
<div class="jsheet" id="jsheet">
  <div class="jgrip"></div>
  <h3>Filters</h3>
  <div class="jf-field">
    <label>Keyword</label>
    <input id="jf-q" placeholder="Title, company, skill…"/>
  </div>
  <div class="jf-field">
    <label>Country</label>
    <select id="jf-country">
      <option value="">Any Country</option>
      <option>United Kingdom</option><option>United States</option>
      <option>UAE</option><option>Canada</option><option>Germany</option>
      <option>Australia</option><option>India</option><option>Pakistan</option>
    </select>
  </div>
  <div class="jf-field">
    <label>Job Type</label>
    <select id="jf-type">
      <option value="">Any Type</option>
      <option value="remote">Remote</option>
      <option value="hybrid">Hybrid</option>
      <option value="onsite">On-site</option>
    </select>
  </div>
  <label class="jf-toggle"><input type="checkbox" id="jf-verified"/> Visa-Verified sponsors only</label>
  <label class="jf-toggle"><input type="checkbox" id="jf-salary"/> Has salary listed</label>
  <button class="jf-apply" onclick="jFilterApply()">Apply Filters</button>
</div>

<script>
(function(){
  /* ── Nav ── */
  var NAV=[
    ['Jobs','Jobs','<path d="M20 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',true],
    ['Edu','Education','<path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/>',false],
    ['Visa','Visa','<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/>',false],
    ['sep'],
    ['Cars','Cars','<path d="M5 17H3a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v5h-1"/><circle cx="14" cy="17" r="2"/><circle cx="6" cy="17" r="2"/>',false],
    ['Leads','Leads','<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',false],
    ['sep'],
    ['/concierge','AI Analyzer','<circle cx="12" cy="12" r="3"/><path d="M3 12h1M20 12h1M12 3v1M12 20v1M5.6 5.6l.7.7M17.7 17.7l.7.7M5.6 18.4l.7-.7M17.7 6.3l.7-.7"/>',false],
    ['/','Health','<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',false],
    ['/','Config','<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',false]
  ];
  var navEl=document.getElementById('side-nav');
  navEl.innerHTML=NAV.map(function(x){
    if(x[0]==='sep')return '<div class="nav-sep"></div>';
    var href=x[0]==='Jobs'?'/jobs':x[0];
    return '<a class="ni'+(x[3]?' on':'')+'" href="'+href+'"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">'+x[2]+'</svg>'+x[1]+'</a>';
  }).join('');

  /* ── State ── */
  var JOBS=[],VIEW=[],page=1,per=15,saved={},sel=null,activeSrc='';
  var GRAD=[
    'linear-gradient(135deg,#6366f1,#8b5cf6)',
    'linear-gradient(135deg,#f59e0b,#d97706)',
    'linear-gradient(135deg,#10b981,#059669)',
    'linear-gradient(135deg,#ef4444,#dc2626)',
    'linear-gradient(135deg,#3b82f6,#2563eb)',
    'linear-gradient(135deg,#ec4899,#db2777)',
    'linear-gradient(135deg,#14b8a6,#0d9488)',
    'linear-gradient(135deg,#f97316,#ea580c)'
  ];

  function esc(s){return(s||'').replace(/[<>&"]/g,function(c){return{'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c];})}
  function domain(co){return(co||'').toLowerCase().replace(/[^a-z0-9]/g,'')+'.com';}
  function letterLogo(co,i,cls){
    var g=GRAD[(co||'').charCodeAt(0)%GRAD.length]||GRAD[0];
    return '<div class="'+(cls||'logo-fb')+'" style="background:'+g+'">'+((co||'?')[0]||'?').toUpperCase()+'</div>';
  }
  function logo(co,i,cls,sz){
    if(!co)return letterLogo('?',i,cls);
    var c=cls||'job-logo';
    return '<img class="'+c+'" src="https://logo.clearbit.com/'+domain(co)+'" '+
      'onerror="this.outerHTML=window.__lf('+JSON.stringify(co).replace(/"/g,'&quot;')+','+i+',\''+c+'\')"/>';
  }
  window.__lf=function(co,i,cls){return letterLogo(co,i,cls);};

  /* ── Load ── */
  function load(){
    document.getElementById('jobs-list').innerHTML='<div class="center-msg"><span class="spin spin-lg"></span><span>Loading jobs…</span></div>';
    fetch('/api/jobs/all').then(function(r){return r.json();}).then(function(d){
      JOBS=d.jobs||[]; VIEW=JOBS.slice();
      var lat=(d.sources||[]).map(function(s){return s.elapsed||0;});
      var avg=lat.length?(lat.reduce(function(a,b){return a+b;},0)/lat.length):0;
      document.getElementById('s-found').textContent=JOBS.length;
      document.getElementById('s-rows').textContent=(d.sponsor_index&&d.sponsor_index.sponsors_indexed||0).toLocaleString();
      document.getElementById('s-pass').textContent=d.verified_sponsors||0;
      document.getElementById('s-lat').textContent=avg.toFixed(1)+'s';
      document.getElementById('last').textContent='Last run '+new Date().toLocaleTimeString();
      var pills=(d.sources||[]).map(function(s){
        return '<span class="src-pill" onclick="filterSource(\''+esc(s.name)+'\')"><span class="dot"></span>'+esc(s.name)+' ('+( s.count||0)+')</span>';
      }).join('');
      var sb=document.getElementById('srcbar');
      sb.innerHTML='<span class="src-pill active" onclick="filterSource(\'\')">All Sources</span>'+pills+'<div class="src-sort">Most Relevant ▾</div>';
      var de=document.getElementById('drawer-src');
      if(de)de.innerHTML=(d.sources||[]).map(function(s){return '<div style="display:flex;align-items:center;gap:6px;padding:4px 0"><span class="dot" style="width:6px;height:6px;border-radius:50%;background:var(--success);flex-shrink:0"></span>'+esc(s.name)+' · '+(s.count||0)+'</div>';}).join('');
      page=1;render();jBootExtra();
    }).catch(function(){
      document.getElementById('jobs-list').innerHTML='<div class="center-msg" style="gap:16px"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg><div style="font-size:16px;color:var(--text-secondary)">Could not load jobs</div><button class="run-btn" onclick="location.reload()">Retry</button></div>';
    });
  }

  var BOOTED=false;
  function jBootExtra(){
    if(BOOTED)return;BOOTED=true;
    fetch('/api/jobs/search?q=&type=remote').then(function(r){return r.json();}).then(function(d){
      var added=0,keys={};
      JOBS.forEach(function(j){keys[((j.position||'')+'|'+(j.company||'')).toLowerCase()]=1;});
      (d.jobs||[]).forEach(function(j){
        var k=((j.position||'')+'|'+(j.company||'')).toLowerCase();
        if(!keys[k]){keys[k]=1;JOBS.push(j);added++;}
      });
      if(added){document.getElementById('s-found').textContent=JOBS.length;applyFilter();}
    }).catch(function(){});
  }

  /* ── Run ── */
  window.runJobs=function(){
    var b=document.getElementById('runbtn');
    b.innerHTML='<span class="spin" style="width:13px;height:13px;border-width:2px"></span>Running…';
    b.disabled=true;
    fetch('/api/jobs/all').then(function(r){return r.json();}).then(function(){
      b.innerHTML='<svg viewBox="0 0 24 24" width="12" height="12" fill="#000"><polygon points="6 3 20 12 6 21 6 3"/></svg>Run Jobs';
      b.disabled=false;load();
    }).catch(function(){b.innerHTML='Run Jobs';b.disabled=false;});
  };

  /* ── Filters ── */
  var FILT={q:'',country:'',type:'',verified:false,salary:false};

  window.filterSource=function(src){
    activeSrc=src;
    document.querySelectorAll('.src-pill').forEach(function(p){
      p.classList.toggle('active',p.textContent.trim().startsWith(src?src:'All'));
    });
    applyFilter();
  };

  window.applyFilter=function(){
    var q=((document.getElementById('q').value||'')||FILT.q).toLowerCase();
    VIEW=JOBS.filter(function(j){
      if(activeSrc&&(j.source||'').toLowerCase().indexOf(activeSrc.toLowerCase())<0)return false;
      if(q&&JSON.stringify(j).toLowerCase().indexOf(q)<0)return false;
      if(FILT.country&&(j.location||'').toLowerCase().indexOf(FILT.country.toLowerCase())<0)return false;
      if(FILT.type==='remote'&&!j.remote&&(j.location||'').toLowerCase().indexOf('remote')<0)return false;
      if(FILT.type==='onsite'&&(j.remote||(j.location||'').toLowerCase().indexOf('remote')>=0))return false;
      if(FILT.verified&&!j.sponsor_verified)return false;
      if(FILT.salary&&(!j.salary||j.salary==='—'))return false;
      return true;
    });
    page=1;render();
  };

  window.jNav=function(open){document.body.classList.toggle('jnav',open);};
  window.jFilterOpen=function(){
    document.getElementById('jf-q').value=FILT.q||document.getElementById('q').value||'';
    document.getElementById('jf-country').value=FILT.country;
    document.getElementById('jf-type').value=FILT.type;
    document.getElementById('jf-verified').checked=FILT.verified;
    document.getElementById('jf-salary').checked=FILT.salary;
    document.getElementById('jsheet').classList.add('on');
  };
  window.jFilterApply=function(){
    FILT.q=document.getElementById('jf-q').value;
    FILT.country=document.getElementById('jf-country').value;
    FILT.type=document.getElementById('jf-type').value;
    FILT.verified=document.getElementById('jf-verified').checked;
    FILT.salary=document.getElementById('jf-salary').checked;
    var qi=document.getElementById('q');if(qi)qi.value=FILT.q;
    document.getElementById('jsheet').classList.remove('on');
    applyFilter();jFetchFresh();
  };

  window.jFetchFresh=function(){
    if(!(FILT.q||FILT.country||FILT.type))return;
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
      }).catch(function(){});
  };

  /* ── Render cards ── */
  function render(){
    var list=document.getElementById('jobs-list');
    var jc=document.getElementById('jcount-n');if(jc)jc.textContent=VIEW.length;
    if(!VIEW.length){
      list.innerHTML='<div class="center-msg"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="1.5"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg><div style="font-size:15px;color:var(--text-secondary)">No jobs match your filters</div><div style="font-size:13px;color:var(--text-muted)">Try adjusting your search or filters</div></div>';
      document.getElementById('pginfo').textContent='0 results';
      return;
    }
    var start=(page-1)*per,slice=VIEW.slice(start,start+per);
    list.innerHTML=slice.map(function(j,k){
      var idx=start+k;
      var isRemote=j.remote||(j.location||'').toLowerCase().indexOf('remote')>=0;
      var tags='';
      if(j.sponsor_verified)tags+='<span class="tag-visa">✓ Visa Verified</span>';
      if(isRemote)tags+='<span class="tag-remote">Remote</span>';
      if(j.intelligence&&j.intelligence.ai_score>0.7)tags+='<span class="tag-ai">⚡ AI Match</span>';
      return '<div class="job-card'+(sel===idx?' sel':'')+'" onclick="openJob('+idx+',this)" data-idx="'+idx+'">'+
        logo(j.company,idx,'job-logo')+
        '<div class="job-body">'+
          '<div class="job-top">'+
            '<span class="job-company">'+esc(j.company||'—')+'</span>'+
            '<span class="job-source">'+esc(j.source||'')+'</span>'+
            tags+
          '</div>'+
          '<div class="job-title">'+esc((j.position||'').slice(0,70))+'</div>'+
          '<div class="job-meta">'+
            (j.location?'<span class="job-meta-item"><svg viewBox="0 0 24 24"><path d="M12 21s-7-6-7-11a7 7 0 0 1 14 0c0 5-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>'+esc(j.location)+'</span>':'')+
            (j.salary&&j.salary!=='—'?'<span class="job-meta-item"><svg viewBox="0 0 24 24"><path d="M12 1v22M17 5H9.5a3.5 3.5 0 1 0 0 7h5a3.5 3.5 0 1 1 0 7H6"/></svg>'+esc(j.salary)+'</span>':'')+
            (j.employees&&j.employees!=='—'?'<span class="job-meta-item"><svg viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>'+esc(j.employees)+'</span>':'')+
          '</div>'+
        '</div>'+
        '<div class="job-right">'+
          '<button class="bookmark-btn'+(saved[idx]?' on':'')+'" onclick="event.stopPropagation();toggleSave('+idx+',this)">'+(saved[idx]?'★':'☆')+'</button>'+
          '<span class="job-posted">'+esc(j.posted||'')+'</span>'+
          (j.salary&&j.salary!=='—'?'<span class="job-salary">'+esc(j.salary)+'</span>':'')+
        '</div>'+
      '</div>';
    }).join('');
    var tot=VIEW.length,to=Math.min(start+per,tot);
    document.getElementById('pginfo').textContent='Showing '+(start+1)+'–'+to+' of '+tot+' results';
    document.getElementById('pgnum').textContent=page;
  }

  window.pg=function(d){var max=Math.ceil(VIEW.length/per)||1;page=Math.min(max,Math.max(1,page+d));render();window.scrollTo&&document.querySelector('.jobs-wrap')&&(document.querySelector('.jobs-wrap').scrollTop=0);};
  window.toggleSave=function(i,el){saved[i]=!saved[i];el.textContent=saved[i]?'★':'☆';el.classList.toggle('on',saved[i]);};

  /* ── Sponsor / Intel blocks ── */
  function sponsorBlock(j){
    if(j.sponsor_verified){
      var routes=(j.visa_routes||[]).map(esc).join(', ')||'Skilled Worker';
      return '<div class="d-sponsor-ok">'+
        '<div class="h"><svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>UK Licensed Sponsor — Verified</div>'+
        '<div class="r"><b>'+esc(j.company)+'</b> is on the official UK Register of Licensed Sponsors.<br>Routes: '+routes+'</div>'+
        '</div>';
    }
    return '<div class="d-sponsor-no">⚪ Sponsorship: <b>'+esc(j.sponsor_status||'Not Verified')+'</b> — no matching licence in the official register.</div>';
  }

  function intelBlock(j){
    var ig=j.intelligence||{};if(!ig.summary)return '';
    function pc(x){return Math.round((x||0)*100);}
    var ev=(ig.evidence||[]).map(function(e){return '<div class="d-bullet"><span class="d-bullet-dot">›</span>'+esc(e.detail||'')+'</div>';}).join('');
    var sp=pc(ig.ai_score);var vp=pc(ig.visa_score);
    return '<div class="d-section-title"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M3 12h1M20 12h1M12 3v1M12 20v1"/></svg>AI Intelligence</div>'+
      '<div class="d-scores">'+
        '<div class="d-score"><div class="v">'+pc(ig.ai_score)+'%</div><div class="k">AI Score</div></div>'+
        '<div class="d-score"><div class="v">'+pc(ig.visa_score)+'%</div><div class="k">Visa</div></div>'+
        '<div class="d-score"><div class="v">'+pc(ig.salary_score)+'%</div><div class="k">Salary</div></div>'+
        '<div class="d-score"><div class="v">'+pc(ig.confidence)+'%</div><div class="k">Confidence</div></div>'+
      '</div>'+
      '<div class="d-progress-row"><div class="d-progress-label"><span>Sponsor Score</span><span>'+sp+'%</span></div><div class="d-progress"><div class="d-progress-bar" style="width:'+sp+'%"></div></div></div>'+
      '<div class="d-progress-row"><div class="d-progress-label"><span>AI Match</span><span>'+vp+'%</span></div><div class="d-progress"><div class="d-progress-bar" style="width:'+vp+'%;background:linear-gradient(90deg,#3b82f6,#2563eb)"></div></div></div>'+
      '<p class="d-p">'+esc(ig.summary)+'</p>'+
      (ev?'<div class="d-evidence">'+ev+'</div>':'');
  }

  /* ── Open job detail ── */
  window.openJob=function(i,row){
    sel=i;var j=VIEW[i];if(!j)return;
    document.querySelectorAll('.job-card').forEach(function(c){c.classList.remove('sel');});
    if(row)row.classList.add('sel');
    var desc=esc(j.description||'');var parts=desc.split(/[.!?]\s/).filter(Boolean);
    var about=parts.slice(0,2).join('. ');var role=parts.slice(2,4).join('. ');var bullets=parts.slice(4,8);
    var d=document.getElementById('details');
    d.classList.remove('empty');d.classList.add('show');
    d.innerHTML=
      '<div class="d-header"><h2>Job Details</h2><button class="d-close" onclick="closeJob()"><svg viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div>'+
      '<div class="d-scroll">'+
        '<div class="d-company-row">'+
          logo(j.company,i,'d-co-logo')+
          '<div>'+
            '<div class="d-co-name">'+esc(j.company||'—')+'</div>'+
            (j.sponsor_verified?'<div class="d-co-badge"><svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>UK Licensed Sponsor</div>':'')+
            '<div class="d-rating"><span class="d-stars">★★★★★</span><span>4.9 (256 reviews)</span></div>'+
          '</div>'+
        '</div>'+
        '<div class="d-title">'+esc(j.position||'')+'</div>'+
        '<div class="d-location"><svg viewBox="0 0 24 24"><path d="M12 21s-7-6-7-11a7 7 0 0 1 14 0c0 5-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>'+esc(j.location||'Remote')+'</div>'+
        '<div class="d-grid">'+
          '<div class="d-meta-item"><div class="k">Salary</div><div class="v">'+esc(j.salary||'—')+'</div></div>'+
          '<div class="d-meta-item"><div class="k">Employment</div><div class="v">'+esc(j.employment_type||'Full Time')+'</div></div>'+
          '<div class="d-meta-item"><div class="k">Employees</div><div class="v">'+esc(j.employees||'—')+'</div></div>'+
          '<div class="d-meta-item"><div class="k">Posted</div><div class="v">'+esc(j.posted||'—')+'</div></div>'+
        '</div>'+
        sponsorBlock(j)+
        intelBlock(j)+
        (about?'<div class="d-section-title"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>About '+esc(j.company||'the role')+'</div><p class="d-p">'+about+'.</p>':'')+
        (role?'<div class="d-section-title"><svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18"/></svg>What\'s the role?</div><p class="d-p">'+role+'.</p>':'')+
        (bullets.length?'<div class="d-section-title">In this role you will…</div>'+bullets.map(function(b){return '<div class="d-bullet"><span class="d-bullet-dot">›</span>'+b+'.</div>';}).join(''):'')+
        (!about&&!role?'<p class="d-p">'+(desc||'No description available for this listing.')+'</p>':'')+
        '<div id="d-full"></div>'+
      '</div>'+
      '<div class="d-footer">'+
        '<button class="d-save-btn" onclick="toggleSave('+i+',this)">'+(saved[i]?'★ Saved':'☆ Save')+'</button>'+
        '<button class="d-share-btn">Share</button>'+
        (j.url?'<a class="d-apply-btn" href="'+j.url+'" target="_blank">Apply Now <svg viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg></a>':'<button class="d-apply-btn">Apply Now <svg viewBox="0 0 24 24"><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg></button>')+
      '</div>';
    if(j.url){
      var fd=document.getElementById('d-full');
      fd.innerHTML='<div class="d-section-title">Full Description</div><p class="d-p" style="display:flex;align-items:center;gap:8px"><span class="spin" style="width:14px;height:14px;border-width:2px"></span>Loading from source…</p>';
      fetch('/api/jobs/detail?url='+encodeURIComponent(j.url)).then(function(r){return r.json();}).then(function(dd){
        if(dd.description&&dd.description.length>(j.description||'').length){
          fd.innerHTML='<div class="d-section-title">Full Description <span style="font-size:11px;font-weight:400;color:var(--text-muted)">· from source</span></div><p class="d-p">'+esc(dd.description)+'</p>';
        }else{fd.innerHTML='';}
      }).catch(function(){fd.innerHTML='';});
    }
  };

  window.closeJob=function(){
    var d=document.getElementById('details');
    d.classList.remove('show');d.classList.add('empty');
    d.innerHTML='<div class="d-empty-icon"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="var(--text-muted)" stroke-width="1.75"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M7 15h4"/></svg></div><div style="font-size:14px;color:var(--text-secondary);margin-top:8px">Select a job to view details</div><div style="font-size:13px;color:var(--text-muted);margin-top:4px">Click any job card to get started</div>';
    sel=null;
    document.querySelectorAll('.job-card').forEach(function(c){c.classList.remove('sel');});
  };

  load();
})();
</script></body></html>"""
