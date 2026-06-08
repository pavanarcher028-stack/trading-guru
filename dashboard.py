import json
import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import log_capture

log_capture.install()

PORT = int(os.environ.get("DASHBOARD_PORT", 8081))

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>trading-agent500 — Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400;14..32,500;14..32,600;14..32,700&display=swap" rel="stylesheet">
<style>
:root{--bg:#0a0e17;--surface:#111827;--surface2:#1a2332;--border:#1e2d3d;--text:#e2e8f0;--muted:#64748b;--accent:#3b82f6;--green:#22c55e;--red:#ef4444;--orange:#f59e0b;--cyan:#06b6d4;--radius:12px;--shadow:0 1px 3px rgba(0,0,0,.4)}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.layout{display:flex;min-height:100vh}
.sidebar{width:240px;background:var(--surface);border-right:1px solid var(--border);padding:24px 0;flex-shrink:0;position:sticky;top:0;height:100vh;overflow-y:auto}
.sidebar-logo{font-size:20px;font-weight:700;padding:0 20px 24px;border-bottom:1px solid var(--border);margin-bottom:8px}
.sidebar-logo span{color:var(--accent)}
.sidebar-nav{padding:8px 12px}
.nav-item{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;font-size:14px;font-weight:500;color:var(--muted);cursor:pointer;transition:.15s;text-decoration:none;border:none;background:none;width:100%;text-align:left}
.nav-item:hover{background:var(--surface2);color:var(--text)}
.nav-item.active{background:var(--accent);color:#fff;box-shadow:0 0 12px rgba(59,130,246,.3)}
.nav-item .icon{font-size:18px;width:22px;text-align:center}
.main{flex:1;padding:28px 32px;overflow-y:auto;max-width:1400px}
.page{display:none}
.page.active{display:block}
h1{font-size:28px;font-weight:700;margin-bottom:4px}
.subtitle{color:var(--muted);font-size:14px;margin-bottom:24px}
.grid{display:grid;gap:16px;margin-bottom:20px}
.grid-2{grid-template-columns:1fr 1fr}
.grid-3{grid-template-columns:1fr 1fr 1fr}
.grid-4{grid-template-columns:repeat(4,1fr)}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:20px;box-shadow:var(--shadow)}
.card-header{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:12px}
.card-value{font-size:28px;font-weight:700}
.stat-row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);font-size:14px}
.stat-row:last-child{border-bottom:none}
.stat-label{color:var(--muted)}
.stat-value{font-weight:600}
.badge{display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600}
.badge-green{background:rgba(34,197,94,.12);color:var(--green);border:1px solid rgba(34,197,94,.25)}
.badge-red{background:rgba(239,68,68,.12);color:var(--red);border:1px solid rgba(239,68,68,.25)}
.badge-blue{background:rgba(59,130,246,.12);color:var(--accent);border:1px solid rgba(59,130,246,.25)}
.badge-orange{background:rgba(245,158,11,.12);color:var(--orange);border:1px solid rgba(245,158,11,.25)}
.badge-cyan{background:rgba(6,182,212,.12);color:var(--cyan);border:1px solid rgba(6,182,212,.25)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:10px 8px;color:var(--muted);border-bottom:2px solid var(--border);font-size:11px;text-transform:uppercase;letter-spacing:.5px;font-weight:600}
td{padding:10px 8px;border-bottom:1px solid var(--border)}
tr:hover td{background:var(--surface2)}
pre.code{background:#050a14;border:1px solid var(--border);border-radius:8px;padding:16px;font-size:12px;line-height:1.6;overflow:auto;max-height:500px;font-family:'JetBrains Mono','Fira Code','Consolas',monospace;white-space:pre-wrap;word-break:break-all;color:#a5b4fc}
pre.code .kw{color:#c084fc}pre.code .fn{color:#22d3ee}pre.code .str{color:#86efac}pre.code .cm{color:#6b7280}pre.code .num{color:#fbbf24}
.log-box{background:#050a14;border:1px solid var(--border);border-radius:8px;padding:12px;max-height:400px;overflow-y:auto;font-size:12px;line-height:1.5;font-family:'JetBrains Mono','Fira Code','Consolas',monospace}
.log-line{padding:2px 8px;white-space:pre-wrap;word-break:break-all;border-radius:3px}
.log-line:nth-child(odd){background:rgba(255,255,255,.02)}
.log-line:hover{background:rgba(255,255,255,.04)}
.coin-pill{display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:20px;font-size:13px;font-weight:500;margin:2px}
.coin-pill.live{background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.3);color:var(--accent)}
.coin-pill.pass{background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.3);color:var(--green)}
.coin-pill.fail{background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.3);color:var(--red)}
.coin-pill .dot{width:7px;height:7px;border-radius:50%;display:inline-block}
.coin-pill.live .dot{background:var(--accent);animation:pulse 1.5s infinite}
.coin-pill.pass .dot{background:var(--green)}
.coin-pill.fail .dot{background:var(--red)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.empty{text-align:center;padding:40px;color:var(--muted);font-size:14px}
.loading{text-align:center;padding:30px;color:var(--muted)}
.loading::after{content:'';display:inline-block;width:20px;height:20px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite;margin-left:8px;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.refresh-bar{display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);margin-top:20px;font-size:13px;color:var(--muted)}
.refresh-bar .spinner{width:14px;height:14px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite}
.hero{background:linear-gradient(135deg,var(--surface),var(--surface2));border:1px solid var(--border);border-radius:var(--radius);padding:28px;margin-bottom:20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px}
.hero h2{font-size:22px;font-weight:700}
.hero p{color:var(--muted);font-size:14px;margin-top:4px}
.hero-status{display:flex;align-items:center;gap:8px;font-size:14px;font-weight:500}
.hero-status .dot{width:10px;height:10px;border-radius:50%}
.hero-status .dot.green{background:var(--green);box-shadow:0 0 10px rgba(34,197,94,.5)}
.hero-status .dot.red{background:var(--red);box-shadow:0 0 10px rgba(239,68,68,.5)}
.hero-status .dot.yellow{background:var(--orange);box-shadow:0 0 10px rgba(245,158,11,.5)}
.mb-2{margin-bottom:16px}
@media(max-width:900px){.grid-2,.grid-3,.grid-4{grid-template-columns:1fr}.sidebar{width:56px;overflow:hidden}.sidebar-logo{font-size:0;padding:16px 0;text-align:center}.sidebar-logo::after{content:'TA5';font-size:16px;font-weight:700;color:var(--accent)}.nav-item span.nav-label{display:none}.nav-item{padding:12px;justify-content:center}.nav-item .icon{font-size:20px;margin:0}.main{padding:16px}}
</style>
</head>
<body>
<div class="layout">
<nav class="sidebar">
<div class="sidebar-logo">trading<span>agent</span>500</div>
<div class="sidebar-nav">
<button class="nav-item active" data-page="overview"><span class="icon">&#9679;</span><span class="nav-label">Overview</span></button>
<button class="nav-item" data-page="strategy"><span class="icon">&#128220;</span><span class="nav-label">Strategy</span></button>
<button class="nav-item" data-page="trades"><span class="icon">&#128202;</span><span class="nav-label">Trades</span></button>
<button class="nav-item" data-page="positions"><span class="icon">&#128188;</span><span class="nav-label">Positions</span></button>
<button class="nav-item" data-page="backtests"><span class="icon">&#128200;</span><span class="nav-label">Backtests</span></button>
<button class="nav-item" data-page="activity"><span class="icon">&#128163;</span><span class="nav-label">Activity</span></button>
</div>
</nav>
<div class="main">
<div id="page-overview" class="page active">
<div class="hero">
<div><h2 id="hero-title">trading-agent500</h2><p id="hero-subtitle">Loading agent status...</p></div>
<div id="hero-status" class="hero-status"><span class="dot yellow"></span> Initializing...</div>
</div>
<div class="grid grid-4 mb-2">
<div class="card"><div class="card-header">Total Trades</div><div class="card-value" id="stat-trades" style="color:var(--accent)">-</div></div>
<div class="card"><div class="card-header">Win Rate</div><div class="card-value" id="stat-winrate">-</div></div>
<div class="card"><div class="card-header">Total P&amp;L</div><div class="card-value" id="stat-pnl">-</div></div>
<div class="card"><div class="card-header">Consec. Losses</div><div class="card-value" id="stat-consec">-</div></div>
</div>
<div class="grid grid-2 mb-2">
<div class="card"><div class="card-header">Balance</div><div id="balance-display" class="loading"></div></div>
<div class="card"><div class="card-header">Active Coins</div><div id="coins-display" class="loading"></div></div>
</div>
<div class="card"><div class="card-header">Current Positions</div><div id="positions-mini" class="loading"></div></div>
</div>

<div id="page-strategy" class="page">
<div class="card">
<div class="card-header">Active Strategy</div>
<div id="strategy-info" class="loading"></div>
<div style="margin-top:12px"><pre class="code" id="strategy-code">Loading...</pre></div>
</div>
</div>

<div id="page-trades" class="page">
<div class="card">
<div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
<span>Trade History</span>
<span id="trade-count" style="font-size:11px;color:var(--muted);font-weight:400"></span>
</div>
<div id="trades-table" class="loading"></div>
</div>
</div>

<div id="page-positions" class="page">
<div class="card">
<div class="card-header">Open Positions</div>
<div id="positions-full" class="loading"></div>
</div>
</div>

<div id="page-backtests" class="page">
<div class="card">
<div class="card-header">Backtest Metrics — Per Coin Failure Counts</div>
<div id="backtests-content" class="loading"></div>
</div>
</div>

<div id="page-activity" class="page">
<div class="card">
<div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
<span>Live Activity Log</span>
<span id="log-count" style="font-size:11px;color:var(--muted);font-weight:400"></span>
</div>
<div id="activity-box" class="loading"></div>
</div>
</div>

<div class="refresh-bar">
<div class="spinner"></div>
<span>Auto-refreshes every <strong>10s</strong></span>
<span style="margin-left:auto;color:var(--accent)" id="update-time">-</span>
</div>
</div>
</div>

<script>
function q(s){return document.querySelector(s)}
function qa(s){return document.querySelectorAll(s)}
function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}
function num(n,d){return Number(n).toLocaleString('en-IN',{minimumFractionDigits:d??2})}
async function get(p){return fetch(p).then(r=>r.json())}
function updateTime(){document.getElementById('update-time').textContent=new Date().toLocaleTimeString()}

