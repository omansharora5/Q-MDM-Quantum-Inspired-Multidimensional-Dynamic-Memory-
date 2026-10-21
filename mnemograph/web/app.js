const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icon = (name) => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
const colors = {project:'#c4f375',decision:'#c4f375',fact:'#78cbd3',episode:'#b9a0e8',procedure:'#e9b57b',source:'#9ca9bc',cue:'#769e84',agent:'#d2dba9',task:'#e7bb93',message:'#92cdd4',version:'#c6a4e6',core:'#c4f375',resource:'#e9b57b',hypothesis:'#dfa4b7',insight:'#a7c8ee'};
const labels = {conversation:['Conversations','Read the messages that became memory.','Conversations'],experiments:['Experiments','Compare measured retrieval behavior on saved local runs.','Experiments'],graph:['Memory explorer','See what your agents know. Follow how it connects.','Memory graph'],flow:['Memory flow','The full journey, read live from your service.','Memory flow'],agents:['Agents','Independent agents. One shared thread of knowledge.','Agents'],context:['Context & handoffs','Follow what agents retrieve and what they pass forward.','Context & handoffs'],integrations:['Agent setup guide','Bring persistent memory into your existing workflow.','Agent setup guide']};
let token = sessionStorage.getItem('mnemo-key') || '';
let state, graphData = {nodes:[],edges:[]}, selected, focusMode = false, packet;
let zoom = 1, pan = {x:0,y:0}, rotation = 0, paused = matchMedia('(prefers-reduced-motion: reduce)').matches;
let graphElements = [], edgeElements = [], loading = false, lastRevision = -1, polling = false;
let activeIntegration = 'codex', lastPollError = false;
let dataset = 'personal-assistant', timeline = {messages:[],changes:[]}, listMode=false, editingRecord=null, extraction=null, extractionSupported=null;
let nodeHistory=[], positions=new Map(), changeEdges=new Set(), removedEdges=[], graphVersion=-1, inspectorSignature='', packetIsActive=false;
let flowStory=null,flowStage=0,flowPlaying=false,flowTimer=null;
let spaceMode='2d', pitch=-10, pins=new Map(), pinScope='', setupInfo=null, setupAgent='developer', suppressClickUntil=0, edgeFilter='all';
const sampleLabels={'personal-assistant':'Personal assistant','camera-lab':'Camera lab','team-planning':'Team planning'};
const relationGroups={
  evidence:new Set(['SUPPORTS','EVIDENCED_BY','SUPPORTED_BY','SOURCED_FROM','DERIVED_FROM']),
  context:new Set(['ABOUT','CONTEXT','HAS_CUE','ASSOCIATED_WITH','RELATED_TO']),
  ownership:new Set(['WORKS_ON','AUTHORED_BY','COORDINATES','ASSIGNED_TO']),
  history:new Set(['HAS_REVISION','SUPERSEDES','REFINES','DUPLICATES']),
  conflict:new Set(['CONTRADICTS'])
};
function relationMatches(edge){return edgeFilter==='all'||relationGroups[edgeFilter]?.has(edge.type);}
const scoped = path => path + (dataset ? '?dataset='+encodeURIComponent(dataset) : '');

async function api(path, method='GET', data) {
  const response = await fetch('/api' + path, {method, headers:{Authorization:`Bearer ${token}`, ...(data ? {'Content-Type':'application/json'} : {})},body:data ? JSON.stringify(data) : undefined});
  const result = await response.json();
  if (!response.ok) {
    const detail = typeof result.detail === 'string' ? result.detail : JSON.stringify(result.detail);
    if (response.status === 401 && !$('#login-dialog').open) $('#login-dialog').showModal();
    const error=new Error(detail || 'The memory service did not respond.'); error.status=response.status; throw error;
  }
  return result;
}

function notify(message) {
  $('#toast').textContent = message;
  $('#toast').hidden = false;
  clearTimeout(notify.timer);
  notify.timer = setTimeout(() => $('#toast').hidden = true, 4500);
}

function fail(error) {
  $('#global-error').textContent = error.message;
  $('#global-error').hidden = false;
}

async function action(button, work) {
  button.disabled = true;
  try { await work(); } catch (error) { fail(error); }
  finally { button.disabled = false; }
}

function currentPage() { return labels[location.hash.slice(1)] ? location.hash.slice(1) : 'graph'; }
function route() {
  const page = currentPage();
  scrollTo(0,0);
  for (const [key, values] of Object.entries(labels)) {
    $(`#page-${key}`).hidden = page !== key;
    const link = $(`[data-page="${key}"]`);
    link.classList.toggle('active', page === key);
    if (page === key) link.setAttribute('aria-current','page'); else link.removeAttribute('aria-current');
  }
  $('#page-title').innerHTML = esc(labels[page][0]) + '<span>.</span>';
  $('#page-subtitle').textContent = labels[page][1];
  $('#breadcrumb').textContent = labels[page][2];
  $('#add-memory').hidden = !['graph','conversation','context'].includes(page);
  if (page==='experiments' && token) loadExperiments();
  if (page==='flow' && token) loadFlow(); else stopFlowTimer();
}
addEventListener('hashchange', route);
route();

function time(value) {
  return value ? new Date(value).toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit'}) : 'Not recorded';
}

async function fetchExtraction() {
  // Older servers have no /api/extraction; probe the API schema once so the graceful path never 404s.
  if (extractionSupported === null) { try { extractionSupported = Object.hasOwn((await api('/openapi.json')).paths || {}, '/api/extraction'); } catch { extractionSupported = false; } }
  if (!extractionSupported) return null;
  try { return (await api(scoped('/extraction'))).messages || []; } catch { return null; }
}

async function refresh(force=false) {
  if (!token) return;
  if (polling) {
    if (force) { await polling; return refresh(true); }
    return;
  }
  let finishRefresh;
  polling = new Promise(resolve => finishRefresh = resolve);
  try {
    const next = await api(scoped('/state'));
    state = next;
    if(!setupInfo){try{setupInfo=await api('/setup');}catch{setupInfo={};}}
    renderSetup();
    $('#connection-status').innerHTML = '<i class="status-dot"></i>Service online';
    if (lastPollError) $('#global-error').hidden = true;
    lastPollError = false;
    $('#workspace-name').textContent = state.project;
    $('#actor-label').textContent = state.agent;
    $('.local-label').textContent=location.host;
    $('#store-label').textContent = state.storage === 'falkordb' ? 'FalkorDB · persistent graph' : setupInfo?.local_setup===false?'SQLite · service storage':'SQLite · local storage';
    $('#footer-storage').textContent = state.storage === 'falkordb' ? 'FalkorDB · graph backend' : setupInfo?.local_setup===false?'SQLite · remote service':'Local SQLite · replaceable storage';
    $('#memory-count').textContent = state.memories.length;
    $('#nav-count').textContent = state.memories.length;
    $('#agent-count').innerHTML = state.agents.filter(a => a.status === 'active').length + `<em> / ${state.agents.length}</em>`;
    $('#revision-count').textContent = String(state.memory_revision ?? state.revision).padStart(3,'0');
    renderAgents();
    if (force || state.revision !== lastRevision) {
      const firstGraph = graphVersion < 0;
      const nextGraph = await api(scoped('/graph'));
      trackGraphChange(nextGraph); graphData = nextGraph;
      timeline = await api(scoped('/timeline'));
      extraction = await fetchExtraction();
      renderTimeline();
      lastRevision = state.revision;
      if(selected) selected=graphData.nodes.find(n=>n.id===selected.id);
      renderGraph(); renderActivity(); renderContext();
      if(firstGraph) fitGraph();
      if (selected) { const updated=graphData.nodes.find(n=>n.id===selected.id); if(updated) inspect(updated,false,false); }
      $('#dataset-note').textContent = dataset ? `${sampleLabels[dataset]||dataset} · ${state.memories.length} sourced memories. Generated samples are synthetic. Agent presence remains real.` : 'All records this credential can access. Dataset labels distinguish sample memories.';
    }
  } catch (error) {
    $('#connection-status').textContent = 'Service unavailable';
    if (!lastPollError) fail(error);
    lastPollError = true;
  } finally { polling = null; finishRefresh(); }
}

$('#login-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = event.submitter;
  button.disabled = true;
  token = $('#api-key').value.trim();
  try {
    await api('/state');
    sessionStorage.setItem('mnemo-key', token);
    $('#api-key').value = '';
    $('#login-error').textContent = '';
    $('#login-dialog').close();
    await refresh(true);
    if(setupInfo?.local_setup!==false)await api('/connect','POST',{platform:'dashboard',context:'Exploring shared memory'});
    if (currentPage()==='flow') loadFlow();
  } catch (error) { $('#login-error').textContent = error.message; token = ''; }
  finally { button.disabled = false; }
});
$('#login-dialog').addEventListener('cancel', event => event.preventDefault());
$('#signout').onclick = () => { sessionStorage.removeItem('mnemo-key'); token = ''; $('#login-dialog').showModal(); };
$('#workspace-button').onclick = () => { location.hash = 'integrations'; };

function renderActivity() {
  const events = state.events.slice(-5).reverse();
  $('#event-count').textContent = state.events.length;
  $('#activity').innerHTML = events.length ? events.map(event => `<div class="activity-row"><span class="event-actor">${esc(event.actor)}</span><span class="event-action">${esc(event.action.replaceAll('.',' / '))}</span><time datetime="${esc(event.at)}">${time(event.at)}</time></div>`).join('') : '<div class="activity-empty">No memory activity yet. Connect an agent or save your first memory.</div>';
}

