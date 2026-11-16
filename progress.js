(() => {
 const updated = document.getElementById('page-updated');
 const status = document.getElementById('refresh-status');
 const dot = document.getElementById('connection-dot');
 const label = document.getElementById('connection-label');
 const stamp = new Date(document.lastModified);
 const loadedAt = stamp.getTime();
 updated.textContent = Number.isNaN(stamp.getTime()) ? 'data não disponível' : stamp.toLocaleString('pt-BR');
 const clock = () => { const now = new Date(); const t = now.toLocaleTimeString('pt-BR'); document.querySelectorAll('[data-when="now"]').forEach(x => x.textContent = 'agora · ' + t); };
 clock(); setInterval(clock,1000);
 setInterval(()=>{secondsUntilCheck=Math.max(0,secondsUntilCheck-1);if(label.textContent==='PÁGINA CONECTADA')status.textContent='Página conferida · próxima consulta em '+secondsUntilCheck+' s';},1000);
 const filterButtons=[...document.querySelectorAll('#filters button')];
 const milestoneItems=[...document.querySelectorAll('#milestones .item')];
 const filterStatus=document.getElementById('filter-status');
 const filterLabels={all:'Todos',active:'Em andamento',blocked:'Aguardando',done:'Concluídos'};
 function applyFilter(button){
   const filter=button.dataset.filter;
   filterButtons.forEach(candidate=>{
     const selected=candidate===button;
     candidate.classList.toggle('active',selected);
     candidate.setAttribute('aria-pressed',String(selected));
   });
   let shown=0;
   milestoneItems.forEach(item=>{
     const visible=filter==='all'||item.dataset.status===filter;
     item.hidden=!visible;
     if(visible)shown++;
   });
   if(filterStatus)filterStatus.textContent=`Exibindo ${shown} ${shown===1?'marco':'marcos'} · filtro: ${filterLabels[filter]||'Todos'}.`;
 }
 filterButtons.forEach(button=>button.addEventListener('click',()=>applyFilter(button)));
 const initialFilter=filterButtons.find(button=>button.getAttribute('aria-pressed')==='true')||filterButtons[0];
 if(initialFilter)applyFilter(initialFilter);
 let checking=false;
 let baselineHtml=null;
 let secondsUntilCheck=20;
 async function checkForUpdate(){
   if(checking)return; checking=true; status.textContent='Consultando se há uma versão mais recente…';
   try{
     if(location.protocol==='file:') throw new Error('arquivo local');
     const response=await fetch(location.href.split('#')[0],{cache:'no-store',headers:{'Cache-Control':'no-cache'}});
     if(!response.ok)throw new Error('servidor indisponível');
     const modified=response.headers.get("Last-Modified");
     if(modified && Number.isFinite(loadedAt) && Date.parse(modified)>loadedAt+1000){status.textContent='Nova versão encontrada · atualizando…';location.reload();return;}
     const latest=await response.text();
     if(baselineHtml===null){baselineHtml=latest;}
     else if(latest!==baselineHtml){status.textContent='Nova versão encontrada · atualizando…';location.reload();return;}
     dot.className='dot ok';label.textContent='PÁGINA CONECTADA';secondsUntilCheck=20;status.textContent='Página conferida às '+new Date().toLocaleTimeString('pt-BR')+' · próxima consulta em 20 s';
   }catch(e){
     secondsUntilCheck=20;dot.className='dot';label.textContent=location.protocol==='file:'?'ARQUIVO LOCAL':'SEM CONEXÃO';
     status.textContent='Sem detecção automática do arquivo · conferido às '+new Date().toLocaleTimeString('pt-BR');
   }finally{checking=false;}
 }
 document.getElementById('check-now').addEventListener('click',checkForUpdate);
 setInterval(checkForUpdate,20000);
 checkForUpdate();
})();