qa('.nav-item').forEach(el=>{
el.addEventListener('click',()=>{
qa('.nav-item').forEach(e=>e.classList.remove('active'));
qa('.page').forEach(e=>e.classList.remove('active'));
el.classList.add('active');
document.getElementById('page-'+el.dataset.page).classList.add('active');
});
});

async function loadOverview(){
try{
const d=await get('/api/dashboard');
const p=d.performance||{};
document.getElementById('stat-trades').textContent=p.total_trades||0;
const wr=document.getElementById('stat-winrate');
const wrv=p.win_rate||0;
wr.textContent=wrv+'%';wr.style.color=wrv>=55?'var(--green)':wrv>=45?'var(--orange)':'var(--red)';
const pnl=document.getElementById('stat-pnl');
const pnlv=p.total_pnl||0;
pnl.textContent='\u20b9'+num(pnlv);pnl.style.color=pnlv>=0?'var(--green)':'var(--red)';
const cl=document.getElementById('stat-consec');
const clv=p.consecutive_losses||0;
cl.textContent=clv;cl.style.color=clv>=3?'var(--red)':'var(--orange)';
document.getElementById('hero-subtitle').textContent=(p.total_trades||0)+' trades \u00b7 v'+(p.strategy_version||1)+(d.balance?' \u00b7 Balance: \u20b9'+num(d.balance):'');
const hs=document.getElementById('hero-status');
if(d.balance){hs.innerHTML='<span class="dot green"></span> Live';}
else if(p.total_trades>0){hs.innerHTML='<span class="dot yellow"></span> Paper Trading';}
else{hs.innerHTML='<span class="dot yellow"></span> Waiting...';}
const balEl=document.getElementById('balance-display');
if(d.balance){balEl.innerHTML='<div style="font-size:32px;font-weight:700;color:var(--accent);margin:4px 0">\u20b9'+num(d.balance)+'</div><div style="font-size:12px;color:var(--muted)">from '+esc(d.balance_source)+'</div>';}
else{balEl.innerHTML='<div style="color:var(--muted);padding:8px 0">No balance data (API keys may be missing)</div>';}
const coins=d.coins||{};
let ch='<div style="display:flex;flex-wrap:wrap;gap:6px">';
let has=false;
for(const[c,s]of Object.entries(coins)){
has=true;
let cls='fail',label='FAIL';
if(s.trading){cls='live';label='LIVE';}
else if(s.passed){cls='pass';label='PASS';}
ch+='<span class="coin-pill '+cls+'"><span class="dot"></span>'+c+' '+label+'</span>';
}
if(!has)ch+='<span style="color:var(--muted)">No coins configured</span>';
ch+='</div>';
document.getElementById('coins-display').innerHTML=ch;
const pos=d.positions||{};
const pk=Object.keys(pos);
const pm=document.getElementById('positions-mini');
if(pk.length>0){
let ph='<table><thead><tr><th>Coin</th><th>Entry</th><th>Qty</th><th>SL</th><th>TP</th><th>Duration</th><th>PnL</th></tr></thead><tbody>';
for(const[coin,po]of Object.entries(pos)){
const dur=po.entry_time?Math.floor((Date.now()/1000-po.entry_time)/3600)+'h':'';
const pnlVal=po.current_price?(po.current_price-po.entry_price)*po.quantity:0;
ph+='<tr><td><strong>'+coin+'</strong></td><td>\u20b9'+num(po.entry_price)+'</td><td>'+po.quantity+'</td><td style="color:var(--red)">'+po.sl_pct+'%</td><td style="color:var(--green)">'+po.tp_pct+'%</td><td>'+dur+'</td><td style="color:'+(pnlVal>=0?'var(--green)':'var(--red)')+'">\u20b9'+num(pnlVal)+'</td></tr>';
}
ph+='</tbody></table>';
pm.innerHTML=ph;
}else{pm.innerHTML='<div class="empty">No open positions</div>';}
}catch(e){console.error(e)}
}

