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
:root{--bg:#fff;--panel:#f6f7f9;--fg:#1c2128;--mute:#667085;--line:#e1e4e8;--acc:#2563eb;--sel:#e8f0fe;--k-archify:#6d28d9;--k-registry:#c2410c;--k-canvas:#0f766e}
@media(prefers-color-scheme:dark){:root{--bg:#0e1116;--panel:#151a21;--fg:#e6edf3;--mute:#8b96a5;--line:#262d37;--acc:#6ea8ff;--sel:#1b2a44;--k-archify:#b794f6;--k-registry:#fb923c;--k-canvas:#2dd4bf}}
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
.tag.k-archify{--k:var(--k-archify)}.tag.k-registry{--k:var(--k-registry)}.tag.k-canvas{--k:var(--k-canvas)}
.tag[class*="k-"]{color:var(--k);border-color:var(--k);background:color-mix(in srgb,var(--k) 12%,transparent)}
main{flex:1;display:flex;flex-direction:column;min-width:0}
.bar{display:flex;gap:12px;align-items:center;padding:8px 12px;border-bottom:1px solid var(--line);color:var(--mute);font-size:12px}
.bar a{color:var(--acc)}
#view{flex:1;overflow:auto;display:flex;flex-direction:column}
iframe{border:0;background:#fff}
#view>iframe{flex:1;width:100%}
.board{padding:12px}.board h3{margin:0 0 6px;font-size:13px}
.wrap{overflow:hidden;border:1px solid var(--line);border-radius:6px}
.wrap iframe{transform-origin:0 0}
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
function fit(){
  for(const w of document.querySelectorAll(".wrap")){
    const f=w.firstElementChild,s=Math.min(1,w.clientWidth/f.width);
    f.style.transform=`scale(${s})`;w.style.height=f.height*s+"px";
  }
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
  if(i.boards.length)v=i.boards.map(b=>`<div class="board"><h3>${esc(b.title)}</h3><div class="wrap"><iframe src="${esc(b.href)}" width="${b.w}" height="${b.h}" title="${esc(b.title)}"></iframe></div></div>`).join("");
  else if(i.href)v=`<iframe src="${esc(i.href)}" title="${esc(i.title)}"></iframe>`;
  else v=`<div class="card"><b>${esc(i.title)}</b><p>${esc(i.purpose)}</p><p style="color:var(--mute)">${i.url?"This page lives on claude.ai and is private to its owner, so it cannot be embedded here.":"This canvas has no boards to show."}</p>${i.url?`<a href="${esc(i.url)}" target="_blank" rel="noopener">Open on claude.ai ↗</a>`:""}</div>`;
  $("#view").innerHTML=v;fit();
}
$("#list").onclick=e=>{const a=e.target.closest(".it");if(a)location.hash=encodeURIComponent(a.dataset.k)};
addEventListener("hashchange",()=>{show();render()});
addEventListener("resize",fit);
if(typeof ResizeObserver!=="undefined")new ResizeObserver(fit).observe($("#view"));
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
