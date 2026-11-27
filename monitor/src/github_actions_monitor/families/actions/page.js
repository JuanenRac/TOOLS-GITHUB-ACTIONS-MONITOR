/* Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
   GPL-3.0-or-later - see LICENSE */
(function(){
  let at=0,msg="";
  function el(tag,text){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n}
  function safe(url){return /^https?:\/\//i.test(String(url||""))?url:""}
  function link(text,url){if(!safe(url))return el("span",text);const a=el("a",text);a.href=url;a.target="_blank";a.rel="noopener noreferrer";return a}
  function button(text,fn){const b=el("button",text);b.type="button";b.onclick=fn;return b}
  function table(head,rows){
    const t=el("table"),h=el("tr");
    head.forEach(x=>h.append(el("th",x)));t.append(h);
    rows.forEach(r=>{const tr=el("tr");r.forEach(x=>{const td=el("td");td.append(x&&x.nodeType?x:document.createTextNode(x===null||x===undefined?"":String(x)));tr.append(td)});t.append(tr)});
    return t;
  }
  function fold(title,node){const d=el("details");d.append(el("summary",title),node);return d}
  async function get(url){try{return await (await fetch(url)).json()}catch(e){return{ok:false}}}
  async function post(url,body){
    try{
      const t=await get("/api/session-token");
      const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json","X-Monitor-Token":t.token||""},body:JSON.stringify(body)});
      return await r.json();
    }catch(e){return{ok:false,status:"network"}}
  }
  /* one action: the reason and the operator, the plan (nothing sent), the confirmation of the whole plan, then the confirmation route of the actions */
  function act(form,body){
    return async()=>{
      const p=await post("/api/actions/plan",Object.assign({reason:form.reason.value.trim(),operator:form.who.value.trim()},body));
      if(p.status==="choose_environment"){choose(form,body,p.environments||[]);return}
      if(!p.ok){show(T("ui.actions.refused",{why:(p.status||p.error||"?")+(p.detail?" - "+p.detail:"")}));return}
      const q=p.plan;
      const where=q.environments?" ["+q.environments.join(", ")+"]":"";
      if(!await askConfirm(T("ui.actions.confirm",{what:q.method+" "+q.endpoint+" "+JSON.stringify(q.fields)+where}),{danger:true}))return;
      const done=await post("/api/gh-action/confirm",{plan:q.id});
      show(done.ok?T("ui.actions.done"):T("ui.actions.refused",{why:done.status||done.error||"?"}));
    };
  }
  /* a run that waits for several environments: one button for each, each with its own plan and confirmation */
  function choose(form,body,names){
    show(T("ui.actions.choose_environment"));
    const o=document.getElementById("actions-msg");
    if(o)names.forEach(n=>o.append(document.createTextNode(" "),button(n,act(form,Object.assign({},body,{environment:n})))));
  }
  function show(text){msg=text;const o=document.getElementById("actions-msg");if(o)o.textContent=text}
  async function draw(force){
    if(!force&&Date.now()-at<30000)return;
    at=Date.now();
    const j=await get("/api/actions/state");
    if(!j.ok||(!j.enabled&&!document.getElementById("actions-box")))return;
    const body=FAM.panel("scol","actions-box","ui.actions.title");
    if(!body)return;
    if(!force&&body.contains(document.activeElement))return;
    body.textContent="";
    if(!j.enabled){body.append(el("p",T("ui.actions.off")));return}
    const form={reason:el("input"),who:el("input")};
    form.reason.maxLength=200;form.reason.setAttribute("aria-label",T("ui.actions.reason"));form.reason.placeholder=T("ui.actions.reason");
    form.who.maxLength=60;form.who.setAttribute("aria-label",T("ui.actions.operator"));form.who.placeholder=T("ui.actions.operator");
    const out=el("p",msg);out.id="actions-msg";out.setAttribute("role","status");
    const who=[T("ui.actions.col_repo"),T("ui.actions.col_what"),T("ui.actions.col_detail"),""];
    body.append(el("p",T("ui.actions.writes")),form.reason,document.createTextNode(" "),form.who,out);
    body.append(fold(T("ui.actions.proposals")+" ("+j.proposals.length+")",table(who,j.proposals.map(p=>[p.repo,p.action+" "+p.number,T("ui.actions.why_"+p.why)+" "+p.detail,button(T("ui.actions.prepare"),act(form,{action:p.action,repo:p.repo,number:p.number}))]))));
    const waits=j.waiting.person.map(r=>{
      const cell=el("span");
      if(r.kind==="environment")cell.append(button(T("ui.actions.approve"),act(form,{action:"approve_deployment",repo:r.repo,number:r.run})));
      if(r.kind==="fork"){
        const info=el("div");
        cell.append(button(T("ui.actions.approve"),act(form,{action:"approve_fork",repo:r.repo,number:r.run})),button(T("ui.actions.facts"),async()=>{
          const f=await get("/api/actions/fork-facts?repo="+encodeURIComponent(r.repo)+"&run="+encodeURIComponent(r.run));
          info.textContent=f.ok?T("ui.actions.facts_line",{author:f.author,age:f.account_age_days===null?"?":f.account_age_days,merged:f.merged_before===undefined?"?":f.merged_before,files:f.workflow_files===null?"?":(f.workflow_files.join(", ")||"0")}):T("ui.actions.refused",{why:f.reason||f.error||"?"});
        }),info);
      }
      return[r.repo,link(r.workflow,r.url),T("ui.actions.kind_"+r.kind),cell];
    });
    body.append(fold(T("ui.actions.waiting_person")+" ("+waits.length+")",table(who,waits)));
    body.append(fold(T("ui.actions.waiting_machine")+" ("+j.waiting.machine.length+")",table(who,j.waiting.machine.map(r=>[r.repo,link(r.workflow,r.url),r.since,""]))));
    body.append(fold(T("ui.actions.lanes"),table(who,j.lanes.filter(r=>r.red).map(r=>[r.repo,link(r.workflow+" @ "+r.branch,r.url),r.conclusion,button(T("ui.actions.dismiss"),async()=>{
      const d=await post("/api/actions/dismiss",{repo:r.repo,run:r.run,reason:form.reason.value.trim(),operator:form.who.value.trim()});
      show(d.ok?T("ui.actions.done"):T("ui.actions.refused",{why:d.status||d.error||"?"}));draw(true);
    })]))));
    body.append(fold(T("ui.actions.set_aside")+" ("+j.dismissed.length+")",table(who,j.dismissed.map(d=>[d.repo,String(d.run),d.owner+": "+d.reason,button(T("ui.actions.restore"),async()=>{await post("/api/actions/dismiss",{repo:d.repo,run:d.run,restore:true});draw(true)})]))));
    body.append(fold(T("ui.actions.dependencies")+" ("+j.pulls.length+")",table(who,j.pulls.map(p=>[p.repo,link("#"+p.number+" "+p.title,p.url),T("ui.actions.group_"+p.group)+(p.bot?" - "+p.author:""),p.behind?button(T("ui.actions.update_branch"),act(form,{action:"update_branch",repo:p.repo,number:p.number})):""]))));
    body.append(fold(T("ui.actions.vulnerable")+" ("+j.vulnerable.length+")",table(who,j.vulnerable.map(v=>[v.repo,link(T("ui.actions.counts",{critical:v.critical,high:v.high}),v.url),v.oldest_days===null?"":T("ui.actions.oldest",{days:v.oldest_days}),""]))));
    if(j.unread.length||j.not_read_yet.length)body.append(fold(T("ui.actions.unread")+" ("+(j.unread.length+j.not_read_yet.length)+")",table(who,j.unread.map(u=>[u.repo,u.part,u.reason,""]).concat(j.not_read_yet.map(n=>[n,T("ui.actions.not_yet"),"",""])))));
    if(j.dismissals.length)body.append(fold(T("ui.actions.dismissals")+" ("+j.dismissals.length+")",table(who,j.dismissals.map(d=>[d.repo,link(d.kind+" #"+d.number,d.url),d.who+" - "+d.reason+" - "+d.at,d.authorized===false?el("b",T("ui.actions.not_authorized")):""]))));
    if(j.runner_events.length)body.append(fold(T("ui.actions.runner_events"),table(who,j.runner_events.map(h=>[h.repo,h.job+" ("+h.phase+")",h.runner+" - "+h.at,""]))));
    const repo=el("input"),file=el("input"),area=el("div");
    repo.placeholder=T("ui.actions.col_repo");repo.setAttribute("aria-label",T("ui.actions.col_repo"));file.placeholder="build.yml";file.setAttribute("aria-label",T("ui.actions.workflow_file"));
    const load=button(T("ui.actions.read_inputs"),async()=>{
      const f=await get("/api/actions/dispatch-form?repo="+encodeURIComponent(repo.value.trim())+"&workflow="+encodeURIComponent(file.value.trim()));
      area.textContent="";
      if(!f.ok){area.append(el("p",T("ui.actions.refused",{why:f.reason||f.error||"?"})));return}
      const fields={};
      f.inputs.forEach(i=>{
        const label=el("label",i.name+(i.required?" *":"")+" ");
        let field;
        if(i.type==="choice"||i.type==="boolean"){field=el("select");(i.type==="boolean"?["true","false"]:i.options).forEach(o=>field.append(el("option",o)))}
        else{field=el("input");if(i.type==="number")field.type="number"}
        if(i.default!==null)field.value=i.default;
        field.title=i.description;fields[i.name]=field;label.append(field);area.append(label,el("br"));
      });
      area.append(button(T("ui.actions.prepare"),async()=>{
        const inputs={};Object.keys(fields).forEach(k=>inputs[k]=fields[k].value);
        await act(form,{action:"dispatch",repo:repo.value.trim(),workflow:file.value.trim(),inputs:inputs,ref:f.ref})();
      }));
    });
    const dispatch=el("div");dispatch.append(repo,document.createTextNode(" "),file,document.createTextNode(" "),load,area);
    body.append(fold(T("ui.actions.dispatch"),dispatch));
  }
  FAM.on("tab",tab=>{if(tab==="scol"){at=0;draw()}});
  FAM.on("data",()=>{if(CURTAB==="scol")draw()});
})();
