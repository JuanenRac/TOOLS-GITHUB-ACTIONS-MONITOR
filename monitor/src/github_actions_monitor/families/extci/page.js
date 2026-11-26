/* Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
   GPL-3.0-or-later - see LICENSE */
(function(){
  let at=0;
  function el(tag,text){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n}
  function safe(url){return /^https?:\/\//i.test(String(url||""))?url:""}
  async function showLog(source,build,out){
    try{
      const r=await fetch("/api/external-ci/log?source="+encodeURIComponent(source)+"&build="+encodeURIComponent(build));
      const j=await r.json();
      out.textContent=j.ok?(j.cut?T("ui.extci.log_cut")+"\n":"")+j.text:T("ui.extci.log_none");
    }catch(e){out.textContent=T("ui.extci.log_none")}
  }
  function row(s){
    const li=el("li");
    li.append(el("b",s.repo+" - "+s.kind),el("span"," "+T("ui.extci.state_"+s.state)+(s.reason?" ("+s.reason+")":"")));
    if(s.experimental)li.append(el("em"," "+T("ui.extci.experimental")));
    (s.red||[]).forEach(red=>{
      const line=el("div",red.workflow+(red.branch?" @ "+red.branch:"")+" ");
      if(safe(red.url)){const a=el("a",T("ui.extci.open"));a.href=red.url;a.target="_blank";a.rel="noopener noreferrer";line.append(a)}
      const build=red.workflow.replace(/ \([a-z]+\)$/,"")+"#"+red.run_id;
      if((s.logs||[]).indexOf(build)>=0){
        const button=el("button",T("ui.extci.log"));button.type="button";const pre=el("pre");pre.className="extci-log";
        button.onclick=()=>showLog(s.id,build,pre);line.append(" ",button,pre);
      }
      li.append(line);
    });
    return li;
  }
  async function draw(){
    if(Date.now()-at<30000)return;
    at=Date.now();
    let j;
    try{j=await (await fetch("/api/external-ci/status")).json()}catch(e){return}
    if(!j.ok||(!j.enabled&&!document.getElementById("extci-box")))return;
    const body=FAM.panel("sci","extci-box","ui.extci.title");
    if(!body)return;
    body.textContent="";
    if(!j.enabled){body.append(el("p",T("ui.extci.off")));return}
    if(!j.sources.length)body.append(el("p",T("ui.extci.none")));
    const list=el("ul");j.sources.forEach(s=>list.append(row(s)));body.append(list);
    (j.invalid||[]).forEach(x=>body.append(el("p",T("ui.extci.invalid")+" "+x.line+" ("+x.reason+")")));
  }
  function tester(){
    const host=document.getElementById("cfp-extci");
    if(!host||document.getElementById("extci-test"))return;
    const wrap=el("div");wrap.id="extci-test";
    const input=el("input");input.type="text";input.size=70;input.placeholder="gitlab;repo=my-repo;url=https://gitlab.example.org;project=group/app";input.setAttribute("aria-label",T("ui.extci.test_label"));
    const button=el("button",T("ui.extci.test"));button.type="button";
    const out=el("p");out.setAttribute("role","status");
    button.onclick=async()=>{
      out.textContent="...";
      try{
        const t=await (await fetch("/api/session-token",{cache:"no-store"})).json();
        const r=await fetch("/api/external-ci/probe",{method:"POST",headers:{"Content-Type":"application/json","X-Monitor-Token":t.token||""},body:JSON.stringify({source:input.value.trim()})});
        const j=await r.json();
        out.textContent=j.ok?T("ui.extci.test_ok",{workflows:j.workflows,builds:j.builds,red:j.red}):T("ui.extci.test_failed",{reason:j.reason||j.error||r.status});
      }catch(e){out.textContent=T("ui.extci.test_failed",{reason:"network"})}
    };
    wrap.append(el("p",T("ui.extci.test_label")),input," ",button,out);
    host.append(wrap);
  }
  async function about(body){
    let j;
    try{j=await (await fetch("/api/external-ci/status")).json()}catch(e){return}
    if(!j.ok||!j.enabled||document.getElementById("extci-about"))return;
    const card=el("section");card.id="extci-about";card.append(el("h3",T("ui.extci.title")));
    if(!j.sources.length)card.append(el("p",T("ui.extci.none")));
    const list=el("ul");
    j.sources.forEach(s=>list.append(el("li",s.repo+" - "+s.kind+": "+T("ui.extci.state_"+s.state)+(s.reason?" ("+s.reason+")":"")+(s.last_ok?" - "+T("ui.extci.last_ok",{at:s.last_ok}):""))));
    card.append(list);body.append(card);
  }
  FAM.on("about",about);
  FAM.on("tab",tab=>{if(tab==="sci"){at=0;draw()}});
  FAM.on("data",()=>{if(CURTAB==="sci")draw()});
  FAM.on("settings",tester);
})();
