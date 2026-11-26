/* Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
   GPL-3.0-or-later - see LICENSE */
/* The catalogue of extensions inside its sub-tab of Settings: what runs, with which permissions and key, its state and what is isolated. Everything a plugin says is shown as plain text. */
(function(){
  function el(tag,text){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n}
  async function post(path,body){
    const t=await (await fetch("/api/session-token",{cache:"no-store"})).json();
    const r=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json","X-Monitor-Token":t.token||""},body:JSON.stringify(body)});
    return r.json();
  }
  function button(key,fn){const b=el("button",T(key));b.type="button";b.addEventListener("click",fn);return b}
  async function act(path,body,out){
    try{
      const j=await post(path,body);
      if(!j.ok){out.textContent=T("ui.plugins.failed",{reason:j.reason||j.error||"?"});return}
    }catch(e){out.textContent=T("ui.plugins.failed",{reason:"network"});return}
    draw();
  }
  function row(p,out){
    const li=el("li");
    li.append(el("b",p.name+" "+p.version),el("span"," "+T("ui.plugins.state_"+p.state)+" · "+T("ui.plugins.isolation_"+p.isolation)));
    if(p.description)li.append(el("div",p.description));
    li.append(el("div",T("ui.plugins.permissions")+": "+(p.permissions.join(", ")||"-")+(p.fingerprint?" · "+T("ui.plugins.key")+" "+p.key_id+" "+p.fingerprint:"")));
    if(p.reason)li.append(el("div",p.reason));
    if(p.check&&p.check!=="ok")li.append(el("div",T("ui.plugins.failed",{reason:p.check})));
    const bar=el("div");
    if(p.state==="paused")bar.append(button("ui.plugins.resume",()=>act("/api/plugins/enable",{name:p.name,enabled:true},out))," ");
    if(p.trust!=="official"){
      bar.append(button(p.enabled?"ui.plugins.disable":"ui.plugins.enable",()=>act("/api/plugins/enable",{name:p.name,enabled:!p.enabled},out))," ",
        button("ui.plugins.uninstall",async()=>{if(await askConfirm(T("ui.plugins.uninstall_confirm",{name:p.name})))act("/api/plugins/uninstall",{name:p.name},out)}));
    }
    li.append(bar);
    return li;
  }
  function installer(out){
    const wrap=el("div");wrap.className="plugins-install";
    const label=el("label",T("ui.plugins.path_label"));
    const input=el("input");input.type="text";input.size=60;label.append(input);
    wrap.append(label," ",button("ui.plugins.inspect",async()=>{
      const path=input.value.trim();
      let j;
      try{j=await post("/api/plugins/inspect",{path:path})}catch(e){out.textContent=T("ui.plugins.failed",{reason:"network"});return}
      if(!j.ok){out.textContent=T("ui.plugins.failed",{reason:j.reason||j.error||"?"});return}
      const m=j.manifest;
      const yes=await askConfirm(T("ui.plugins.install_confirm",{name:m.name,version:m.version,author:m.author,permissions:m.permissions.concat(m.get_paths).join(", ")||"-",fingerprint:j.fingerprint}));
      if(yes)act("/api/plugins/install",{path:path,fingerprint:j.fingerprint},out);
    }));
    return wrap;
  }
  async function draw(){
    const host=document.getElementById("cfp-plugins");
    if(!host)return;
    let j;
    try{j=await (await fetch("/api/plugins/catalog",{cache:"no-store"})).json()}catch(e){return}
    if(!j||!j.ok)return;      /* a viewer or a maintainer does not see the management */
    let box=document.getElementById("plugins-catalog");
    if(!box){box=el("section");box.id="plugins-catalog";host.append(box)}
    box.textContent="";
    box.append(el("h3",T("ui.plugins.title")));
    if(!j.enabled)box.append(el("p",T("ui.plugins.off")));
    const out=el("p");out.setAttribute("role","status");
    const list=el("ul");j.plugins.forEach(p=>list.append(row(p,out)));
    box.append(j.plugins.length?list:el("p",T("ui.plugins.none")));
    (j.candidates||[]).forEach(c=>box.append(el("p","pip: "+c.distribution+" "+c.package)));
    box.append(installer(out),out);
  }
  window.FAM.on("settings",draw);
})();