function renderAgents() {
  const names = {active:'Active heartbeat',idle:'Idle · heartbeat expired',not_connected:'Not connected'};
  $('#agents-list').innerHTML = state.agents.map(agent => `<article class="agent-card panel"><span class="agent-status">${agent.status === 'active' ? '<i class="status-dot"></i> ' : ''}${names[agent.status]}</span><div class="agent-logo">${esc(agent.id[0].toUpperCase())}</div><h2>${esc(agent.id)}</h2><p>${esc(agent.context || 'Ready for a scoped connection. No authenticated traffic observed.')}</p><dl><dt>Platform</dt><dd>${esc(agent.platform || 'Unassigned')}</dd><dt>Last heartbeat</dt><dd>${agent.last_seen ? time(agent.last_seen) : 'Never'}</dd><dt>Project</dt><dd>${esc(state.project)}</dd></dl><a class="secondary button-link" href="#integrations">Connection guide ↗</a></article>`).join('');
  const select = $('#handoff-agent');
  const previous = select.value;
  select.innerHTML = state.agents.map(agent => `<option value="${esc(agent.id)}">${esc(agent.id)}</option>`).join('');
  if (state.agents.some(agent => agent.id === previous)) select.value = previous;
  else if (state.agents.some(agent => agent.id === 'developer')) select.value = 'developer';
  updateSetupStatus();
}

function renderContext() {
  $('#traces-list').innerHTML = state.traces.length ? state.traces.map(trace => {
    const data = trace.payload;
    return `<article class="trace-card panel"><header><span>${esc(trace.actor)} · RECALL</span><time>${time(trace.updated_at)}</time></header><h3>${esc(data.query)}</h3><div class="trace-stats"><span>${data.handles.length} selected handles</span><span>${data.visited} candidates visited</span><span>${data.context_chars} / ${data.budget_chars} characters</span><span>Read revision ${data.revision}</span></div>${data.handles.map(handle => `<div class="trace-path">${esc(handle.title)}<small>${esc(handle.path.join(' → '))}${handle.relations.length ? ' · '+esc(handle.relations.join(' / ')) : ' · direct seed'}</small></div>`).join('')}${data.insufficient_evidence ? '<p class="quiet-note">Insufficient evidence. No memory matched this query.</p>' : ''}<details><summary>Inspect returned context · ${esc(data.strategy)}</summary><pre>${esc(data.context)}</pre><p>${esc(data.warning)}</p></details></article>`;
  }).join('') : '<div class="panel information"><h2>No recall trace yet</h2><p>Use “Follow a thought” on the memory graph, or let an agent call memory_recall. Its query and selected evidence will appear here.</p><a class="secondary button-link" href="#graph">Try a recall ↗</a></div>';
  $('#tasks-list').innerHTML = state.tasks.length ? state.tasks.map(task => `<article class="panel task-card"><h3>${esc(task.payload.title)}</h3><p>${esc(task.payload.context)}</p><small>${esc(task.actor)} → ${esc(task.payload.target_agent)} · v${task.version}</small><label class="sr-only" for="status-${esc(task.id)}">Task status</label><select id="status-${esc(task.id)}" data-task-id="${esc(task.id)}" ${[task.actor,task.payload.target_agent].includes(state.agent) ? '' : 'disabled'}>${['open','in_progress','blocked','completed'].map(status => `<option value="${status}" ${task.payload.status===status?'selected':''}>${status.replaceAll('_',' ')}</option>`).join('')}</select></article>`).join('') : '<p class="quiet-note">Handoffs will appear here after an agent assigns work.</p>';
  for (const select of document.querySelectorAll('[data-task-id]')) select.onchange = async () => {
    const task = state.tasks.find(item => item.id === select.dataset.taskId);
    try { await api('/handoffs/'+task.id,'PUT',{...task.payload,status:select.value,expected_version:task.version,idempotency_key:crypto.randomUUID()}); await refresh(true); }
    catch (error) { fail(error); await refresh(true); }
  };
}

$('#handoff-form').addEventListener('submit', async event => {
  event.preventDefault(); const form = event.target, values = Object.fromEntries(new FormData(form));
  values.memory_ids = values.memory_ids.split(',').map(id => id.trim()).filter(Boolean);
  values.idempotency_key = form.dataset.retryKey || crypto.randomUUID();
  form.dataset.retryKey = values.idempotency_key;
  event.submitter.disabled = true;
  try { await api('/handoffs','POST',values); form.reset(); delete form.dataset.retryKey; form.querySelector('.form-message').textContent='Handoff saved.'; await refresh(true); }
  catch (error) { form.querySelector('.form-message').textContent=error.message; }
  finally { event.submitter.disabled = false; }
});
$('#handoff-form').addEventListener('input', event => delete event.currentTarget.dataset.retryKey);

