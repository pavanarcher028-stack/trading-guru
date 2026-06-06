import json
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from monitor import load_log
import log_capture

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trading Agent 500 — Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px;min-height:100vh}
h1{font-size:24px;margin-bottom:20px;color:#58a6ff}
h2{font-size:16px;margin-bottom:12px;color:#8b949e;text-transform:uppercase;letter-spacing:1px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin-bottom:20px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px}
.card h3{font-size:14px;color:#8b949e;margin-bottom:8px}
.coin-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px;margin-top:8px}
.coin-card{border-radius:6px;padding:10px;text-align:center;font-size:13px}
.coin-card.pass{background:#003d1a;border:1px solid #238636;color:#3fb950}
.coin-card.fail{background:#3d0000;border:1px solid #da3633;color:#f85149}
.coin-card.live{background:#002d3d;border:1px solid #1f6feb;color:#58a6ff}
.coin-card .label{font-size:11px;opacity:.7;margin-top:4px}
.coin-card .value{font-size:18px;font-weight:600}
.balance-large{font-size:36px;font-weight:700;color:#58a6ff;margin:8px 0}
.balance-label{font-size:12px;color:#8b949e}
.stat-row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #21262d;font-size:13px}
.stat-row:last-child{border-bottom:none}
.stat-label{color:#8b949e}
.stat-value{color:#c9d1d9;font-weight:500}
.stat-value.green{color:#3fb950}
.stat-value.red{color:#f85149}
.stat-value.orange{color:#d29922}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:8px 12px;color:#8b949e;border-bottom:2px solid #30363d;font-size:11px;text-transform:uppercase}
td{padding:8px 12px;border-bottom:1px solid #21262d}
tr:hover td{background:#1c2128}
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600}
.badge-win{background:#003d1a;color:#3fb950;border:1px solid #238636}
.badge-loss{background:#3d0000;color:#f85149;border:1px solid #da3633}
.log-container{background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:10px;max-height:320px;overflow-y:auto;font-family:'Cascadia Code','Fira Code','Consolas',monospace;font-size:11px;line-height:1.5}
.log-container div{padding:1px 4px;white-space:pre-wrap;word-break:break-all}
.log-container div:nth-child(odd){background:#010409}
.refresh-info{text-align:center;margin-top:20px;font-size:12px;color:#484f58}
.loading{text-align:center;padding:40px;color:#484f58}
.error{text-align:center;padding:20px;color:#f85149;background:#3d0000;border-radius:8px;border:1px solid #da3633}
@media(max-width:600px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<h1>trading-agent500</h1>
<div class="grid">
<div class="card"><h3>Balance</h3><div id="balance" class="loading">Loading...</div></div>
<div class="card"><h3>Performance</h3><div id="performance" class="loading">Loading...</div></div>
</div>
<div class="grid">
<div class="card"><h3>Coin Status</h3><div id="coins" class="loading">Loading...</div></div>
<div class="card"><h3>Open Positions</h3><div id="positions" class="loading">Loading...</div></div>
</div>
<div class="card"><h3>Recent Trades</h3><div id="trades" class="loading">Loading...</div></div>
<div class="card"><h3>Recent Activity</h3><div id="activity" class="loading">Loading...</div></div>
<div class="refresh-info">Auto-refreshes every 15s &middot; <span id="last-update">-</span></div>
<script>
function fetchAPI(endpoint,timeout){timeout=timeout||12000;const c=new AbortController();setTimeout(()=>c.abort(),timeout);return fetch(endpoint,{signal:c.signal}).then(r=>{if(!r.ok)throw new Error(r.statusText+' ('+r.status+')');return r.json()})}
function escapeHTML(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}
function render(){
fetchAPI('/api/dashboard').then(d=>{
document.getElementById('last-update').textContent=new Date().toLocaleTimeString();
const balDiv=document.getElementById('balance');
if(d.balance!==null&&d.balance!==undefined){
balDiv.innerHTML='<div class="balance-large">\u20b9'+Number(d.balance).toLocaleString('en-IN',{minimumFractionDigits:2})+'</div><div class="balance-label">'+d.balance_source+'</div>';
}else{
balDiv.innerHTML='<div class="balance-large" style="color:#f85149">N/A</div><div class="balance-label">Balance fetch failed</div>';
}
const perfDiv=document.getElementById('performance');
const p=d.performance||{total_trades:0,win_rate:0,total_pnl:0,wins:0,losses:0,consecutive_losses:0};
perfDiv.innerHTML='<div class="stat-row"><span class="stat-label">Total Trades</span><span class="stat-value">'+p.total_trades+'</span></div><div class="stat-row"><span class="stat-label">Win Rate</span><span class="stat-value '+(p.win_rate>=55?'green':'red')+'">'+p.win_rate+'%</span></div><div class="stat-row"><span class="stat-label">Total PnL</span><span class="stat-value '+(p.total_pnl>=0?'green':'red')+'">\u20b9'+Number(p.total_pnl).toLocaleString('en-IN',{minimumFractionDigits:2})+'</span></div><div class="stat-row"><span class="stat-label">Wins</span><span class="stat-value green">'+p.wins+'</span></div><div class="stat-row"><span class="stat-label">Losses</span><span class="stat-value red">'+p.losses+'</span></div><div class="stat-row"><span class="stat-label">Consec. Losses</span><span class="stat-value '+(p.consecutive_losses>=3?'red':'orange')+'">'+p.consecutive_losses+'</span></div>';
const coinDiv=document.getElementById('coins');
let coinHTML='<div class="coin-grid">';
for(const[coin,status]of Object.entries(d.coins||{})){
let cls='fail',label='FAIL';
if(status.passed){cls='pass';label='PASS'}
if(status.trading){cls='live';label='LIVE'}
coinHTML+='<div class="coin-card '+cls+'"><div class="value">'+escapeHTML(coin)+'</div><div class="label">'+label+'</div></div>';
}
coinHTML+='</div>';
coinDiv.innerHTML=coinHTML;
const posDiv=document.getElementById('positions');
const pos=d.positions||{};
const posKeys=Object.keys(pos);
if(posKeys.length===0){
posDiv.innerHTML='<div style="text-align:center;padding:16px;color:#484f58">No open positions</div>';
}else{
let posHTML='';
for(const[coin,p]of Object.entries(pos)){
const cp=(d.current_prices&&d.current_prices[coin])||p.entry_price;
const pnl=((cp-p.entry_price)/p.entry_price*100);
posHTML+='<div class="coin-card" style="background:#002d3d;border-color:#1f6feb;margin-bottom:6px;text-align:left">';
posHTML+='<div style="display:flex;justify-content:space-between;align-items:center">';
posHTML+='<span style="font-weight:600;color:#58a6ff">'+coin+'</span>';
posHTML+='<span class="stat-value '+(pnl>=0?'green':'red')+'">'+pnl.toFixed(2)+'%</span>';
posHTML+='</div>';
posHTML+='<div style="font-size:11px;color:#8b949e;margin-top:4px">Entry: \u20b9'+Number(p.entry_price).toLocaleString('en-IN')+' &middot; SL: '+p.sl_pct+'% &middot; TP: '+p.tp_pct+'%</div>';
posHTML+='</div>';
}
posDiv.innerHTML=posHTML;
}
const tradesDiv=document.getElementById('trades');
const trades=d.trades||[];
if(trades.length===0){
tradesDiv.innerHTML='<div style="text-align:center;padding:16px;color:#484f58">No trades yet</div>';
}else{
let tableHTML='<table><thead><tr><th>Time</th><th>Coin</th><th>PnL</th><th>Result</th></tr></thead><tbody>';
const recent=trades.slice(-20).reverse();
for(const t of recent){
const cls=t.won?'badge-win':'badge-loss';
const label=t.won?'WIN':'LOSS';
tableHTML+='<tr><td style="color:#8b949e">'+escapeHTML(t.time||'')+'</td><td><strong>'+escapeHTML(t.coin)+'</strong></td><td class="stat-value '+(t.won?'green':'red')+'">\u20b9'+Number(t.pnl).toLocaleString('en-IN',{minimumFractionDigits:2})+'</td><td><span class="badge '+cls+'">'+label+'</span></td></tr>';
}
tableHTML+='</tbody></table>';
tradesDiv.innerHTML=tableHTML;
}
}).catch(e=>{
document.getElementById('balance').innerHTML='<div class="error">Failed to load dashboard: '+e.message+'</div>';
});
fetchAPI('/api/logs').then(d=>{
const actDiv=document.getElementById('activity');
const lines=d.lines||[];
if(lines.length===0){
actDiv.innerHTML='<div style="text-align:center;padding:16px;color:#484f58">No activity yet</div>';
}else{
let html='<div class="log-container">';
for(const line of lines){
const clean=escapeHTML(line);
const cls=clean.includes('FAIL')||clean.includes('fail')||clean.includes('Error')||clean.includes('error')?'red':clean.includes('PASS')||clean.includes('WIN')||clean.includes('pass')?'green':clean.includes('LIVE')||clean.includes('BUY')||clean.includes('SELL')?'orange':'';
html+='<div'+(cls?' style="color:'+cls+'"':'')+'>'+clean+'</div>';
}
html+='</div>';
actDiv.innerHTML=html;
const container=actDiv.querySelector('.log-container');
if(container)container.scrollTop=container.scrollHeight;
}).catch(e=>{
document.getElementById('activity').innerHTML='<div class="error">Failed to load logs</div>';
});
}
render();
setInterval(render,15000);
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path in ("/", "/dashboard"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(DASHBOARD_HTML.encode())
            elif self.path == "/api/dashboard":
                data = self._build_dashboard_data()
                self._json_response(200, data)
            elif self.path == "/api/logs":
                lines = log_capture.get_recent(60)
                self._json_response(200, {"lines": lines})
            elif self.path == "/status":
                log = load_log()
                self._json_response(200, log)
            else:
                self._json_response(404, {"error": "not found"})
        except Exception as e:
            self._json_response(500, {"error": str(e)})

    def _json_response(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _build_dashboard_data(self):
        log = load_log()
        total = log["win_count"] + log["loss_count"]
        win_rate = round((log["win_count"] / total) * 100, 1) if total > 0 else 0
        coins = {}
        for c in ["BTC", "ETH", "BNB", "SOL", "XRP"]:
            coins[c] = {"passed": False, "failed": None, "trading": False}
        strategy_data = self._load_json("strategy_store.json")
        if strategy_data:
            for c in strategy_data.get("good_coins", []):
                if c in coins:
                    coins[c]["passed"] = True
        metric_fails = self._load_json("metric_failures.json")
        if metric_fails:
            for c, data in metric_fails.items():
                if c in coins and not coins[c]["passed"]:
                    failures = data.get("failures", {})
                    coins[c]["failed"] = ", ".join(failures.keys()) if failures else "unknown"
        positions = self._load_json("positions.json") or {}
        for c in positions:
            if c in coins:
                coins[c]["trading"] = True
        balance_data = self._try_get_balance()
        return {
            "balance": balance_data.get("balance"),
            "balance_source": balance_data.get("source", "unknown"),
            "current_prices": balance_data.get("prices", {}),
            "performance": {
                "total_trades": total,
                "win_rate": win_rate,
                "total_pnl": log.get("total_pnl", 0),
                "wins": log["win_count"],
                "losses": log["loss_count"],
                "consecutive_losses": log.get("consecutive_losses", 0),
                "strategy_version": log.get("strategy_version", 1)
            },
            "coins": coins,
            "positions": positions,
            "trades": log.get("trades", [])
        }

    def _load_json(self, path):
        try:
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def _try_get_balance(self):
        try:
            from trader import get_balance
            bal = get_balance()
            if bal and bal > 0:
                return {"balance": bal, "source": "live (CoinDCX)", "prices": {}}
        except Exception:
            pass
        try:
            import requests as req
            prices = {}
            pairs = {"BTC": "B-BTC_USDT", "ETH": "B-ETH_USDT", "BNB": "B-BNB_USDT", "SOL": "B-SOL_USDT", "XRP": "B-XRP_USDT"}
            for sym, pair in pairs.items():
                r = req.get("https://public.coindcx.com/market_data/candles", params={"pair": pair, "interval": "1h", "limit": 1}, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    if data and len(data) > 0:
                        prices[sym] = float(data[-1]["close"])
            return {"balance": None, "source": "unavailable", "prices": prices}
        except Exception:
            return {"balance": None, "source": "unavailable", "prices": {}}

    def log_message(self, format, *args):
        pass

def start_api():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print("[API] Dashboard at http://0.0.0.0:" + str(port) + "/", flush=True)
    server.serve_forever()
