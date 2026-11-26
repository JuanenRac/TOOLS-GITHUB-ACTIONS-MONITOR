/* Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
   GPL-3.0-or-later - see LICENSE */
(function(){
  let at=0;
  const MARK={red:"✖",running:"▶",ok:"✔",unknown:"?"};
  function el(tag,text){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n}
  function state(s){const n=el("span",s?MARK[s]+" "+T("ui.fleet.state_"+s):"-");if(s)n.className="fleet-"+s;return n}
  async function draw(){
    if(Date.now()-at<30000)return;
    at=Date.now();
    let j;
    try{j=await (await fetch("/api/fleet/columns")).json()}catch(e){return}
    if(!j.ok)return;
    const body=FAM.panel("fleet","fleet-columns","ui.fleet.title");
    if(!body)return;
    body.textContent="";
    const groups=el("ul");
    j.groups.forEach(g=>{
      const li=el("li"),a=el("a",g.key);a.href="/g/"+encodeURIComponent(g.key);a.target="_blank";a.rel="noopener";
      li.append(a,document.createTextNode(" "),state(g.state),document.createTextNode(" "+T("ui.fleet.group_counts",{red:g.red,repos:g.repos})));groups.append(li);
    });
    body.append(groups);
    const wrap=el("div"),t=el("table"),head=el("tr");wrap.style.overflowX="auto";
    head.append(el("th",T("ui.fleet.col_repo")));j.roles.forEach(r=>head.append(el("th",r)));t.append(head);
    j.rows.forEach(r=>{const tr=el("tr");tr.append(el("td",r.repo));j.roles.forEach(role=>{const td=el("td");td.append(state(r.cells[role]));tr.append(td)});t.append(tr)});
    wrap.append(t);
    const fold=el("details");fold.append(el("summary",T("ui.fleet.by_role")),wrap);body.append(fold);
  }
  FAM.on("tab",tab=>{if(tab==="fleet"){at=0;draw()}});
  FAM.on("data",()=>{if(CURTAB==="fleet")draw()});
})();
