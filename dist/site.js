(()=>{
 const panels=['outdoor','indoor','floors','walk'];
 function select(name){if(!panels.includes(name))name='outdoor';for(const n of panels){document.getElementById('panel-'+n).hidden=n!==name;document.querySelector('[data-panel="'+n+'"]').setAttribute('aria-pressed',String(n===name));}for(const id of ['cs-play','ci-play']){const b=document.getElementById(id);if(b.textContent==='Pause')b.click();}if(name==='walk')window.ClevelandWalk?.activate();else window.ClevelandWalk?.pause();if(name==='floors')window.ClevelandFloors?.activate();else window.ClevelandFloors?.pause();history.replaceState(null,'','#'+name);window.dispatchEvent(new Event('resize'));}
 document.querySelectorAll('[data-panel]').forEach(b=>b.onclick=()=>select(b.dataset.panel));window.addEventListener('hashchange',()=>select(location.hash.slice(1)));select(location.hash.slice(1)||'outdoor');
})();