function edgeKey(e) { return [e.source,e.type,e.target].join('|'); }
function trackGraphChange(next) {
  const revision = next.memory_revision ?? next.revision;
  if (revision === graphVersion) {changeEdges.clear();removedEdges=[];return;}
  // First paint has no known baseline; highlight nothing as added/removed.
  if (graphVersion < 0) {changeEdges.clear();removedEdges=[];graphVersion=revision;$('#graph-change').textContent=`${next.nodes.length} nodes · live knowledge revision ${revision}`;return;}
  const old=new Set(graphData.edges.map(edgeKey)), fresh=new Set(next.edges.map(edgeKey));
  changeEdges=new Set(next.edges.filter(e=>!old.has(edgeKey(e))).map(edgeKey));
  removedEdges=graphData.edges.filter(e=>!fresh.has(edgeKey(e)));
  $('#graph-change').textContent=`${changeEdges.size} links added · ${removedEdges.length} removed · revision ${revision}`;
  graphVersion=revision;
}
function visibleNodes() {
  const layer=$('#facet').value;
  if (focusMode && selected) {
    const ids=new Set([selected.id]);
    // The first view shows direct relationships; each dimension opens its wider neighborhood.
    if(layer!=='all') (selected.facets?.[layer] || []).forEach(id=>ids.add(id));
    if(layer==='all') graphData.edges.filter(e=>e.source===selected.id || e.target===selected.id).forEach(e=>{ids.add(e.source);ids.add(e.target);});
    return graphData.nodes.filter(n=>ids.has(n.id));
  }
  // Keep the overview legible; source, cue, message and revision records open within each node.
  if(layer==='all') return graphData.nodes.filter(n=>n.type!=='revision'&&n.type!=='version'&&(n.type==='project'||n.type==='task'||n.type==='agent'||n.record?.kind==='memory'));
  const ids=new Set();
  graphData.nodes.filter(n=>n.record?.kind==='memory' || n.type==='project').forEach(n=>{ids.add(n.id);(n.facets?.[layer] || []).forEach(id=>ids.add(id));});
  return graphData.nodes.filter(n=>ids.has(n.id));
}
function labelLines(text, max=20) {
  // Two lines max, word-aware, hard-break long words, ellipsis when the label keeps going.
  const lines=[];
  for (const word of String(text).trim().split(/\s+/)) {
    if (!word) continue;
    if (word.length > max) { lines.push(...(word.match(new RegExp(`.{1,${max}}`,'g')) || [])); continue; }
    const last=lines[lines.length-1];
    if (last && last.length<max && last.length+1+word.length<=max) lines[lines.length-1]=last+' '+word;
    else lines.push(word);
  }
  if (!lines.length) lines.push(String(text).slice(0,max));
  const shown=lines.slice(0,2);
  if (lines.length>2) shown[1]=(shown[1].length>=max?shown[1].slice(0,max-1):shown[1])+'…';
  return shown;
}
function renderGraph() {
  const nodes=visibleNodes(), visible=new Set(nodes.map(n=>n.id));
  const width=$('#graph-canvas').clientWidth || 900, height=$('#graph-canvas').clientHeight || 590;
  $('#graph').setAttribute('viewBox',`0 0 ${width} ${height}`);
  loadPins();
  const layout=QMDMGraph.layout(nodes,focusMode?selected?.id:null,pins);
  graphElements=nodes.map(n=>({...n,...layout.get(n.id)}));
  edgeElements=graphData.edges.filter(e=>visible.has(e.source)&&visible.has(e.target)&&relationMatches(e));
  const ghosts=removedEdges.filter(e=>visible.has(e.source)&&visible.has(e.target)&&relationMatches(e)).map(e=>({...e,removed:true}));
  edgeElements.push(...ghosts);
  $('#graph-edges').innerHTML=edgeElements.map((e,i)=>{
    const a=graphData.nodes.find(n=>n.id===e.source),b=graphData.nodes.find(n=>n.id===e.target);
    return `<g class="connection" data-connection="${i}" tabindex="0" role="button" aria-label="Explain connection: ${esc(a?.label)} ${esc(QMDMGraph.relation(e.type))} ${esc(b?.label)}"><path class="graph-edge ${e.removed?'edge-removed':changeEdges.has(edgeKey(e))?'edge-added':''}" data-edge="${i}" marker-end="url(#edge-arrow)"/><path class="edge-hit"/><text class="edge-label">${esc(QMDMGraph.relation(e.type))}</text></g>`;
  }).join('');
  $('#graph-nodes').innerHTML=graphElements.map((node,i)=>{
    const color=colors[node.type]||'#aab7c7', label=node.label||node.id, lines=labelLines(node.type==='revision'?`Version ${node.record?.version||''}`:label);
    const versions=node.record?.kind==='memory'?node.record?.version||0:0, versionHint=focusMode||node.type==='revision'||versions<2?'':versions+'v';
    return `<g class="node node-${esc(node.type)} ${selected?.id===node.id?'selected':''}" data-index="${i}" tabindex="0" role="button" aria-label="Inspect ${esc(node.type)}: ${esc(label)}"><title>${esc(label)}. ${esc(node.latest_message?.text||'No source message recorded')}</title><circle class="node-hit" r="42" fill="transparent"/><circle class="node-circle" r="30" fill="#161e25" stroke="${color}"/><text class="node-kind" x="0" y="4" text-anchor="middle">${esc(node.type)}</text>${versionHint?`<text class="node-version" x="25" y="-20" text-anchor="middle">${versionHint}</text>`:''}${lines.map((line,j)=>`<text class="node-label" x="0" y="${47+j*16}" text-anchor="middle">${esc(line)}</text>`).join('')}</g>`;
  }).join('');
  graphElements.forEach((node,i)=>{node.element=$(`#graph-nodes [data-index="${i}"]`);node.element.onclick=()=>{if(performance.now()>suppressClickUntil)inspect(node,true);};node.element.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();inspect(node,true);}};node.element.onmouseenter=()=>hoverEmphasis(node);node.element.onmouseleave=hoverClear;node.element.onfocus=()=>hoverEmphasis(node);node.element.onblur=hoverClear;});
  edgeElements.forEach((e,i)=>{e.element=$(`[data-edge="${i}"]`);e.group=$(`[data-connection="${i}"]`);e.group.onclick=()=>explainRelation(e);e.group.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();explainRelation(e);}};});
  $('#empty-graph').hidden=(state?.memories.length||0)>0;
  $('#graph').classList.toggle('focused',focusMode);
  $('#graph').classList.toggle('graph-filtered',edgeFilter!=='all');
  $('#graph').classList.toggle('motion-paused',paused);
  $('#graph-heading').textContent=focusMode && selected ? selected.label : 'A memory, with its evidence.';
  $('#graph-caption-text').textContent=focusMode ? `${$('#facet').selectedOptions[0].textContent} · ${Math.max(0,nodes.length-1)} records · ${edgeElements.length} connections` : `${nodes.length} overview nodes · ${graphData.nodes.length} total records · open a node for evidence`;
  $('#graph-path').textContent=focusMode && selected ? `All memories / ${selected.label} / ${$('#facet').selectedOptions[0].textContent}`:'All memories';
  $('#graph-back').disabled=!focusMode;
  $('#all-view').classList.toggle('selected',!focusMode);
  $('#focus-view').classList.toggle('selected',focusMode);
  const listNodes=!focusMode&&$('#facet').value==='all'?graphData.nodes:nodes;
  $('#graph-list').innerHTML=listNodes.map(n=>{const links=graphData.edges.filter(e=>e.source===n.id||e.target===n.id);return `<button class="list-node" data-node="${esc(n.id)}"><span class="node-type">${esc(n.type)}</span><b>${esc(n.label)}</b><small>${links.length} connections · ${esc(time(n.updated_at))}</small><span>${esc(n.latest_message?.text||'No source message recorded')}</span></button>`;}).join('') || '<p class="quiet-note">No records in this dimension.</p>';
  $('#graph-list').querySelectorAll('[data-node]').forEach(button=>button.onclick=()=>inspect(graphData.nodes.find(n=>n.id===button.dataset.node),true));
  highlightPacket();draw();
}
function camera(){return {mode:spaceMode,yaw:rotation,pitch};}
function loadPins(){
  const key=`qmdm-layout:${state?.tenant}:${state?.project}:${dataset}`;
  if(key===pinScope)return;pinScope=key;pins=new Map();
  try{for(const [id,p]of JSON.parse(sessionStorage.getItem(key)||'[]'))if(['x','y','z'].every(k=>Number.isFinite(p[k])))pins.set(id,p);}catch{}
}
function savePins(){sessionStorage.setItem(pinScope,JSON.stringify([...pins]));}
function explainRelation(edge){
  const a=graphData.nodes.find(n=>n.id===edge.source),b=graphData.nodes.find(n=>n.id===edge.target);
  if(!a||!b)return;
  $('#relation-detail').hidden=false;
  $('#relation-detail').innerHTML=`<span>${edge.removed?'Removed relationship':'Relationship'}</span><b>${esc(a.label)}</b><strong>→ ${esc(QMDMGraph.relation(edge.type))} →</strong><b>${esc(b.label)}</b><button class="text-button" id="close-relation" aria-label="Close relationship explanation">×</button><small>${esc(edge.type)} · arrows follow the stored source-to-target direction</small>`;
  $('#close-relation').onclick=()=>$('#relation-detail').hidden=true;
}
function draw() {
  const nodes=new Map(),cx=$('#graph-canvas').clientWidth/2,cy=$('#graph-canvas').clientHeight/2;
  $('#graph').dataset.viewMode=spaceMode;$('#graph').dataset.cameraYaw=rotation;$('#graph').dataset.cameraPitch=pitch;
  const projected=graphElements.map(node=>({node,p:QMDMGraph.project(node,camera())})).sort((a,b)=>b.p.depth-a.p.depth);
  for(const {node,p} of projected){node.sx=cx+p.x;node.sy=cy+p.y;node.depthScale=p.scale;
    node.element.setAttribute('transform',`translate(${node.sx},${node.sy}) scale(${p.scale})`);
    for(const key of ['x','y','z'])node.element.dataset['world'+key.toUpperCase()]=node[key];
    node.element.classList.toggle('pinned',pins.has(node.id));$('#graph-nodes').append(node.element);nodes.set(node.id,node);}
  for(const e of edgeElements){const a=nodes.get(e.source),b=nodes.get(e.target),geometry=QMDMGraph.edge({x:a.sx,y:a.sy},{x:b.sx,y:b.sy},34*a.depthScale,37*b.depthScale,14,selected?.id===e.source ? .7 : selected?.id===e.target ? .3 : .5);
    e.element.setAttribute('d',geometry.path);e.group.querySelector('.edge-hit').setAttribute('d',geometry.path);
    const label=e.group.querySelector('.edge-label');label.setAttribute('x',geometry.x);label.setAttribute('y',geometry.y);
    e.group.classList.toggle('near-selected',Boolean(selected&&(selected.id===e.source||selected.id===e.target)));
  }
  $('#graph-camera').setAttribute('transform',`translate(${pan.x},${pan.y}) translate(${cx} ${cy}) scale(${zoom}) translate(${-cx} ${-cy})`);
}
function setSpace(mode){
  spaceMode=mode;if(mode==='3d'&&rotation===0)rotation=20;
  $('#space-controls').hidden=mode!=='3d';$('#depth-guide').hidden=mode!=='3d';$('#orbit').value=rotation;$('#tilt').value=pitch;
  for(const value of ['2d','3d']){const button=$('#space-'+value);button.classList.toggle('selected',mode===value);button.setAttribute('aria-pressed',String(mode===value));}
  $('#graph-instructions').innerHTML=mode==='3d'?'<b>3D is the same graph:</b> drag the background to orbit, Shift-drag to pan, and drag a node to place it. Depth separates work, people, evidence, and history. Select an arrow to read its relationship.':'<b>How to read it:</b> Select a memory to open its evidence and dimensions. Click an arrow to read its meaning, or filter connections by type.';
  $('.graph-footnote').textContent=mode==='3d'?'Drag to orbit · Shift-drag to pan · Scroll to zoom':'Drag nodes to place · Drag background to pan · Scroll to zoom';
  renderGraph();fitGraph();
}
$('#space-2d').onclick=()=>setSpace('2d');$('#space-3d').onclick=()=>setSpace('3d');
$('#arrange-graph').onclick=()=>{pins.clear();savePins();renderGraph();fitGraph();notify('Automatic arrangement restored.');};
function fitGraph(){
  if(!graphElements.length)return;
  const projected=graphElements.map(n=>QMDMGraph.project(n,camera())),xs=projected.map(n=>n.x),ys=projected.map(n=>n.y),left=Math.min(...xs)-72,right=Math.max(...xs)+72,top=Math.min(...ys)-44,bottom=Math.max(...ys)+80;
  const width=$('#graph-canvas').clientWidth,height=$('#graph-canvas').clientHeight;
  // Gutter bands keep the caption (top) and the controls plus footnote (bottom) clear of the circles and labels.
  const pad={left:34,right:34,top:92,bottom:108},areaW=Math.max(140,width-pad.left-pad.right),areaH=Math.max(140,height-pad.top-pad.bottom);
  zoom=Math.max(.3,Math.min(1,areaW/(right-left),areaH/(bottom-top)));
  const cx=width/2,cy=height/2,modelW=(right-left)*zoom,modelH=(bottom-top)*zoom;
  pan={x:pad.left+(areaW-modelW)/2-cx-zoom*left,y:pad.top+(areaH-modelH)/2-cy-zoom*top};
  draw();
}
new ResizeObserver(()=>{if(currentPage()==='graph'){renderGraph();fitGraph();}}).observe($('#graph-canvas'));
function highlightPacket() {
  const ids = new Set(packet?.handles.flatMap(handle => handle.path) || []);
  for (const handle of packet?.handles || []) {
    for (const relation of handle.relations) {
      if (relation.startsWith('cue:')) {
        graphData.nodes.filter(node=>node.type==='cue' && node.label===relation.slice(4)).forEach(node=>ids.add(node.id));
      }
    }
  }
  for (const node of graphElements) node.element.classList.toggle('dimmed', ids.size>0 && !ids.has(node.id) && node.type!=='project');
  for (const edge of edgeElements) edge.element.classList.toggle('highlight',ids.has(edge.source) && ids.has(edge.target));
  packetIsActive=ids.size>0;
}
function hoverEmphasis(node) {
  if(packetIsActive)return;   // a recall packet keeps priority over hover
  const lit=new Set([node.id]);
  for(const e of edgeElements)if(e.source===node.id||e.target===node.id){lit.add(e.source);lit.add(e.target);}
  for(const n of graphElements)n.element?.classList.toggle('hover-dim',!lit.has(n.id));
  for(const e of edgeElements){const near=e.source===node.id||e.target===node.id;e.element?.classList.toggle('hover-lit',near);e.element?.classList.toggle('hover-dim',!near);}
}
function hoverClear(){
  // Blur fires during renderGraph teardown, before elements are wired; optional chaining covers that window.
  for(const n of graphElements)n.element?.classList.remove('hover-dim');
  for(const e of edgeElements)e.element?.classList.remove('hover-lit','hover-dim');
}

