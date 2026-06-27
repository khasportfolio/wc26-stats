"""
HTML template strings for the WC26 dashboard pages.
Kept separate from logic to avoid 1000-line files.
"""


def r32_html(js_array, nav_html):
    """Return the full R32 dashboard HTML."""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>World Cup 2026 — Round of 32 Analytics</title>
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<style>
:root {{
    --wc-green:#3CAC3B;--wc-blue:#2A398D;--wc-red:#E61D25;
    --bg:#FAFAFA;--card-bg:#FFF;--card-border:#E2E4E2;
    --text-primary:#2D2D2D;--text-secondary:#5F6368;--text-muted:#8A8F94;
    --bar-bg:#ECEEED;--hover-shadow:rgba(42,57,141,.08);
}}
@media(prefers-color-scheme:dark){{:root{{
    --bg:#0F1318;--card-bg:#1A1F27;--card-border:#2D333B;
    --text-primary:#E6EDF3;--text-secondary:#A8B1BA;--text-muted:#6E7681;
    --bar-bg:#2D333B;--hover-shadow:rgba(88,166,255,.1);
}}}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text-primary);padding:24px;min-height:100vh}}
h1{{text-align:center;font-size:1.8rem;color:var(--wc-blue);margin-bottom:4px}}
.subtitle{{text-align:center;color:var(--text-secondary);font-size:.85rem;margin-bottom:8px}}
.nav{{text-align:center;margin-bottom:20px;font-size:.85rem}}
.nav-link{{color:var(--text-secondary);text-decoration:none;padding:4px 10px;border-radius:4px}}
.nav-link:hover{{background:var(--bar-bg)}}
.nav-link.active{{color:var(--wc-blue);font-weight:600;background:rgba(42,57,141,.08)}}
.controls{{display:flex;justify-content:center;gap:12px;margin-bottom:20px;flex-wrap:wrap;align-items:center}}
.controls select,.controls input{{padding:6px 12px;border-radius:6px;border:1px solid var(--card-border);background:var(--card-bg);color:var(--text-primary);font-size:.8rem}}
.controls input{{width:180px}}
.controls label{{font-size:.8rem;color:var(--text-secondary)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px;max-width:1600px;margin:0 auto}}
.card{{background:var(--card-bg);border:1px solid var(--card-border);border-radius:10px;padding:16px;transition:all .2s;border-top:3px solid var(--wc-green)}}
.card:hover{{border-color:var(--wc-blue);transform:translateY(-1px);box-shadow:0 4px 12px var(--hover-shadow)}}
.card-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}}
.team-name{{font-weight:600;font-size:.95rem}}
.rank-badge{{font-size:.7rem;font-weight:700;padding:2px 8px;border-radius:10px;background:rgba(42,57,141,.08);color:var(--wc-blue)}}
.radar-wrap{{display:flex;justify-content:center;margin:8px 0}}
canvas.radar{{width:180px;height:180px}}
.dim-bars{{margin-top:8px}}
.dim-row{{display:flex;align-items:center;margin-bottom:4px;font-size:.7rem}}
.dim-label{{width:75px;color:var(--text-secondary);font-weight:500}}
.dim-bar-bg{{flex:1;height:7px;background:var(--bar-bg);border-radius:4px;overflow:hidden}}
.dim-bar{{height:100%;border-radius:4px;transition:width .4s ease}}
.dim-val{{width:32px;text-align:right;color:var(--text-muted);font-size:.65rem}}
.con-dot{{width:7px;height:7px;border-radius:50%;margin-left:4px;display:inline-block;flex-shrink:0}}
.con-high{{background:var(--wc-green)}}.con-med{{background:#E6A817}}.con-low{{background:var(--wc-red)}}.con-na{{background:#D1D4D1}}
.consistency-row{{display:flex;align-items:center;justify-content:space-between;margin-top:8px;padding-top:6px;border-top:1px solid var(--card-border);font-size:.68rem}}
.con-label{{color:var(--text-muted)}}
.con-badge{{padding:2px 7px;border-radius:8px;font-weight:600;font-size:.65rem}}
.con-badge-high{{background:rgba(60,172,59,.1);color:#2D8A2C}}
.con-badge-med{{background:rgba(230,168,23,.1);color:#B8860B}}
.con-badge-low{{background:rgba(230,29,37,.1);color:#C41920}}
.con-badge-na{{background:rgba(209,212,209,.3);color:var(--text-muted)}}
.bar-finishing{{background:linear-gradient(90deg,#E61D25,#C41920)}}
.bar-creation{{background:linear-gradient(90deg,#2A398D,#1E2A6B)}}
.bar-control{{background:linear-gradient(90deg,#3CAC3B,#2D8A2C)}}
.bar-defense{{background:linear-gradient(90deg,#5B7EC2,#3A5CA0)}}
.bar-physicality{{background:linear-gradient(90deg,#E67E22,#D35400)}}
.bar-pressing{{background:linear-gradient(90deg,#8E44AD,#6C3483)}}
.meta-row{{display:flex;justify-content:space-between;font-size:.63rem;color:var(--text-muted);margin-top:6px;border-top:1px solid var(--card-border);padding-top:6px}}
.legend{{display:flex;justify-content:center;gap:16px;margin-bottom:16px;flex-wrap:wrap}}
.legend-item{{display:flex;align-items:center;gap:5px;font-size:.72rem;color:var(--text-secondary)}}
.legend-dot{{width:10px;height:10px;border-radius:2px}}
.dot-fin{{background:#E61D25}}.dot-cre{{background:#2A398D}}.dot-ctrl{{background:#3CAC3B}}
.dot-def{{background:#5B7EC2}}.dot-phy{{background:#E67E22}}.dot-press{{background:#8E44AD}}
@media(prefers-color-scheme:dark){{
    h1{{color:#79B8FF}}.nav-link.active{{color:#79B8FF;background:rgba(88,166,255,.12)}}
    .rank-badge{{background:rgba(88,166,255,.12);color:#79B8FF}}
    .con-badge-high{{background:rgba(60,172,59,.15);color:#56D364}}
    .con-badge-med{{background:rgba(230,168,23,.15);color:#E6A817}}
    .con-badge-low{{background:rgba(230,29,37,.15);color:#F87171}}
    .con-na{{background:#3D444D}}
    .bar-creation{{background:linear-gradient(90deg,#5B7EC2,#3A5CA0)}}
}}
</style>
</head>
<body>
<h1>⚽ World Cup 2026 — Round of 32</h1>
<p class="subtitle">6 dimensions · Normalized against qualified knockout teams only</p>
<div class="nav">{nav_html}</div>
<div class="legend">
<div class="legend-item"><div class="legend-dot dot-fin"></div>Finishing</div>
<div class="legend-item"><div class="legend-dot dot-cre"></div>Creation</div>
<div class="legend-item"><div class="legend-dot dot-ctrl"></div>Control</div>
<div class="legend-item"><div class="legend-dot dot-def"></div>Defense</div>
<div class="legend-item"><div class="legend-dot dot-phy"></div>Physicality</div>
<div class="legend-item"><div class="legend-dot dot-press"></div>Pressing</div>
</div>
<div class="controls">
<label>Sort:</label>
<select id="sortBy" onchange="render()">
<option value="overall">Overall</option><option value="finishing">Finishing</option>
<option value="creation">Creation</option><option value="control">Control</option>
<option value="defense">Defense</option><option value="physicality">Physicality</option>
<option value="pressing">Pressing</option><option value="consistency">Consistency</option>
<option value="name">Name</option>
</select>
<label>Filter:</label>
<input type="text" id="filter" placeholder="Type team name..." oninput="render()">
</div>
<div class="grid" id="grid"></div>
<script>
const teams=[{js_array}];
''' + '''
const DIMS=["finishing","creation","control","defense","physicality","pressing"];
const COLORS=["#E61D25","#2A398D","#3CAC3B","#5B7EC2","#E67E22","#8E44AD"];
const BAR_CLASSES=["bar-finishing","bar-creation","bar-control","bar-defense","bar-physicality","bar-pressing"];
const DIM_LABELS=["Finishing","Creation","Control","Defense","Physical","Pressing"];
function getGridColor(){return window.matchMedia("(prefers-color-scheme:dark)").matches?"rgba(100,110,120,.5)":"rgba(209,212,209,.7)"}
function getAxisColor(){return window.matchMedia("(prefers-color-scheme:dark)").matches?"rgba(100,110,120,.35)":"rgba(209,212,209,.5)"}
function getLabelColor(){return window.matchMedia("(prefers-color-scheme:dark)").matches?"#A8B1BA":"#5F6368"}
function drawRadar(canvas,team){
const ctx=canvas.getContext("2d"),w=canvas.width,h=canvas.height,cx=w/2,cy=h/2,r=Math.min(w,h)/2-20;
ctx.clearRect(0,0,w,h);
for(let ring=.25;ring<=1;ring+=.25){ctx.beginPath();for(let i=0;i<=6;i++){const a=(Math.PI*2/6)*i-Math.PI/2,x=cx+Math.cos(a)*r*ring,y=cy+Math.sin(a)*r*ring;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y)}ctx.closePath();ctx.strokeStyle=getGridColor();ctx.lineWidth=.5;ctx.stroke()}
for(let i=0;i<6;i++){const a=(Math.PI*2/6)*i-Math.PI/2;ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(cx+Math.cos(a)*r,cy+Math.sin(a)*r);ctx.strokeStyle=getAxisColor();ctx.lineWidth=.5;ctx.stroke()}
ctx.beginPath();for(let i=0;i<6;i++){const a=(Math.PI*2/6)*i-Math.PI/2,v=team[DIMS[i]]/100,x=cx+Math.cos(a)*r*v,y=cy+Math.sin(a)*r*v;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y)}ctx.closePath();ctx.fillStyle=COLORS[0]+"22";ctx.fill();ctx.strokeStyle=COLORS[0];ctx.lineWidth=1.5;ctx.stroke();
for(let i=0;i<6;i++){const a=(Math.PI*2/6)*i-Math.PI/2,v=team[DIMS[i]]/100,x=cx+Math.cos(a)*r*v,y=cy+Math.sin(a)*r*v;ctx.beginPath();ctx.arc(x,y,3,0,Math.PI*2);ctx.fillStyle=COLORS[i];ctx.fill();const lx=cx+Math.cos(a)*(r+14),ly=cy+Math.sin(a)*(r+14);ctx.font="9px system-ui";ctx.fillStyle=getLabelColor();ctx.textAlign="center";ctx.textBaseline="middle";ctx.fillText(DIM_LABELS[i],lx,ly)}
}
function createCard(team,rank){
const card=document.createElement("div");card.className="card";
const conKeys=["finCon","creCon","ctrlCon","defCon","phyCon","prsCon"];
let bars="";for(let i=0;i<6;i++){const v=team[DIMS[i]],c=team[conKeys[i]];let dc="con-na";if(c!==null){dc=c>=70?"con-high":c>=40?"con-med":"con-low"}bars+=`<div class="dim-row"><span class="dim-label">${DIM_LABELS[i]}</span><div class="dim-bar-bg"><div class="dim-bar ${BAR_CLASSES[i]}" style="width:${v}%"></div></div><span class="dim-val">${v}</span><span class="con-dot ${dc}"></span></div>`}
const con=team.consistency;let cb="";
if(con!==null){let cls="con-badge-med",lbl="Mixed";if(con>=70){cls="con-badge-high";lbl="Stable"}else if(con<40){cls="con-badge-low";lbl="Volatile"}cb=`<div class="consistency-row"><span class="con-label">Consistency</span><span class="con-badge ${cls}">${lbl} (${con}%)</span></div>`}else{cb=`<div class="consistency-row"><span class="con-label">Consistency</span><span class="con-badge con-badge-na">1 match</span></div>`}
card.innerHTML=`<div class="card-header"><span class="team-name">#${rank} ${team.name}</span><span class="rank-badge">${team.overall}</span></div><div class="radar-wrap"><canvas class="radar" width="180" height="180"></canvas></div><div class="dim-bars">${bars}</div>${cb}<div class="meta-row"><span>${team.avgGoals}g · ${team.avgXG}xG · ${team.avgXA}xA</span><span>${team.avgPoss}% poss · ${team.avgPassAcc}% pass</span><span>${team.avgXGC}xGC · PPDA ${team.avgPPDA}</span></div>`;
return card}
function render(){
const sortBy=document.getElementById("sortBy").value,filter=document.getElementById("filter").value.toLowerCase();
let f=teams.filter(t=>t.name.toLowerCase().includes(filter));
if(sortBy==="name")f.sort((a,b)=>a.name.localeCompare(b.name));else if(sortBy==="consistency")f.sort((a,b)=>(b.consistency??-1)-(a.consistency??-1));else f.sort((a,b)=>b[sortBy]-a[sortBy]);
const grid=document.getElementById("grid");grid.innerHTML="";
f.forEach((t,i)=>{const card=createCard(t,i+1);grid.appendChild(card);drawRadar(card.querySelector("canvas"),t)})}
render();window.matchMedia("(prefers-color-scheme:dark)").addEventListener("change",()=>render());
</script>
</body></html>'''


def trends_html(js_data, nav_html):
    """Return the full trends page HTML."""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>World Cup 2026 — Team Trends</title>
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<style>
:root {{
    --wc-green:#3CAC3B;--wc-blue:#2A398D;--wc-red:#E61D25;
    --bg:#FAFAFA;--card-bg:#FFF;--card-border:#E2E4E2;
    --text-primary:#2D2D2D;--text-secondary:#5F6368;--text-muted:#8A8F94;
    --bar-bg:#ECEEED;--hover-shadow:rgba(42,57,141,.08);
}}
@media(prefers-color-scheme:dark){{:root{{
    --bg:#0F1318;--card-bg:#1A1F27;--card-border:#2D333B;
    --text-primary:#E6EDF3;--text-secondary:#A8B1BA;--text-muted:#6E7681;
    --bar-bg:#2D333B;--hover-shadow:rgba(88,166,255,.1);
}}}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text-primary);padding:24px;min-height:100vh}}
h1{{text-align:center;font-size:1.8rem;color:var(--wc-blue);margin-bottom:4px}}
.subtitle{{text-align:center;color:var(--text-secondary);font-size:.85rem;margin-bottom:8px}}
.nav{{text-align:center;margin-bottom:20px;font-size:.85rem}}
.nav-link{{color:var(--text-secondary);text-decoration:none;padding:4px 10px;border-radius:4px}}
.nav-link:hover{{background:var(--bar-bg)}}
.nav-link.active{{color:var(--wc-blue);font-weight:600;background:rgba(42,57,141,.08)}}
.controls{{display:flex;justify-content:center;gap:12px;margin-bottom:20px;flex-wrap:wrap;align-items:center}}
.controls select,.controls input{{padding:6px 12px;border-radius:6px;border:1px solid var(--card-border);background:var(--card-bg);color:var(--text-primary);font-size:.8rem}}
.controls input{{width:180px}}
.controls label{{font-size:.8rem;color:var(--text-secondary)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(440px,1fr));gap:16px;max-width:1600px;margin:0 auto}}
.card{{background:var(--card-bg);border:1px solid var(--card-border);border-radius:10px;padding:18px;transition:all .2s;border-top:3px solid var(--wc-green)}}
.card:hover{{border-color:var(--wc-blue);box-shadow:0 4px 12px var(--hover-shadow)}}
.card-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}}
.team-name{{font-weight:600;font-size:1rem}}
.match-count{{font-size:.7rem;color:var(--text-muted)}}
canvas.trend-chart{{width:100%;height:160px;display:block}}
.legend{{display:flex;justify-content:center;gap:16px;margin-bottom:16px;flex-wrap:wrap}}
.legend-item{{display:flex;align-items:center;gap:5px;font-size:.72rem;color:var(--text-secondary)}}
.legend-dot{{width:10px;height:10px;border-radius:2px}}
.dot-fin{{background:#E61D25}}.dot-cre{{background:#2A398D}}.dot-ctrl{{background:#3CAC3B}}
.dot-def{{background:#5B7EC2}}.dot-phy{{background:#E67E22}}.dot-press{{background:#8E44AD}}
@media(prefers-color-scheme:dark){{h1{{color:#79B8FF}}.nav-link.active{{color:#79B8FF;background:rgba(88,166,255,.12)}}}}
</style>
</head>
<body>
<h1>⚽ World Cup 2026 — Team Trends</h1>
<p class="subtitle">Per-match dimension scores · Normalized across all R32 team performances</p>
<div class="nav">{nav_html}</div>
<div class="legend">
<div class="legend-item"><div class="legend-dot dot-fin"></div>Finishing</div>
<div class="legend-item"><div class="legend-dot dot-cre"></div>Creation</div>
<div class="legend-item"><div class="legend-dot dot-ctrl"></div>Control</div>
<div class="legend-item"><div class="legend-dot dot-def"></div>Defense</div>
<div class="legend-item"><div class="legend-dot dot-phy"></div>Physicality</div>
<div class="legend-item"><div class="legend-dot dot-press"></div>Pressing</div>
</div>
<div class="controls">
<label>Filter:</label>
<input type="text" id="filter" placeholder="Type team name..." oninput="render()">
<label>Highlight:</label>
<select id="highlight" onchange="render()">
<option value="all">All Dimensions</option>
<option value="finishing">Finishing</option><option value="creation">Creation</option>
<option value="control">Control</option><option value="defense">Defense</option>
<option value="physicality">Physicality</option><option value="pressing">Pressing</option>
</select>
</div>
<div class="grid" id="grid"></div>
<script>
const trendsData={js_data};
''' + '''
const DIMS=["finishing","creation","control","defense","physicality","pressing"];
const COLORS=["#E61D25","#2A398D","#3CAC3B","#5B7EC2","#E67E22","#8E44AD"];
const DIM_LABELS=["Finishing","Creation","Control","Defense","Physical","Pressing"];
function drawTrendChart(canvas,trend,highlight){
const ctx=canvas.getContext("2d"),w=canvas.width,h=canvas.height;
const pad={top:10,bottom:32,left:5,right:5},cW=w-pad.left-pad.right,cH=h-pad.top-pad.bottom;
ctx.clearRect(0,0,w,h);if(!trend.length)return;
const isDark=window.matchMedia("(prefers-color-scheme:dark)").matches;
ctx.strokeStyle=isDark?"rgba(100,110,120,.3)":"rgba(209,212,209,.5)";ctx.lineWidth=.5;
for(let p=0;p<=100;p+=25){const y=pad.top+cH*(1-p/100);ctx.beginPath();ctx.moveTo(pad.left,y);ctx.lineTo(w-pad.right,y);ctx.stroke()}
const n=trend.length,xStep=n>1?cW/(n-1):cW/2;
DIMS.forEach((dim,di)=>{
const on=highlight==="all"||highlight===dim;
ctx.globalAlpha=on?1:.15;ctx.strokeStyle=COLORS[di];ctx.lineWidth=on?2.5:1;
ctx.beginPath();trend.forEach((pt,pi)=>{const x=pad.left+(n>1?pi*xStep:cW/2),y=pad.top+cH*(1-pt[dim]/100);pi===0?ctx.moveTo(x,y):ctx.lineTo(x,y)});ctx.stroke();
if(on){trend.forEach((pt,pi)=>{const x=pad.left+(n>1?pi*xStep:cW/2),y=pad.top+cH*(1-pt[dim]/100);ctx.beginPath();ctx.arc(x,y,3,0,Math.PI*2);ctx.fillStyle=COLORS[di];ctx.fill()})}
});ctx.globalAlpha=1;
ctx.font="9px system-ui";ctx.fillStyle=isDark?"#6E7681":"#8A8F94";ctx.textAlign="center";
trend.forEach((pt,pi)=>{const x=pad.left+(n>1?pi*xStep:cW/2);
const opp=shortName(pt.opponent||"");
ctx.fillText(`vs ${opp}`,x,h-5);
ctx.fillText(`${pt.goals}-${pt.conceded}`,x,h-16)})}
const SHORT_NAMES={"Bosnia and Herzegovina":"Bosnia","Czech Republic":"Czechia","South Africa":"S. Africa","South Korea":"S. Korea","New Zealand":"N. Zealand","Saudi Arabia":"S. Arabia","Ivory Coast":"Iv. Coast","Cape Verde":"C. Verde","United States":"USA"};
function shortName(n){return SHORT_NAMES[n]||n.substring(0,12)}}
function createCard(name,trend){
const card=document.createElement("div");card.className="card";
card.innerHTML=`<div class="card-header"><span class="team-name">${name}</span><span class="match-count">${trend.length} matches</span></div><canvas class="trend-chart" width="420" height="160"></canvas>`;
return card}
function render(){
const filter=document.getElementById("filter").value.toLowerCase();
const highlight=document.getElementById("highlight").value;
const grid=document.getElementById("grid");grid.innerHTML="";
Object.keys(trendsData).sort().filter(n=>n.toLowerCase().includes(filter)).forEach(name=>{
const card=createCard(name,trendsData[name]);grid.appendChild(card);
drawTrendChart(card.querySelector("canvas"),trendsData[name],highlight)})}
render();window.matchMedia("(prefers-color-scheme:dark)").addEventListener("change",()=>render());
</script>
</body></html>'''
