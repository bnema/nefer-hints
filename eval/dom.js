(() => {
const selector='a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=link],[role=tab],[role=menuitem],[role=checkbox],[role=radio],[role=switch],[role=option],[role=treeitem],[onclick],[tabindex]:not([tabindex="-1"])';
const visible=e=>{for(let p=e;p;p=p.parentElement){let s=getComputedStyle(p);if(s.visibility==='hidden'||s.visibility==='collapse'||s.display==='none'||+s.opacity===0)return false;}return true;};
let all=[...document.querySelectorAll('*')].filter(e=>(e.matches(selector)||getComputedStyle(e).cursor==='pointer')&&visible(e));
let candidates=all.filter(e=>!all.some(c=>c!==e&&e.contains(c)));
let boxes=[],kinds=[];
for(let e of candidates){for(let r of e.getClientRects()){
 let x1=Math.max(0,r.left),y1=Math.max(0,r.top),x2=Math.min(innerWidth,r.right),y2=Math.min(innerHeight,r.bottom);
 for(let p=e.parentElement;p;p=p.parentElement){let s=getComputedStyle(p),q=p.getBoundingClientRect();if(/hidden|clip|scroll|auto/.test(s.overflowX)){x1=Math.max(x1,q.left);x2=Math.min(x2,q.right);}if(/hidden|clip|scroll|auto/.test(s.overflowY)){y1=Math.max(y1,q.top);y2=Math.min(y2,q.bottom);}}
 if(x2-x1<4||y2-y1<4)continue;
 let hit=document.elementFromPoint((x1+x2)/2,(y1+y2)/2);if(!hit||!(hit===e||e.contains(hit)))continue;
 boxes.push([x1,y1,x2,y2]);kinds.push(e.matches('input,select,textarea')?'field':e.matches('a[href]')?'text_link':e.getAttribute('role')==='tab'?'tab':e.getAttribute('role')==='menuitem'?'menu_item':e.matches('button,[role=button]')?'icon_button':'other');
}}
return {boxes,kinds,source:'dom',notes:'Viewport CSS pixels; fullscreen mapping checked against screenshot; innermost candidates, clipping and centre hit testing. Cursor:pointer inherited descendants retained by requested innermost rule.',verified:false,viewport:{width:innerWidth,height:innerHeight,dpr:devicePixelRatio},title:document.title,url:location.href};
})()
