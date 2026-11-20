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