async function loadStrategy(){
try{
const s=await get('/api/strategy');
const info=document.getElementById('strategy-info');
if(s.coins&&s.coins.length){
info.innerHTML='<div class="stat-row"><span class="stat-label">Approved Coins</span><span class="stat-value" style="color:var(--accent)">'+s.coins.join(', ')+'</span></div>'+
'<div class="stat-row"><span class="stat-label">Code Size</span><span class="stat-value">'+(s.code?s.code.length:0)+' chars</span></div>'+
'<div class="stat-row"><span class="stat-label">SL / TP</span><span class="stat-value">'+(s.sl_pct||'?')+'% / '+(s.tp_pct||'?')+'%</span></div>';
}else{info.innerHTML='<div class="empty">No strategy saved yet. Run the agent.</div>'}
const codeEl=document.getElementById('strategy-code');
if(s.code)codeEl.textContent=s.code;
else codeEl.textContent='// No strategy selected';
}catch(e){console.error(e)}
}

async function loadTrades(){
try{
const t=await get('/api/trades');
document.getElementById('trade-count').textContent=t.length+' trades';
const div=document.getElementById('trades-table');
if(t.length>0){
const recent=t.slice(-100).reverse();
let h='<table><thead><tr><th>Time</th><th>Coin</th><th>Entry</th><th>Exit</th><th>PnL</th><th>Result</th></tr></thead><tbody>';
for(const tr of recent){
h+='<tr><td style="color:var(--muted);font-size:12px">'+esc(tr.time||'')+'</td><td><strong>'+esc(tr.coin)+'</strong></td>'+
'<td>\u20b9'+num(tr.entry)+'</td><td>\u20b9'+num(tr.exit)+'</td>'+
'<td style="color:'+(tr.won?'var(--green)':'var(--red)')+';font-weight:600">'+(tr.won?'+':'')+'\u20b9'+num(tr.pnl)+'</td>'+
'<td><span class="badge '+(tr.won?'badge-green':'badge-red')+'">'+(tr.won?'WIN':'LOSS')+'</span></td></tr>';
}
h+='</tbody></table>';
div.innerHTML=h;
}else{div.innerHTML='<div class="empty">No trades yet. The bot will trade once it finds a strategy.</div>'}
}catch(e){console.error(e)}
}