async function inspect(node,drill=false,remember=true) {
  if(!node)return;
  const signature=JSON.stringify(node);
  if(!drill&&!remember&&signature===inspectorSignature)return;
  inspectorSignature=signature;
  if(drill && remember && selected?.id!==node.id) nodeHistory.push(selected?.id||null);
  selected=node;$('.inspector').classList.add('open');
  if(drill){focusMode=true;zoom=1;pan={x:0,y:0};renderGraph();fitGraph();}
  for(const item of graphElements)item.element.classList.toggle('selected',item.id===node.id);
  const linked=graphData.edges.filter(e=>e.source===node.id||e.target===node.id).map(e=>({edge:e,node:graphData.nodes.find(n=>n.id===(e.source===node.id?e.target:e.source))})).filter(x=>x.node);
  const m=node.record?.kind==='memory'?node.record:null,msg=node.latest_message;
  $('#inspector-content').innerHTML=`<span class="node-type">${esc(node.type)} ${m?.payload.synthetic?'· synthetic':''}</span><h2>${esc(node.label)}</h2><p>${esc(m?.payload.content || node.detail || 'Inspect the connected evidence in each dimension.')}</p><div class="latest-message"><span class="tiny-label">LATEST SOURCE MESSAGE</span>${msg?`<blockquote>${esc(msg.text)}</blockquote><small>${esc(msg.speaker)} · ${esc(msg.platform)}<br><time>${esc(time(msg.at))}</time></small>`:'<p>No source message recorded for this node.</p>'}</div><div class="inspector-details"><dl><dt>Updated</dt><dd>${esc(time(node.updated_at||m?.updated_at))}</dd><dt>Node ID</dt><dd>${esc(node.id)}</dd>${node.source_hash?`<dt>Source hash</dt><dd>${esc(node.source_hash)}</dd>`:''}${m?`<dt>Source trust</dt><dd>${esc(m.payload.source_trust||'not recorded')}</dd><dt>Source time</dt><dd>${esc(time(node.latest_message?.at))}</dd><dt>Author</dt><dd>${esc(m.actor)}</dd><dt>Version</dt><dd>${m.version}</dd><dt>Status</dt><dd>${esc(m.payload.status)}</dd>`:''}</dl></div><div class="facet-buttons">${['semantic','temporal','provenance','collaboration'].map(f=>`<button class="secondary" data-layer="${f}">${f} <small>${(node.facets?.[f]||[]).length}</small></button>`).join('')}</div>${m?'<button class="secondary" id="edit-memory">Edit with version check</button><button class="secondary" id="expand-evidence">Read evidence & history</button><div id="evidence-content"></div>':''}<details class="adjacency"><summary>Connected records · ${linked.length}</summary>${linked.map((x,i)=>`<button class="result-handle" data-related="${i}"><span>${esc(x.node.label)}<small>${esc(x.edge.type)}</small></span>→</button>`).join('')||'<p>No linked records.</p>'}</details>`;
  $('#inspector-content').querySelectorAll('[data-layer]').forEach(b=>b.onclick=()=>{$('#facet').value=b.dataset.layer;focusMode=true;renderGraph();fitGraph();});
  $('#inspector-content').querySelectorAll('[data-related]').forEach(b=>b.onclick=()=>inspect(linked[Number(b.dataset.related)].node,true));
  if(m){if(node.type==='revision')$('#edit-memory').remove();else $('#edit-memory').onclick=()=>openMemoryEditor(m);$('#expand-evidence').onclick=e=>action(e.currentTarget,async()=>{
    const full=await api('/memories/'+encodeURIComponent(m.id)+'?version='+m.version);if(selected?.id!==node.id)return;
    const source=full.payload.source;
    $('#evidence-content').innerHTML=`<div class="source-block"><b>${esc(source.title)}</b><p>${esc(source.text)}</p><small>${esc(source.uri)}<br>${esc(time(source.occurred_at))}${full.source_hash?'<br>SHA-256 '+esc(full.source_hash):''}</small></div><p class="quiet-note">History: ${(full.history||[]).map(x=>`v${x.version} · ${esc(x.actor)} · ${esc(time(x.at||x.updated_at))}`).join('<br>')}</p>`;
  });}
}
$('#all-view').onclick = () => {focusMode=false;$('#facet').value='all';edgeFilter='all';$('#relation-filter').value='all';$('#all-view').classList.add('selected');$('#focus-view').classList.remove('selected');renderGraph();fitGraph();};
$('#focus-view').onclick = () => {if (!selected) return notify('Select a graph node first.');focusMode=true;$('#focus-view').classList.add('selected');$('#all-view').classList.remove('selected');renderGraph();fitGraph();};
$('#facet').onchange=()=>{renderGraph();fitGraph();};
$('#relation-filter').onchange=event=>{edgeFilter=event.target.value;$('#relation-detail').hidden=true;renderGraph();fitGraph();};
$('#graph-back').onclick=()=>{const id=nodeHistory.pop();if(id){const n=graphData.nodes.find(n=>n.id===id);if(n)inspect(n,true,false);}else {focusMode=false;selected=null;$('#facet').value='all';renderGraph();fitGraph();}};
$('#list-view').onclick=()=>{listMode=!listMode;$('#graph-list').hidden=!listMode;$('#graph').toggleAttribute('hidden',listMode);$('.graph-caption').hidden=listMode;$('#empty-graph').hidden=listMode||(state?.memories.length||0)>0;$('#list-view').setAttribute('aria-pressed',String(listMode));$('#list-view').classList.toggle('selected',listMode);};
for(const [id,x,y]of [['pan-left',60,0],['pan-right',-60,0],['pan-up',0,60],['pan-down',0,-60]])$('#'+id).onclick=()=>{pan.x+=x;pan.y+=y;draw();};
$('#pause').onclick=()=>{paused=!paused;$('#pause').textContent=paused?'▷':'Ⅱ';$('#pause').setAttribute('aria-label',paused?'Resume graph animation':'Pause graph animation');$('#graph').classList.toggle('motion-paused',paused);draw(performance.now());};
$('#orbit').oninput=event=>{rotation=Number(event.target.value);draw();};
$('#tilt').oninput=event=>{pitch=Number(event.target.value);draw();};
$('#zoom-in').onclick=()=>{zoom=Math.min(2.5,zoom+.15);draw(performance.now());};
$('#zoom-out').onclick=()=>{zoom=Math.max(.3,zoom-.15);draw(performance.now());};
$('#reset-graph').onclick=()=>{zoom=1;pan={x:0,y:0};rotation=0;pitch=-10;$('#orbit').value=0;$('#tilt').value=pitch;edgeFilter='all';$('#relation-filter').value='all';packet=null;focusMode=false;$('#all-view').classList.add('selected');$('#focus-view').classList.remove('selected');renderGraph();fitGraph();};
$('#graph-canvas').addEventListener('wheel',event=>{if(event.target.closest('button,input,select'))return;event.preventDefault();zoom=Math.max(.3,Math.min(2.5,zoom-event.deltaY*.001));draw(performance.now());},{passive:false});
let drag;
$('#graph').addEventListener('pointerdown',event=>{
  if(event.button!==0||event.target.closest('.connection'))return;
  const element=event.target.closest('.node'),node=element?graphElements[Number(element.dataset.index)]:null;
  drag={x:event.clientX,y:event.clientY,pan:{...pan},yaw:rotation,pitch,node,point:node?{x:node.x,y:node.y,z:node.z}:null,moved:false,shift:event.shiftKey};
  event.currentTarget.setPointerCapture(event.pointerId);
});
$('#graph').addEventListener('pointermove',event=>{
  if(!drag)return;const dx=event.clientX-drag.x,dy=event.clientY-drag.y;
  if(Math.hypot(dx,dy)<4&&!drag.moved)return;drag.moved=true;
  if(drag.node){const p=QMDMGraph.moveOnScreen(drag.point,dx,dy,camera(),zoom);Object.assign(drag.node,p);pins.set(drag.node.id,p);}
  else if(spaceMode==='3d'&&!drag.shift){rotation=Math.max(-180,Math.min(180,drag.yaw+dx*.45));pitch=Math.max(-65,Math.min(65,drag.pitch+dy*.35));$('#orbit').value=rotation;$('#tilt').value=pitch;}
  else pan={x:drag.pan.x+dx,y:drag.pan.y+dy};
  draw();
});
function finishDrag(event){
  const previous=drag;drag=null;
  if(previous?.moved){suppressClickUntil=performance.now()+200;if(previous.node)savePins();}
  else if(previous?.node&&event.type==='pointerup'){suppressClickUntil=performance.now()+200;inspect(previous.node,true);}
}
$('#graph').addEventListener('pointerup',finishDrag);$('#graph').addEventListener('pointercancel',finishDrag);

