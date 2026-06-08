import json
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import log_capture

log_capture.install()

PORT = int(os.environ.get("DASHBOARD_PORT", 8081))

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>trading-agent500</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#080c14;--surface:#0f1724;--surface2:#182235;--border:#1e2f4a;--border2:#2a3d5c;--text:#e0e7f0;--muted:#6b7f99;--accent:#3b82f6;--accent2:#60a5fa;--green:#22c55e;--green2:#16a34a;--red:#ef4444;--red2:#dc2626;--orange:#f59e0b;--cyan:#06b6d4;--purple:#8b5cf6;--pink:#ec4899;--radius:10px;--shadow:0 4px 24px rgba(0,0,0,.5)}
body{background:var(--bg);color:var(--text);font-family:Inter,system-ui,-apple-system,sans-serif;min-height:100vh;overflow-x:hidden}
.bg-glow{position:fixed;top:-200px;right:-200px;width:600px;height:600px;background:radial-gradient(circle,rgba(59,130,246,.08),transparent 70%);pointer-events:none;z-index:0}
.container{max-width:1440px;margin:0 auto;padding:0 24px 40px;position:relative;z-index:1}

/* HEADER */
.header{display:flex;align-items:center;justify-content:space-between;padding:20px 0 16px;border-bottom:1px solid var(--border);margin-bottom:28px;flex-wrap:wrap;gap:12px}
.header-left{display:flex;align-items:center;gap:14px}
.header-logo{font-size:22px;font-weight:800;letter-spacing:-.5px;background:linear-gradient(135deg,#60a5fa,#3b82f6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.header-logo span{font-weight:400;color:var(--muted);-webkit-text-fill-color:var(--muted)}
.header-right{display:flex;align-items:center;gap:16px;font-size:13px}
.header-status{display:flex;align-items:center;gap:7px;padding:6px 14px;border-radius:20px;background:var(--surface2);border:1px solid var(--border);font-weight:500;font-size:12px}
.pulse-dot{width:8px;height:8px;border-radius:50%;display:inline-block;animation:pulse 2s infinite}
.pulse-dot.green{background:var(--green);box-shadow:0 0 8px rgba(34,197,94,.6)}
.pulse-dot.yellow{background:var(--orange);box-shadow:0 0 8px rgba(245,158,11,.6)}
.pulse-dot.red{background:var(--red);box-shadow:0 0 8px rgba(239,68,68,.6)}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.6;transform:scale(1.15)}}

/* NAV */
.nav{display:flex;gap:4px;margin-bottom:24px;flex-wrap:wrap}
.nav-btn{padding:8px 18px;border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;border:1px solid transparent;background:transparent;color:var(--muted);transition:.15s;font-family:inherit}
.nav-btn:hover{background:var(--surface2);color:var(--text)}
.nav-btn.active{background:var(--accent);color:#fff;border-color:var(--accent);box-shadow:0 0 16px rgba(59,130,246,.25)}

/* GRID */
.grid{display:grid;gap:16px;margin-bottom:16px}
.g2{grid-template-columns:1fr 1fr}
.g3{grid-template-columns:repeat(3,1fr)}
.g4{grid-template-columns:repeat(4,1fr)}
@media(max-width:1100px){.g4{grid-template-columns:repeat(2,1fr)}}
@media(max-width:750px){.g2,.g3,.g4{grid-template-columns:1fr}}

/* CARDS */
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:20px;box-shadow:var(--shadow);transition:border-color .2s}
.card:hover{border-color:var(--border2)}
.card-sm{padding:16px}
.card-label{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:1.2px;color:var(--muted);margin-bottom:8px}
.card-value{font-size:26px;font-weight:700;letter-spacing:-.5px}
.card-sub{font-size:12px;color:var(--muted);margin-top:2px}
.card-row{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid rgba(30,47,74,.5);font-size:13px}
.card-row:last-child{border-bottom:none}
.card-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}

/* SPARKLINE */
.spark{display:flex;align-items:flex-end;gap:2px;height:32px;margin-top:6px}
.spark-bar{width:6px;border-radius:2px 2px 0 0;min-height:2px;transition:height .3s}

/* TABLES */
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:10px 10px;color:var(--muted);border-bottom:2px solid var(--border);font-size:10px;text-transform:uppercase;letter-spacing:.8px;font-weight:600;white-space:nowrap}
td{padding:9px 10px;border-bottom:1px solid rgba(30,47,74,.4)}
tr:hover td{background:var(--surface2)}