async function loadPositions(){
try{
const p=await get('/api/positions');
const div=document.getElementById('positions-full');
const keys=Object.keys(p);
if(keys.length>0){
let h='<table><thead><tr><th>Coin</th><th>Entry Price</th><th>Quantity</th><th>SL %</th><th>TP %</th><th>Entry Time</th><th>Duration</th></tr></thead><tbody>';
for(const[coin,po]of Object.entries(p)){
const dur=po.entry_time?Math.floor((Date.now()/1000-po.entry_time)/3600)+'h':'';
const et=po.entry_time?new Date(po.entry_time*1000).toLocaleString():'-';
h+='<tr><td><strong>'+coin+'</strong></td><td>\u20b9'+num(po.entry_price)+'</td><td>'+po.quantity+'</td><td style="color:var(--red)">'+po.sl_pct+'%</td><td style="color:var(--green)">'+po.tp_pct+'%</td><td style="font-size:12px;color:var(--muted)">'+et+'</td><td>'+dur+'</td></tr>';
}
h+='</tbody></table>';
div.innerHTML=h;
}else{div.innerHTML='<div class="empty">No open positions.</div>'}
}catch(e){console.error(e)}
}

async function loadBacktests(){
try{
const b=await get('/api/metric_failures');
const div=document.getElementById('backtests-content');
if(b&&Object.keys(b).length>0){
let h='<table><thead><tr><th>Coin</th><th>Attempts</th><th>Sharpe</th><th>Win Rate</th><th>Drawdown</th><th>Trades</th></tr></thead><tbody>';
for(const[coin,data]of Object.entries(b)){
const f=data.failures||{};
h+='<tr><td><strong>'+coin+'</strong></td><td>'+data.total_attempts+'</td>'+
'<td style="color:'+(f.sharpe?'var(--red)':'var(--muted)')+'">'+(f.sharpe||0)+'x</td>'+
'<td style="color:'+(f.win_rate?'var(--red)':'var(--muted)')+'">'+(f.win_rate||0)+'x</td>'+
'<td style="color:'+(f.max_drawdown?'var(--red)':'var(--muted)')+'">'+(f.max_drawdown||0)+'x</td>'+
'<td style="color:'+(f.trades_count?'var(--red)':'var(--muted)')+'">'+(f.trades_count||0)+'x</td></tr>';
}
h+='</tbody></table>';
div.innerHTML=h;
}else{div.innerHTML='<div class="empty">No backtest data yet.</div>'}
}catch(e){console.error(e)}
}

