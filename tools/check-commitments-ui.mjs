import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const source = await readFile(new URL('../channel/web/static/js/chat/commitments.js', import.meta.url), 'utf8');
const handlers = {};
const card = {
  addEventListener(name, handler) { handlers[name] = handler; },
  querySelectorAll() { return []; },
  contains() { return false; }
};
const status = { textContent: '', classList: { toggle() {} } };
const identity = { textContent: '' };
const content = { innerHTML: 'initial' };
let messages = [{ dataset: { seq: '0' } }];
const elements = new Map([
  ['commitments-card', card], ['commitments-status', status],
  ['commitments-identity', identity], ['commitments-content', content]
]);
const loadHandlers = [];
const requests = [];
let fetchImpl = async (url, init = {}) => {
  requests.push({ url, init });
  return { ok: true, status: 200, json: async () => ({ status: 'success', source_seq: 0, identity: { name: 'O"<wner' }, commitments: [
    { commitment_id: 'c"1', objective: '<img src=x onerror="alert(1)">', preferences: ['A & B'], priority: 3, status: 'active', revision: 2,
      endpoint: 'https://example.org/api', read_authorized: true, schedule: null, source_seq: 0, next_action: 'Check "this"', pending_decisions: '',
      last_attempt: 0, last_success: null, last_selected: [{ id: 0, title: 'Story "zero"', url: 'https://news.example/story/0' }, { id: 'old', title: 'Older selected story', url: 'https://older.example/story' }],
      runs: [{ run_id: 'r2', status: 'delivered', started_at: 1, briefing: 'No new stories found.', selected: [] }, { run_id: 'r1', status: 'uncertain', started_at: 0, error: 'run lease expired' }, { run_id: 'r0', status: 'delivered', started_at: 0, briefing: 'See [Story](https://news.example/story/0)\n<script>data</script>', selected: [{ id: 0, title: 'Story "zero"', url: 'https://news.example/story/0', pub_date: '2026-11-10', sources: [{ publisher: 'Wire A', source_url: 'https://wire-a.example/article/1', source_id: 'wire-a' }, { publisher: '<img src=x onerror="alert(1)">', source_url: 'https://wire-b.example/article/2', source_id: 'wire-b' }] }] }],
      followups: [{ text: 'Revisit old topic', source_ids: ['old'] }, { text: 'Preserve explicit source reference', sources: [{ publisher: 'Follow-up Archive', source_url: 'https://followup-archive.example/item' }], source_ids: ['old'] }],
      drafts: [{ text: 'Draft with old source', status: 'awaiting_publication_approval', source_ids: ['old'], sources: [{ publisher: 'Draft Archive', source_url: 'https://draft-archive.example/item' }], claims: ['Retained claim'] }] },
    { commitment_id: 'c2', objective: 'Two successive reports', priority: 2, status: 'active', revision: 1, endpoint: 'https://example.org/news', read_authorized: true,
      last_selected: [{ id: 'story-b', title: 'Story B', source_url: 'https://news.example/b' }], followups: [], drafts: [],
      runs: [{ run_id: 'b', status: 'delivered', selected: [{ id: 'story-b', title: 'Story B', source_url: 'https://news.example/b' }], articles: [{ id: 'unreported', title: 'Not reported', source_url: 'https://news.example/unreported' }] },
        { run_id: 'a', status: 'delivered', selected: [{ id: 'story-a', title: 'Story A', source_url: 'https://news.example/a' }] }] }
  ] }) };
};

const context = {
  console, URL, Date, JSON, Number, String, Object, Array, Set, Promise, Math,
  crypto: { randomUUID: () => 'request-uuid-1' }, setInterval: fn => { context.pollHandler = fn; return 1; },
  activeAgentId: 'agent-a', defaultAgentId: 'default', sessionId: 'session-a',
  appConfig: { web_password_masked: '********' }, messagesDiv: { querySelectorAll: () => messages },
  window: { location: { href: 'https://console.example/' }, addEventListener: (name, fn) => { if (name === 'load') loadHandlers.push(fn); } },
  document: { getElementById: id => elements.get(id) || null, visibilityState: 'visible', activeElement: null },
  escapeHtml: value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;'),
  requestAuthGatedStart: fn => fn(), fetch: (...args) => fetchImpl(...args)
};
vm.createContext(context);
vm.runInContext(source, context, { filename: 'commitments.js' });

