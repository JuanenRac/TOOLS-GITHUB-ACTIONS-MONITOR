/* Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
   GPL-3.0-or-later - see LICENSE */
/* In the Alerts tab: the proposals of the AI that people decide, the free chat with read only tools and the report of a repository to copy. Every text of a model or a repository is shown as plain text. */
(function(){
  if(typeof LITE!=="undefined"&&LITE)return;
  let extras=null,at=0,history=[];
  function el(tag,text){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n}
  function button(key,fn){const b=el("button",T(key));b.type="button";b.addEventListener("click",fn);return b}
  function field(labelKey,size){const label=el("label",T(labelKey));const input=el("input");input.type="text";input.size=size;label.append(input);return [label,input]}
  async function post(path,body){
    const t=await (await fetch("/api/session-token",{cache:"no-store"})).json();
    const r=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json","X-Monitor-Token":t.token||""},body:JSON.stringify(body)});
    return r.json();
  }
  function say(out,key,args){out.textContent=T(key,args)}
  function proposalRow(p,out){
    const li=el("li");
    li.append(el("code",p.command),el("div",T("ui.assistant.hash",{hash:String(p.hash||"").slice(0,16)})+" · "+T("ui.assistant.status_"+p.status)+(p.creator?" · "+p.creator:"")));
    const bar=el("div");
    if(p.status==="pending"){
      let code=null;
      if(extras.people<2){
        const [label,input]=field("ui.assistant.type_code",10);
        code=input;
        bar.append(el("div",T("ui.assistant.code_is",{code:String(p.hash||"").slice(0,8)})),label," ");
      }else bar.append(el("div",T("ui.assistant.two_people",{done:p.approvals})));
      const review=async decision=>{
        try{
          const j=await post("/api/ai/actions/review",{id:p.id,decision:decision,confirm:code?code.value.trim():""});
          if(!j.ok)return say(out,"ui.assistant.refused",{reason:j.reason||j.error||"?"});
          say(out,j.reason==="needs_second"?"ui.assistant.needs_second":"ui.assistant.done");
        }catch(e){say(out,"ui.assistant.refused",{reason:"network"})}
        at=0;draw();
      };
      bar.append(button("ui.assistant.approve",()=>review("approve"))," ",button("ui.assistant.reject",()=>review("reject")));
    }
    if(p.status==="approved"&&p.runnable){
      bar.append(button("ui.assistant.run",async()=>{
        if(!await askConfirm(T("ui.ai_prop_confirm",{cmd:p.command}),{danger:true}))return;
        try{const j=await post("/api/ai/actions/confirm",{id:p.id,command:p.command});say(out,j.ok?"ui.assistant.done":"ui.assistant.refused",{reason:j.reason||j.error||"?"})}
        catch(e){say(out,"ui.assistant.refused",{reason:"network"})}
        at=0;draw();
      }));
    }
    li.append(bar);
    return li;
  }
  async function proposals(){
    let j;
    try{j=await (await fetch("/api/ai/actions",{cache:"no-store"})).json()}catch(e){return}
    const list=j.proposals||[];
    if(!list.length&&!document.getElementById("assistant-proposals"))return;
    const body=window.FAM.panel("al","assistant-proposals","ui.assistant.proposals");
    if(!body)return;
    if(body.contains(document.activeElement))return;      /* a code being typed is not wiped */
    let out=body.querySelector("[role=status]");
    const kept=out?out.textContent:"";
    body.textContent="";
    out=el("p",kept);out.setAttribute("role","status");
    const ul=el("ul");list.forEach(p=>ul.append(proposalRow(p,out)));
    body.append(list.length?ul:el("p",T("ui.assistant.no_proposals")),out);
  }
  function chat(){
    const body=window.FAM.panel("al","assistant-chat","ui.assistant.chat");
    if(!body||body.childElementCount)return;
    const log=el("div");log.id="assistant-log";log.setAttribute("role","log");
    const [label,input]=field("ui.assistant.question",60);
    input.maxLength=2000;
    const out=el("p");out.setAttribute("role","status");
    const send=async()=>{
      const message=input.value.trim();
      if(!message)return;
      say(out,"ui.assistant.waiting");
      try{
        const j=await post("/api/assistant/chat",{message:message,history:history});
        if(!j.ok)return say(out,"ui.assistant.refused",{reason:j.error||"?"});
        history=history.concat({role:"user",text:message},{role:"assistant",text:j.text.slice(0,2000)}).slice(-6);
        input.value="";out.textContent="";
        log.append(el("p","> "+message),el("p",j.text),el("small",T("ui.assistant.sources",{sources:(j.sources||[]).map(s=>s.tool+(s.repo?" "+s.repo:"")).join(", ")||"-"})));
        if((j.proposals||[]).length){at=0;draw()}
      }catch(e){say(out,"ui.assistant.refused",{reason:"network"})}
    };
    input.addEventListener("keydown",e=>{if(e.key==="Enter")send()});
    body.append(el("p",T("ui.assistant.chat_hint")),log,label," ",button("ui.assistant.send",send),out);
  }
  function report(){
    const body=window.FAM.panel("al","assistant-report","ui.assistant.report");
    if(!body||body.childElementCount)return;
    const [label,input]=field("ui.assistant.repo",30);
    const area=el("textarea");area.rows=10;area.readOnly=true;area.hidden=true;area.setAttribute("aria-label",T("ui.assistant.report"));
    const out=el("p");out.setAttribute("role","status");
    const make=which=>async()=>{
      try{
        const j=await (await fetch("/api/assistant/repo-report?repo="+encodeURIComponent(input.value.trim())+"&lang="+encodeURIComponent(LANG),{cache:"no-store"})).json();
        if(!j.ok)return say(out,"ui.assistant.refused",{reason:j.error||"?"});
        area.value=j[which];area.hidden=false;
        try{await navigator.clipboard.writeText(j[which]);say(out,"ui.assistant.copied")}catch(e){area.select();say(out,"ui.assistant.select_copy")}
      }catch(e){say(out,"ui.assistant.refused",{reason:"network"})}
    };
    body.append(label," ",button("ui.assistant.copy_report",make("markdown"))," ",button("ui.assistant.copy_triage",make("triage")),out,area);
  }
  async function draw(){
    if(Date.now()-at<15000)return;
    at=Date.now();
    try{
      const j=await (await fetch("/api/assistant/extras",{cache:"no-store"})).json();
      if(!j.ok)return;
      extras=j;
    }catch(e){return}
    if(extras.actions)proposals();
    if(extras.chat)chat();
    if(extras.copy_report)report();
  }
  window.FAM.on("tab",tab=>{if(tab==="al"){at=0;draw()}});
  window.FAM.on("data",()=>{if(CURTAB==="al")draw()});
})();