async function loadActivity(){
try{
const a=await get('/api/logs');
const lines=a.lines||[];
document.getElementById('log-count').textContent=lines.length+' lines';
const box=document.getElementById('activity-box');
if(lines.length>0){
let h='<div class="log-box">';
for(const line of lines.slice(-100)){
const clean=esc(line);
let c='';
if(/FAIL|fail|Error|error|loss|LOSS/.test(clean))c='color:var(--red)';
else if(/PASS|pass|WIN|WIN/.test(clean))c='color:var(--green)';
else if(/LIVE|BUY|SELL|SL|TP|trade|TRADE/.test(clean))c='color:var(--orange)';
else if(/search|SEARCH|strategy|STRATEGY/.test(clean))c='color:var(--cyan)';
h+='<div class="log-line" style="'+c+'">'+clean+'</div>';
}
h+='</div>';
box.innerHTML=h;
const lb=box.querySelector('.log-box');
if(lb)lb.scrollTop=lb.scrollHeight;
}else{box.innerHTML='<div class="empty">No activity yet.</div>'}
}catch(e){console.error(e)}
}

updateTime();
loadOverview();loadStrategy();loadTrades();loadPositions();loadBacktests();loadActivity();
setInterval(()=>{updateTime();loadOverview();loadStrategy();loadTrades();loadPositions();loadBacktests();loadActivity()},10000);
</script>
</body>
</html>"""

def load_json(path):
    try:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    except: pass
    return None

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path in ("/", "/dashboard"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(DASHBOARD_HTML.encode())
            elif self.path == "/api/dashboard":
                data = self._build_dashboard()
                self._json(200, data)
            elif self.path == "/api/strategy":
                data = load_json("strategy_store.json")
                code = data.get("strategy_code") if data else None
                sl_pct, tp_pct = None, None
                if code:
                    import re
                    m = re.search(r"SL_PCT\s*=\s*([\d.]+)", code)
                    if m: sl_pct = float(m.group(1))
                    m = re.search(r"TP_PCT\s*=\s*([\d.]+)", code)
                    if m: tp_pct = float(m.group(1))
                self._json(200, {
                    "code": code,
                    "coins": data.get("good_coins") if data else [],
                    "sl_pct": sl_pct,
                    "tp_pct": tp_pct
                } if data else {"code": None, "coins": []})
            elif self.path == "/api/metric_failures":
                data = load_json("metric_failures.json")
                self._json(200, data or {})
            elif self.path == "/api/positions":
                data = load_json("positions.json")
                self._json(200, data or {})
            elif self.path == "/api/trades":
                log = load_json("performance_log.json")
                self._json(200, (log or {}).get("trades", []))
            elif self.path == "/api/logs":
                lines = log_capture.get_recent(80)
                self._json(200, {"lines": lines})
            else:
                self._json(404, {"error": "not found"})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _build_dashboard(self):
        log = load_json("performance_log.json") or {}
        total = (log.get("win_count", 0) + log.get("loss_count", 0))
        win_rate = round((log["win_count"] / total) * 100, 1) if total > 0 else 0
        coins = {}
        for c in ["BTC", "ETH", "BNB", "SOL", "XRP"]:
            coins[c] = {"passed": False, "failed": None, "trading": False}
        strat = load_json("strategy_store.json")
        if strat:
            for c in strat.get("good_coins", []):
                if c in coins: coins[c]["passed"] = True
        fails = load_json("metric_failures.json")
        if fails:
            for c, d in fails.items():
                if c in coins and not coins[c]["passed"]:
                    coins[c]["failed"] = ", ".join(d.get("failures", {}).keys()) or "unknown"
        pos = load_json("positions.json") or {}
        for c in pos:
            if c in coins: coins[c]["trading"] = True
        bal = 0
        bal_src = "unavailable"
        try:
            from trader import get_balance
            b = get_balance()
            if b and b > 0:
                bal = b
                bal_src = "live (CoinDCX)"
        except: pass
        return {
            "balance": bal if bal > 0 else None,
            "balance_source": bal_src,
            "performance": {
                "total_trades": total,
                "win_rate": win_rate,
                "total_pnl": log.get("total_pnl", 0),
                "wins": log.get("win_count", 0),
                "losses": log.get("loss_count", 0),
                "consecutive_losses": log.get("consecutive_losses", 0),
                "strategy_version": log.get("strategy_version", 1)
            },
            "coins": coins,
            "positions": pos
        }

    def log_message(self, *args): pass

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[DASHBOARD] Running at http://0.0.0.0:{PORT}/")
    server.serve_forever()