/* BADGES / PILLS */
.pill{display:inline-flex;align-items:center;gap:5px;padding:3px 11px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap}
.pill-g{background:rgba(34,197,94,.12);color:var(--green);border:1px solid rgba(34,197,94,.2)}
.pill-r{background:rgba(239,68,68,.12);color:var(--red);border:1px solid rgba(239,68,68,.2)}
.pill-b{background:rgba(59,130,246,.12);color:var(--accent);border:1px solid rgba(59,130,246,.2)}
.pill-o{background:rgba(245,158,11,.12);color:var(--orange);border:1px solid rgba(245,158,11,.2)}
.pill-p{background:rgba(139,92,246,.12);color:var(--purple);border:1px solid rgba(139,92,246,.2)}
.coin-strip{display:flex;flex-wrap:wrap;gap:6px}
.coin-chip{display:inline-flex;align-items:center;gap:5px;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:500}
.coin-chip .dot{width:6px;height:6px;border-radius:50%}
.coin-chip.live{background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.25);color:var(--accent)}
.coin-chip.live .dot{background:var(--accent);animation:pulse 1.5s infinite}
.coin-chip.pass{background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.25);color:var(--green)}
.coin-chip.pass .dot{background:var(--green)}
.coin-chip.fail{background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.25);color:var(--red)}
.coin-chip.fail .dot{background:var(--red)}

