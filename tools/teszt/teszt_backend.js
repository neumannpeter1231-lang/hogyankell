/* TESZT-backend: belépés nélkül, memóriában tárolt adatbázis + élő csatorna a teszt-relén át. */
(function(){
  const gate=document.getElementById("gate"); if(gate){gate.hidden=true;gate.innerHTML="";} document.body.classList.remove("locked");
  const BOT = (new URLSearchParams(location.search).get("bot")) || "bot";
  const store = {};
  const collOf=p=>p.slice(0,p.lastIndexOf("/")), last=p=>p.slice(p.lastIndexOf("/")+1);
  const db={ doc:path=>({ async get(){const d=store[path];return{exists:!!d,id:last(path),data:()=>d};},
      async set(o){store[path]=JSON.parse(JSON.stringify(o));}, async delete(){delete store[path];},
      async update(o){store[path]=Object.assign({},store[path]||{},o);} }),
    collection:path=>{const all=()=>Object.keys(store).filter(k=>collOf(k)===path).map(k=>({id:last(k),data:()=>store[k]}));
      return {where:(f,op,v)=>({get:async()=>({docs:all().filter(d=>String((d.data()||{})[f])===String(v))})}), get:async()=>({docs:all()})};} };
  const user={id:async()=>"u_"+BOT, me:async()=>({id:"u_"+BOT,name:BOT}), isOwner:()=>false, profiles:async ids=>Object.fromEntries((ids||[]).map(i=>[i,{name:i.replace("u_","")}]))};
  const live={ open: async (code,name,onMsg,onPeers)=>{ window.__liveRecv=onMsg; window.__livePeersCb=onPeers;
      await window.__liveJoin(code,"u_"+BOT,name);
      return { send: m=>window.__liveSend(code,"u_"+BOT,m), close: ()=>window.__liveLeave(code,"u_"+BOT) }; } };
  window.HOGYANKELL_URL=location.origin+"/";
  window.claude={use:async n=>({db,user,downloads:{save:async()=>({status:"saved"})},push:{enable:async()=>({ok:false}),sync:async()=>{}},live})[n]||null};
  const s=document.createElement("script"); s.src="/app.js?v=test"; document.body.appendChild(s);
})();