$('#seed-demo').onclick=event=>generateData(event.currentTarget);
$('#recall-form').addEventListener('submit',async event=>{
  event.preventDefault();
  await action(event.submitter,async()=>{
    packet=await api('/recall','POST',{query:$('#recall-query').value,budget_chars:2400,max_hops:2,dataset:dataset||null,strategy:'pace'});
    $('#recall-result').hidden=false;
     const messages=packet.messages||[];
     $('#recall-result').innerHTML=`<p class="result-summary">${packet.insufficient_evidence?'Insufficient evidence. Try another cue or save a sourced memory.':`${packet.handles.length} handles · ${messages.length} exact messages · ${packet.context_chars} characters · ${packet.visited} candidates visited`}${packet.truncated?' · Context budget reached':''}</p>${packet.handles.map((handle,index)=>`<button class="result-handle" data-handle="${index}"><i class="dot ${esc(handle.kind)}"></i><span>${esc(handle.title)}<small>${esc(handle.path.join(' → '))} · v${handle.version}</small>${handle.why?`<small class="handle-why">${esc([handle.why.matched?.length?`matched: ${handle.why.matched.join(', ')}`:null,handle.why.via].filter(Boolean).join(' · '))}</small>`:''}</span>↗</button>`).join('')}${messages.map(message=>`<article class="recall-message"><span class="tiny-label">EXACT MESSAGE · ${esc(message.role)}</span><p>${esc(message.text)}</p><small>${esc(message.platform)} · ${esc(message.session_id)} · ${esc(time(message.at))}</small></article>`).join('')}`;
    const mapping={intent:packet.intent,answer_ready:packet.answer_ready,missing:packet.missing,conflicts:packet.conflicts,evidence_forest:packet.evidence_forest};
    $('#recall-result').insertAdjacentHTML('beforeend',`<details class="recall-mapping"><summary>Context mapping & evidence paths${packet.answer_ready===false?' · needs more evidence':''}</summary><pre>${esc(JSON.stringify(mapping,null,2))}</pre></details>`);
    $('#recall-result').querySelectorAll('[data-handle]').forEach(button=>button.onclick=()=>{const handle=packet.handles[Number(button.dataset.handle)];const node=graphData.nodes.find(n=>n.id===handle.id);if(node)inspect(node,true);});
    await refresh(true);highlightPacket();
  });
});

