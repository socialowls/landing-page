const lb=document.getElementById('lb'),lbi=document.getElementById('lbi');
document.addEventListener('click',e=>{const z=e.target.closest('[data-z]');if(z){lbi.src=z.dataset.z;lb.hidden=false;return}
const c=e.target.closest('[data-copy]');if(c){navigator.clipboard&&navigator.clipboard.writeText(c.dataset.copy).then(()=>{c.textContent='Copied';setTimeout(()=>c.textContent='Copy',1500)});return}
if(e.target===lb||e.target.id==='lbx'){lb.hidden=true;lbi.src=''}});
addEventListener('keydown',e=>{if(e.key==='Escape'&&!lb.hidden){lb.hidden=true;lbi.src=''}});
