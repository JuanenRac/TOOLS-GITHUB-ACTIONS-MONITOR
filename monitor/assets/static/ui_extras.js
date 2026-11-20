/* Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
   GPL-3.0-or-later - see LICENSE */
/* Extras of the page (the server puts this file in place of the marker at the end of actions_monitor.html, so it sees the same functions and texts as the page).
   Every visible text is a key "ui.*" of the locales. Nothing here writes to GitHub; the only writes are the pairing of a phone (POST /api/pair/start, /api/devices/revoke).
   Sections: compact profile and keyboard of a phone, refresh of the app when it returns, pairing of a phone, palette (Ctrl+K) and shortcuts. */
(function(){
  const SC=I18N.screens||{},PW=I18N.pwa||{},PR=I18N.pairing||{};
  const root=document.documentElement,tx=(k,v)=>T(k,v);
  const h=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const typing=e=>{const t=e.target;return !!t&&(t.isContentEditable||/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))};

  /* ---- compact profile (ui.compact: auto = a narrow window or a touch screen; ?compact=1 or ?compact=0 for one window) ---- */
  function compactNow(){
    const q=new URLSearchParams(location.search).get("compact"),m=q==="1"?"on":q==="0"?"off":(SC.compact||"auto");
    return m==="on"||(m==="auto"&&window.matchMedia("(max-width: 700px)").matches);
  }
  function compactApply(){root.classList.toggle("compact",compactNow())}
  compactApply();
  window.addEventListener("resize",compactApply);
  /* the virtual keyboard: the height that is really free goes to a variable the dialogs use, and the field being typed in is brought into view */
  if(window.visualViewport){
    const vv=window.visualViewport,set=()=>root.style.setProperty("--vvh",Math.round(vv.height)+"px");
    vv.addEventListener("resize",set);set();
    document.addEventListener("focusin",e=>{if(/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)&&root.classList.contains("compact"))setTimeout(()=>{try{e.target.scrollIntoView({block:"center",behavior:"auto"})}catch(x){}},250)});
  }

  /* ---- the app comes back to the front or the network returns: ask for fresh data at once ---- */
  if(PW.enabled&&PW.refresh_on_return!==false){
    const again=()=>{try{if(typeof tick==="function")tick(true)}catch(e){}};
    document.addEventListener("visibilitychange",()=>{if(!document.hidden)again()});
    window.addEventListener("online",again);
  }

  /* ---- a small dialog made on demand (same look as the other dialogs of the page) ---- */
  function dialog(id,title,body){
    let d=document.getElementById(id);
    if(!d){d=document.createElement("div");d.id=id;d.className="dlg";d.setAttribute("role","dialog");d.setAttribute("aria-modal","true");d.setAttribute("aria-labelledby",id+"-h");document.body.appendChild(d)}
    d.innerHTML='<div class="dlg-box"><div class="dlg-top"><h2 id="'+id+'-h">'+h(title)+'</h2><span class="sp"></span><button type="button" class="ib" data-x aria-label="'+h(tx("ui.close"))+'">&times;</button></div><div class="dlg-body">'+body+'</div></div>';
    const close=()=>{d.hidden=true;if(d._back&&d._back.focus)try{d._back.focus()}catch(e){}};
    d._back=document.activeElement;d.hidden=false;
    d.querySelector("[data-x]").onclick=close;
    d.onclick=e=>{if(e.target===d)close()};
    d.onkeydown=e=>{if(e.key==="Escape"){e.stopPropagation();close()}};
    const first=d.querySelector("input,button:not([data-x])")||d.querySelector("[data-x]");if(first)first.focus();
    return d;
  }

  /* ---- pairing of a phone (2.1.7): a one-use code shown as a QR code, and the list of paired devices ---- */
  async function pairOpen(){
    const d=dialog("pair-dlg",tx("ui.pair_title"),'<p class="mut">'+h(tx("ui.pair_intro"))+'</p><div id="pair-main" role="status">'+h(tx("ui.loading"))+'</div>');
    let timer=0;const main=d.querySelector("#pair-main");
    const stop=()=>{if(timer){clearInterval(timer);timer=0}};
    const draw=async()=>{
      let j=null;try{const r=await fetch("/api/devices",{cache:"no-store"});j=r.ok?await r.json():null}catch(e){}
      if(!j){main.textContent=tx("ui.pair_err_off");return}
      if(!j.enabled){main.textContent=tx("ui.pair_err_off");return}
      if(!j.network){main.textContent=tx("ui.pair_not_network");return}
      let html='<p><button type="button" id="pair-new">'+h(tx("ui.pair_start"))+'</button></p><div id="pair-qr"></div>';
      html+='<h3>'+h(tx("ui.pair_devices"))+'</h3>';
      if(!j.devices.length)html+='<p class="mut">'+h(tx("ui.pair_none"))+'</p>';
      else html+='<ul class="pair-list">'+j.devices.map(x=>'<li><span><b>'+h(x.name||"?")+'</b> <span class="mut">'+h(tx("ui.pair_last",{when:new Date(x.last_seen*1000).toLocaleString()}))+'</span></span><button type="button" data-revoke="'+h(x.id)+'">'+h(tx("ui.pair_revoke"))+'</button></li>').join("")+'</ul>';
      main.innerHTML=html;
      main.querySelectorAll("[data-revoke]").forEach(b=>b.onclick=async()=>{b.disabled=true;try{await fetch("/api/devices/revoke",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id:b.dataset.revoke})})}catch(e){}draw()});
      main.querySelector("#pair-new").onclick=async()=>{
        stop();const box=main.querySelector("#pair-qr");box.textContent=tx("ui.loading");
        let a=null;try{const r=await fetch("/api/pair/start",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});a=await r.json()}catch(e){}
        if(!a||!a.ok){box.textContent=tx("ui.pair_err_"+((a&&a.error)||"off"));return}
        let left=a.expires_in;
        box.innerHTML='<div class="pair-qr">'+a.svg+'</div><p>'+h(tx("ui.pair_scan"))+'</p><p><code class="pair-url">'+h(a.url)+'</code></p><p id="pair-left" class="mut"></p>';
        const upd=()=>{const e=document.getElementById("pair-left");if(!e){stop();return}e.textContent=left>0?tx("ui.pair_expires",{n:Math.ceil(left/60)}):tx("ui.pair_err_closed");if(left<=0){stop();box.querySelector(".pair-qr").style.opacity=".25"}left-=1};
        upd();timer=setInterval(()=>{upd();if(left%5===0)fetch("/api/devices",{cache:"no-store"}).then(r=>r.json()).then(s=>{if(!s.open&&left>0){stop();draw()}}).catch(()=>{})},1000);
      };
    };
    draw();
    const mo=new MutationObserver(()=>{if(d.hidden){stop();mo.disconnect()}});mo.observe(d,{attributes:true,attributeFilter:["hidden"]});
  }
  window.pairOpen=pairOpen;

  /* ---- the keyboard shortcuts ---- */
  const SHORTCUTS=[["Ctrl+K","ui.sc_palette"],["?","ui.sc_help"],["/","ui.sc_filter"],["r","ui.sc_refresh"],["[ ]","ui.sc_tabs"]];
  function shortcutsOpen(){
    dialog("sc-dlg",tx("ui.sc_title"),'<dl class="dl">'+SHORTCUTS.map(r=>'<dt><kbd>'+h(r[0])+'</kbd></dt><dd>'+h(tx(r[1]))+'</dd>').join("")+'</dl>');
  }
  const tabsShown=()=>TABS.filter(t=>{const b=document.getElementById("n-"+t);return !!b&&!b.closest("[hidden]")});

  /* ---- the palette (Ctrl+K): tabs, repositories and actions, with a search that takes any part of the words ---- */
  function palItems(){
    const out=[];
    tabsShown().forEach(t=>out.push({g:"ui.pal_g_tabs",k:"tab:"+t,label:tx("ui.tab_"+t),run:()=>showTab(t)}));
    const repos=DATA&&DATA.ecosystems?Object.keys(DATA.ecosystems):[];
    repos.slice(0,500).forEach(r=>out.push({g:"ui.pal_g_repos",k:"repo:"+r,label:r,run:()=>{if(typeof openPanel==="function")openPanel(r)}}));
    const act=(key,fn)=>out.push({g:"ui.pal_g_actions",k:"act:"+key,label:tx("ui.pal_"+key),run:fn});
    act("refresh",()=>{try{tick(true)}catch(e){}});
    if(document.getElementById("dense"))act("dense",()=>document.getElementById("dense").click());
    if(document.getElementById("theme"))act("theme",()=>{const s=document.getElementById("theme"),o=[...s.options].map(x=>x.value),i=(o.indexOf(s.value)+1)%o.length;s.value=o[i];s.dispatchEvent(new Event("change",{bubbles:true}))});
    if(document.getElementById("help-tab"))act("help",()=>document.getElementById("help-tab").click());
    act("shortcuts",shortcutsOpen);
    if(PR.enabled)act("pair",pairOpen);
    if(document.getElementById("er-open")&&window.expectedRedOpen)act("expected",window.expectedRedOpen);
    if(window.whatsNewOpen)act("whatsnew",window.whatsNewOpen);
    if(window.glossaryOpen)act("glossary",window.glossaryOpen);
    return out;
  }
  function palScore(label,words){
    const l=label.toLowerCase();let score=0;
    for(const w of words){const i=l.indexOf(w);if(i<0)return -1;score+=i===0?0:(l[i-1]===" "||l[i-1]==="-"||l[i-1]==="/"||l[i-1]==="_")?1:3}
    return score;
  }
  function palOpen(){
    if(SC.palette===false)return;
    const d=dialog("pal-dlg",tx("ui.pal_title"),'<input id="pal-q" type="search" autocomplete="off" spellcheck="false" role="combobox" aria-expanded="true" aria-controls="pal-list" placeholder="'+h(tx("ui.pal_ph"))+'" aria-label="'+h(tx("ui.pal_ph"))+'"><ul id="pal-list" role="listbox"></ul><p class="mut pal-hint">'+h(tx("ui.pal_hint"))+'</p>');
    const q=d.querySelector("#pal-q"),list=d.querySelector("#pal-list"),all=palItems();let shown=[],at=0;
    const paint=()=>{
      const words=q.value.toLowerCase().split(/\s+/).filter(Boolean);
      shown=all.map(x=>({x,s:words.length?palScore(x.label,words):0})).filter(r=>r.s>=0).sort((a,b)=>a.s-b.s).slice(0,40).map(r=>r.x);
      if(at>=shown.length)at=Math.max(0,shown.length-1);
      let last="",html="";
      shown.forEach((x,i)=>{if(x.g!==last){last=x.g;html+='<li role="presentation" class="pal-g">'+h(tx(x.g))+'</li>'}html+='<li role="option" id="pal-o'+i+'" data-i="'+i+'" aria-selected="'+(i===at)+'">'+h(x.label)+'</li>'});
      list.innerHTML=html||'<li role="presentation" class="mut">'+h(tx("ui.pal_none"))+'</li>';
      q.setAttribute("aria-activedescendant",shown.length?"pal-o"+at:"");
      const cur=list.querySelector('[aria-selected="true"]');if(cur&&cur.scrollIntoView)cur.scrollIntoView({block:"nearest"});
    };
    const go=i=>{const x=shown[i];if(!x)return;d.hidden=true;setTimeout(()=>{try{x.run()}catch(e){}},0)};
    q.oninput=()=>{at=0;paint()};
    q.onkeydown=e=>{
      if(e.key==="ArrowDown"){e.preventDefault();at=Math.min(shown.length-1,at+1);paint()}
      else if(e.key==="ArrowUp"){e.preventDefault();at=Math.max(0,at-1);paint()}
      else if(e.key==="Enter"){e.preventDefault();go(at)}
    };
    list.onclick=e=>{const li=e.target.closest("[data-i]");if(li)go(+li.dataset.i)};
    paint();q.focus();
  }
  window.paletteOpen=palOpen;

  document.addEventListener("keydown",e=>{
    if((e.ctrlKey||e.metaKey)&&!e.altKey&&!e.shiftKey&&e.key.toLowerCase()==="k"){if(SC.palette===false)return;e.preventDefault();const d=document.getElementById("pal-dlg");if(d&&!d.hidden){d.hidden=true;return}palOpen();return}
    if(e.ctrlKey||e.metaKey||e.altKey||typing(e)||SC.palette===false)return;
    if(document.querySelector(".dlg:not([hidden])"))return;
    if(e.key==="?"){e.preventDefault();shortcutsOpen()}
    else if(e.key==="/"){const i=document.querySelector(".tab.on input[type=search],.tab.on input[id$='-q']");if(i){e.preventDefault();i.focus()}}
    else if(e.key==="r"){try{tick(true)}catch(x){}}
    else if(e.key==="["||e.key==="]"){const l=tabsShown(),i=l.indexOf(typeof CURTAB!=="undefined"?CURTAB:"now");if(l.length){e.preventDefault();showTab(l[(i+(e.key==="]"?1:-1)+l.length)%l.length])}}
  });
})();