function openMemoryEditor(record=null){
  editingRecord=record;const form=$('#memory-form');form.reset();delete form.dataset.retryKey;form.querySelector('.form-message').textContent='';
  $('#memory-form-title').textContent=record?`Edit memory · v${record.version}`:'Create a memory';
  const m=record?.payload;if(m){for(const key of ['title','kind','status','content','dataset'])form.elements[key].value=m[key]||'';form.elements.cues.value=(m.cues||[]).join(', ');form.elements.source_title.value=m.source.title;form.elements.source_text.value=m.source.text;form.elements.typed_links.value=(m.links||[]).map(l=>l.relation+' '+l.target_id).join('\n');}else form.elements.dataset.value=dataset||'workspace';
  $('#memory-dialog').showModal();
}
$('#add-memory').onclick=()=>openMemoryEditor();
$('#close-memory').onclick=()=>$('#memory-dialog').close();
$('#memory-form').addEventListener('input',event=>delete event.currentTarget.dataset.retryKey);
$('#memory-form').addEventListener('submit',async event=>{
  event.preventDefault();const form=event.target,v=Object.fromEntries(new FormData(form)),button=event.submitter;button.disabled=true;
  try{
    const links=v.typed_links.split('\n').map(x=>x.trim()).filter(Boolean).map(line=>{const [relation,target_id,...extra]=line.split(/\s+/);if(!['SUPPORTS','SUPERSEDES','CONTRADICTS','REFINES','DUPLICATES','DERIVED_FROM'].includes(relation)||!target_id||extra.length)throw new Error('Use one typed link per line: SUPPORTS memory-id');return{relation,target_id};});
    const key=form.dataset.retryKey||crypto.randomUUID();form.dataset.retryKey=key;
    const memory={...(editingRecord?.payload||{}),title:v.title,kind:v.kind,status:v.status,content:v.content,dataset:v.dataset,cues:v.cues.split(',').map(x=>x.trim()).filter(Boolean),links,source:{...(editingRecord?.payload.source||{}),title:v.source_title,text:v.source_text}};
    const receipt=await api(editingRecord?'/memories/'+encodeURIComponent(editingRecord.id):'/memories',editingRecord?'PUT':'POST',{memory,idempotency_key:key,expected_version:editingRecord?.version||0});
    form.reset();delete form.dataset.retryKey;$('#memory-dialog').close();await refresh(true);location.hash='graph';inspect(graphData.nodes.find(n=>n.id===receipt.id),true);notify('Versioned memory saved. Graph links refreshed.');
  }catch(error){form.querySelector('.form-message').textContent=error.status===409?'This memory changed in another session. Your edits are still here. Close and reopen the editor to review the current version before retrying. '+error.message:error.message;}
  finally{button.disabled=false;}
});
const configs={
  chatgpt:{instruction:'For an API-driven agent, expose these REST/SDK operations through its tool loop. Connecting the ordinary ChatGPT website requires a supported remote MCP integration, HTTPS and OAuth for protected data. This service provides REST and a local stdio bridge; a ChatGPT website integration is not installed.',code:`# API-driven ChatGPT agent or custom model wrapper\n# Register memory tools in your agent loop:\nPOST /api/connect    {"platform":"openai-api-agent"}\nPOST /api/messages   # record exact, consented messages\nPOST /api/recall     # retrieve bounded context\nGET  /api/memories/{id}?version={version}\nPOST /api/memories   # save sourced outcomes\n\n# Call /api/connect periodically for live presence.\n# The personal-assistant sample is entirely synthetic.`},
  codex:{instruction:'Add to your Codex config.toml. Set MNEMO_TOKEN in the environment that launches Codex.',code:`[mcp_servers.mnemograph]\ncommand = "D:/agent memory/.venv/Scripts/python.exe"\nargs = ["-m", "mnemograph.mcp_server"]\nenv_vars = ["MNEMO_TOKEN"]\n\n[mcp_servers.mnemograph.env]\nMNEMO_URL = "http://127.0.0.1:8000"\nMNEMO_PLATFORM = "codex"`},
  claude:{instruction:'Add to your project .mcp.json. Replace the executable path if you move the project.',code:JSON.stringify({mcpServers:{mnemograph:{type:'stdio',command:'D:/agent memory/.venv/Scripts/python.exe',args:['-m','mnemograph.mcp_server'],env:{MNEMO_TOKEN:'${MNEMO_TOKEN}',MNEMO_URL:'http://127.0.0.1:8000',MNEMO_PLATFORM:'claude-code'}}}},null,2)},
  python:{instruction:'Expose these client methods as tools in your agent loop. The same client works with API models and local models.',code:`from mnemograph.client import MemoryClient\n\n# MNEMO_TOKEN is a scoped credential in your environment.\nwith MemoryClient() as memory:\n    memory.connect("local-llm", "Continue the travel planning task")\n    state = memory.context()\n    packet = memory.recall("travel plan", budget_chars=2400)\n    for handle in packet["handles"]:\n        evidence = memory.expand(handle["id"], handle["version"])\n        # Pass needed evidence to your model as untrusted data.\n    # memory.remember(memory_record, key="task-42:decision")`},
  rest:{instruction:'Any tool-capable agent can call the scoped REST API. PowerShell example:',code:`$headers = @{ Authorization = "Bearer $env:MNEMO_TOKEN" }\n$body = @{ query = "travel plan"; budget_chars = 2400 } | ConvertTo-Json\nInvoke-RestMethod -Method Post \u0060\n  -Uri 'http://127.0.0.1:8000/api/recall' \u0060\n  -Headers $headers -ContentType 'application/json' -Body $body`}
};
function powershell(value){return "'"+String(value).replaceAll("'","''")+"'";}
function renderConfig(){
  if(setupInfo){
    const python=setupInfo.local_setup===false?'python':(setupInfo.python||'python').replaceAll('\\','/'),url=setupInfo.local_setup===false?location.origin:setupInfo.url||location.origin;
    configs.codex.code=`[mcp_servers.mnemograph]
command = ${JSON.stringify(python)}
args = ["-m", "mnemograph.mcp_server"]
env_vars = ["MNEMO_TOKEN"]

[mcp_servers.mnemograph.env]
MNEMO_URL = ${JSON.stringify(url)}
MNEMO_PLATFORM = "codex"`;
    configs.claude.code=JSON.stringify({mcpServers:{mnemograph:{type:'stdio',command:python,args:['-m','mnemograph.mcp_server'],env:{MNEMO_TOKEN:'${MNEMO_TOKEN}',MNEMO_URL:url,MNEMO_PLATFORM:'claude-code'}}}},null,2);
    configs.rest.code=`$headers = @{ Authorization = "Bearer $env:MNEMO_TOKEN" }
$connect = @{ platform = 'custom-rest'; context = 'Connected through REST' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$env:MNEMO_URL/api/connect" -Headers $headers -ContentType 'application/json' -Body $connect
Invoke-RestMethod -Uri "$env:MNEMO_URL/api/context" -Headers $headers
$recall = @{ query = 'current project decisions'; budget_chars = 2400 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$env:MNEMO_URL/api/recall" -Headers $headers -ContentType 'application/json' -Body $recall`;
  }
  const config=configs[activeIntegration];$('#integration-instruction').textContent=config.instruction;$('#integration-code').textContent=config.code;
  const where={codex:'Merge this server table into your Codex config.toml. Launch Codex from the terminal prepared in step 2, open /mcp, then ask it to call memory_connect and memory_state.',claude:'Merge this into your project .mcp.json. Launch Claude Code from the prepared terminal, approve the project server if requested, open /mcp, then ask for memory_connect and memory_state.',chatgpt:'For an API agent, expose these calls through its tool loop. Set platform to openai-api-agent in its heartbeat. The ordinary ChatGPT website needs a separate remote MCP/OAuth adapter, which is not installed.',python:'Use the Python client in your model wrapper. Start with memory.connect("local-llm", task). You provide the local or hosted model and decide which evidence to pass to it.',rest:'Run this REST example from your prepared terminal. It reports a custom-rest client heartbeat and reads scoped memory. A model can use the same calls through its tools.'};
  $('#setup-host-instruction').textContent=where[activeIntegration];
  document.querySelectorAll('[data-integration]').forEach(button=>{const active=button.dataset.integration===activeIntegration;button.classList.toggle('selected',active);button.setAttribute('aria-selected',String(active));});
}
function markSetupStep(index,done=true){$('#setup-step-'+index)?.classList.toggle('done',done);}
function selectIntegration(name){if(!configs[name])return;activeIntegration=name;renderConfig();markSetupStep(1);document.querySelectorAll('[data-setup]').forEach(button=>button.classList.toggle('selected',button.dataset.setup===name));renderSetup();}
function renderSetup(){
  if(!state||!setupInfo)return;
  const selector=$('#setup-agent'),agents=state.agents.filter(agent=>agent.id!=='operator').map(agent=>agent.id);
  if(!agents.length)agents.push(state.agent);
  if(!agents.includes(setupAgent))setupAgent=agents[0];
  const options=agents.map(id=>`<option value="${esc(id)}">${esc(id)}</option>`).join('');
  if(selector.innerHTML!==options)selector.innerHTML=options;selector.value=setupAgent;
  const dir=setupInfo.data_directory||setupInfo.workspace+'/.local';
  const label=[state.tenant,state.project,setupAgent].join('/');
  const remote=setupInfo.local_setup===false;
  $('#setup-intro').textContent=remote?'Your agent runs on your computer and calls this remote memory service. Run the steps on your computer. MCP uses a locally installed bridge; the memory service needs no model-provider key.':'This browser is the dashboard. Your agent runs separately and calls the same local memory service. Follow the steps below; no model-provider key is needed by the memory service.';
  $('#setup-key-note').textContent=remote?'Run this PowerShell block on your computer. For MCP or Python, start in your cloned Q-MDM folder. Enter the selected identity\'s workspace key at the secure prompt. This tests API access; it does not start a model.':'Every agent gets its own workspace key. Run this PowerShell block in the terminal you will use to launch the agent. It loads the selected identity locally and tests the API; it does not start a model.';
  $('#integration-key-note').textContent=remote?'Get a scoped workspace key from the service operator. The published demo key works only for the disposable demo. Launch your MCP host from the prepared terminal so it finds the local Python bridge. These examples do not change host configuration. The service offers REST; MCP uses a local stdio bridge.':'Use a separate scoped key for each agent. Keys live in .local/keys.json. These templates do not change your host configuration. REST is an HTTP API; the MCP bridge uses stdio. This service does not expose HTTP MCP.';
  const bridge=activeIntegration==='rest'?'':`# Run from your cloned Q-MDM repository folder.
python -m venv .venv
& '.\\.venv\\Scripts\\python.exe' -m pip install -e .
$env:PATH = (Resolve-Path '.\\.venv\\Scripts').Path + [IO.Path]::PathSeparator + $env:PATH
`;
  $('#setup-shell').textContent=remote?`${bridge}$taskKey = Read-Host 'Workspace key for ${setupAgent}' -AsSecureString
$env:MNEMO_TOKEN = [Net.NetworkCredential]::new('', $taskKey).Password
$env:MNEMO_URL = ${powershell(location.origin)}
$headers = @{ Authorization = "Bearer $env:MNEMO_TOKEN" }
$body = @{ platform = 'connection-check'; context = 'API access test' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$env:MNEMO_URL/api/connect" -Headers $headers -ContentType 'application/json' -Body $body | Out-Null
Invoke-RestMethod -Uri "$env:MNEMO_URL/api/context" -Headers $headers | Out-Null
Write-Host 'API access passed. Start the selected agent to complete its connection.'`:`Set-Location -LiteralPath ${powershell(setupInfo.workspace||'.')}
$taskKeys = Get-Content -Raw -LiteralPath ${powershell(dir+'/keys.json')} | ConvertFrom-Json
$env:MNEMO_TOKEN = $taskKeys.PSObject.Properties[${powershell(label)}].Value
if (-not $env:MNEMO_TOKEN) { $env:MNEMO_TOKEN = $taskKeys.PSObject.Properties[${powershell(setupAgent)}].Value }
if (-not $env:MNEMO_TOKEN) { throw 'This identity has no key in that file. Check the server data directory.' }
$env:MNEMO_URL = ${powershell(setupInfo.url||location.origin)}
& ${powershell(setupInfo.python||'python')} -m mnemograph check`;
  renderConfig();updateSetupStatus();
}
function updateSetupStatus(){
  const status=$('#setup-status');if(!status)return;
  const platform={codex:'codex',claude:'claude-code',chatgpt:'openai-api-agent',python:'local-llm',rest:'custom-rest'}[activeIntegration];
  const agent=(state?.agents||[]).find(agent=>agent.id===setupAgent);
  const connected=agent?.status==='active'&&agent.platform===platform;
  markSetupStep(2,Boolean(agent?.status==='active'&&agent.platform!=='dashboard'));
  markSetupStep(3,connected);status.classList.toggle('ok',connected);
  status.textContent=connected?`${setupAgent} contacted this service as ${platform}. Last heartbeat: ${time(agent.last_seen)}.`
    :agent?.status==='active'&&agent.platform==='connection-check'?`API connection test passed for ${setupAgent}. Complete step 3 to connect your selected agent.`
    :`Waiting for ${setupAgent} to contact the service as ${platform}. This dashboard does not count as an agent connection.`;
}
$('#setup-agent').onchange=event=>{setupAgent=event.target.value;renderSetup();};
document.querySelectorAll('[data-integration]').forEach(button=>button.onclick=()=>selectIntegration(button.dataset.integration));
document.querySelectorAll('[data-setup]').forEach(button=>button.onclick=()=>selectIntegration(button.dataset.setup));
async function copySetup(selector,button){try{await navigator.clipboard.writeText($(selector).textContent);notify('Copied. Run or save it in your agent environment.');}catch{notify('Clipboard unavailable. Select the text and copy it.');}}
$('#copy-config').onclick=event=>copySetup('#integration-code',event.currentTarget);
$('#copy-shell').onclick=event=>copySetup('#setup-shell',event.currentTarget);
renderConfig();
if(paused){$('#pause').textContent='▷';$('#pause').setAttribute('aria-label','Resume graph animation');}
async function generateData(button){await action(button,async()=>{if(!dataset){dataset='personal-assistant';$('#dataset').value=dataset;}await api('/demo','POST',{dataset});lastRevision=-1;await refresh(true);fitGraph();notify('Synthetic sample loaded. No external account connected.');});}
$('#generate-data').onclick=e=>generateData(e.currentTarget);
$('#dataset').onchange=async e=>{dataset=e.target.value;$('#relation-detail').hidden=true;lastRevision=-1;graphVersion=-1;graphData={nodes:[],edges:[]};positions.clear();selected=null;nodeHistory=[];focusMode=false;packet=null;edgeFilter='all';$('#facet').value='all';$('#relation-filter').value='all';$('#evolve-data').disabled=!dataset;await refresh(true);fitGraph();};
$('#evolve-data').onclick=e=>action(e.currentTarget,async()=>{if(!dataset)return;const receipt=await api('/demo/evolve','POST',{dataset});await refresh(true);const id=receipt.id||receipt.memory_id||receipt.changed_memory_id;const node=graphData.nodes.find(n=>n.id===id);if(node)inspect(node,true);notify('Change receipt saved. Added links are green; removed links are dashed.');});
function extractionWhy(entry, inline=false){
  const features=entry.features||{};
  const chips=(list,prefix)=>list?.length?`<div class="why-chips">${list.map(term=>`<span class="tiny-chip">${esc(prefix+term)}</span>`).join('')}</div>`:'';
  return entry.rationale?.length?`<details class="why-toggle${inline?' inline':''}"><summary>why</summary><ul>${entry.rationale.map(line=>`<li>${esc(line)}</li>`).join('')}</ul>${chips(features.cue_overlap,'cue: ')}${chips(features.change_words,'')}</details>`:'';
}
function renderTimeline(){
  const extractionById=new Map((extraction||[]).map(item=>[item.id,item]));
  $('#retention-note').hidden=!extractionById.size;
  $('#messages-list').innerHTML=timeline.messages.length?timeline.messages.map(message=>{
    const entry=extractionById.get(message.id);
    const linkedIds=new Set(message.memory_ids||[]);
    let whyInline=false;
    // One "why" per card: attach it to the linked-memory chip it explains instead of repeating the memory as an extraction chip.
    const memoryChips=(message.memory_ids||[]).map(id=>{
      const chip=`<button class="memory-chip" data-message-memory="${esc(id)}">${esc(graphData.nodes.find(n=>n.id===id)?.label||id)} →</button>`;
      if(entry&&!whyInline&&entry.retained&&entry.memories.some(memory=>memory.id===id)){whyInline=true;return chip+extractionWhy(entry,true);}
      return chip;
    }).join('');
    const newMemories=entry&&entry.retained?entry.memories.filter(memory=>!linkedIds.has(memory.id)):[];
    const row=[entry?`<span class="extraction-chip${entry.retained?'':' skipped'}">${entry.retained?'Retained ✓':'Not retained'}</span>`:'',
      newMemories.map(memory=>`<button class="extraction-chip" data-extract-memory="${esc(memory.id)}">→ ${esc(memory.title)}</button>`).join(''),
      whyInline?'':(entry?extractionWhy(entry):'')].join('');
    return `<article class="panel message-card"><header><b>${esc(message.role)}</b><span>${esc(message.platform)} ${message.synthetic?'· synthetic':''}</span><time datetime="${esc(message.at)}">${esc(time(message.at))}</time></header><p>${esc(message.text)}</p><small>Session ${esc(message.session_id)}</small><div>${memoryChips}</div>${row?`<div class="extraction-row">${row}</div>`:''}</article>`;
  }).join(''):'<div class="panel information"><h2>No messages in this space</h2><p>Generate a synthetic sample, or connect an agent and record exact messages with /api/messages.</p></div>';
  $('#messages-list').querySelectorAll('[data-message-memory]').forEach(b=>b.onclick=()=>{location.hash='graph';inspect(graphData.nodes.find(n=>n.id===b.dataset.messageMemory),true);});
  $('#messages-list').querySelectorAll('[data-extract-memory]').forEach(b=>b.onclick=()=>{location.hash='graph';inspect(graphData.nodes.find(n=>n.id===b.dataset.extractMemory),true);});
  $('#timeline-changes').innerHTML=(timeline.changes||[]).slice(-8).reverse().map(c=>`<div class="timeline-change"><b>${esc(c.action||c.type||c.kind||'Memory update')}</b><small>${esc(time(c.at||c.updated_at))}</small><p>${esc(c.title||c.memory_id||c.id||(/trace/i.test(String(c.action||c.type||c.kind||''))?'Recall context recorded':'Versioned memory change'))}</p></div>`).join('')||'<p class="quiet-note">No recorded changes yet.</p>';
}
const FLOW_QUERIES={'personal-assistant':'What changed about the travel plan?','camera-lab':'What changed about the camera arrangement?','team-planning':'What changed about the meeting plan?'};
const FLOW_STEPS=['Message arrives','Retention explained','Memory stored','Agent recalls','Context delivered'];
const kindGroups={fact:'Facts',decision:'Facts',resource:'Facts',core:'Preferences & how-to',procedure:'Preferences & how-to',episode:'Episodes',hypothesis:'Advanced',insight:'Advanced'};

