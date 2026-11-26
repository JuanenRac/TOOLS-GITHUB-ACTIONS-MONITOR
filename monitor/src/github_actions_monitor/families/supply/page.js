/* Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
   GPL-3.0-or-later - see LICENSE */
/* The window that announces a newer version (setting updates.notify_window): once per browser session, never on a wall or kiosk screen. The summary is shown as plain text. */
(function(){
  if(typeof LITE!=="undefined"&&LITE)return;
  const KEY="am-upd-later";
  let box=null,back=null,shown="";
  const quiet=()=>document.body.classList.contains("kiosk")||document.body.classList.contains("allmode");
  const later=()=>{try{return sessionStorage.getItem(KEY)||""}catch(e){return ""}};
  const remember=v=>{try{sessionStorage.setItem(KEY,v)}catch(e){}};
  function close(){
    if(!box||box.hidden)return;
    box.hidden=true;remember(shown);document.removeEventListener("keydown",keys,true);
    if(back&&back.focus&&document.contains(back))try{back.focus()}catch(e){}
  }
  function keys(e){
    if(e.key==="Escape"){e.preventDefault();e.stopImmediatePropagation();close();return}
    if(e.key!=="Tab")return;
    const all=[...box.querySelectorAll("button,a[href]")];if(!all.length)return;
    const first=all[0],last=all[all.length-1],now=document.activeElement;
    if(e.shiftKey&&(now===first||!box.contains(now))){e.preventDefault();last.focus()}
    else if(!e.shiftKey&&(now===last||!box.contains(now))){e.preventDefault();first.focus()}
  }
  async function dismiss(version){
    try{
      const t=await (await fetch("/api/session-token",{cache:"no-store"})).json();
      await fetch("/api/supply/update-dismiss",{method:"POST",headers:{"Content-Type":"application/json","X-Monitor-Token":t.token||""},body:JSON.stringify({version:version})});
    }catch(e){console.error(e)}
  }
  function button(id,key,fn){const b=document.createElement("button");b.type="button";b.id=id;b.textContent=T(key);b.addEventListener("click",fn);return b}
  function open(j){
    if(!box){box=document.createElement("div");box.id="updn-dlg";box.className="dlg";box.hidden=true;document.body.appendChild(box)}
    box.textContent="";shown=j.version;
    const inner=document.createElement("div");inner.className="dlg-box";inner.setAttribute("role","dialog");inner.setAttribute("aria-modal","true");inner.setAttribute("aria-labelledby","updn-title");
    const title=document.createElement("h2");title.id="updn-title";title.textContent=T("ui.supply_notice_title",{version:j.version});
    const sub=document.createElement("p");sub.className="mut";sub.textContent=T("ui.supply_notice_current",{current:j.current});
    const text=document.createElement("div");text.id="updn-notes";text.textContent=j.notes||T("ui.supply_notice_no_summary");
    inner.append(title,sub,text);
    if(j.changelog&&j.changelog.indexOf("https://github.com/")===0){
      const a=document.createElement("a");a.href=j.changelog;a.target="_blank";a.rel="noopener noreferrer";a.textContent=T("ui.supply_notice_changelog");inner.appendChild(a);
    }
    const bar=document.createElement("div");bar.className="updn-bar";
    bar.append(button("updn-go","ui.supply_notice_go",()=>{close();showTab("upd")}),button("updn-later","ui.supply_notice_later",close),
      button("updn-never","ui.supply_notice_never",()=>{const v=shown;close();dismiss(v)}));
    inner.appendChild(bar);box.appendChild(inner);
    back=document.activeElement;box.hidden=false;document.addEventListener("keydown",keys,true);$("updn-go").focus();
  }
  async function look(){
    if(quiet()||(box&&!box.hidden))return;
    try{
      const j=await (await fetch("/api/supply/update-notice?lang="+encodeURIComponent(LANG),{cache:"no-store"})).json();
      if(j&&j.show&&j.version!==later())open(j);
    }catch(e){console.error(e)}
  }
  let started=false;
  window.FAM.on("data",()=>{if(started)return;started=true;setTimeout(look,1500);setInterval(look,3600000)});
})();
