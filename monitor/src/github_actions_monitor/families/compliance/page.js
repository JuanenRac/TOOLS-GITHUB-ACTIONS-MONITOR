/* Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
   GPL-3.0-or-later - see LICENSE */
/* The compliance report: a box at the end of the Security tab of the Sentinel, read only, shown when asked for. Everything is plain text. */
(function(){
  if(typeof LITE!=="undefined"&&LITE)return;
  async function show(out){
    out.textContent="";
    try{
      const r=await fetch("/api/compliance/report",{cache:"no-store"});
      if(!r.ok){out.textContent=T("ui.compliance.failed");return}
      const j=await r.json();
      const note=document.createElement("p");note.className="mut";note.textContent=T("ui.compliance.notice")+" "+j.at;out.appendChild(note);
      const list=document.createElement("ul");list.className="compliance-lines";
      (j.lines||[]).forEach(row=>{
        const item=document.createElement("li");
        const name=document.createElement("span");name.textContent=T("ui.compliance.line_"+row.id);
        const value=document.createElement("code");value.textContent=String(row.value);
        const how=document.createElement("span");how.className="mut";how.textContent=T("ui.compliance.evidence_"+row.evidence);
        item.append(name,value,how);list.appendChild(item);
      });
      out.appendChild(list);
    }catch(e){console.error(e);out.textContent=T("ui.compliance.failed")}
  }
  window.FAM.on("tab",tab=>{
    if(tab!=="ssec")return;
    const body=window.FAM.panel("ssec","compliance-box","ui.compliance.title");
    if(!body||body.firstChild)return;
    const button=document.createElement("button");button.type="button";button.setAttribute("data-i18n","ui.compliance.show");button.textContent=T("ui.compliance.show");
    const out=document.createElement("div");out.setAttribute("aria-live","polite");
    button.addEventListener("click",()=>show(out));
    body.append(button,out);
  });
})();