/* ---- the notes about the repositories: expected red (a button in Alerts) and the metadata columns of the Repositories table ---- */
(function(){
  const h=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const tx=(k,v)=>T(k,v),jget=async u=>{try{const r=await fetch(u,{cache:"no-store"});return r.ok?await r.json():null}catch(e){return null}};
  const pp=(o)=>fetch("/api/expected-red",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(o)}).then(r=>r.json().then(j=>Object.assign({status:r.status},j))).catch(()=>({ok:false,error:"off"}));

  /* expected red: a workflow that is red on purpose, with a reason, an owner and an end (data/expected_red.json; a note of this monitor) */
  async function erOpen(){
    const d=document.createElement("div");d.id="er-dlg";d.className="dlg";d.setAttribute("role","dialog");d.setAttribute("aria-modal","true");d.setAttribute("aria-labelledby","er-h");
    document.querySelectorAll("#er-dlg").forEach(x=>x.remove());document.body.appendChild(d);
    const back=document.activeElement,close=()=>{d.remove();if(back&&back.focus)try{back.focus()}catch(e){}};
    d.onclick=e=>{if(e.target===d)close()};d.onkeydown=e=>{if(e.key==="Escape"){e.stopPropagation();close()}};
    const draw=async()=>{
      const j=await jget("/api/expected-red");if(!j||!j.enabled){d.innerHTML='<div class="dlg-box"><div class="dlg-body" style="padding:16px">'+h(tx("ui.er_err_off"))+'</div></div>';return}
      const repos=DATA&&DATA.ecosystems?Object.keys(DATA.ecosystems):[];
      const rows=j.entries.map(e=>'<li><span><b>'+h(e.repo)+'</b> '+h(e.workflow)+' <span class="chip'+(e.state==="expired"?" bad":"")+'">'+h(e.state==="expired"?tx("ui.er_expired"):tx("ui.er_until",{when:new Date(e.until*1000).toLocaleString()}))+'</span><br><span class="mut">'+h(e.owner)+' · '+h(e.reason)+'</span></span><button type="button" data-rm="'+h(e.id)+'">'+h(tx("ui.er_remove"))+'</button></li>').join("");
      d.innerHTML='<div class="dlg-box"><div class="dlg-top"><h2 id="er-h">'+h(tx("ui.er_title"))+'</h2><span class="sp"></span><button type="button" class="ib" data-x aria-label="'+h(tx("ui.close"))+'">&times;</button></div><div class="dlg-body" style="padding:12px 16px;overflow:auto"><p class="mut">'+h(tx("ui.er_intro"))+'</p>'
        +(rows?'<ul class="pair-list">'+rows+'</ul>':'<p class="mut">'+h(tx("ui.er_none"))+'</p>')
        +'<form id="er-form" class="er-form"><label>'+h(tx("ui.er_repo"))+'<input name="repo" list="er-repos" required maxlength="140"></label><datalist id="er-repos">'+repos.slice(0,300).map(r=>'<option value="'+h(r)+'">').join("")+'</datalist>'
        +'<label>'+h(tx("ui.er_workflow"))+'<input name="workflow" required maxlength="120" placeholder="ci.yml"></label><label>'+h(tx("ui.er_reason"))+'<input name="reason" required maxlength="200"></label>'
        +'<label>'+h(tx("ui.er_owner"))+'<input name="owner" required maxlength="40"></label><label>'+h(tx("ui.er_days"))+'<input name="days" type="number" min="1" max="'+h(j.max_days)+'" value="'+h(Math.min(7,j.max_days))+'"></label>'
        +'<button type="submit">'+h(tx("ui.er_add"))+'</button> <span id="er-msg" role="status" class="mut"></span></form></div></div>';
      d.querySelector("[data-x]").onclick=close;
      d.querySelectorAll("[data-rm]").forEach(b=>b.onclick=async()=>{b.disabled=true;await pp({action:"remove",id:b.dataset.rm});await draw();erCount()});
      d.querySelector("#er-form").onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target),r=await pp({action:"add",repo:f.get("repo"),workflow:f.get("workflow"),reason:f.get("reason"),owner:f.get("owner"),days:+f.get("days")});
        if(r.ok){await draw();erCount();try{if(typeof tick==="function")tick(true)}catch(x){}}else{const m=d.querySelector("#er-msg");m.textContent=tx("ui.er_err_"+(r.error||"off"))===("ui.er_err_"+(r.error||"off"))?tx("ui.er_err_off"):tx("ui.er_err_"+r.error)}};
      const first=d.querySelector("input");if(first)first.focus();
    };
    await draw();
  }
  window.expectedRedOpen=erOpen;
  async function erCount(){
    const j=await jget("/api/expected-red");if(!j||!j.enabled)return;
    const row=document.getElementById("al-filters");if(!row)return;
    let b=document.getElementById("er-open");
    if(!b){b=document.createElement("button");b.type="button";b.id="er-open";b.onclick=erOpen;row.appendChild(b)}
    b.textContent=tx("ui.er_button",{n:j.entries.filter(e=>e.state==="active").length});
  }
  erCount();setInterval(erCount,60000);

  /* metadata columns: one column of the Repositories table for each entry of fleet.meta_columns (read by the monitor, a few files per round) */
  let known="",tries=0;
  async function metaLoad(){
    if(typeof REPO_TABLE==="undefined")return;
    const j=await jget("/api/meta-columns");if(!j||!j.columns||!j.columns.length)return;
    window.META_ROWS=j.rows||{};
    const ids=j.columns.map(c=>"meta_"+c.id).join(",");
    if(ids!==known){
      REPO_TABLE.cols.splice(0,REPO_TABLE.cols.length,...REPO_TABLE.cols.filter(c=>!String(c.id).startsWith("meta_")));
      REPO_TABLE.show=REPO_TABLE.show.filter(i=>!String(i).startsWith("meta_"));
      j.columns.forEach(c=>{const id="meta_"+c.id;REPO_TABLE.cols.push({id:id,label:c.name,sort:r=>(window.META_ROWS[r.repo]||{})[c.id]||"",cell:r=>{const v=(window.META_ROWS[r.repo]||{})[c.id];return v?h(v):dash_}});REPO_TABLE.show.push(id)});
      known=ids;REPO_TABLE.made="";
    }
    if(typeof DATA!=="undefined"&&DATA&&typeof render==="function")render(DATA);
    if(j.pending>0&&tries++<40)setTimeout(metaLoad,6000);
  }
  setTimeout(metaLoad,1500);
  document.addEventListener("click",e=>{const t=e.target.closest&&e.target.closest("#n-repos");if(t){tries=0;setTimeout(metaLoad,300)}});
})();

