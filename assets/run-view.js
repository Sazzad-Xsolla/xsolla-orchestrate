/* The embedded snapshot works offline; localhost views refresh from their own server. */
let data = "__DATA__";
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = value => value == null ? 'Not recorded' : '$' + Number(value).toFixed(2);
const stateClass = state => ['verified','running','dispatching','paused','blocked','failed'].includes(state) ? state : '';
const empty = text => `<p class="empty">${escape(text)}</p>`;

function render() {
  document.getElementById('run-title').textContent = data.title || 'Orchestration run';
  document.getElementById('goal').textContent = data.goal || 'Define a goal in Claude to begin this run';
  document.getElementById('run-id').textContent = data.run_id || 'New run';
  document.getElementById('demo').hidden = !data.demo;
  document.getElementById('updated').textContent = 'Updated ' + data.updated;
  const workers = data.workers || [];
  const approved = (data.memory || []).filter(m => m.status === 'approved');
  const verified = workers.filter(w => w.state === 'verified').length;
  const active = workers.filter(w => ['running','dispatching'].includes(w.state)).length;
  const queued = (data.messages || []).filter(m => m.delivery === 'queued').length;
  document.getElementById('stats').innerHTML = `
    <div class="metric featured"><label>Verified progress</label><strong>${verified} / ${workers.length}</strong><progress aria-label="Verified progress" value="${Number(data.progress) || 0}" max="100"></progress></div>
    <div class="metric"><label>Active workers</label><strong>${active}</strong><label>Up to 4 at once</label></div>
    <div class="metric"><label>Worker spend</label><strong>${escape(money(data.spend_usd))}</strong><label>${data.run_budget_usd ? escape(money(data.run_budget_usd)) + ' run checkpoint' : 'No run checkpoint'}</label></div>
    <div class="metric"><label>Queued messages</label><strong>${queued}</strong><label>Delivered at next dispatch</label></div>`;
  const open = new Set([...document.querySelectorAll('details[open]')].map(d => d.id));
  document.getElementById('tasks').innerHTML = workers.map(w => `
    <article class="task"><div class="task-head"><div class="task-title"><span class="task-id">${escape(w.id)}</span><div><h3>${escape(w.title)}</h3><p>${escape(w.model)} · ${escape(w.effort)} effort · ${escape(w.specialist || 'Task worker')}</p></div></div><span class="pill ${stateClass(w.state)}">${escape(w.state)}</span></div>
    <p>${escape(w.last_action || w.last_text || 'Waiting for dispatch')}</p>
    <details id="task-${escape(w.id)}" ${open.has('task-' + w.id) ? 'open' : ''}><summary>Inspect routing and checks</summary><dl class="detail-grid">
    <div><dt>Routing reason</dt><dd>${escape(w.routing_reason || 'No reason recorded')}</dd></div>
    <div><dt>Dependencies</dt><dd>${escape((w.depends_on || []).join(', ') || 'None')}</dd></div>
    <div><dt>Critic review</dt><dd>${escape(w.critic || 'Not reviewed')}</dd></div>
    <div><dt>Watchdog</dt><dd>${escape(w.watchdog || 'No active signal')}</dd></div>
    <div><dt>Acceptance</dt><dd>${w.accept ? (w.accept.passed ? 'Passed' : 'Failed') : 'Not checked'}</dd></div>
    <div><dt>Spend / task checkpoint</dt><dd>${escape(money(w.cost_usd))} / ${escape(money(w.budget_usd))}${w.cost_estimated ? ' (estimate)' : ''}</dd></div>
    </dl></details></article>`).join('') || empty('Tasks will appear after the orchestrator creates a plan');
  const needs = [...(data.approvals || []).map(a => ({title: a.kind + ': ' + a.target, text: a.text})),
    ...(data.blockers || []).map(w => ({title: w.title + ' · ' + w.state, text: w.last_text || 'Review the worker report in Claude'}))];
  document.getElementById('attention').innerHTML = needs.length ? needs.map(n => `<div class="attention"><h3>${escape(n.title)}</h3><p>${escape(n.text)}</p></div>`).join('') + '<div class="section-body"><button id="copy-review" class="xui-btn xui-btn--secondary xui-btn--brand xui-btn--sm"><span class="xui-btn__label">Copy review request</span></button><p id="copy-status" class="empty" role="status">Paste the request into your Claude conversation to review</p></div>' : '<div class="section-body">' + empty('No decisions are waiting for you') + '</div>';
  const copy = document.getElementById('copy-review');
  if (copy) copy.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText('Review pending decisions and blockers for run ' + data.run_id + '. Show the evidence and exact actions before asking for authorization.'); document.getElementById('copy-status').textContent = 'Copied — paste into your Claude conversation'; }
    catch (_) { document.getElementById('copy-status').textContent = 'Ask Claude to review pending decisions for run ' + data.run_id; }
  });
  document.getElementById('activity').innerHTML = (data.log || []).slice().reverse().map(e => `<div class="event"><small>${escape(e.at)}</small><p>${escape(e.note)}</p></div>`).join('') || empty('Critic, watchdog, and coordination updates will appear as the run progresses');
  document.getElementById('messages').innerHTML = (data.messages || []).slice(-12).map(m => `<article class="message"><small>${escape(m.sender)} → ${escape(m.recipient)} · ${escape(m.kind)}</small><p>${escape(m.text)}</p><small>${escape(m.evidence || 'No evidence reference')} · ${escape(m.delivery)}</small></article>`).join('') || empty('Agent handoffs will appear when the orchestrator forwards a finding or question');
  document.getElementById('memory').innerHTML = approved.map(m => `<article class="message"><small>${escape(m.specialist)} · Reviewed by ${escape(m.reviewed_by)}</small><p>${escape(m.text)}</p><small>${escape(m.evidence)} · Project context</small></article>`).join('') || empty('Reviewed lessons will appear after a verified task produces reusable project knowledge');
}

render();
if (location.protocol !== 'file:') {
  setInterval(async () => {
    try {
      const response = await fetch('/data.json', {cache: 'no-store'});
      if (!response.ok) throw new Error('unavailable');
      data = await response.json();
      render();
      document.getElementById('connection').textContent = 'Connected to local run';
      document.getElementById('connection').classList.remove('error-line');
    } catch (_) {
      document.getElementById('connection').textContent = 'Connection lost — showing last update';
      document.getElementById('connection').classList.add('error-line');
    }
  }, 5000);
} else {
  document.getElementById('connection').textContent = 'Saved snapshot';
}