context.commitmentsBeginSession('session-a');
context.commitmentsMarkPersistedTurn('session-a');
await new Promise(resolve => setTimeout(resolve, 0));
assert.match(requests[0].url, /^\/api\/commitments\/session-a\?agent_id=agent-a$/);
assert.match(content.innerHTML, /&lt;img src=x onerror=&quot;alert\(1\)&quot;&gt;/);
assert.doesNotMatch(content.innerHTML, /<img src=x/);
assert.match(content.innerHTML, /value="0"/); // Article ID zero is valid.
assert.match(content.innerHTML, /Story &quot;zero&quot;/);
assert.match(content.innerHTML, /href="https:\/\/news\.example\/story\/0"/);
assert.match(content.innerHTML, /href="https:\/\/news\.example\/story\/0" target="_blank"/);
assert.match(content.innerHTML, /href="https:\/\/wire-a\.example\/article\/1"[^>]*>Wire A<\/a>/);
assert.match(content.innerHTML, /href="https:\/\/wire-b\.example\/article\/2"[^>]*>&lt;img src=x onerror=&quot;alert\(1\)&quot;&gt;<\/a>/);
assert.doesNotMatch(content.innerHTML, /<img src=x onerror/);
assert.match(content.innerHTML, /&lt;script&gt;data&lt;\/script&gt;/);
assert.match(content.innerHTML, /2026-11-10/);
assert.match(content.innerHTML, /&quot;this&quot;/);
assert.match(content.innerHTML, /Acknowledge uncertain run and allow a fresh read/);
assert.match(content.innerHTML, /Draft only — publication requires separate approval/);
assert.match(content.innerHTML, /Previously reported sources/);
assert.match(content.innerHTML, /option value="0">Story &quot;zero&quot;<\/option>/);
assert.match(content.innerHTML, /No new stories found/);
assert.match(content.innerHTML, /href="https:\/\/older\.example\/story"[^>]*>Older selected story<\/a>/);
assert.match(content.innerHTML, /href="https:\/\/followup-archive\.example\/item"[^>]*>Follow-up Archive<\/a>/);
assert.match(content.innerHTML, /href="https:\/\/draft-archive\.example\/item"[^>]*>Draft Archive<\/a>/);
assert.match(content.innerHTML, /<optgroup label="Latest report"><option value="story-b">Story B<\/option><\/optgroup><optgroup label="Previously reported sources"><option value="story-a">Story A<\/option><\/optgroup>/);
assert.doesNotMatch(content.innerHTML, /option value="unreported"/);
assert.match(content.innerHTML, /value="https:\/\/tyl\.ee\/api\/news"/);
assert.match(content.innerHTML, /name="read_authorized" type="checkbox"/);

// Snapshot source_seq remains usable when the conversation DOM has no messages.
messages = [];
await context.commitmentsSubmit('run', { commitmentId: 'c0' });
const snapshotBody = JSON.parse(requests.findLast(request => request.init.method === 'POST').init.body);
assert.equal(snapshotBody.source_seq, 0);
assert.equal(snapshotBody.request_id, 'request-uuid-1');
messages = [{ dataset: { seq: '0' } }];

// Acknowledgement is an owner action and does not use the ordinary run body.
fetchImpl = async (url, init = {}) => {
  requests.push({ url, init });
  return { ok: true, status: 200, json: async () => ({ status: 'success', source_seq: 0, commitments: [] }) };
};
await context.commitmentsSubmit('acknowledge_run', { commitmentId: 'c1', extra: { run_id: 'r1' } });
const ackBody = JSON.parse(requests.findLast(request => request.init.method === 'POST').init.body);
assert.equal(ackBody.operation, 'acknowledge_run');
assert.equal(ackBody.commitment_id, 'c1');
assert.equal(ackBody.run_id, 'r1');
assert.equal(ackBody.source_seq, 0);
assert.equal(Object.hasOwn(ackBody, 'fields'), false);

// A delayed GET from an old conversation must not replace the new session view.
let releaseGet;
fetchImpl = () => new Promise(resolve => { releaseGet = resolve; });
const staleGet = context.refreshCommitments();
context.sessionId = 'session-b';
context.commitmentsBeginSession('session-b');
const switchedContent = content.innerHTML;
releaseGet({ ok: true, status: 200, json: async () => ({ status: 'success', commitments: [] }) });
await staleGet;
assert.equal(content.innerHTML, switchedContent);

// A delayed POST is fenced after a conversation switch and run sends no fields.
context.sessionId = 'session-a';
context.commitmentsBeginSession('session-a');
context.commitmentsMarkPersistedTurn('session-a');
await new Promise(resolve => setTimeout(resolve, 0));
let releasePost;
fetchImpl = (url, init) => {
  requests.push({ url, init });
  if (init.method === 'POST') return new Promise(resolve => { releasePost = resolve; });
  return Promise.resolve({ ok: true, status: 200, json: async () => ({ status: 'success', commitments: [] }) });
};
const stalePost = context.commitmentsSubmit('run', { commitmentId: 'c1' });
await new Promise(resolve => setTimeout(resolve, 0));
const post = requests.at(-1);
const body = JSON.parse(post.init.body);
assert.equal(post.init.method, 'POST');
assert.equal(body.operation, 'run');
assert.equal(body.commitment_id, 'c1');
assert.equal(body.source_seq, 0);
assert.equal(body.request_id, 'request-uuid-1');
assert.equal(Object.hasOwn(body, 'fields'), false);
context.sessionId = 'session-b';
context.commitmentsBeginSession('session-b');
releasePost({ ok: true, status: 200, json: async () => ({ status: 'success' }) });
await stalePost;
assert.equal(content.innerHTML, '<p class="commitments-muted">Start or reopen a conversation to review its owner commitments.</p>');

// Visible polling waits when a card control is focused or the page is hidden.
context.commitmentsBeginSession('session-b');
context.commitmentsMarkPersistedTurn('session-b');
await new Promise(resolve => setTimeout(resolve, 0));
const beforePoll = requests.length;
context.document.activeElement = {};
card.contains = () => true;
context.pollHandler();
context.document.activeElement = null;
context.document.visibilityState = 'hidden';
context.pollHandler();
await new Promise(resolve => setTimeout(resolve, 0));
assert.equal(requests.length, beforePoll);

console.log('Commitments UI checks passed.');
