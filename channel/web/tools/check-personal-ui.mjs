import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../static/js/chat/personal.js', import.meta.url), 'utf8');
const nodes = new Map();
for (const id of ['personal-card', 'personal-status', 'personal-content', 'personal-identity']) {
  nodes.set(id, { id, innerHTML: '', textContent: '', classList: { toggle() {} }, addEventListener() {}, querySelectorAll: () => [] });
}
const calls = [];
const panelStorage = new Map();
let pendingFetch = null;
const queuedFetches = [];
const context = {
  console,
  URL,
  Date,
  Number,
  JSON,
  FormData,
  Map,
  setTimeout,
  clearTimeout,
  activeAgentId: 'owner-1',
  defaultAgentId: 'owner-1',
  appConfig: { web_password_masked: '' },
  sessionId: 'session-a',
  messagesDiv: { querySelectorAll: () => [] },
  document: { getElementById: id => nodes.get(id) || null },
  window: { addEventListener() {} },
  localStorage: { getItem: key => panelStorage.get(key) ?? null, setItem: (key, value) => panelStorage.set(key, value) },
  requestAuthGatedStart() {},
  escapeHtml(value) {
    // Match core/utils.js: its text-node helper escapes markup characters,
    // but it does not encode quotes for quoted attribute values.
    return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  },
  fetch(url, init = {}) {
    calls.push(url);
    if (pendingFetch) {
      const request = pendingFetch;
      pendingFetch = null;
      return request;
    }
    if (queuedFetches.length) return queuedFetches.shift()(url, init);
    return Promise.resolve({ ok: true, status: 200, json: async () => ({
      status: 'success', identity: { name: 'BullGod' }, latest_source_seq: 0,
      continuity: { goal: 'Cedar" autofocus onfocus="alert(1)', progress: '', pending_decision: '', next_step: '', revision: 1, source_seq: 0, updated_at: 1700000000 },
      memories: [{ memory_id: 'm1', text: '<script>bad()</script>', source_seq: 0, created_at: 1700000000, revision: 1 }],
      recent_goals: [], actions: [
        { action_id: 'pending" onmouseover="alert(2)', path: 'notes.txt', content: '<exact content>', status: 'pending', source_seq: 0, expires_at: 1700000600 },
        { action_id: 'approved-1', path: 'approved.txt', content: 'approved body', status: 'approved', source_seq: 0 }
      ], capabilities: { status: 'loaded', permission_mode: 'read_only', tools: [{ name: 'write', allowed: false, reason: 'workspace-only' }], skills: [{ name: 'checklist', description: 'Create a checklist' }], limits: 'Call limits apply' },
      memory_retention_note: 'Transcript retained separately.'
    }) });
  }
};
vm.createContext(context);
vm.runInContext(`${source}\n;globalThis.__personal = { refreshPersonalContinuity, personalSubmit, personalMarkPersistedTurn, personalBeginSession, personalLatestUserSeq, personalUpdatePanelSummary, personalSetPanelOpen, personalRestorePanelState, personalPanelPreferenceKey, setPanelReady: value => { _personalPanelReady = value; }, setPanelHarness: (dialog, toggle, summary) => { _personalPanelDialog = dialog; _personalPanelToggle = toggle; _personalPanelSummary = summary; _personalPanelAgent = personalOwnerId(); }, getPersisted: () => _personalHasPersistedTurn };`, context);

assert.equal(await context.__personal.refreshPersonalContinuity(), undefined);
assert.equal(calls.length, 0, 'must not call API before a saved owner turn exists');
context.__personal.personalMarkPersistedTurn('session-a');
await new Promise(resolve => setImmediate(resolve));
assert.equal(calls.length, 0, 'must not call owner API without authenticated-console configuration');
context.appConfig.web_password_masked = '********';
context.__personal.personalMarkPersistedTurn('session-a');
await new Promise(resolve => setImmediate(resolve));
assert.equal(calls.length, 1);
assert.match(calls[0], /agent_id=owner-1/);
assert.equal(context.__personal.personalLatestUserSeq(), 0, 'sequence zero is valid');
assert.match(nodes.get('personal-content').innerHTML, /value="Cedar&quot; autofocus onfocus=&quot;alert\(1\)"/);
assert.doesNotMatch(nodes.get('personal-content').innerHTML, /value="Cedar" autofocus/,
  'quotes in owner text must not escape a quoted form attribute');
assert.match(nodes.get('personal-content').innerHTML, /data-personal-approve="pending&quot; onmouseover=&quot;alert\(2\)"/);
assert.doesNotMatch(nodes.get('personal-content').innerHTML, /data-personal-approve="pending" onmouseover=/,
  'quotes in action IDs must not escape a quoted data attribute');
