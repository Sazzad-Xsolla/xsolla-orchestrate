import { expect, mock, test } from 'claude-code/testing';

const PANE = {
  plugin: 'xsolla-orchestrate', component: 'Pane', requestId: 'xsolla-field-team',
  viewport: { columns: 120, rows: 40 },
  props: { title: 'Xsolla Field Team', isFocused: true, bodyColumns: 60,
    placement: 'inline', scroll: { offset: 0, bodyRows: 20 }, view: {} },
} as const;

const snapshot = {
  run: '/work/.xsolla-orchestrator/run', goal: 'Ship checkout', progress: 50,
  demo: true, spend_usd: 1.25, orchestrator: { name: 'Atlas', model: 'opus', status: 'working' },
  workers: [{ id: 't1', state: 'verified', model: 'sonnet', effort: 'medium', objective: 'Fix totals' }],
  approvals: [{ id: 'a1', kind: 'publish', target: 'staging', text: 'Publish checkout' }],
  decisions: [], activity: [{ agent: 't1', text: 'Tests pass' }],
};

test('native pane renders party and requests on terminal and desktop; review only fills a draft', async ($, on) => {
  let draft = '';
  on('process.run', ($, e) => {
    expect(e.argv[0]).toBe('python3');
    expect(e.argv[1].endsWith('/scripts/mod_snapshot.py')).toBe(true);
    expect(e.argv[2]).toBe('/work');
    return { value: { exitCode: 0, stdout: JSON.stringify(snapshot), stderr: '' } };
  });
  on('session.cwd', () => ({ value: '/work' }));
  on('ui.open', () => ({ value: { isPlaced: true } }));
  on('prompt.fill', ($, e) => { draft = e.text; return { isFilled: true }; });
  await $.command.run({ command: 'field-team', args: '' });
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface });
    expect(await ui.find({ type: 'Text', text: 't1 · verified' })).toBeDefined();
    expect(await ui.find({ type: 'Text', text: /DEMONSTRATION/ })).toBeDefined();
    await ui.press({ key: 'tab-needs-you' });
    expect(await ui.find({ type: 'Text', text: 'Publish checkout' })).toBeDefined();
    await ui.press({ key: 'review' });
    expect(draft).toContain(snapshot.run);
    await ui.press({ key: 'tab-activity' });
    expect(await ui.find({ type: 'Text', text: /Tests pass/ })).toBeDefined();
    await ui.press({ key: 'tab-party' });
    await ui.unmount();
  }
});

test('a process failure is visible and does not claim fresh progress', async ($, on) => {
  on('process.run', () => ({ value: { exitCode: 1, stdout: '', stderr: 'Cannot read run' } }));
  on('ui.open', () => ({ value: { isPlaced: true } }));
  await $.command.run({ command: 'field-team', args: '/missing' });
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' });
  expect(await ui.find({ type: 'Text', text: /Refresh failed: Cannot read run/ })).toBeDefined();
});

test('interactive refresh stops when the session ends', async ($, on) => {
  const clock = mock.clock(on);
  let reads = 0;
  on('command.register', () => ({ value: undefined }));
  on('process.run', () => {
    reads += 1;
    return { value: { exitCode: 0, stdout: JSON.stringify(snapshot), stderr: '' } };
  });
  on('session.start', () => ({ cwd: '/work' }));
  on('session.end', () => ({ sessionId: 'test' }));
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/work' });
  expect(reads).toBe(1);
  await clock.advance(5000);
  expect(reads).toBe(2);
  await $.session.end({ reason: 'other' });
  await clock.advance(10000);
  expect(reads).toBe(2);
});
