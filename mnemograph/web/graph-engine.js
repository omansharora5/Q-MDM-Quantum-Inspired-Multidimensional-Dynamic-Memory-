(function (root) {
  'use strict';
  const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
  const category = node => ['source','message'].includes(node.type) ? 'sources'
    : ['revision','version'].includes(node.type) ? 'history'
    : ['agent','task','checkpoint'].includes(node.type) ? 'people' : 'meaning';
  const depth = node => ({sources:-130,history:130,people:75,meaning:0}[category(node)]);
  const names = {ABOUT:'contains memory',WORKS_ON:'has agent',AUTHORED_BY:'written by',HAS_MESSAGE:'contains message',
    EVIDENCED_BY:'has source',SOURCED_FROM:'quotes',ASSOCIATED_WITH:'tags',HAS_CUE:'has topic',
    HAS_REVISION:'has version',RELATED_TO:'related to',SUPPORTS:'supports',SUPERSEDES:'replaces',
    CONTRADICTS:'conflicts with',REFINES:'clarifies',DUPLICATES:'duplicates',DERIVED_FROM:'based on',
    COORDINATES:'tracks',CONTEXT:'uses evidence',ASSIGNED_TO:'assigned to'};
  function layout(nodes, selectedId, pins) {
    const result = new Map(), sorted = [...nodes].sort((a,b)=>category(a).localeCompare(category(b)) || a.id.localeCompare(b.id));
    if (selectedId && nodes.some(n=>n.id===selectedId)) {
      result.set(selectedId,{x:0,y:0,z:0});
      const neighbors=sorted.filter(n=>n.id!==selectedId);
      neighbors.forEach((node,i)=>{
        const ring=Math.floor(i/12), count=Math.min(12,neighbors.length-ring*12), angle=(i%12)/count*Math.PI*2-Math.PI/2;
        const radius=290+ring*210;
        result.set(node.id,{x:Math.cos(angle)*radius,y:Math.sin(angle)*radius*.82,z:depth(node)});
      });
    } else {
      const agents=sorted.filter(n=>n.type==='agent'), hub=sorted.find(n=>n.type==='project');
      agents.forEach((node,i)=>result.set(node.id,{x:(i-(agents.length-1)/2)*210,y:-250,z:depth(node)}));
      if(hub)result.set(hub.id,{x:0,y:-95,z:0});
      const rest=sorted.filter(n=>n!==hub&&n.type!=='agent');
      const columns=rest.length>12?4:3;
      rest.forEach((node,i)=>result.set(node.id,{x:(i%columns-(Math.min(columns,rest.length)-1)/2)*230,
        y:75+Math.floor(i/columns)*145,z:depth(node)}));
    }
    for(const node of nodes)if(pins?.has(node.id))result.set(node.id,{...result.get(node.id),...pins.get(node.id)});
    return result;
  }
  function project(point, camera) {
    if(camera.mode!=='3d')return {x:point.x,y:point.y,scale:1,depth:0};
    const yaw=camera.yaw*Math.PI/180,pitch=camera.pitch*Math.PI/180;
    const x=point.x*Math.cos(yaw)+point.z*Math.sin(yaw), z=-point.x*Math.sin(yaw)+point.z*Math.cos(yaw);
    const y=point.y*Math.cos(pitch)-z*Math.sin(pitch), distance=1200;
    const depth=point.y*Math.sin(pitch)+z*Math.cos(pitch), scale=distance/Math.max(120,distance+depth);
    return {x:x*scale,y:y*scale,scale:clamp(scale,.45,2),depth};
  }
  function moveOnScreen(point, dx, dy, camera, screenScale=1) {
    const p=project(point,camera), ux=dx/(screenScale*p.scale), uy=dy/(screenScale*p.scale);
    if(camera.mode!=='3d')return {x:clamp(point.x+ux,-600,600),y:clamp(point.y+uy,-600,600),z:point.z};
    const yaw=camera.yaw*Math.PI/180,pitch=camera.pitch*Math.PI/180,z=-uy*Math.sin(pitch);
    return {x:clamp(point.x+ux*Math.cos(yaw)-z*Math.sin(yaw),-600,600),
      y:clamp(point.y+uy*Math.cos(pitch),-600,600),z:clamp(point.z+ux*Math.sin(yaw)+z*Math.cos(yaw),-360,360)};
  }
  function edge(a,b,sourceRadius=34,targetRadius=34,bend=14,labelFraction=.5) {
    const dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy)||1,ux=dx/len,uy=dy/len;
    const trimA=Math.min(sourceRadius,len*.35),trimB=Math.min(targetRadius,len*.35);
    const x1=a.x+ux*trimA,y1=a.y+uy*trimA,x2=b.x-ux*trimB,y2=b.y-uy*trimB;
    const cx=(x1+x2)/2-uy*bend,cy=(y1+y2)/2+ux*bend;
    const t=labelFraction,u=1-t;
    return {path:`M${x1},${y1}Q${cx},${cy} ${x2},${y2}`,x:u*u*x1+2*u*t*cx+t*t*x2,y:u*u*y1+2*u*t*cy+t*t*y2-9};
  }
  const api={layout,project,moveOnScreen,edge,category,relation:type=>names[type]||type.toLowerCase().replaceAll('_',' ')};
  if(typeof module==='object'&&module.exports)module.exports=api;else root.QMDMGraph=api;
})(typeof window==='object'?window:{});
