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
  function fold(title,node){const d=el("details");d.append(el("summary",title),node);return d}
  async function draw(){
    if(Date.now()-at<30000&&drawn===LANG)return;      // the titles of the findings come translated from the monitor: another language is read again at once
    at=Date.now();drawn=LANG;
    let j;
    try{j=await (await fetch("/api/posture?"+qlang())).json()}catch(e){return}
    if(!j.ok||(!j.enabled&&!document.getElementById("posture-box")))return;
    const body=FAM.panel("ssec","posture-box","ui.posture.title");
    if(!body)return;
    body.textContent="";
    if(!j.enabled){body.append(el("p",T("ui.posture.off")));return}
    body.append(el("p",T("ui.posture.summary",{repos:j.repos.length,unchecked:j.not_checked})));
    const rows=[];
    [{repo:T("ui.posture.org"),findings:j.org.findings,unread:j.org.unread}].concat(j.repos).forEach(r=>{
      r.findings.forEach(f=>rows.push([r.repo,T("ui.posture.level_"+f.level),f.title+(f.item?" ("+f.item+")":""),f.owasp+" / CIS "+f.cis]));
      Object.keys(r.unread).forEach(g=>rows.push([r.repo,T("ui.posture.unchecked"),g+" ("+r.unread[g]+")",""]));
    });
    body.append(rows.length?table([T("ui.posture.col_repo"),T("ui.posture.col_level"),T("ui.posture.col_finding"),T("ui.posture.col_standard")],rows):el("p",T("ui.posture.none")));
    body.append(fold(T("ui.posture.maturity"),table([T("ui.posture.col_repo"),T("ui.posture.maturity")],j.repos.map(r=>[r.repo,r.maturity?r.maturity.passed+" / "+r.maturity.checked:T("ui.posture.unchecked")]))));
    body.append(fold(T("ui.posture.history"),table([T("ui.posture.col_day"),T("ui.posture.level_error"),T("ui.posture.level_warning"),T("ui.posture.level_info")],j.history.slice(-30).map(h=>[h.day,h.error,h.warning,h.info]))));
    body.append(fold(T("ui.posture.report_title"),(()=>{
      const box=el("div");box.append(el("p",T("ui.posture.report_note")),el("p",T("ui.posture.trend_"+j.trend.direction,{since:j.trend.since,delta:j.trend.delta})));
      box.append(table(["OWASP",T("ui.posture.col_finding"),T("ui.posture.col_level")],j.compliance.owasp.map(r=>[r.id+" "+r.name,r.findings,T("ui.posture.status_"+r.status)])));
      box.append(table(["CIS",T("ui.posture.col_finding"),T("ui.posture.col_level")],j.compliance.cis.map(r=>[r.id,r.findings,T("ui.posture.status_"+r.status)])));
      return box;
    })()));
    const lessons=el("ul");j.compliance.owasp.filter(r=>r.findings).forEach(r=>lessons.append(el("li",r.id+": "+j.learn[r.id])));
    if(lessons.children.length)body.append(fold(T("ui.posture.learn_title"),lessons));
    body.append(fold(T("ui.posture.permissions"),table([T("ui.posture.permissions"),"GitHub App",T("ui.posture.col_finding")],j.permissions.map(p=>[p.permission+(p.refused?" - "+T("ui.posture.refused"):""),p.app_permission+": "+p.granted,p.checks.join(", ")]))));
  }
  FAM.on("tab",tab=>{if(tab==="ssec"){at=0;draw()}});
  FAM.on("data",()=>{if(CURTAB==="ssec")draw()});
})();
