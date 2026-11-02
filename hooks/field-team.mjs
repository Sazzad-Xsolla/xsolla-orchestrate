// Native Claude Code mod. The Python runtime remains the source of run state.
const PANE = 'xsolla-field-team';
let target = null;
let data = { run: null, message: 'Run /field-team to open your party.' };
let failure = '';
let refreshing = false;
let timer;
let tab = 'party';

async function refresh($) {
  if (refreshing || !target) return;
  refreshing = true;
  const readingTarget = target;
  try {
    const root = $.plugin.root;
    const result = await $.process.run(
      ['python3', root + '/scripts/mod_snapshot.py', target], { timeoutMs: 15000 });
    if (result.exitCode !== 0) throw new Error(result.stderr || 'Snapshot failed');
    if (target !== readingTarget) return;
    data = JSON.parse(result.stdout);
    failure = '';
  } catch (error) {
    if (target === readingTarget) failure = 'Refresh failed: ' + String(error.message || error);
  } finally {
    refreshing = false;
    $.ui.invalidate('ui.render');
  }
}

export function register(on) {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'field-team', description: 'Open Xsolla Field Team; optionally specify a run path', immediate: true });
    target = e.cwd;
    await refresh($);
    timer?.cancel();
    // No timer in print mode, where background work could keep the process open.
    if (e.isInteractive) timer = $.clock.every(5000, async () => { await refresh($); });
    return next(e);
  });

  on('session.end', async ($, e, next) => {
    timer?.cancel();
    timer = undefined;
    return next(e);
  });

  on('command.run', { command: 'field-team' }, async ($, e) => {
    const requested = e.args.trim();
    const selected = requested || await $.session.cwd();
    if (target !== selected) {
      data = { run: null, message: 'Loading selected run…' };
      failure = '';
    }
    target = selected;
    await refresh($);
    await $.ui.open({ id: PANE, title: 'Xsolla Field Team', focus: true, closeOnEscape: true });
    return {};
  });

  on('turn.complete', async ($, e, next) => {
    const result = await next(e);
    if (!e.agentId) await refresh($);
    return result;
  });

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const rest = await next(e);
    if (!data.run && !failure) return rest;
    const { Box, Text } = $.ui.resolve(e);
    const summary = failure ? 'Field Team · stale · /field-team' :
      `Field Team${data.demo ? ' · DEMO' : ''} · ${data.progress}% verified · ${(data.approvals || []).length} need you · /field-team`;
    return Box({ flexDirection: 'column', children: [rest, Text({ color: failure ? 'yellow' : 'cyan', children: summary })] });
  });

  on('ui.render', { component: 'Pane' }, async ($, e, next) => {
    if (e.requestId !== PANE) return next(e);
    const { Box, Text, Button } = $.ui.resolve(e);
    const text = (value) => Text({ children: String(value || '') });
    const tabs = ['party', 'needs-you', 'activity'].map((name) => Button({
      key: 'tab-' + name, label: name === 'needs-you' ? 'Needs you' : name === 'party' ? 'Party' : 'Activity',
      plain: true, dimColor: tab !== name,
      onPress: () => { tab = name; $.ui.invalidate('ui.render'); },
    }));
    let body = [text(data.message)];
    if (data.run) {
      if (tab === 'party') {
        const boss = data.orchestrator || {};
        body = [text(`${boss.name || 'Orchestrator'} · ${boss.model || 'model not recorded'} · ${boss.status || 'status not recorded'}`),
          text(`${data.progress}% verified · $${data.spend_usd ?? 0} recorded spend`),
          ...(data.workers || []).map((worker) => Box({ flexDirection: 'column', children: [
            Text({ bold: true, children: `${worker.character?.name || worker.id} · ${worker.state}` }),
            text(`${worker.model || 'unrouted'} / ${worker.effort || 'effort not recorded'}`),
            text(worker.objective || worker.title), text(worker.last_action),
          ] })),
        ];
      } else if (tab === 'needs-you') {
        body = [...(data.approvals || []).map((request) => Box({ flexDirection: 'column', children: [
          Text({ bold: true, children: `${request.id} · ${request.kind || 'Request'}` }),
          text(request.target), text(request.text),
        ] })), text(`${(data.decisions || []).length} decision(s) recorded; execution is tracked separately.`),
        text('Review requests with the supervising conversation. A draft grants no permission.'),
        Button({ key: 'review', label: 'Review in chat', onPress: async () => {
          await $.prompt.fill({ text: `Review pending requests in ${data.run}. Explain the exact targets and actions and ask for any required authorization.` });
        } })];
      } else {
        body = (data.activity || []).map((item) => text(`${item.at || ''} · ${item.agent || ''} · ${item.text || ''}`));
        if (!body.length) body = [text('No recorded activity yet.')];
      }
    }
    return Box({ flexDirection: 'column', children: [
      Text({ bold: true, color: 'cyan', children: data.demo ? 'Xsolla Field Team · DEMONSTRATION' : 'Xsolla Field Team' }),
      text(data.goal || data.title), text(data.run), ...(failure ? [text(failure + ' · showing the last snapshot')] : []),
      Box({ flexDirection: 'row', columnGap: 1, children: tabs }), ...body,
      Button({ key: 'refresh', label: 'Refresh', onPress: async () => { await refresh($); } }),
    ] });
  });
}