assert.doesNotMatch(nodes.get('personal-content').innerHTML, /<script>bad\(\)<\/script>/);
assert.match(nodes.get('personal-content').innerHTML, /Transcript retained separately\./);
assert.match(nodes.get('personal-content').innerHTML, /&lt;exact content&gt;/);
assert.doesNotMatch(nodes.get('personal-content').innerHTML, /<exact content>/);
assert.match(nodes.get('personal-content').innerHTML, /Approve and execute once/);
assert.match(nodes.get('personal-content').innerHTML, /Execute approved action once/);
assert.match(nodes.get('personal-content').innerHTML, /not allowed in current mode: workspace-only/);
assert.doesNotMatch(nodes.get('personal-content').innerHTML, /type="submit" disabled>Save goal/,
  'sequence zero must enable explicit owner save');

const panelSummary = { textContent: '' };
let dialogOpen = false;
let focusCount = 0;
const panelDialog = { get open() { return dialogOpen; }, showModal() { dialogOpen = true; }, close() { dialogOpen = false; } };
const panelToggle = { attrs: {}, setAttribute(name, value) { this.attrs[name] = value; }, focus() { focusCount++; } };
context.__personal.setPanelHarness(panelDialog, panelToggle, panelSummary);
context.__personal.personalUpdatePanelSummary();
assert.equal(panelSummary.textContent, '2 open actions');
assert.notEqual(context.__personal.personalPanelPreferenceKey('owner-1'), context.__personal.personalPanelPreferenceKey('owner-2'),
  'panel preference keys must be agent scoped');
panelStorage.set(context.__personal.personalPanelPreferenceKey('owner-1'), 'open');
context.__personal.personalRestorePanelState();
assert.equal(dialogOpen, false, 'saved state must not open before authenticated panel readiness');
context.__personal.setPanelReady(true);
context.__personal.personalRestorePanelState();
assert.equal(dialogOpen, true);
assert.equal(panelToggle.attrs['aria-expanded'], 'true');
assert.equal(panelStorage.get(context.__personal.personalPanelPreferenceKey('owner-1')), 'open');
context.__personal.personalSetPanelOpen(false);
assert.equal(dialogOpen, false);
assert.equal(panelToggle.attrs['aria-expanded'], 'false');
assert.equal(panelStorage.get(context.__personal.personalPanelPreferenceKey('owner-1')), 'closed');
assert.equal(focusCount, 1, 'closing an open editor returns focus to its header');

let finish;
pendingFetch = new Promise(resolve => { finish = resolve; });
const stale = context.__personal.refreshPersonalContinuity(true);
context.activeAgentId = 'owner-2';
context.__personal.personalBeginSession('session-a');
finish({ ok: true, status: 200, json: async () => ({ status: 'success', identity: { name: 'Old session' }, memories: [], continuity: {}, actions: [] }) });
await stale;
assert.equal(nodes.get('personal-identity').textContent, '', 'stale agent response must not render');
pendingFetch = null;
context.activeAgentId = 'owner-1';
context.__personal.personalBeginSession('session-a');
context.__personal.personalMarkPersistedTurn('session-a');
await new Promise(resolve => setImmediate(resolve));

// A GET that started before a forget mutation must not restore the old fact.
let finishOldGet;
pendingFetch = new Promise(resolve => { finishOldGet = resolve; });
const oldGet = context.__personal.refreshPersonalContinuity(true);
queuedFetches.push(() => Promise.resolve({ ok: true, status: 200, json: async () => ({
  status: 'success', identity: { name: 'BullGod' }, latest_source_seq: 0,
  continuity: {}, memories: [], recent_goals: [], actions: [], capabilities: { tools: [], skills: [] }
}) }));
assert.equal(await context.__personal.personalSubmit('forget_memory', { memory_id: 'm1', revision: 1 }), true);
finishOldGet({ ok: true, status: 200, json: async () => ({
  status: 'success', identity: { name: 'Old GET' }, latest_source_seq: 0,
  continuity: {}, memories: [{ memory_id: 'm1', text: 'forgotten fact' }],
  recent_goals: [], actions: [], capabilities: { tools: [], skills: [] }
}) });
await oldGet;
assert.doesNotMatch(nodes.get('personal-content').innerHTML, /forgotten fact/,
  'a pre-mutation GET must not restore forgotten memory');

// A POST from session A must not render after A -> B -> A, even though the
// visible agent and session IDs match again when the response arrives.
let finishOldMutation;
pendingFetch = new Promise(resolve => { finishOldMutation = resolve; });
const oldMutation = context.__personal.personalSubmit('forget_memory', { memory_id: 'm1', revision: 1 });
context.sessionId = 'session-b';
context.__personal.personalBeginSession('session-b');
context.sessionId = 'session-a';
context.__personal.personalBeginSession('session-a');
finishOldMutation({ ok: true, status: 200, json: async () => ({
  status: 'success', identity: { name: 'Stale mutation' }, memories: [], continuity: {}, actions: []
}) });
assert.equal(await oldMutation, false);
assert.equal(nodes.get('personal-identity').textContent, '', 'away/back mutation response must stay stale');
console.log('personal UI checks passed');
