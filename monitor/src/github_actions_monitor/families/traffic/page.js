/* Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
   GPL-3.0-or-later - see LICENSE */
(function(){
  let at=0,drawn="";
  function el(tag,text){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n}
  function table(head,rows){
    const t=el("table"),h=el("tr");
    head.forEach(x=>h.append(el("th",x)));t.append(h);
    rows.forEach(r=>{const tr=el("tr");r.forEach(x=>tr.append(el("td",x)));t.append(tr)});
    return t;
  }
  const shown=v=>v===null||v===undefined?"–":String(v);      // a day that was not read is a dash, never a zero
  function bars(days,field,label){
    const NS="http://www.w3.org/2000/svg",last=days.slice(-30),top=Math.max(1,...last.map(d=>d[field]||0));
    const box=el("figure"),svg=document.createElementNS(NS,"svg");
    box.className="traffic-chart";box.append(el("figcaption",label));
    svg.setAttribute("viewBox","0 0 300 40");svg.setAttribute("preserveAspectRatio","none");svg.setAttribute("role","img");svg.setAttribute("aria-label",label);
    last.forEach((d,i)=>{
      if(d[field]===null||d[field]===undefined)return;
      const r=document.createElementNS(NS,"rect"),h=Math.max(1,38*d[field]/top);
      r.setAttribute("x",String(i*10+1));r.setAttribute("y",String(40-h));r.setAttribute("width","8");r.setAttribute("height",String(h));
      const title=document.createElementNS(NS,"title");title.textContent=d.date+": "+d[field];r.append(title);svg.append(r);
    });
    box.append(svg);return box;
  }
  function link(what,key){const a=el("a",T(key));a.href="/api/traffic/export?what="+what;a.setAttribute("download","traffic_"+what+".csv");return a}
  async function draw(){
    if(Date.now()-at<30000&&drawn===LANG)return;
    at=Date.now();drawn=LANG;
    let j;
    try{j=await (await fetch("/api/traffic")).json()}catch(e){return}
    if(!j.ok||(!j.enabled&&!document.getElementById("traffic-box")))return;
    const body=FAM.panel("repos","traffic-box","ui.traffic.title");
    if(!body)return;
    body.textContent="";
    if(!j.enabled){body.append(el("p",T("ui.traffic.off")));return}
    body.append(el("p",T("ui.traffic.note")));
    if(!j.repos.length){body.append(el("p",T("ui.traffic.none")));return}
    j.repos.forEach(r=>{
      body.append(el("h3",r.repo));
      body.append(el("p",T("ui.traffic.summary",{downloads:shown(r.downloads),day:r.day||"–"})));
      [["releases_status","ui.traffic.col_downloads"],["traffic_status","ui.traffic.col_traffic"]].forEach(pair=>{
        if(r[pair[0]]!=="ok")body.append(el("p",T(pair[1])+": "+T("ui.traffic.status_"+r[pair[0]])));
      });
      if(!r.days.length)return;
      body.append(bars(r.days,"new",T("ui.traffic.col_new")),bars(r.days,"views",T("ui.traffic.col_views")),bars(r.days,"clones",T("ui.traffic.col_clones")));
      const more=el("details");
      more.append(el("summary",T("ui.traffic.days")),table([T("ui.traffic.col_date"),T("ui.traffic.col_downloads"),T("ui.traffic.col_new"),T("ui.traffic.col_views"),T("ui.traffic.col_views_unique"),T("ui.traffic.col_clones"),T("ui.traffic.col_clones_unique")],
        r.days.slice().reverse().map(d=>[d.date,shown(d.downloads),shown(d["new"]),shown(d.views),shown(d.views_unique),shown(d.clones),shown(d.clones_unique)])));
      body.append(more);
    });
    const out=el("p");out.append(link("days","ui.traffic.export_days")," · ",link("assets","ui.traffic.export_assets"));body.append(out);
  }
  FAM.on("tab",tab=>{if(tab==="repos"){at=0;draw()}});
  FAM.on("data",()=>{if(CURTAB==="repos")draw()});
})();
