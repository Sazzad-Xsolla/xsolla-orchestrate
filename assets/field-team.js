/* Field Team shares one snapshot and one decision API across browser and widget. */
let data = "__DATA__";
const characterSheet = "__CHARACTERS__";
const atlasPortrait = "__ATLAS_PORTRAIT__";
const sessionToken = "__SESSION__";
const widgetMode = new URLSearchParams(location.search).get('widget') === '1';
const live = location.protocol === 'http:' && sessionToken !== '__' + 'SESSION__';
let connected = live, busy = false, page = 'home', widgetTab = 'party', agentFilter = '', selectedDetail = null, detailTab = 'overview';
const $ = id => document.getElementById(id);
const observeMotion = createMotionTracker();
let motion = observeMotion(data), cueTimer;
const motionMedia = matchMedia('(prefers-reduced-motion: reduce)');
let reduceMotion = new URLSearchParams(location.search).get('reduceMotion') === '1';
try { if(!new URLSearchParams(location.search).has('reduceMotion')) reduceMotion=localStorage.getItem('field-team-reduce-motion')==='true'; } catch(_) {}
function syncMotion() {
  document.body.classList.toggle('no-motion',reduceMotion || motionMedia.matches);
  document.querySelectorAll('.reduce-motion').forEach(el=>el.checked=reduceMotion || motionMedia.matches);
}
function playCue(effect) {
  if(effect==='none')return;
  clearTimeout(cueTimer);
  document.body.classList.remove('motion-attention','motion-complete','motion-log');
  if(reduceMotion || motionMedia.matches)return;
  void document.body.offsetWidth;
  document.body.classList.add('motion-'+effect);
  cueTimer=setTimeout(()=>document.body.classList.remove('motion-attention','motion-complete','motion-log'),1100);
}
motionMedia.addEventListener('change',syncMotion);
document.addEventListener('change',e=>{
  if(!e.target.matches('.reduce-motion'))return;
  reduceMotion=e.target.checked;
  try {localStorage.setItem('field-team-reduce-motion',String(reduceMotion));} catch(_) {}
  syncMotion();
  window.webkit?.messageHandlers?.fieldTeam?.postMessage({action:'motion',value:String(reduceMotion)});
});
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const crops = {atlas:[870,219,112,107],pip:[196,446,120,138],rivet:[531,446,115,138],aegis:[852,447,121,138]};
function sprite(kind, extra='') {
  if(kind==='atlas') return `<img class="sprite avatar-portrait ${extra}" src="${atlasPortrait}" alt="" aria-hidden="true">`;
  const box = crops[kind] || crops.rivet;
  return `<svg class="sprite ${extra}" aria-hidden="true" viewBox="${box.join(' ')}"><svg x="${box[0]}" y="${box[1]}" width="${box[2]}" height="${box[3]}" viewBox="${box.join(' ')}" overflow="hidden"><image href="${characterSheet}" width="1536" height="1024"/></svg></svg>`;
}
function model(value) {
  if (!value) return 'Not recorded';
  const aliases = {sonnet:'Claude Sonnet',opus:'Claude Opus',haiku:'Claude Haiku',fable:'Claude Fable'};
  return aliases[value] || value;
}
const effort = value => value ? String(value).charAt(0).toUpperCase() + String(value).slice(1) : 'Not recorded';
const tags = agent => `<div class="tags"><span class="tag">Model: ${esc(model(agent.model))}</span><span class="tag">Effort: ${esc(effort(agent.effort))}</span></div>`;
const workers = () => data.workers || [];
const pending = () => data.approvals || [];
const workerById = id => workers().find(w => w.id === id);
const character = w => w?.character || {name:'Agent',role:'Worker',species:'rivet'};
function state(w) {
  if (w.awaiting_approval) return ['Awaiting approval','waiting'];
  if (w.awaiting_supervisor) return [w.latest_decision?.decision==='reject' ? 'Denied · Awaiting revised plan' : 'Approved · Awaiting Claude','waiting'];
  return ({running:['Working',''],dispatching:['Starting',''],verified:['Verified','good'],planned:['Planned','quiet'],blocked:['Blocked','waiting'],paused:['Paused','waiting'],failed:['Failed','bad'],rejected:['Rejected','bad'],'awaiting review':['Awaiting review','waiting']})[w.state] || [w.state || 'Not recorded','quiet'];
}
function status(w) { const [text, cls] = state(w); return `<span class="status ${cls}">${esc(text)}</span>`; }
function empty(text) { return `<p class="empty">${esc(text)}</p>`; }
function nowText(w) { return w.last_action || w.last_text || (w.state === 'planned' ? 'Waiting for dispatch' : 'No activity recorded'); }
function relative(value) {
  if (!value) return 'No update recorded';
  const seconds = Math.max(0,Math.round((Date.now()-Date.parse(value))/1000));
  if (!Number.isFinite(seconds)) return 'Update time not recorded';
  return seconds < 60 ? `Updated ${seconds}s ago` : seconds < 3600 ? `Updated ${Math.floor(seconds/60)}m ago` : `Updated ${Math.floor(seconds/3600)}h ago`;
}
function time(value) {
  if (!value) return 'No time';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});
}
function card(w) {
  const c=character(w);
  return `<article class="agent-card ${w.awaiting_approval ? 'needs-you':''}"><div class="agent-head">${sprite(c.species)}<div><h3>${esc(c.name)}</h3><small>${esc(c.role)}${c.level != null ? ' · Lv. '+esc(c.level):''} · ${esc(w.id)}</small>${tags(w)}${status(w)}</div></div><dl><div class="agent-goal"><dt>Goal</dt><dd>${esc(w.objective || w.title)}</dd></div><div class="agent-goal"><dt>Now</dt><dd>${esc(nowText(w).slice(0,180))}</dd></div></dl><footer class="card-footer"><small>${esc(relative(w.updated_at))}</small><button class="text-action" data-agent="${esc(w.id)}">View details →</button></footer></article>`;
}
function events(limit=120) { return (data.activity || []).filter(e => !agentFilter || e.agent===agentFilter).slice(0,limit); }
function eventRows(list) {
  return list.map(e => {
    const index=(data.activity || []).indexOf(e), w=workerById(e.agent), c=character(w), name=e.agent==='orchestrator' ? (data.orchestrator?.name || 'Orchestrator') : c.name;
    return `<button class="event ${motion.fresh.includes(JSON.stringify([e.agent,e.at,e.kind,e.text,e.sequence])) ? 'arriving' : ''}" data-event="${index}"><time>${esc(time(e.at))}</time>${sprite(e.agent==='orchestrator'?'atlas':c.species)}<strong>${esc(name)}</strong><span class="excerpt">${esc(e.text)}</span><span aria-hidden="true">›</span></button>`;
  }).join('') || empty('Activity will appear when agents produce log events');
}
const arrow = '<svg class="xui-btn__icon" width="28" height="28" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M11.9983 19.0824L18.0706 13.0111L2.99927 13.0111L2.99927 11.0111L18.0706 11.0111L11.9993 4.93985L13.4133 3.52579L21.1915 11.304C21.5821 11.6945 21.5821 12.3277 21.1915 12.7182L13.4124 20.4965L11.9983 19.0824Z"/></svg>';
function requestCard(a) {
  const w=workerById(a.from_task), c=character(w);
  const disabled=busy||!connected||!live;
  return `<article class="request"><div class="request-owner">${sprite(c.species)}<div><strong>${esc(w ? c.name : a.from_task || 'Orchestrator')}</strong><small>${esc(a.kind || 'Action')} · ${esc(a.id)}</small></div></div><h3>${esc(a.title || a.kind || 'Requested action')}</h3><p class="request-target">${esc(a.target || 'Target not recorded')}</p><p class="request-body">${esc(a.text || 'No description recorded')}</p>${a.reason ? `<p class="request-body">Reason: ${esc(a.reason)}</p>`:''}<button class="text-action" data-request="${esc(a.id)}">View request details →</button><div class="decision-buttons"><button class="xui-btn xui-btn--ghost xui-btn--brand xui-btn--sm" data-decision="reject" data-request-id="${esc(a.id)}" ${disabled?'disabled':''}><span class="xui-btn__label">Deny</span></button><button class="xui-btn xui-btn--primary xui-btn--brand xui-btn--sm xui-btn--spread" data-decision="approve" data-request-id="${esc(a.id)}" ${disabled?'disabled':''}><span class="xui-btn__label">Approve</span>${arrow}</button></div><small>${!live ? 'Saved snapshot · Open the live dashboard to answer' : !connected ? 'Reconnect to answer this request' : data.demo ? 'Demo choice only · No real action will be taken' : 'Records permission · Claude executes the requested action'}</small></article>`;
}
function decisions() {
  return (data.decisions || []).slice(-8).reverse().map(a => {
    const yes=a.response.decision==='approve';
    return `<article class="request resolved ${yes?'':'denied'}"><strong>${yes?'Approved':'Denied'} · ${esc(a.target || a.id)}</strong><p class="summary">${yes?'Permission recorded; awaiting Claude update':'No action executed; awaiting a revised plan'}</p><small>${esc(time(a.response.at))} · ${esc(a.response.source)}</small></article>`;
  }).join('');
}
function attention() {
  const blockers=workers().filter(w => ['failed','blocked','paused'].includes(w.state) && !w.awaiting_approval);
  return pending().map(requestCard).join('') + blockers.map(w => `<article class="request"><strong>${esc(character(w).name)} · ${esc(state(w)[0])}</strong><p class="summary">${esc(nowText(w))}</p><button class="text-action" data-agent="${esc(w.id)}">Inspect agent →</button></article>`).join('') + (!pending().length&&!blockers.length ? empty('No decisions are waiting for you'): '') + decisions();
}
function render() {
  const focus=document.activeElement;
  const focusKey=focus?.dataset?.agent ? ['agent',focus.dataset.agent] : focus?.dataset?.page ? ['page',focus.dataset.page] : null;
  $('demo').hidden=!data.demo;
  $('goal').textContent=data.goal || 'Define a goal in Claude to begin';
  $('run-title').textContent=data.title || 'Orchestration run';
  $('run-id').textContent=data.run_id || '';
  $('updated').textContent='Snapshot: '+(data.updated || 'Not recorded');
  $('connection').textContent=!live?'Saved snapshot':connected?'Live · Connected to local run':'Disconnected · Showing last update';
  const done=workers().filter(w=>w.state==='verified').length, active=workers().filter(w=>['running','dispatching'].includes(w.state)&&!w.awaiting_approval&&!w.awaiting_supervisor).length;
  $('stats').innerHTML=`<div class="stat"><b>${done} / ${workers().length}</b><span>tasks verified</span></div><div class="stat"><b>${active}</b><span>working</span></div><div class="stat"><b>${pending().length}</b><span>waiting for you</span></div>`;
  const o=data.orchestrator || {};
  $('orchestrator').innerHTML=`<p class="eyebrow">Orchestrator</p><div class="row">${sprite('atlas')}<div><h3>${esc(o.name || 'Claude orchestrator')}</h3>${tags(o)}<span class="status ${o.status==='Not recorded'?'quiet':''}">${esc(o.status || 'Not recorded')}</span><p class="summary">${esc(o.summary || 'Supervising conversation in Claude Code')}</p><button class="text-action" data-open="orchestrator">View orchestrator →</button></div></div>`;
  $('party-count').textContent=workers().length+' agents';
  $('party').innerHTML=workers().slice(0,6).map(card).join('') || empty('Create tasks in your Claude run to assemble a party');
  $('approval-count').textContent=pending().length || '';
  $('pending-count').textContent=pending().length+' pending';
  $('attention').innerHTML=attention();
  const filter=$('activity-agent');
  const choices='<option value="">All agents</option><option value="orchestrator">Orchestrator</option>'+workers().map(w=>`<option value="${esc(w.id)}">${esc(character(w).name)} · ${esc(w.id)}</option>`).join('');
  if (filter.innerHTML!==choices && document.activeElement!==filter) {filter.innerHTML=choices; filter.value=agentFilter;}
  $('activity').innerHTML=eventRows(events(6));
  renderPage(); renderWidget(); syncMotion();
  motion.fresh=[];
  if (selectedDetail && $('drawer').open) renderDetail();
  if (focusKey) document.querySelector(`[data-${focusKey[0]}="${CSS.escape(focusKey[1])}"]`)?.focus({preventScroll:true});
}
function renderPage() {
  $('home-page').hidden=page!=='home'; $('other-page').hidden=page==='home';
  document.querySelectorAll('nav [data-page]').forEach(el=>el.classList.toggle('selected',el.dataset.page===page));
  $('page-title').textContent=({home:'Mission control',party:'Your party',activity:'Activity log',approvals:'Decisions',knowledge:'Project memory'})[page] || 'Mission control';
  if(page==='party') $('other-page').innerHTML=`<div class="party-grid">${workers().map(card).join('') || empty('No agents in this run')}</div>`;
  if(page==='activity') $('other-page').innerHTML=`<section class="surface"><div class="section-header"><h2>Recent activity</h2><small>Newest first · Click for full event</small></div><div class="activity-list">${eventRows(events())}</div></section>`;
  if(page==='approvals') $('other-page').innerHTML=`<section class="surface">${attention()}</section>`;
  if(page==='knowledge') $('other-page').innerHTML=`<section class="surface">${(data.memory||[]).filter(m=>m.status==='approved').map(m=>`<article class="request"><strong>${esc(m.specialist)}</strong><p class="request-body">${esc(m.text)}</p><small>${esc(m.evidence)} · Reviewed by ${esc(m.reviewed_by)}</small></article>`).join('') || empty('Reviewed project lessons appear after verified work')}</section>`;
}
function fields(items) {return items.map(([name,text])=>`<section class="detail-field"><h3>${esc(name)}</h3><p>${esc(text || 'Not recorded')}</p></section>`).join('');}
function openDetail(detail) {selectedDetail=detail; detailTab='overview'; renderDetail(); if(!$('drawer').open) $('drawer').showModal();}
function renderDetail() {
  const root=$('drawer-content'), d=selectedDetail;
  if(d.type==='agent') {
    const w=workerById(d.id); if(!w){$('drawer').close();return;}
    const c=character(w); $('drawer-title').textContent=c.name+' · '+w.id;
    const tabs=['overview','activity','report'];
    root.innerHTML=`<div class="detail-head">${sprite(c.species)}<div><h3>${esc(c.name)}</h3><small>${esc(c.role)}${c.level != null?' · Lv. '+esc(c.level):''}</small>${tags(w)}${status(w)}</div></div><div class="detail-tabs">${tabs.map(t=>`<button data-detail-tab="${t}" class="${detailTab===t?'selected':''}">${t.charAt(0).toUpperCase()+t.slice(1)}</button>`).join('')}</div>`;
    if(detailTab==='overview') root.innerHTML+=fields([['Assigned goal',w.objective],['Current activity',nowText(w)],['Task',w.title],['Routing reason',w.routing_reason],['Dependencies',(w.depends_on||[]).join(', ') || 'None'],['Permitted writes',(w.writes||[]).join(', ') || 'No writes assigned'],['Critic',w.critic || 'Not reviewed'],['Watchdog',w.watchdog || 'No active signal'],['Acceptance',w.accept ? (w.accept.passed?'Passed':'Failed'):'Not checked']])+`<section class="detail-field"><h3>Done criteria</h3><ul>${(w.done_criteria||[]).map(t=>`<li>${esc(t)}</li>`).join('')}</ul></section>`;
    if(detailTab==='activity') root.innerHTML+=(w.activity||[]).slice().reverse().map(e=>`<article class="detail-event"><small>${esc(time(e.at))} · ${esc(e.kind)}</small><p>${esc(e.text)}</p></article>`).join('') || empty('No agent log events recorded');
    if(detailTab==='report') root.innerHTML=`${root.innerHTML}<pre>${esc(w.report || 'The agent has not written a report yet')}</pre>`;
  } else if(d.type==='request') {
    const a=pending().find(a=>a.id===d.id); $('drawer-title').textContent='Request details';
    root.innerHTML=a ? requestCard(a)+`<details><summary>Full recorded request</summary><pre>${esc(JSON.stringify(a,null,2))}</pre></details>` : empty('This request was answered or changed; review the current decisions');
  } else if(d.type==='event') {
    $('drawer-title').textContent='Activity event'; const e=d.event;
    root.innerHTML=fields([['Agent',e.agent],['Time',e.at || 'Not recorded'],['Event type',e.kind]])+`<pre>${esc(e.text)}</pre>`;
  } else if(d.type==='orchestrator') {
    const o=data.orchestrator || {}; $('drawer-title').textContent='Orchestrator';
    root.innerHTML=tags(o)+fields([['Name',o.name],['Status',o.status],['Latest update',o.summary]])+'<p class="empty">The supervising conversation runs in Claude Code</p>';
  } else {
    $('drawer-title').textContent='Main goal and plan';
    root.innerHTML=fields([['Goal',data.goal]])+`<section class="detail-field"><h3>Definition of done</h3><ul>${(data.definition_of_done||[]).map(g=>`<li>${g.met?'Verified':'Pending'} · ${esc(g.text)}${g.evidence?' · '+esc(g.evidence):''}</li>`).join('')}</ul></section>`+workers().map(w=>fields([[w.id+' · '+w.title,w.objective]])).join('');
  }
}
function renderWidget() {
  if(!widgetMode) return;
  $('widget-goal').textContent=data.goal || data.title || 'Choose a run to connect';
  $('widget-count').textContent=pending().length || '';
  document.querySelectorAll('[data-widget-tab]').forEach(el=>el.classList.toggle('selected',el.dataset.widgetTab===widgetTab));
  if(widgetTab==='party') $('widget-body').innerHTML=workers().map(w=>`<button class="widget-row" data-widget-agent="${esc(w.id)}">${sprite(character(w).species)}<div><strong>${esc(character(w).name)}</strong><small>${character(w).level != null ? " · Lv. "+esc(character(w).level) : " · "+esc(w.id)}</small>${tags(w)}${status(w)}<p class="summary">Goal: ${esc(w.objective)}</p><p class="summary">${esc(nowText(w).slice(0,130))}</p></div></button>`).join('') || empty('No agents in this run');
  if(widgetTab==='attention') $('widget-body').innerHTML=attention();
  if(widgetTab==='activity') $('widget-body').innerHTML=(data.activity||[]).slice(0,20).map(e=>`<article class="detail-event"><small>${esc(time(e.at))} · ${esc(e.agent)}</small><p>${esc(e.text.slice(0,350))}</p></article>`).join('') || empty('No activity recorded');
}
function notify(text,error=false) { $('notice').hidden=false; $('notice').textContent=text; $('notice').classList.toggle('error',error); $('widget-notice').textContent=text; }
async function refresh() {
  if(!live || busy) return;
  try {
    const r=await fetch('/data.json',{cache:'no-store'}); const next=await r.json();
    if(!r.ok) throw new Error(next.error || 'Run unavailable');
    motion=observeMotion(next); data=next; connected=true; render(); playCue(motion.effect);
  } catch(e) { connected=false; render(); notify('Connection lost; showing the last update. Decisions are disabled.',true); }
}
async function decide(id,choice) {
  if(busy||!connected||!live) return;
  const a=pending().find(a=>a.id===id); if(!a) return;
  const request={id:a.id,fingerprint:a.fingerprint,decision:choice,run_key:data.run_key,source:widgetMode?'desktop-widget':'mission-control'};
  busy=true; render();
  try {
    const r=await fetch('/decision',{method:'POST',headers:{'Content-Type':'application/json','X-Field-Team-Token':sessionToken},body:JSON.stringify(request)});
    const response=await r.json(); if(!r.ok) throw new Error(response.error || 'Could not record decision');
    notify(data.demo?'Demo decision recorded; no real action was taken':response.message);
  } catch(e) { notify(e.message,true); }
  finally {busy=false; await refresh();}
}
document.addEventListener('click',event=>{
  const b=event.target.closest('button'); if(!b) return;
  if(b.dataset.page){page=b.dataset.page; renderPage();}
  if(b.dataset.agent) openDetail({type:'agent',id:b.dataset.agent});
  if(b.dataset.open) openDetail({type:b.dataset.open});
  if(b.dataset.request) openDetail({type:'request',id:b.dataset.request});
  if(b.dataset.event!=null) openDetail({type:'event',event:(data.activity||[])[Number(b.dataset.event)]});
  if(b.dataset.decision) decide(b.dataset.requestId,b.dataset.decision);
  if(b.dataset.detailTab){detailTab=b.dataset.detailTab; renderDetail();}
  if(b.dataset.widgetTab){widgetTab=b.dataset.widgetTab; renderWidget();}
  if(b.dataset.widgetAgent){if(window.webkit?.messageHandlers?.fieldTeam) window.webkit.messageHandlers.fieldTeam.postMessage({action:'dashboard',agent:b.dataset.widgetAgent});else window.open('/#agent='+encodeURIComponent(b.dataset.widgetAgent),'_blank','noopener');}
});
$('activity-agent').addEventListener('change',e=>{agentFilter=e.target.value;render();});
$('drawer-close').addEventListener('click',()=>{$('drawer').close();selectedDetail=null;});
$('drawer').addEventListener('close',()=>{selectedDetail=null;});
$('widget-close').addEventListener('click',()=>window.webkit?.messageHandlers?.fieldTeam?.postMessage({action:'close'}));
$('open-mission').addEventListener('click',()=>{if(window.webkit?.messageHandlers?.fieldTeam)window.webkit.messageHandlers.fieldTeam.postMessage({action:'dashboard'});else window.open('/','_blank','noopener');});
document.body.classList.toggle('widget-mode',widgetMode); $('widget').hidden=!widgetMode;
render();
if(location.hash.startsWith('#agent=')){try{openDetail({type:'agent',id:decodeURIComponent(location.hash.slice(7))});}catch(_){}}
if(live) setInterval(refresh,3000);