/* LOGBOX */
.logbox{background:#050a14;border:1px solid var(--border);border-radius:8px;padding:8px;max-height:420px;overflow-y:auto;font-family:'JetBrains Mono',monospace;font-size:11px;line-height:1.6}
.ln{padding:1px 8px;border-radius:2px;white-space:pre-wrap;word-break:break-all}
.ln:nth-child(odd){background:rgba(255,255,255,.015)}
.ln:hover{background:rgba(255,255,255,.03)}

/* CODE */
.prec{background:#050a14;border:1px solid var(--border);border-radius:8px;padding:16px;font-size:12px;line-height:1.6;overflow:auto;max-height:480px;font-family:'JetBrains Mono',monospace;white-space:pre-wrap;word-break:break-all}

/* PAGES */
.page{display:none}
.page.show{display:block}

/* MISC */
.empty{text-align:center;padding:36px 16px;color:var(--muted);font-size:13px}
.loader{text-align:center;padding:28px;color:var(--muted)}
.bar{margin-top:8px;height:4px;border-radius:4px;background:var(--border);overflow:hidden}
.bar-fill{height:100%;border-radius:4px;transition:width .5s}
.two-up{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:800px){.two-up{grid-template-columns:1fr}}

/* FOOTER BAR */
.footer{display:flex;align-items:center;gap:14px;padding:14px 18px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);margin-top:24px;font-size:12px;color:var(--muted)}
.footer .spin{width:12px;height:12px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:rot 1s linear infinite}
@keyframes rot{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="bg-glow"></div>
<div class="container">

<header class="header">
<div class="header-left">
<div class="header-logo">trading<span>agent</span>500</div>
</div>
<div class="header-right">
<div class="header-status" id="hdr-status"><span class="pulse-dot yellow"></span><span>Initializing</span></div>
<span style="color:var(--muted);font-size:12px" id="hdr-time"></span>
</div>
</header>

<nav class="nav" id="nav">
<button class="nav-btn active" data-pg="overview">Overview</button>
<button class="nav-btn" data-pg="strategy">Strategy</button>
<button class="nav-btn" data-pg="trades">Trades</button>
<button class="nav-btn" data-pg="positions">Positions</button>
<button class="nav-btn" data-pg="backtests">Backtests</button>
<button class="nav-btn" data-pg="activity">Live Log</button>
</nav>

<div id="pg-overview" class="page show">
<div class="grid g4">
<div class="card card-sm"><div class="card-label">Total Trades</div><div class="card-value" id="ov-tr" style="color:var(--accent)">-</div></div>
<div class="card card-sm"><div class="card-label">Win Rate</div><div class="card-value" id="ov-wr">-</div><div class="bar" id="ov-wr-bar"><div class="bar-fill" style="width:0%;background:var(--green)"></div></div></div>
<div class="card card-sm"><div class="card-label">Total P&amp;L</div><div class="card-value" id="ov-pnl">-</div></div>
<div class="card card-sm"><div class="card-label">Strategy Version</div><div class="card-value" id="ov-ver" style="color:var(--purple)">-</div></div>
</div>

<div class="grid g2">
<div class="card">
<div class="card-label">Balance</div>
<div id="ov-bal" class="loader">Loading...</div>
</div>
<div class="card">
<div class="card-label">Active Coins</div>
<div id="ov-coins" class="loader">Loading...</div>
</div>
</div>

<div class="card">
<div class="card-label" style="display:flex;justify-content:space-between;align-items:center"><span>Current Positions</span><span id="ov-pos-count" style="font-weight:400;font-size:10px;color:var(--muted)"></span></div>
<div id="ov-pos" class="loader">Loading...</div>
</div>

<div class="card" style="margin-top:16px">
<div class="card-label">Recent Trades <span style="font-weight:400;font-size:10px;color:var(--muted)" id="ov-tr-count"></span></div>
<div id="ov-tr-table" class="loader">Loading...</div>
</div>
</div>

<div id="pg-strategy" class="page">
<div class="grid g2">
<div class="card">
<div class="card-label">Strategy Info</div>
<div id="strat-info" class="loader">Loading...</div>
</div>
<div class="card">
<div class="card-label">SL / TP Configuration</div>
<div id="strat-sl-tp" class="loader">Loading...</div>
</div>
</div>
<div class="card">
<div class="card-label">Source Code</div>
<pre class="prec" id="strat-code">Loading...</pre>
</div>
</div>

<div id="pg-trades" class="page">
<div class="card">
<div class="card-label">Trade History <span id="tr-count" style="font-weight:400;font-size:10px;color:var(--muted)"></span></div>
<div id="tr-table" class="loader">Loading...</div>
</div>
</div>

<div id="pg-positions" class="page">
<div class="card">
<div class="card-label">Open Positions</div>
<div id="pos-table" class="loader">Loading...</div>
</div>
</div>

<div id="pg-backtests" class="page">
<div class="card">
<div class="card-label">Backtest Metric Failures</div>
<div id="bt-table" class="loader">Loading...</div>
</div>
</div>

<div id="pg-activity" class="page">
<div class="card">
<div class="card-label" style="display:flex;justify-content:space-between;align-items:center"><span>Live Activity Log</span><span id="log-count" style="font-weight:400;font-size:10px;color:var(--muted)"></span></div>
<div id="log-box" class="loader">Loading...</div>
</div>
</div>

<div class="footer">
<div class="spin"></div>
<span>Auto-refresh every <strong>8s</strong></span>
<span id="ft-time" style="margin-left:auto;color:var(--accent)"></span>
</div>
</div>

<script>
const $ =(s,q=document)=>q.querySelector(s);
const $$=(s,q=document)=>[...q.querySelectorAll(s)];
const esc=(s)=>{const d=document.createElement('div');d.textContent=s;return d.innerHTML};
const inr=(n,d=2)=>Number(n).toLocaleString('en-IN',{minimumFractionDigits:d});
const api=(p)=>fetch(p).then(r=>r.json());

$$('.nav-btn').forEach(b=>b.onclick=()=>{
$$('.nav-btn').forEach(x=>x.classList.remove('active'));
$$('.page').forEach(x=>x.classList.remove('show'));
b.classList.add('active');
$('#pg-'+b.dataset.pg).classList.add('show');
});

/* sparkline helper */
function spark(vals,color='var(--accent)'){
if(!vals||vals.length<2)return'';
const mx=Math.max(...vals.map(Math.abs),1);
return '<div class="spark">'+vals.map(v=>{
const p=Math.abs(v)/mx*100;
return '<div class="spark-bar" style="height:'+Math.max(p,5)+'%;background:'+(v>=0?color:'var(--red)')+'"></div>';
}).join('')+'</div>';
}

async function load(){
try{
const t0=performance.now();
const d=await api('/api/dashboard');
const p=d.performance||{};

/* header */
const hs=$('#hdr-status');
if(d.balance){hs.innerHTML='<span class="pulse-dot green"></span><span>Live Trading</span>';}
else if(p.total_trades>0){hs.innerHTML='<span class="pulse-dot yellow"></span><span>Paper Trading</span>';}
else{hs.innerHTML='<span class="pulse-dot yellow"></span><span>Waiting for strategy</span>';}
$('#hdr-time').textContent=new Date().toLocaleTimeString();
$('#ft-time').textContent=new Date().toLocaleTimeString()+' — '+(performance.now()-t0|0)+'ms';

/* overview stats */
const tot=p.total_trades||0;
$('#ov-tr').textContent=tot;
const wr=p.win_rate||0;
const wrEl=$('#ov-wr');
wrEl.textContent=wr+'%';
const wrC=wr>=55?'var(--green)':wr>=45?'var(--orange)':'var(--red)';
wrEl.style.color=wrC;
$('#ov-wr-bar .bar-fill').style.width=wr+'%';
$('#ov-wr-bar .bar-fill').style.background=wrC;

const pnlV=p.total_pnl||0;
const pnlEl=$('#ov-pnl');
pnlEl.textContent=(pnlV>=0?'+':'')+'\u20b9'+inr(pnlV);
pnlEl.style.color=pnlV>=0?'var(--green)':'var(--red)';
$('#ov-ver').textContent='v'+(p.strategy_version||1);

/* balance */
const balEl=$('#ov-bal');
if(d.balance){balEl.innerHTML='<div style="font-size:30px;font-weight:700;color:var(--accent);margin:2px 0">\u20b9'+inr(d.balance)+'</div><div style="font-size:12px;color:var(--muted)">source: '+esc(d.balance_source)+'</div>';}
else{balEl.innerHTML='<div style="color:var(--muted);padding:6px 0;font-size:13px">No balance data — API keys may be missing</div>';}

/* coins */
const coins=d.coins||{};
const coinEl=$('#ov-coins');
let ch='<div class="coin-strip">';
let hasCoin=false;
for(const[c,st]of Object.entries(coins)){
hasCoin=true;
let cls='fail',lab='FAIL';
if(st.trading){cls='live';lab='LIVE';}
else if(st.passed){cls='pass';lab='PASS';}
ch+='<span class="coin-chip '+cls+'"><span class="dot"></span>'+c+' '+lab+'</span>';
}
if(!hasCoin)ch+='<span style="color:var(--muted);font-size:13px">No coins</span>';
ch+='</div>';
coinEl.innerHTML=ch;

/* positions mini */
const pos=d.positions||{};
const pk=Object.keys(pos);
$('#ov-pos-count').textContent=pk.length+' open';
const posEl=$('#ov-pos');
if(pk.length>0){
let h='<div class="table-wrap"><table><thead><tr><th>Coin</th><th>Entry</th><th>Qty</th><th>SL</th><th>TP</th><th>Unrealized</th><th>Duration</th></tr></thead><tbody>';
for(const[coin,po]of Object.entries(pos)){
const dur=po.entry_time?Math.floor((Date.now()/1000-po.entry_time)/3600)+'h':'';
const up=po.current_price?(po.current_price-po.entry_price)*po.quantity:0;
h+='<tr><td><strong style="color:var(--accent)">'+coin+'</strong></td><td>\u20b9'+inr(po.entry_price)+'</td><td>'+po.quantity+'</td><td style="color:var(--red)">'+po.sl_pct+'%</td><td style="color:var(--green)">'+po.tp_pct+'%</td><td style="font-weight:600;color:'+(up>=0?'var(--green)':'var(--red)')+'">'+(up>=0?'+':'')+'\u20b9'+inr(up)+'</td><td style="color:var(--muted);font-size:12px">'+dur+'</td></tr>';
}
h+='</tbody></table></div>';
posEl.innerHTML=h;
}else{posEl.innerHTML='<div class="empty">No open positions</div>';}

/* recent trades mini */
const trAll=await api('/api/trades');
$('#ov-tr-count').textContent=trAll.length+' total';
const trMini=$('#ov-tr-table');
if(trAll.length>0){
const recent=trAll.slice(-20).reverse();
let h='<div class="table-wrap"><table><thead><tr><th>Time</th><th>Coin</th><th>Entry</th><th>Exit</th><th>PnL</th><th>R</th></tr></thead><tbody>';
for(const tr of recent){
h+='<tr><td style="color:var(--muted);font-size:11px">'+esc(tr.time||'')+'</td><td><strong>'+esc(tr.coin)+'</strong></td>'+
'<td>\u20b9'+inr(tr.entry)+'</td><td>\u20b9'+inr(tr.exit)+'</td>'+
'<td style="font-weight:600;color:'+(tr.won?'var(--green)':'var(--red)')+'">'+(tr.won?'+':'')+'\u20b9'+inr(tr.pnl)+'</td>'+
'<td><span class="pill '+(tr.won?'pill-g':'pill-r')+'">'+(tr.won?'WIN':'LOSS')+'</span></td></tr>';
}
h+='</tbody></table></div>';
trMini.innerHTML=h;
}else{trMini.innerHTML='<div class="empty">No trades yet</div>';}
}
catch(e){console.error('overview err',e)}
}

async function loadStrat(){
try{
const s=await api('/api/strategy');
if(s.coins&&s.coins.length){
const cList=s.coins.map(c=>'<span class="pill pill-b">'+c+'</span>').join(' ');
$('#strat-info').innerHTML='<div class="card-row"><span class="card-row-l" style="color:var(--muted)">Approved Coins</span><span>'+cList+'</span></div>'+
'<div class="card-row"><span style="color:var(--muted)">Code Size</span><span>'+(s.code?s.code.length:0)+' chars</span></div>'+
'<div class="card-row"><span style="color:var(--muted)">Source</span><span class="pill pill-p">Fallback Strategy</span></div>';
}else{
$('#strat-info').innerHTML='<div class="empty">No strategy saved yet</div>';
}
if(s.sl_pct&&s.tp_pct){
const sl=Math.abs(s.sl_pct);
$('#strat-sl-tp').innerHTML=
'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:4px">'+
'<div style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.2);border-radius:8px;padding:14px;text-align:center"><div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:4px">Stop Loss</div><div style="font-size:22px;font-weight:700;color:var(--red)">'+sl+'%</div></div>'+
'<div style="background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.2);border-radius:8px;padding:14px;text-align:center"><div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:4px">Take Profit</div><div style="font-size:22px;font-weight:700;color:var(--green)">'+s.tp_pct+'%</div></div>'+
'</div>';
}else{$('#strat-sl-tp').innerHTML='<div class="empty">No SL/TP configured</div>';}
if(s.code){$('#strat-code').textContent=s.code;}
else{$('#strat-code').textContent='// waiting for strategy';}
}catch(e){console.error(e)}
}

async function loadTrades(){
try{
const t=await api('/api/trades');
$('#tr-count').textContent=t.length+' total';
const div=$('#tr-table');
if(t.length>0){
const rev=t.slice(-200).reverse();
let h='<div class="table-wrap"><table><thead><tr><th>#</th><th>Time</th><th>Coin</th><th>Entry</th><th>Exit</th><th>PnL</th><th>Result</th></tr></thead><tbody>';
let wi=0,lo=0;
for(let i=0;i<rev.length;i++){
const tr=rev[i];
if(tr.won)wi++;else lo++;
h+='<tr><td style="color:var(--muted);font-size:11px">'+(t.length-i)+'</td><td style="color:var(--muted);font-size:11px">'+esc(tr.time||'')+'</td><td><strong>'+esc(tr.coin)+'</strong></td>'+
'<td>\u20b9'+inr(tr.entry)+'</td><td>\u20b9'+inr(tr.exit)+'</td>'+
'<td style="font-weight:600;color:'+(tr.won?'var(--green)':'var(--red)')+'">'+(tr.won?'+':'')+'\u20b9'+inr(tr.pnl)+'</td>'+
'<td><span class="pill '+(tr.won?'pill-g':'pill-r')+'">'+(tr.won?'WIN':'LOSS')+'</span></td></tr>';
}
h+='</tbody></table></div>'+
'<div style="margin-top:12px;display:flex;gap:12px;font-size:12px"><span><span class="pill pill-g">WIN</span> '+wi+'</span><span><span class="pill pill-r">LOSS</span> '+lo+'</span></div>';
div.innerHTML=h;
}else{div.innerHTML='<div class="empty">No trades yet</div>';}
}catch(e){console.error(e)}
}

async function loadPositions(){
try{
const p=await api('/api/positions');
const div=$('#pos-table');
const k=Object.keys(p);
if(k.length>0){
let h='<div class="table-wrap"><table><thead><tr><th>Coin</th><th>Entry Price</th><th>Quantity</th><th>Value</th><th>SL</th><th>TP</th><th>Unrealized PnL</th><th>Duration</th></tr></thead><tbody>';
for(const[coin,po]of Object.entries(p)){
const dur=po.entry_time?Math.floor((Date.now()/1000-po.entry_time)/3600)+'h':'';
const val=po.entry_price*po.quantity;
const up=po.current_price?(po.current_price-po.entry_price)*po.quantity:0;
h+='<tr><td><strong style="color:var(--accent)">'+coin+'</strong></td><td>\u20b9'+inr(po.entry_price)+'</td><td>'+po.quantity+'</td><td>\u20b9'+inr(val)+'</td>'+
'<td style="color:var(--red)">'+po.sl_pct+'%</td><td style="color:var(--green)">'+po.tp_pct+'%</td>'+
'<td style="font-weight:600;color:'+(up>=0?'var(--green)':'var(--red)')+'">'+(up>=0?'+':'')+'\u20b9'+inr(up)+'</td>'+
'<td style="color:var(--muted);font-size:12px">'+dur+'</td></tr>';
}
h+='</tbody></table></div>';
div.innerHTML=h;
}else{div.innerHTML='<div class="empty">No open positions</div>';}
}catch(e){console.error(e)}
}

async function loadBacktests(){
try{
const b=await api('/api/metric_failures');
const div=$('#bt-table');
if(b&&Object.keys(b).length>0){
let h='<div class="table-wrap"><table><thead><tr><th>Coin</th><th>Attempts</th><th>Sharpe Fail</th><th>Win Rate Fail</th><th>Drawdown Fail</th><th>Trades Fail</th></tr></thead><tbody>';
for(const[coin,data]of Object.entries(b)){
const f=data.failures||{};
h+='<tr><td><strong>'+coin+'</strong></td><td>'+data.total_attempts+'</td>'+
'<td>'+(f.sharpe?'<span class="pill pill-r">'+f.sharpe+'x</span>':'<span style="color:var(--muted)">0</span>')+'</td>'+
'<td>'+(f.win_rate?'<span class="pill pill-r">'+f.win_rate+'x</span>':'<span style="color:var(--muted)">0</span>')+'</td>'+
'<td>'+(f.max_drawdown?'<span class="pill pill-r">'+f.max_drawdown+'x</span>':'<span style="color:var(--muted)">0</span>')+'</td>'+
'<td>'+(f.trades_count?'<span class="pill pill-r">'+f.trades_count+'x</span>':'<span style="color:var(--muted)">0</span>')+'</td></tr>';
}
h+='</tbody></table></div>';
div.innerHTML=h;
}else{div.innerHTML='<div class="empty">No backtest failures recorded</div>';}
}catch(e){console.error(e)}
}

async function loadLogs(){
try{
const a=await api('/api/logs');
const lines=a.lines||[];
$('#log-count').textContent=lines.length+' lines';
const box=$('#log-box');
if(lines.length>0){
let h='<div class="logbox">';
for(const line of lines.slice(-120)){
const cl=esc(line);
let c='';
if(/FAIL|fail|Error|error|loss|LOSS/.test(cl))c='color:var(--red)';
else if(/PASS|pass|WIN/.test(cl))c='color:var(--green)';
else if(/LIVE|BUY|SELL|SL|TP|trade|TRADE/.test(cl))c='color:var(--orange)';
else if(/search|SEARCH|strategy|FALLBACK|STORE/.test(cl))c='color:var(--cyan)';
else if(/AGENT/.test(cl))c='color:var(--purple)';
h+='<div class="ln" style="'+c+'">'+cl+'</div>';
}
h+='</div>';
box.innerHTML=h;
const lb=box.querySelector('.logbox');
if(lb)lb.scrollTop=lb.scrollHeight;
}else{box.innerHTML='<div class="empty">No activity yet</div>';}
}catch(e){console.error(e)}
}

$('#hdr-time').textContent=new Date().toLocaleTimeString();
load();loadStrat();loadTrades();loadPositions();loadBacktests();loadLogs();
setInterval(()=>{
$('#hdr-time').textContent=new Date().toLocaleTimeString();
load();loadStrat();loadTrades();loadPositions();loadBacktests();loadLogs();
},8000);
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
                self._json(200, load_json("metric_failures.json") or {})
            elif self.path == "/api/positions":
                self._json(200, load_json("positions.json") or {})
            elif self.path == "/api/trades":
                log = load_json("performance_log.json")
                self._json(200, (log or {}).get("trades", []))
            elif self.path == "/api/logs":
                self._json(200, {"lines": log_capture.get_recent(80)})
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