function stopFlowTimer(){clearInterval(flowTimer);flowTimer=null;flowPlaying=false;const button=$('#flow-play');if(button){button.textContent='▶ Play';button.setAttribute('aria-pressed','false');}}
function setFlowStage(stage){
  flowStage=stage;
  const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.querySelectorAll('#flow-stages .flow-stage').forEach(section=>{
    const index=Number(section.dataset.stage);
    section.hidden=!reduced&&index>stage;
    section.classList.toggle('active',index===stage);
  });
  document.querySelectorAll('#flow-rail li').forEach(item=>{
    const active=Number(item.dataset.stage)===stage;
    item.classList.toggle('active',active);
    if(active)item.setAttribute('aria-current','step');else item.removeAttribute('aria-current');
  });
  const live=$('#flow-live');if(live)live.textContent=`Step ${stage} of 5: ${FLOW_STEPS[stage-1]}`;
}
function playFlow(){
  if(!flowStory||flowStory.empty)return;
  if(flowPlaying){stopFlowTimer();return;}
  if(flowStage>=5)setFlowStage(1);
  flowPlaying=true;const button=$('#flow-play');button.textContent='Ⅱ Pause';button.setAttribute('aria-pressed','true');
  flowTimer=setInterval(()=>{if(flowStage>=5){stopFlowTimer();return;}setFlowStage(flowStage+1);},1400);
}
function stepFlow(){stopFlowTimer();if(flowStory&&!flowStory.empty&&flowStage<5)setFlowStage(flowStage+1);}
function restartFlow(){stopFlowTimer();if(flowStory&&!flowStory.empty)setFlowStage(1);}
$('#flow-play').onclick=playFlow;
$('#flow-step').onclick=stepFlow;
$('#flow-restart').onclick=restartFlow;

function pickFlowStory(snapshot,messages,extractionMessages,packet){
  const entries=extractionMessages||[];
  const memoryNodes=(graphData.nodes||[]).filter(node=>node.record?.kind==='memory');
  const nodeById=new Map(memoryNodes.map(node=>[node.id,node]));
  const story={message:null,memory:null,memoryMeta:null,entry:null,extraction:entries,packet,snapshot};
  // Preferred story: the memory that changed (version ≥ 2), e.g. an evolved plan.
  const evolved=entries.flatMap(entry=>entry.memories.map(memory=>({entry,memory}))).filter(pair=>pair.memory.version>=2).sort((a,b)=>b.memory.version-a.memory.version)[0];
  if(evolved){story.entry=evolved.entry;story.message=messages.find(message=>message.id===evolved.entry.id)||null;story.memoryMeta=evolved.memory;story.memory=nodeById.get(evolved.memory.id)||null;}
  if(!story.message){
    // Fallback: the most recent retained message and its memory.
    const retained=entries.filter(entry=>entry.retained&&entry.memories.length);
    const last=retained[retained.length-1];
    if(last){story.entry=last;story.message=messages.find(message=>message.id===last.id)||null;story.memoryMeta=last.memories[0];story.memory=nodeById.get(last.memories[0].id)||null;}
  }
  if(!story.message){
    // No extraction lane (older servers): newest message with an evolved memory, else newest linked message.
    const linked=[...messages].reverse().filter(message=>(message.memory_ids||[]).length);
    const message=linked.find(item=>item.memory_ids.some(id=>(nodeById.get(id)?.record?.version||0)>=2))||linked[0]||messages[messages.length-1];
    if(message){story.message=message;const node=(message.memory_ids||[]).map(id=>nodeById.get(id)).find(Boolean)||null;story.memory=node;story.memoryMeta=node?{id:node.id,title:node.label,kind:node.record.payload.kind,version:node.record.version}:null;}
  }
  if(!story.message&&!story.memory)story.empty=true;
  return story;
}

