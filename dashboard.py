import json
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import log_capture

log_capture.install()

PORT = int(os.environ.get("DASHBOARD_PORT", 8081))

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trading Agent 500 — Live Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}
h1{font-size:24px;margin-bottom:4px;color:#58a6ff}
.subtitle{font-size:13px;color:#8b949e;margin-bottom:20px}
h2{font-size:15px;margin-bottom:10px;color:#8b949e;text-transform:uppercase;letter-spacing:1px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px;margin-bottom:20px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px}
.card h3{font-size:13px;color:#8b949e;margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px}
.flex{display:flex;gap:12px;flex-wrap:wrap}
.badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600}
.badge-pass{background:#003d1a;color:#3fb950;border:1px solid #238636}
.badge-fail{background:#3d0000;color:#f85149;border:1px solid #da3633}
.badge-live{background:#002d3d;color:#58a6ff;border:1px solid #1f6feb}
.badge-pending{background:#3d2e00;color:#d29922;border:1px solid #9e6a03}
.stat-row{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #21262d;font-size:13px}
.stat-row:last-child{border:none}
.stat-label{color:#8b949e}
.stat-value{font-weight:500}
.green{color:#3fb950}
.red{color:#f85149}
.orange{color:#d29922}
.blue{color:#58a6ff}
pre{background:#010409;padding:12px;border-radius:6px;font-size:11px;line-height:1.5;overflow-x:auto;border:1px solid #21262d;font-family:'Cascadia Code','Fira Code','Consolas',monospace;white-space:pre-wrap;word-break:break-all;max-height:400px;overflow-y:auto}
.mono{font-family:'Cascadia Code','Fira Code','Consolas',monospace;font-size:12px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;padding:6px 8px;color:#8b949e;border-bottom:2px solid #30363d;font-size:10px;text-transform:uppercase}
td{padding:6px 8px;border-bottom:1px solid #21262d}
tr:hover td{background:#1c2128}
.log-box{background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:10px;max-height:300px;overflow-y:auto;font-family:'Cascadia Code','Fira Code','Consolas',monospace;font-size:11px;line-height:1.5}
.log-box div{padding:1px 4px;white-space:pre-wrap;word-break:break-all}
.log-box div:nth-child(odd){background:#010409}
.tab-bar{display:flex;gap:4px;margin-bottom:12px;flex-wrap:wrap}
.tab{padding:6px 14px;border-radius:6px;font-size:12px;cursor:pointer;border:1px solid #30363d;background:transparent;color:#8b949e}
.tab.active{background:#1f6feb;color:#fff;border-color:#1f6feb;font-weight:600}
.tab:hover:not(.active){background:#1c2128}
.page{display:none}
.page.active{display:block}
.refresh-info{text-align:center;margin-top:20px;font-size:12px;color:#484f58}
.loading{text-align:center;padding:30px;color:#484f58}
</style>
</head>
<body>
<h1>trading-agent500</h1>
<div class="subtitle">Live Dashboard &middot; <span id="update-time">-</span></div>

<div class="tab-bar">
<div class="tab active" onclick="switchTab('overview')">Overview</div>
<div class="tab" onclick="switchTab('strategy')">Strategy Code</div>
<div class="tab" onclick="switchTab('backtests')">Backtest History</div>
<div class="tab" onclick="switchTab('positions')">Positions</div>
<div class="tab" onclick="switchTab('trades')">Trade Log</div>
<div class="tab" onclick="switchTab('activity')">Activity Log</div>
</div>

<div id="page-overview" class="page active">
<div class="grid">
<div class="card"><h3>Balance</h3><div id="balance" class="loading">Loading...</div></div>
<div class="card"><h3>Performance Summary</h3><div id="perf-summary" class="loading">Loading...</div></div>
</div>
<div class="card"><h3>Coin Status</h3><div id="coin-status" class="loading">Loading...</div></div>
</div>

<div id="page-strategy" class="page">
<div class="card"><h3>Active Strategy Code</h3><div id="strategy-code" class="loading">Loading...</div></div>
</div>

<div id="page-backtests" class="page">
<div class="card"><h3>Metric Failures History</h3><div id="backtest-history" class="loading">Loading...</div></div>
</div>

<div id="page-positions" class="page">
<div class="card"><h3>Open Positions</h3><div id="open-positions" class="loading">Loading...</div></div>
</div>

<div id="page-trades" class="page">
<div class="card"><h3>Trade History</h3><div id="trade-history" class="loading">Loading...</div></div>
</div>

<div id="page-activity" class="page">
<div class="card"><h3>Recent Activity</h3><div id="activity-log" class="loading">Loading...</div></div>
</div>

<div class="refresh-info">Auto-refreshes every 10s</div>

<script>
function switchTab(name){document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));document.getElementById('page-'+name).classList.add('active');event.target.classList.add('active')}
function escapeHTML(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}
function fmtNum(n){return Number(n).toLocaleString('en-IN',{minimumFractionDigits:2})}
function fmtPct(n){return Number(n).toFixed(2)+'%'}

async function loadAll(){
try{
document.getElementById('update-time').textContent=new Date().toLocaleTimeString();
const d=await fetch('/api/dashboard').then(r=>r.json());

const balDiv=document.getElementById('balance');
if(d.balance!==null){
balDiv.innerHTML='<div style="font-size:32px;font-weight:700;color:#58a6ff;margin:8px 0">\u20b9'+fmtNum(d.balance)+'</div><div class="stat-row"><span class="stat-label">Source</span><span class="stat-value">'+escapeHTML(d.balance_source)+'</span></div>';
}else{balDiv.innerHTML='<div style="color:#f85149;padding:10px">Balance unavailable (no API keys or exchange down)</div>'}

const perf=d.performance||{};
document.getElementById('perf-summary').innerHTML=
'<div class="stat-row"><span class="stat-label">Total Trades</span><span class="stat-value">'+(perf.total_trades||0)+'</span></div>'+
'<div class="stat-row"><span class="stat-label">Win Rate</span><span class="stat-value '+(perf.win_rate>=55?'green':'red')+'">'+(perf.win_rate||0)+'%</span></div>'+
'<div class="stat-row"><span class="stat-label">Total PnL</span><span class="stat-value '+(perf.total_pnl>=0?'green':'red')+'">\u20b9'+fmtNum(perf.total_pnl||0)+'</span></div>'+
'<div class="stat-row"><span class="stat-label">Wins / Losses</span><span class="stat-value"><span class="green">'+(perf.wins||0)+'</span> / <span class="red">'+(perf.losses||0)+'</span></span></div>'+
'<div class="stat-row"><span class="stat-label">Consec. Losses</span><span class="stat-value '+(perf.consecutive_losses>=3?'red':'orange')+'">'+(perf.consecutive_losses||0)+'</span></div>'+
'<div class="stat-row"><span class="stat-label">Strategy Version</span><span class="stat-value blue">v'+(perf.strategy_version||1)+'</span></div>';

const coinDiv=document.getElementById('coin-status');
let coinHTML='<div class="flex">';
const coins=d.coins||{};
let hasCoins=false;
for(const[coin,status]of Object.entries(coins)){
hasCoins=true;
let cls='badge-fail',label='FAIL';
if(status.trading){cls='badge-live';label='LIVE'}
else if(status.passed){cls='badge-pass';label='PASS'}
coinHTML+='<div><span class="badge '+cls+'">'+escapeHTML(coin)+' '+label+'</span>'+(status.failed?' <span style="font-size:11px;color:#f85149">'+escapeHTML(status.failed)+'</span>':'')+'</div>';
}
if(!hasCoins)coinHTML+='<div style="color:#484f58">No coin data</div>';
coinHTML+='</div>';
coinDiv.innerHTML=coinHTML;
}catch(e){document.getElementById('balance').innerHTML='<div class="error">Error: '+e.message+'</div>'}
}

async function loadStrategy(){
try{
const s=await fetch('/api/strategy').then(r=>r.json());
const div=document.getElementById('strategy-code');
if(s.code){
let html='<div class="stat-row"><span class="stat-label">Approved Coins</span><span class="stat-value blue">'+(s.coins||[]).join(', ')+'</span></div>';
html+='<div class="stat-row"><span class="stat-label">Strategy Length</span><span class="stat-value">'+(s.code.length)+' chars</span></div>';
html+='<div style="margin-top:10px"><pre>'+escapeHTML(s.code)+'</pre></div>';
div.innerHTML=html;
}else{div.innerHTML='<div style="color:#484f58">No strategy saved yet. Run the agent to generate one.</div>'}
}catch(e){document.getElementById('strategy-code').innerHTML='<div class="error">Error: '+e.message+'</div>'}
}

async function loadBacktests(){
try{
const b=await fetch('/api/metric_failures').then(r=>r.json());
const div=document.getElementById('backtest-history');
if(b&&Object.keys(b).length>0){
let html='<table><thead><tr><th>Coin</th><th>Attempts</th><th>Failures by Metric</th></tr></thead><tbody>';
for(const[coin,data]of Object.entries(b)){
let fails=Object.entries(data.failures||{}).map(([m,c])=>'<span class="red">'+escapeHTML(m)+': '+c+'x</span>').join(' | ');
html+='<tr><td><strong>'+escapeHTML(coin)+'</strong></td><td>'+data.total_attempts+'</td><td>'+fails+'</td></tr>';
}
html+='</tbody></table>';
div.innerHTML=html;
}else{div.innerHTML='<div style="color:#484f58">No backtest failures recorded yet.</div>'}
}catch(e){document.getElementById('backtest-history').innerHTML='<div class="error">Error: '+e.message+'</div>'}
}

async function loadPositions(){
try{
const p=await fetch('/api/positions').then(r=>r.json());
const div=document.getElementById('open-positions');
const keys=Object.keys(p);
if(keys.length>0){
let html='<table><thead><tr><th>Coin</th><th>Entry</th><th>Qty</th><th>SL</th><th>TP</th><th>Duration</th></tr></thead><tbody>';
for(const[coin,pos]of Object.entries(p)){
let dur='';
if(pos.entry_time){dur=Math.floor((Date.now()/1000-pos.entry_time)/3600)+'h'}
html+='<tr><td><strong>'+escapeHTML(coin)+'</strong></td><td>\u20b9'+fmtNum(pos.entry_price)+'</td><td>'+pos.quantity+'</td><td class="red">'+pos.sl_pct+'%</td><td class="green">'+pos.tp_pct+'%</td><td>'+dur+'</td></tr>';
}
html+='</tbody></table>';
div.innerHTML=html;
}else{div.innerHTML='<div style="color:#484f58">No open positions.</div>'}
}catch(e){document.getElementById('open-positions').innerHTML='<div class="error">Error: '+e.message+'</div>'}
}

async function loadTrades(){
try{
const t=await fetch('/api/trades').then(r=>r.json());
const div=document.getElementById('trade-history');
if(t.length>0){
let html='<table><thead><tr><th>Time</th><th>Coin</th><th>Entry</th><th>Exit</th><th>PnL</th><th>Result</th></tr></thead><tbody>';
const recent=t.slice(-50).reverse();
for(const tr of recent){
html+='<tr><td style="color:#8b949e">'+escapeHTML(tr.time||'')+'</td><td><strong>'+escapeHTML(tr.coin)+'</strong></td>'+
'<td>\u20b9'+fmtNum(tr.entry)+'</td><td>\u20b9'+fmtNum(tr.exit)+'</td>'+
'<td class="'+(tr.won?'green':'red')+'">\u20b9'+fmtNum(tr.pnl)+'</td>'+
'<td><span class="badge '+(tr.won?'badge-pass':'badge-fail')+'">'+(tr.won?'WIN':'LOSS')+'</span></td></tr>';
}
html+='</tbody></table>';
div.innerHTML=html;
}else{div.innerHTML='<div style="color:#484f58">No trades yet.</div>'}
}catch(e){document.getElementById('trade-history').innerHTML='<div class="error">Error: '+e.message+'</div>'}
}

async function loadActivity(){
try{
const a=await fetch('/api/logs').then(r=>r.json());
const div=document.getElementById('activity-log');
const lines=a.lines||[];
if(lines.length>0){
let html='<div class="log-box">';
for(const line of lines.slice(-80)){
const clean=escapeHTML(line);
let color='';
if(clean.includes('FAIL')||clean.includes('fail')||clean.includes('Error')||clean.includes('error'))color='color:#f85149';
else if(clean.includes('PASS')||clean.includes('WIN')||clean.includes('pass'))color='color:#3fb950';
else if(clean.includes('LIVE')||clean.includes('BUY')||clean.includes('SELL')||clean.includes('SL')||clean.includes('TP'))color='color:#d29922';
html+='<div'+(color?' style="'+color+'"':'')+'>'+clean+'</div>';
}
html+='</div>';
div.innerHTML=html;
const box=div.querySelector('.log-box');
if(box)box.scrollTop=box.scrollHeight;
}else{div.innerHTML='<div style="color:#484f58">No activity yet.</div>'}
}catch(e){document.getElementById('activity-log').innerHTML='<div class="error">Error: '+e.message+'</div>'}
}

function refreshAll(){loadAll();loadStrategy();loadBacktests();loadPositions();loadTrades();loadActivity()}
refreshAll();
setInterval(refreshAll,10000);
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
                self._json(200, {"code": data.get("strategy_code") if data else None, "coins": data.get("good_coins") if data else []})
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
            "coins": coins
        }

    def log_message(self, *args): pass

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[DASHBOARD] Running at http://0.0.0.0:{PORT}/")
    server.serve_forever()
