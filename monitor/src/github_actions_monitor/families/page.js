/* Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
   GPL-3.0-or-later - see LICENSE */
/* window.FAM: how the page.js of a part joins the page. The server adds this file only when a part has a page.js.
   FAM.on("tab", fn(tab))        when a tab is shown (also called at once with the one that is open)
   FAM.on("data", fn(data))      when new data is drawn
   FAM.on("settings", fn(j))     when the Settings page has been built (j.groups); the sub-tab of a group is the element cfp-<id>
   FAM.on("about", fn(body))     when the About window has been drawn (body = its content)
   FAM.panel(tab, id, titleKey)  the body of a box of its own at the end of a tab (made once); titleKey is a key "ui.<part>.*"
   The page's own T(), esc(), $() are there; confirm(), alert() and prompt() are not allowed (askConfirm). */
window.FAM=(function(){
  const hooks={tab:[],data:[],settings:[],about:[]};
  const call=(fn,arg)=>{try{fn(arg)}catch(e){console.error(e)}};
  return {
    run(name,arg){(hooks[name]||[]).forEach(fn=>call(fn,arg))},
    on(name,fn){
      if(!hooks[name])return;
      hooks[name].push(fn);
      if(name==="tab")call(fn,CURTAB);
      else if(name==="data"&&DATA)call(fn,DATA);
      else if(name==="settings"&&CFG.groups.length)call(fn,{groups:CFG.groups});
    },
    panel(tab,id,titleKey){
      const host=document.getElementById("t-"+tab);
      if(!host)return null;
      let box=document.getElementById(id);
      if(!box){
        box=document.createElement("section");box.id=id;box.className="fam";
        const title=document.createElement("h2");title.setAttribute("data-i18n",titleKey);title.textContent=T(titleKey);
        const body=document.createElement("div");body.className="body";
        box.append(title,body);host.appendChild(box);
      }
      return box.querySelector(".body");
    }
  };
})();