function flowHead(index){const side=index<=3?'write':'read';return `<header><b>STEP 0${index}</b>${FLOW_STEPS[index-1]}<span class="flow-side ${side}">${index<=3?'WRITE':'READ'}</span></header>`;}
function shortLabel(label,limit=18){const text=String(label||'');return text.length>limit?text.slice(0,limit-1)+'…':text;}
function flowStageMessage(story){
  const message=story.message;
  if(!message)return `${flowHead(1)}<p class="quiet-note">No recorded message matches this story yet.</p>`;
  return `${flowHead(1)}<div class="flow-msg"><div class="flow-msg-head"><b>${esc(message.role)}</b><span>${esc(message.platform||'platform not recorded')}${message.synthetic?' · synthetic':''}</span><time datetime="${esc(message.at)}">${esc(time(message.at))}</time></div><p>${esc(message.text)}</p><small>Session ${esc(message.session_id||'not recorded')} · message ${esc(message.id)}</small></div>`;
}
function flowStageExtraction(story){
  const entry=story.entry;
  if(!entry)return `${flowHead(2)}<p class="quiet-note">This service doesn't report extraction decisions — the message still stores exactly as recorded.</p>`;
  const features=entry.features||{};
  const featureChips=[`<span class="tiny-chip">role: ${esc(features.role||'unknown')}</span>`,
    ...(features.cue_overlap||[]).map(term=>`<span class="tiny-chip">cue: ${esc(term)}</span>`),
    ...(features.change_words||[]).map(word=>`<span class="tiny-chip">${esc(word)}</span>`)].join('');
  const notRetained=(story.extraction||[]).find(candidate=>!candidate.retained&&candidate.id!==entry.id);
  const side=notRetained?`<div class="flow-sidecard recede"><span class="flow-verdict skipped">Not retained</span><p class="flow-side-text">${esc(notRetained.text)}</p><ul class="flow-list">${(notRetained.rationale||[]).map(line=>`<li>${esc(line)}</li>`).join('')}</ul></div>`:'';
  return `${flowHead(2)}<div class="flow-cols"><div class="flow-sidecard"><span class="flow-verdict">${entry.retained?'Retained ✓':'Not retained'}</span><ul class="flow-list">${(entry.rationale||[]).map(line=>`<li>${esc(line)}</li>`).join('')}</ul><div class="why-chips">${featureChips}</div></div>${side}</div>`;
}
function flowDiagram(node){
  const all=graphData.edges.filter(edge=>edge.source===node.id||edge.target===node.id).map(edge=>{
    const other=graphData.nodes.find(candidate=>candidate.id===(edge.source===node.id?edge.target:edge.source));
    return other?{node:other,type:edge.type}:null;
  }).filter(Boolean);
  const links=all.slice(0,6),extra=all.length-links.length;
  const W=560,H=Math.max(220,links.length*46+72),cy=H/2,cx=96,parts=[];
  links.forEach((link,index)=>{
    const y=cy+(index-(links.length-1)/2)*46;
    const dx=356-cx,dy=y-cy,len=Math.hypot(dx,dy)||1,ux=dx/len,uy=dy/len;
    const ax=cx+ux*34,ay=cy+uy*34,bx=356-ux*19,by=y-uy*19;
    parts.push(`<path d="M${ax.toFixed(1)},${ay.toFixed(1)} L${bx.toFixed(1)},${by.toFixed(1)}" stroke="#68828b" stroke-width="1.1" opacity=".55"/>`);
    parts.push(`<text x="${((ax+bx)/2).toFixed(1)}" y="${((ay+by)/2-4).toFixed(1)}" text-anchor="middle" font-size="9" fill="#8fa0ad">${esc(link.type)}</text>`);
    parts.push(`<circle cx="356" cy="${y.toFixed(1)}" r="19" fill="#161e25" stroke="${colors[link.node.type]||'#aab7c7'}"/>`);
    parts.push(`<text x="356" y="${(y+3).toFixed(1)}" text-anchor="middle" font-size="8.5" fill="#9aa9b6">${esc(link.node.type)}</text>`);
    parts.push(`<text x="384" y="${(y+3.5).toFixed(1)}" font-size="10" fill="#c3cdd6">${esc(shortLabel(link.node.label,26))}</text>`);
  });
  parts.push(`<circle cx="${cx}" cy="${cy}" r="34" fill="#161e25" stroke="${colors[node.type]||'#c4f375'}" stroke-width="1.4"/>`);
  parts.push(`<text x="${cx}" y="${cy+3.5}" text-anchor="middle" font-size="9" fill="#9aa9b6">${esc(node.type)}</text>`);
  parts.push(`<text x="${cx}" y="${cy+54}" text-anchor="middle" font-size="11" fill="#edf1ed">${esc(shortLabel(node.label,22))}</text>`);
  if(!links.length)parts.push(`<text x="${cx+60}" y="${cy+3.5}" font-size="11" fill="#8fa0ad">No typed links recorded yet.</text>`);
  if(extra>0)parts.push(`<text x="${W-8}" y="${H-10}" text-anchor="end" font-size="9" fill="#6f7b8a">+${extra} more linked records</text>`);
  return `<svg class="flow-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="This memory linked to ${all.length} records">${parts.join('')}</svg>`;
}
function flowStageMemory(story){
  const node=story.memory,meta=story.memoryMeta;
  if(!node&&!meta)return `${flowHead(3)}<p class="quiet-note">No stored memory is linked to this message in the current dataset.</p>`;
  const kind=meta?.kind||node?.record?.payload?.kind;
  const version=Math.max(meta?.version||0,node?.record?.version||0)||1;
  const title=meta?.title||node?.label||'Memory';
  const cues=(node?.record?.payload?.cues||[]);
  const linkCount=node?graphData.edges.filter(edge=>edge.source===node.id||edge.target===node.id).length:0;
  return `${flowHead(3)}<div class="flow-memory"><div class="flow-badges"><span class="flow-badge group">${esc(kindGroups[kind]||'Facts')}</span><span class="flow-badge">${esc(kind||'memory')}</span><span class="flow-badge version">v${version}</span></div><h3>${esc(title)}</h3>${cues.length?`<div class="why-chips">${cues.map(cue=>`<span class="tiny-chip">cue: ${esc(cue)}</span>`).join('')}</div>`:''}${node?flowDiagram(node):'<p class="quiet-note">The record is not in the current graph view.</p>'}<p class="quiet-note">${story.snapshot?.storage==='falkordb'?'Saved to FalkorDB graph':setupInfo?.local_setup===false?'Saved to service SQLite':'Saved to local SQLite'}${node?` · ${linkCount} linked records`:''}</p></div>`;
}
function flowStageRecall(story){
  const packet=story.packet;
  const query=`<div class="flow-query"><span class="tiny-label">RECALL QUERY</span><p>“${esc(story.query)}”</p></div>`;
  if(!packet)return `${flowHead(4)}${query}<p class="quiet-note">No recall result from this service.</p>`;
  if(packet.insufficient_evidence)return `${flowHead(4)}${query}<p class="quiet-note">This query found no matching evidence in the current dataset.</p>`;
  const handles=packet.handles||[];
  const seeds=handles.filter(handle=>handle.why?.via==='direct match');
  const hops=handles.filter(handle=>/\d-hop/.test(handle.why?.via||''));
  const paths=seeds.length||hops.length?`<div class="flow-paths"><span class="tiny-label">SEEDS LIGHT UP FIRST</span><div>${seeds.map((handle,index)=>`<span class="seed-chip" style="animation-delay:${index*160}ms">${esc(handle.title)}</span>`).join('')}</div>${hops.length?`<div>${hops.map((handle,index)=>`<span class="hop-chip" style="animation-delay:${(seeds.length*160)+index*160}ms">${esc(handle.why.via)}</span>`).join('')}</div>`:''}</div>`
    :`<div class="flow-paths"><span class="tiny-label">SELECTED HANDLES</span><div>${handles.map(handle=>`<span class="hop-chip">${esc(handle.title)}</span>`).join('')}</div><p class="quiet-note">This service doesn't report retrieval paths for its handles.</p></div>`;
  return `${flowHead(4)}${query}${paths}<p class="flow-stats">${packet.visited} records visited · ${handles.length} handles · ${packet.context_chars}/${packet.budget_chars} characters${packet.truncated?' · budget reached':''}</p>`;
}
function flowStageContext(story){
  const packet=story.packet;
  if(!packet)return `${flowHead(5)}<p class="quiet-note">No recall result from this service.</p>`;
  if(packet.insufficient_evidence)return `${flowHead(5)}<p class="quiet-note">Insufficient evidence. The agent would be told to look elsewhere rather than guess.</p>`;
  const handles=packet.handles||[];
  const pct=Math.max(0,Math.min(100,packet.budget_chars?Math.round(packet.context_chars/packet.budget_chars*100):0));
  const missing=Array.isArray(packet.missing)?packet.missing.filter(Boolean).join(' · '):(packet.missing?String(packet.missing):'');
  return `${flowHead(5)}<div class="flow-handles">${handles.map((handle,index)=>`<button class="result-handle" data-flow-handle="${index}"><i class="dot ${esc(handle.kind)}"></i><span>${esc(handle.title)}<small>${esc((handle.path||[]).join(' → '))} · v${handle.version}</small>${handle.why?`<small class="handle-why">${esc([handle.why.matched?.length?`matched: ${handle.why.matched.join(', ')}`:null,handle.why.via].filter(Boolean).join(' · '))}</small>`:''}</span>↗</button>`).join('')}</div><span class="tiny-label">CONTEXT BUDGET</span><div class="bar-track flow-meter"><div style="width:${pct}%"></div></div><p class="flow-stats">${packet.context_chars}/${packet.budget_chars} characters · ${pct}% of budget</p><p class="flow-stats">${missing?`Still missing: ${esc(missing)}`:'No evidence gap flagged for this query.'}</p><p class="quiet-note">The agent reads this before answering; sources stay one click away.</p>`;
}
function renderFlow(){
  const story=flowStory,panel=$('#flow-stages');
  if(story.empty){
    panel.innerHTML='<div class="flow-empty"><h3>No messages to walk through yet</h3><p>This walkthrough reads live messages and memories. Generate a synthetic sample on the Memory graph page, or let an agent record its first message.</p><a class="secondary button-link" href="#graph">Open the Memory graph →</a></div>';
    return;
  }
  panel.innerHTML=[flowStageMessage(story),flowStageExtraction(story),flowStageMemory(story),flowStageRecall(story),flowStageContext(story)].map((content,index)=>`<article class="flow-stage" data-stage="${index+1}">${content}</article>`).join('');
  panel.querySelectorAll('[data-flow-handle]').forEach(button=>button.onclick=()=>{const handle=story.packet.handles[Number(button.dataset.flowHandle)];const node=graphData.nodes.find(candidate=>candidate.id===handle.id);location.hash='graph';if(node)inspect(node,true);});
}
async function loadFlow(){
  if(!token)return;
  stopFlowTimer();flowStage=0;flowStory=null;
  const panel=$('#flow-stages');
  panel.innerHTML='<p class="quiet-note">Reading the live workspace…</p>';
  try{
    const snapshot=await api('/state');
    if(!graphData.nodes.length)await refresh(true);
    const timelineData=await api(scoped('/timeline'));
    const extractionMessages=await fetchExtraction();
    const query=FLOW_QUERIES[dataset]||'What changed about the current project?';
    let packet=null;
    try{packet=await api('/recall','POST',{query,budget_chars:2400,max_hops:2,dataset:dataset||null,strategy:'pace'});}catch{}
    flowStory=pickFlowStory(snapshot,timelineData.messages||[],extractionMessages,packet);
    flowStory.query=query;
    renderFlow();
    if(flowStory.empty)return;
    setFlowStage(1);
    if(!matchMedia('(prefers-reduced-motion: reduce)').matches)playFlow();
  }catch(error){panel.innerHTML=`<p class="error-banner">${esc(error.message)}</p>`;}
}
async function loadExperiments(){
  if(!token)return;
  try{const data=await api('/experiments'),container=$('#experiments-result');
    if(data.status==='not_run'||!data.aggregate?.length){container.innerHTML='<div class="panel information"><h2>No saved experiment yet</h2><p>Run the documented local benchmark, then refresh. This page will show only its recorded measurements.</p><pre>python -m benchmarks.run</pre></div>';return;}
    const metrics=[['recall_at_k','Evidence recall at k'],['evidence_precision','Evidence precision'],['coverage','Complete evidence coverage'],['abstention_success','Missing-fact zero-result rate']];
    container.innerHTML=`<div class="panel information"><p>Run ${esc(time(data.run_at))} · dataset ${esc(data.dataset_hash||'not recorded')}</p><p>Methods share the saved dataset. QWAM is an experimental classical numerical simulation.</p></div><div class="metric-charts">${metrics.map(([key,label])=>`<section class="panel metric-chart"><h3>${label}</h3>${data.aggregate.map(row=>`<div class="metric-row"><span>${esc(row.method)}</span><div class="bar-track"><div style="width:${Math.max(0,Math.min(100,Number(row[key]||0)*100))}%"></div></div><b>${Number.isFinite(Number(row[key]))?(Number(row[key])*100).toFixed(1)+'%':'n/a'}</b></div>`).join('')}</section>`).join('')}</div><div class="table-wrap panel"><table><caption>Measured retrieval results</caption><thead><tr><th>Method</th><th>Recall at k</th><th>Evidence precision</th><th>Coverage</th><th>Context chars</th><th>p50 ms</th><th>p95 ms</th></tr></thead><tbody>${data.aggregate.map(r=>`<tr>${['method','recall_at_k','evidence_precision','coverage','context_chars','p50_ms','p95_ms'].map(k=>`<td>${esc(typeof r[k]==='number'?Number(r[k].toFixed(3)):r[k]??'n/a')}</td>`).join('')}</tr>`).join('')}</tbody></table></div><div class="panel information"><h2>Methodology & limits</h2>${(data.limitations||[]).map(x=>`<p>${esc(x)}</p>`).join('')}<details><summary>Inspect saved category results</summary><pre>${esc(JSON.stringify({methods:data.methods,categories:data.categories,by_category:data.by_category},null,2))}</pre></details></div>`;
  }catch(error){$('#experiments-result').innerHTML=`<p class="error-banner">${esc(error.message)}</p>`;}
}
$('#refresh-experiments').onclick=e=>action(e.currentTarget,loadExperiments);
if(!token)$('#login-dialog').showModal();else refresh(true);
setInterval(()=>{if(token && !document.hidden)refresh();},2500);
setInterval(async()=>{if(token && !document.hidden && setupInfo?.local_setup!==false){try{await api('/connect','POST',{platform:'dashboard',context:'Exploring shared memory'});}catch(error){fail(error);}}},60000);
