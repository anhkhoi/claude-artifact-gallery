"""HTML template and rendering of the gallery page."""
import json
from pathlib import Path
from typing import List, Optional

from .model import Item

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Claude Artifact Gallery</title>
<style>
:root{--bg:#fff;--panel:#f6f7f9;--fg:#1c2128;--mute:#667085;--line:#e1e4e8;--acc:#2563eb;--sel:#e8f0fe;--cv:#eeeeec;--k-archify:#6d28d9;--k-registry:#c2410c;--k-canvas:#0f766e;--k-pulled:#1d4ed8}
@media(prefers-color-scheme:dark){:root{--bg:#0e1116;--panel:#151a21;--fg:#e6edf3;--mute:#8b96a5;--line:#262d37;--acc:#6ea8ff;--sel:#1b2a44;--cv:#1a1f27;--k-archify:#b794f6;--k-registry:#fb923c;--k-canvas:#2dd4bf;--k-pulled:#60a5fa}}
*{box-sizing:border-box}html,body{height:100%;margin:0}
body{display:flex;background:var(--bg);color:var(--fg);font:14px/1.4 system-ui,sans-serif}
aside{width:340px;min-width:260px;display:flex;flex-direction:column;background:var(--panel);border-right:1px solid var(--line)}
header{padding:12px;border-bottom:1px solid var(--line)}
h1{font-size:15px;margin:0 0 8px}
input,select{width:100%;padding:7px 9px;margin-bottom:6px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);font:inherit}
#list{overflow:auto;flex:1}
.grp{padding:8px 12px 4px;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--mute);position:sticky;top:0;background:var(--panel)}
.it{display:block;padding:8px 12px;border-left:3px solid transparent;color:inherit;cursor:pointer}
.it:hover,.it.on{background:var(--sel)}.it.on{border-left-color:var(--acc)}
.t{font-weight:600}.m{color:var(--mute);font-size:12px;display:flex;gap:8px;flex-wrap:wrap}
.tag{border:1px solid var(--line);border-radius:10px;padding:0 6px}
.tag.k-archify{--k:var(--k-archify)}.tag.k-registry{--k:var(--k-registry)}.tag.k-canvas{--k:var(--k-canvas)}.tag.k-pulled{--k:var(--k-pulled)}
.tag[class*="k-"]{color:var(--k);border-color:var(--k);background:color-mix(in srgb,var(--k) 12%,transparent)}
main{flex:1;display:flex;flex-direction:column;min-width:0}
.bar{display:flex;gap:12px;align-items:center;padding:8px 12px;border-bottom:1px solid var(--line);color:var(--mute);font-size:12px}
.bar a{color:var(--acc)}
#view{flex:1;overflow:auto;display:flex;flex-direction:column}
iframe{border:0;background:#fff}
#view>iframe{flex:1;width:100%}
.tb{display:flex;gap:6px;align-items:center;padding:6px 12px;border-bottom:1px solid var(--line);color:var(--mute);font-size:12px}
.tb button{padding:3px 10px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);font:inherit;cursor:pointer}
.tb button:hover{border-color:var(--acc);color:var(--acc)}
#view.cv{overflow:hidden}
.stage{flex:1;overflow:auto;background:var(--cv)}
#sizer{position:relative}
#world{position:absolute;left:0;top:0;transform-origin:0 0}
.bd{position:absolute;background:#fff;box-shadow:0 2px 28px rgba(0,0,0,.14)}
.bd iframe{display:block;border:0}
.sh{position:absolute;inset:0;cursor:grab}
.stage.pan,.stage.pan .sh{cursor:grabbing}
.bd.on{outline:8px solid var(--acc)}.bd.on .sh{display:none}
.tb .hint{margin-left:auto}
.bl{position:absolute;left:0;bottom:100%;margin-bottom:14px;font-size:30px;color:var(--mute);white-space:nowrap}
.nt{position:absolute;white-space:pre-wrap}
.nt.t1{font-size:112px;font-weight:600;line-height:1.1;color:var(--fg)}
.nt.st{box-sizing:border-box;padding:32px;border-radius:20px;font-size:28px;line-height:1.45;color:#1c2128;background:#fef3c7}
.nt.st.f-orange{background:#fed7aa}.nt.st.f-blue{background:#bfdbfe}.nt.st.f-green{background:#bbf7d0}.nt.st.f-pink{background:#fbcfe8}.nt.st.f-purple{background:#e9d5ff}
.card{margin:auto;max-width:520px;padding:24px;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
.card a{display:inline-block;margin-top:12px;color:var(--acc)}
.root{display:block;max-width:100%;margin:-4px 0 8px;padding:0;border:0;background:none;color:var(--mute);font:inherit;font-size:12px;text-align:left;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.root:hover{color:var(--acc)}
.empty{margin:auto;color:var(--mute)}
@media(max-width:700px){body{flex-direction:column}aside{width:100%;height:40%;border-right:0}}
</style></head><body>
<aside><header><h1>Claude Artifact Gallery <span style="color:var(--mute);font-weight:400" id="n"></span></h1>
<button class="root" id="root" type="button"></button>
<input id="q" placeholder="Search title, purpose, group…" autofocus>
<select id="kd"><option value="">All kinds</option></select>
<select id="gr"><option value="">All groups</option></select>
</header><div id="list"></div></aside>
<main><div class="bar" id="bar"></div><div id="view"></div></main>
<script>
const ROOT=__ROOT__;
const ITEMS=__DATA__;
const $=s=>document.querySelector(s);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const key=i=>i.key;
const gl=g=>g==="."?ROOT.name:g;
const copy=async t=>{try{await navigator.clipboard.writeText(t)}catch(e){const a=document.createElement("textarea");a.value=t;document.body.appendChild(a);a.select();document.execCommand("copy");a.remove()}};
const rootLabel=()=>{$("#root").textContent=ROOT.name+" ⧉"};
rootLabel();$("#root").title="Copy path: "+ROOT.path;
if(!ROOT.path)$("#root").hidden=true;
$("#root").onclick=async()=>{await copy(ROOT.path);$("#root").textContent="Copied ✓";setTimeout(rootLabel,1200)};
document.title=ROOT.name+" · Claude Artifact Gallery";
const hash=()=>{try{return decodeURIComponent(location.hash.slice(1))}catch(e){return ""}};
const uniq=f=>[...new Set(ITEMS.map(f))].sort();
for(const [id,f] of [["kd",i=>i.kind],["gr",i=>i.group]])
  $("#"+id).innerHTML+=uniq(f).map(v=>`<option value="${esc(v)}">${esc(id==="gr"?gl(v):v)}</option>`).join("");
function render(){
  const q=$("#q").value.toLowerCase(),kd=$("#kd").value,gr=$("#gr").value,sel=hash();
  const hit=ITEMS.filter(i=>(!kd||i.kind===kd)&&(!gr||i.group===gr)&&
    [i.title,i.purpose,i.group,i.tags.join(" ")].join(" ").toLowerCase().includes(q));
  $("#n").textContent=`(${hit.length}/${ITEMS.length})`;
  const groups=new Map();
  for(const i of hit){if(!groups.has(i.group))groups.set(i.group,[]);groups.get(i.group).push(i)}
  let h="";
  for(const [g,list] of groups){
    h+=`<div class="grp">${esc(gl(g)||"(none)")}</div>`;
    for(const i of list)h+=`<a class="it${sel===key(i)?" on":""}" data-k="${esc(key(i))}">
      <div class="t">${esc(i.title)}</div>
      <div class="m"><span class="tag k-${esc(i.kind)}">${esc(i.kind)}</span>${i.tags.map(t=>`<span class="tag">${esc(t)}</span>`).join("")}<span>${esc(i.date)}</span>${i.meta.check?`<span>${esc(i.meta.check)}</span>`:""}</div></a>`;
  }
  $("#list").innerHTML=h||'<p class="empty">No artifacts</p>';
}
const Z={mode:"fit",s:1,cur:1,W:1,H:1};
function canvasHtml(i){
  const PAD=120,LAB=64,nw=n=>n.w||(n.kind==="title1"?1600:600);
  const box=[...i.boards.map(b=>[b.x,b.y-LAB,b.x+b.w,b.y+b.h]),
    ...i.notes.map(n=>[n.x,n.y,n.x+nw(n),n.y+(n.kind==="title1"?150:Math.max(160,n.text.split("\n").length*44+80))])];
  const x0=Math.min(...box.map(b=>b[0])),y0=Math.min(...box.map(b=>b[1]));
  Z.W=Math.max(...box.map(b=>b[2]))-x0+2*PAD;Z.H=Math.max(...box.map(b=>b[3]))-y0+2*PAD;
  const at=(x,y)=>`left:${x-x0+PAD}px;top:${y-y0+PAD}px`;
  const bd=i.boards.map(b=>`<div class="bd" style="${at(b.x,b.y)};width:${b.w}px;height:${b.h}px"><div class="bl">${esc(b.title)}</div><iframe src="${esc(b.href)}" width="${b.w}" height="${b.h}" title="${esc(b.title)}"></iframe><div class="sh" title="Double-click to interact"></div></div>`).join("");
  const nt=i.notes.map(n=>`<div class="nt ${n.kind==="title1"?"t1":"st f-"+esc(n.fill)}" style="${at(n.x,n.y)};width:${nw(n)}px">${esc(n.text)}</div>`).join("");
  return `<div class="tb"><button data-z="fit">Fit</button><button data-z="1">100%</button><button data-z="out">−</button><button data-z="in">+</button><span id="zl"></span><span class="hint">Drag to pan · Ctrl/⌘ + scroll to zoom · 0 to fit · double-click a board to interact</span></div><div class="stage" id="stage"><div id="sizer"><div id="world" style="width:${Z.W}px;height:${Z.H}px">${bd}${nt}</div></div></div>`;
}
function fit(){
  const st=$("#stage");if(!st)return;
  const s=Z.mode==="fit"?Math.max(.02,Math.min(1,st.clientWidth/Z.W)):Z.s;Z.cur=s;
  $("#world").style.transform=`scale(${s})`;
  $("#sizer").style.width=Z.W*s+"px";$("#sizer").style.height=Z.H*s+"px";
  $("#zl").textContent=Math.round(s*100)+"%";
}
function show(){
  const i=ITEMS.find(x=>key(x)===hash());
  if(!i){$("#view").innerHTML="";$("#bar").textContent="";return}
  document.title=i.title+" · Claude Artifact Gallery";
  let bar=`<b>${esc(i.title)}</b><span>${esc(i.date)}</span>`;
  if(i.url)bar+=`<a href="${esc(i.url)}" target="_blank" rel="noopener">open on claude.ai ↗</a>`;
  if(i.href)bar+=`<a href="${esc(i.href)}" target="_blank">open in new tab ↗</a>`;
  $("#bar").innerHTML=bar;
  let v="";
  if(i.boards.length||i.notes.length)v=canvasHtml(i);
  else if(i.href)v=`<iframe src="${esc(i.href)}" title="${esc(i.title)}"></iframe>`;
  else v=`<div class="card"><b>${esc(i.title)}</b><p>${esc(i.purpose)}</p><p style="color:var(--mute)">${i.url?"This page lives on claude.ai and is private to its owner, so it cannot be embedded here.":"This canvas has no boards to show."}</p>${i.url?`<a href="${esc(i.url)}" target="_blank" rel="noopener">Open on claude.ai ↗</a>`:""}</div>`;
  Z.mode="fit";$("#view").className=i.boards.length||i.notes.length?"cv":"";
  $("#view").innerHTML=v;fit();
  if(RO&&$("#stage"))RO.observe($("#stage"));
}
$("#list").onclick=e=>{const a=e.target.closest(".it");if(a)location.hash=encodeURIComponent(a.dataset.k)};
addEventListener("hashchange",()=>{show();render()});
addEventListener("resize",fit);
const RO=typeof ResizeObserver!=="undefined"?new ResizeObserver(fit):null;
if(RO)RO.observe($("#view"));
$("#view").onclick=e=>{const b=e.target.closest("[data-z]");if(!b)return;const z=b.dataset.z;
  if(z==="fit")Z.mode="fit";else{Z.mode="z";Z.s=z==="1"?1:Math.min(4,Math.max(.02,Z.cur*(z==="in"?1.25:.8)))}
  fit()};
const stg=()=>$("#stage");
const clearOn=()=>document.querySelectorAll(".bd.on").forEach(b=>b.classList.remove("on"));
let drag=null;
$("#view").addEventListener("mousedown",e=>{
  if(e.button!==0||e.target.closest(".bd.on"))return;
  clearOn();
  const st=e.target.closest("#stage");if(!st)return;
  e.preventDefault();
  drag={x:e.clientX,y:e.clientY,l:st.scrollLeft,t:st.scrollTop,st};
  st.classList.add("pan");
});
document.addEventListener("mousemove",e=>{if(!drag)return;drag.st.scrollLeft=drag.l-(e.clientX-drag.x);drag.st.scrollTop=drag.t-(e.clientY-drag.y)});
document.addEventListener("mouseup",()=>{if(drag)drag.st.classList.remove("pan");drag=null});
$("#view").addEventListener("dblclick",e=>{const sh=e.target.closest(".sh");if(sh)sh.parentElement.classList.add("on")});
$("#view").addEventListener("wheel",e=>{
  if(!(e.ctrlKey||e.metaKey))return;
  const st=stg();if(!st)return;
  e.preventDefault();
  const r=st.getBoundingClientRect(),cx=e.clientX-r.left,cy=e.clientY-r.top;
  const wx=(st.scrollLeft+cx)/Z.cur,wy=(st.scrollTop+cy)/Z.cur;
  Z.mode="z";Z.s=Math.min(4,Math.max(.02,Z.cur*Math.exp(-e.deltaY*.01)));fit();
  st.scrollLeft=wx*Z.cur-cx;st.scrollTop=wy*Z.cur-cy;
},{passive:false});
document.addEventListener("keydown",e=>{
  if(/^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName||""))return;
  if(e.key==="Escape")clearOn();
  if(e.key==="0"&&!e.ctrlKey&&!e.metaKey&&stg()){Z.mode="fit";fit()}
});
for(const id of ["q","kd","gr"])$("#"+id).oninput=render;
render();
if(location.hash)show();else if(ITEMS.length)location.hash=encodeURIComponent(key(ITEMS[0]));
</script></body></html>
"""


def _js(value) -> str:
    # escape "<" so "</script>" or "<!--" in titles cannot end or confuse the script block
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def render(items: List[Item], root: Optional[Path] = None) -> str:
    info = {"name": root.name or str(root), "path": str(root)} if root else {"name": "", "path": ""}
    return PAGE.replace("__ROOT__", _js(info)).replace("__DATA__", _js([i.to_dict() for i in items]))