/* ---- how the page looks and behaves while you read: density, less movement, colour-blind palette, updates that wait while you read, what is new, the glossary,
        the scope of the filter, the states of the selectors and the actions for an empty page or a failure ---- */
(function(){
  const D=I18N.display||{},q=new URLSearchParams(location.search),root=document.documentElement;
  const h=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const tx=(k,v)=>T(k,v),jget=async u=>{try{const r=await fetch(u,{cache:"no-store"});return r.ok?await r.json():null}catch(e){return null}};
  const mem={get:k=>{try{return localStorage.getItem(k)}catch(e){return null}},set:(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}}};

  /* density of every tab, less movement and the palette for colour blindness (a window can ask for its own with ?density= and ?palette=) */
  root.classList.toggle("dense",(q.get("density")||D.density)==="dense");
  root.classList.toggle("reduce-motion",D.reduce_motion==="on");
  if((q.get("palette")||D.palette)==="colorblind")root.setAttribute("data-palette","colorblind");

  /* an update of the data does not jump under your hand: while the pointer or the focus is inside the tab you read, the new picture waits (display.live_throttle_s) */
  const wait=D.live_throttle_s==null?30:D.live_throttle_s;
  if(wait>0&&typeof render==="function"){
    const drawNow=render;let pending=null,last=Date.now(),pointerAt=0;
    const tab=()=>document.querySelector(".tab.on");
    document.addEventListener("pointermove",e=>{const t=tab();if(t&&t.contains(e.target))pointerAt=Date.now()},{passive:true});
    const reading=()=>{const t=tab();if(!t)return false;const a=document.activeElement;return (!!a&&a!==document.body&&t.contains(a)&&/^(INPUT|TEXTAREA|SELECT|SUMMARY)$/.test(a.tagName))||Date.now()-pointerAt<4000};
    render=function(d){
      const periodic=/\btick\b/.test(String(new Error().stack||""));      /* a refresh asked for by a click or a key is applied at once; the periodic one waits */
      if(periodic&&reading()){pending=d;return}
      pending=null;last=Date.now();return drawNow(d);
    };
    setInterval(()=>{if(pending&&!reading()&&Date.now()-last>=wait*1000){const d=pending;pending=null;last=Date.now();drawNow(d)}},1000);
  }

  /* a small dialog with a close button (the same look as the others) */
  function modal(id,title,body){
    document.querySelectorAll("#"+id).forEach(x=>x.remove());
    const d=document.createElement("div");d.id=id;d.className="dlg";d.setAttribute("role","dialog");d.setAttribute("aria-modal","true");d.setAttribute("aria-labelledby",id+"-h");
    d.innerHTML='<div class="dlg-box"><div class="dlg-top"><h2 id="'+id+'-h">'+h(title)+'</h2><span class="sp"></span><button type="button" class="ib" data-x aria-label="'+h(tx("ui.close"))+'">&times;</button></div><div class="dlg-body">'+body+'</div></div>';
    document.body.appendChild(d);const back=document.activeElement,close=()=>{d.remove();if(back&&back.focus)try{back.focus()}catch(e){}};
    d.querySelector("[data-x]").onclick=close;d.onclick=e=>{if(e.target===d)close()};d.onkeydown=e=>{if(e.key==="Escape"){e.stopPropagation();close()}};d.querySelector("[data-x]").focus();
  }

  /* what is new after an update: a notice that never interrupts; what was seen is kept in this browser before anything else happens */
  function wnShow(j){
    const body=j.versions.length?j.versions.map(v=>'<h3>'+h(v.version)+'</h3><ul class="wn-list">'+v.items.map(x=>'<li>'+h(x)+'</li>').join("")+'</ul>'+(v.more?'<p class="mut">'+h(tx("ui.wn_more",{n:v.more}))+'</p>':'')).join(""):'<p class="mut">'+h(tx("ui.wn_none"))+'</p>';
    modal("wn-dlg",tx("ui.wn_title"),body);
  }
  window.whatsNewOpen=async()=>{const j=await jget("/api/whats-new?"+qlang());if(j)wnShow(j)};
  async function wnInit(){
    const cur=I18N.version;if(D.whats_new===false||!cur)return;
    const seen=mem.get("am-seen-version");
    if(!seen){mem.set("am-seen-version",cur);return}
    if(seen===cur)return;
    const j=await jget("/api/whats-new?since="+encodeURIComponent(seen)+"&"+qlang());
    mem.set("am-seen-version",cur);      /* saved before anything is shown, so a reload does not show the notice again */
    if(!j||!j.enabled||!j.versions.length)return;
    const bar=document.createElement("div");bar.className="wn-bar";bar.setAttribute("role","status");
    bar.innerHTML='<span>'+h(tx("ui.wn_banner",{version:cur}))+'</span><button type="button" data-open>'+h(tx("ui.wn_open"))+'</button><span class="sp"></span><button type="button" class="ib" data-x aria-label="'+h(tx("ui.close"))+'">&times;</button>';
    const shell=document.querySelector(".shell");if(shell&&shell.parentNode)shell.parentNode.insertBefore(bar,shell);
    bar.querySelector("[data-open]").onclick=()=>{wnShow(j);bar.remove()};bar.querySelector("[data-x]").onclick=()=>bar.remove();
  }
  setTimeout(wnInit,800);

  /* the glossary: the figures with their real parameters, the attacks, the limits and where to learn more */
  window.glossaryOpen=async()=>{
    const j=await jget("/api/glossary?"+qlang());if(!j)return;
    const term=x=>'<div class="gl-term"><b>'+h(x.name)+'</b>'+h(x.definition)+'</div>';
    modal("gl-dlg",tx("ui.gl_title"),'<h3>'+h(tx("ui.gl_metrics"))+'</h3>'+j.metrics.map(term).join("")+'<h3>'+h(tx("ui.gl_attacks"))+'</h3>'+j.attacks.map(term).join("")
      +'<h3>'+h(j.limits_title)+'</h3><ul class="wn-list">'+j.limits.map(x=>'<li>'+h(x)+'</li>').join("")+'</ul><h3>'+h(tx("ui.gl_resources"))+'</h3><ul class="wn-list">'+j.resources.map(r=>'<li><a href="'+h(r.url)+'" target="_blank" rel="noopener noreferrer">'+h(r.name)+'</a></li>').join("")+'</ul>');
  };

  /* what the filter of the header covers: which tabs follow it and which are always global */
  const OBEYS=["now","al","charts","sent","sci","scol","ssec","sdel","ssup","repos","hist"],GLOBAL=["syvt","strend","team","fleet","rep","trep","les","upd","cfg"];
  window.FILTER_SCOPE={obeys:OBEYS,global:GLOBAL};
  (function scope(){
    const input=document.getElementById("g-q");if(!input)return;
    const row=input.closest("label")&&input.closest("label").parentElement;if(!row||document.getElementById("scope-note"))return;
    const names=l=>l.filter(t=>TABS.includes(t)).map(t=>tx("ui.tab_"+t)).join(", ");
    const note=document.createElement("div");note.id="scope-note";note.className="scope-note";note.setAttribute("role","note");
    note.textContent=tx("ui.scope_obeys",{tabs:names(OBEYS)})+" "+tx("ui.scope_global",{tabs:names(GLOBAL)});note.title=tx("ui.scope_title");
    row.insertAdjacentElement("afterend",note);
  })();

  /* states of the selector of repositories: loading, failed with a way to try again, nothing yet */
  setInterval(()=>{
    const sel=document.getElementById("f-repo");if(!sel)return;
    let st=document.getElementById("f-repo-state");
    if(!st){st=document.createElement("span");st.id="f-repo-state";st.className="mut";st.setAttribute("role","status");sel.parentElement.appendChild(st)}
    const err=document.getElementById("err"),failed=!!err&&err.style.display==="block";
    let msg="",retry=false;
    if(typeof DATA==="undefined"||!DATA){msg=failed?tx("ui.sel_error"):tx("ui.sel_loading");retry=failed}
    else if(!DATA.repos||!DATA.repos.length)msg=tx("ui.sel_empty");
    if(st.dataset.m!==msg){st.dataset.m=msg;st.textContent=msg?msg+" ":"";if(retry){const b=document.createElement("button");b.type="button";b.textContent=tx("ui.sel_retry");b.onclick=()=>{try{tick(true)}catch(e){}};st.appendChild(b)}}
  },1500);

  /* empty and failed pages that say what to do: a button on the error bar, and a box with the next step when nothing is watched yet or nothing is open */
  const err=document.getElementById("err");
  if(err){
    const addRetry=()=>{if(err.style.display!=="block"||!err.textContent||(err.lastElementChild&&err.lastElementChild.dataset.retry))return;
      const b=document.createElement("button");b.type="button";b.dataset.retry="1";b.textContent=tx("ui.es_retry");b.style.marginLeft="10px";b.onclick=()=>{try{tick(true)}catch(e){}};err.appendChild(b)};
    new MutationObserver(addRetry).observe(err,{childList:true,characterData:true,attributes:true,attributeFilter:["style"]});
  }
  function box(host,id,html,wire){
    let b=document.getElementById(id);
    if(!html){if(b)b.remove();return}
    if(!b){b=document.createElement("div");b.id=id;b.className="es-box";b.setAttribute("role","status");host.insertAdjacentElement("afterbegin",b)}
    if(b.dataset.h!==html){b.dataset.h=html;b.innerHTML=html;wire(b)}
  }
  setInterval(()=>{
    if(typeof DATA==="undefined"||!DATA)return;
    const noRepos=!DATA.repos||!DATA.repos.length;
    ["now","repos"].forEach(t=>{const host=document.getElementById("t-"+t);if(!host)return;
      box(host,"es-"+t,noRepos?'<p>'+h(tx("ui.es_repos_empty"))+'</p><p class="mut">'+h(tx("ui.es_repos_hint"))+'</p><button type="button" data-s>'+h(tx("ui.es_open_settings"))+'</button> <button type="button" data-r>'+h(tx("ui.es_refresh"))+'</button>':"",
        b=>{b.querySelector("[data-s]").onclick=()=>showTab("cfg");b.querySelector("[data-r]").onclick=()=>{try{tick(true)}catch(e){}}})});
    const list=document.getElementById("al-list");
    if(list&&typeof ALERTS!=="undefined"&&ALERTS&&!list.querySelector(".alrow")&&!list.querySelector(".es-box"))
      box(list,"es-al",'<p>'+h(tx("ui.es_alerts_clear"))+'</p><button type="button" data-r>'+h(tx("ui.es_refresh"))+'</button>',b=>{b.querySelector("[data-r]").onclick=()=>{try{tick(true)}catch(e){}}});
    else if(list&&list.querySelector(".alrow")){const old=document.getElementById("es-al");if(old)old.remove()}
  },2000);
})();
