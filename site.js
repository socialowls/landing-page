const lb=document.getElementById('lb'),lbi=document.getElementById('lbi');
document.addEventListener('click',e=>{const z=e.target.closest('[data-z]');if(z){lbi.src=z.dataset.z;lb.hidden=false;return}
const c=e.target.closest('[data-copy]');if(c){navigator.clipboard&&navigator.clipboard.writeText(c.dataset.copy).then(()=>{c.textContent='Copied';setTimeout(()=>c.textContent='Copy',1500)});return}
if(e.target===lb||e.target.id==='lbx'){lb.hidden=true;lbi.src=''}});
addEventListener('keydown',e=>{if(e.key==='Escape'&&!lb.hidden){lb.hidden=true;lbi.src=''}});
document.querySelectorAll('.rail').forEach(r=>{const t=r.querySelector('.track'),p=r.querySelector('.prev'),n=r.querySelector('.next');
const u=()=>{p.hidden=t.scrollLeft<8;n.hidden=t.scrollLeft+t.clientWidth>=t.scrollWidth-8};
p.onclick=()=>t.scrollBy({left:-t.clientWidth*.8});n.onclick=()=>t.scrollBy({left:t.clientWidth*.8});
t.addEventListener('scroll',u,{passive:true});addEventListener('resize',u);t.querySelectorAll('img').forEach(i=>i.addEventListener('load',u));u()});
