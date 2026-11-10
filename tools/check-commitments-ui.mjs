import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const source = await readFile(new URL('../channel/web/static/js/chat/commitments.js', import.meta.url), 'utf8');
const styles = await readFile(new URL('../channel/web/static/css/commitments.css', import.meta.url), 'utf8');
const personalStyles = await readFile(new URL('../channel/web/static/css/personal.css', import.meta.url), 'utf8');
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
      endpoint: 'https://example.org/api', read_authorized: true, initiative_enabled: true,
      read_grant: { expires_at: 1799999999, min_interval_seconds: 60 },
      grant: { grant_id: 'grant-1', agent_id: 'agent-a', commitment_id: 'c"1', operation: 'read', resource: 'https://example.org/api', status: 'active', effective_status: 'authorized', authorized: true, expires_at: 1799999999, min_interval_seconds: 60, read_only: true, individual_approval_required: false, internal_writes: 'commitment state' },
      schedule: null, source_seq: 0, next_action: 'Check "this"', pending_decisions: '',
      last_attempt: 0, last_success: null, last_selected: [{ id: 0, title: 'Story "zero"', url: 'https://news.example/story/0' }, { id: 'old', title: 'Older selected story', url: 'https://older.example/story' }],
      runs: [{ run_id: 'r2', status: 'delivered', started_at: 1, briefing: 'No new stories found.', selected: [] }, { run_id: 'r1', status: 'uncertain', started_at: 0, error: 'run lease expired' }, { run_id: 'r0', status: 'delivered', started_at: 0, briefing: 'See [Story](https://news.example/story/0)\n<script>data</script>', selected: [{ id: 0, title: 'Story "zero"', url: 'https://news.example/story/0', pub_date: '2026-11-10', sources: [{ publisher: 'Wire A', source_url: 'https://wire-a.example/article/1', source_id: 'wire-a' }, { publisher: '<img src=x onerror="alert(1)">', source_url: 'https://wire-b.example/article/2', source_id: 'wire-b' }] }] }],
      followups: [{ text: 'Revisit old topic', source_ids: ['old'] }, { text: 'Preserve explicit source reference', sources: [{ publisher: 'Follow-up Archive', source_url: 'https://followup-archive.example/item' }], source_ids: ['old'] }],
      drafts: [{ item_id: 'draft-1', text: 'Draft with old source', status: 'awaiting_publication_approval', source_ids: ['old'], sources: [{ publisher: 'Draft Archive', source_url: 'https://draft-archive.example/item' }], claims: ['Retained claim'] }] },
    { commitment_id: 'c2', objective: 'Two successive reports', priority: 2, status: 'active', revision: 1, endpoint: 'https://example.org/news', read_authorized: true,
      last_selected: [{ id: 'story-b', title: 'Story B', source_url: 'https://news.example/b' }], followups: [], drafts: [],
      runs: [{ run_id: 'b', status: 'delivered', selected: [{ id: 'story-b', title: 'Story B', source_url: 'https://news.example/b' }], articles: [{ id: 'unreported', title: 'Not reported', source_url: 'https://news.example/unreported' }] },
        { run_id: 'a', status: 'delivered', selected: [{ id: 'story-a', title: 'Story A', source_url: 'https://news.example/a' }] }] }
  ], attention: [
    { attention_id: 'finding-1', commitment_id: 'c"1', kind: 'finding', status: 'unread', created_at: 3, payload: { action: '<img src=x>', reason: 'New story', sources: [{ title: 'safe source', url: 'https://news.example/new' }, { title: 'bad', url: 'javascript:alert(1)' }] } },
    { attention_id: 'decision-1', commitment_id: 'c"1', kind: 'decision', status: 'pending', created_at: 1, payload: { action: 'Review social draft', reason: 'Needs owner approval', scope: 'Prepare a post only', sources: [{ title: 'Decision source', url: 'https://news.example/decision' }] } },
    { attention_id: 'failed-1', commitment_id: 'c2', kind: 'failure', status: 'blocked', created_at: 2, payload: { action: 'News check', reason: 'The check was blocked.' } },
    { attention_id: 'dismissed-1', commitment_id: 'c2', kind: 'finding', status: 'dismissed', dismissed_at: 4, created_at: 0, payload: { action: 'Old item' } },
    { attention_id: 'approved-1', commitment_id: 'c2', kind: 'decision', status: 'approved', created_at: 5, payload: { action: 'Approved request', execution_status: 'blocked', execution_reason: 'unsupported connector' } },
    { attention_id: 'denied-1', commitment_id: 'c2', kind: 'decision', status: 'denied', created_at: 6, payload: { action: 'Denied request' } },
    { attention_id: 'resolved-1', commitment_id: 'c2', kind: 'finding', status: 'resolved', created_at: 7, payload: { action: 'Resolved finding' } },
    { attention_id: 'stale-1', commitment_id: 'c2', kind: 'decision', status: 'pending', stale: true, created_at: 8, payload: { action: 'Earlier draft approval' } }
  ], attention_history: [
    { attention_id: 'finding-1', commitment_id: 'c"1', kind: 'finding', status: 'unread', created_at: 3, payload: { action: '<img src=x>', reason: 'New story', sources: [{ title: 'safe source', url: 'https://news.example/new' }, { title: 'bad', url: 'javascript:alert(1)' }] } },
    { attention_id: 'decision-1', commitment_id: 'c"1', kind: 'decision', status: 'pending', created_at: 1, payload: { action: 'Review social draft', reason: 'Needs owner approval', scope: 'Prepare a post only', sources: [{ title: 'Decision source', url: 'https://news.example/decision' }] } },
    { attention_id: 'failed-1', commitment_id: 'c2', kind: 'failure', status: 'blocked', created_at: 2, payload: { action: 'News check', reason: 'The check was blocked.' } },
    { attention_id: 'dismissed-1', commitment_id: 'c2', kind: 'finding', status: 'dismissed', dismissed_at: 4, created_at: 0, payload: { action: 'Old item' } },
    { attention_id: 'approved-1', commitment_id: 'c2', kind: 'decision', status: 'approved', created_at: 5, payload: { action: 'Approved request', execution_status: 'blocked', execution_reason: 'unsupported connector' } },
    { attention_id: 'denied-1', commitment_id: 'c2', kind: 'decision', status: 'denied', created_at: 6, payload: { action: 'Denied request' } },
    { attention_id: 'resolved-1', commitment_id: 'c2', kind: 'finding', status: 'resolved', created_at: 7, payload: { action: 'Resolved finding' } },
    { attention_id: 'stale-1', commitment_id: 'c2', kind: 'decision', status: 'pending', stale: true, created_at: 8, payload: { action: 'Earlier draft approval' } }
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
assert.match(content.innerHTML, /<label class="commitments-check"><input name="read_authorized" type="checkbox"[^>]*> I explicitly authorize read-only access to this endpoint<\/label>/);
assert.match(content.innerHTML, /name="initiative_enabled" type="checkbox" checked/);
assert.match(content.innerHTML, /name="read_grant_min_interval_seconds" type="number" min="0" step="1" value="60"/);
assert.match(content.innerHTML, /name="read_grant_expires_at" type="datetime-local" value="2027-/);
assert.match(content.innerHTML, /Derived grant contract/);
assert.match(content.innerHTML, /Grant status: active \(authorized\)/);
assert.match(content.innerHTML, /Owner agent: agent-a/);
assert.match(content.innerHTML, /Exact resource: <a href="https:\/\/example\.org\/api"/);
assert.match(content.innerHTML, /Operation: read/);
assert.match(content.innerHTML, /frequency: at most once per 60 seconds/);
assert.match(content.innerHTML, /External publication: not allowed/);
assert.match(content.innerHTML, /Completed/);
assert.match(content.innerHTML, /Needs your attention/);
assert.ok(content.innerHTML.indexOf('Review social draft') < content.innerHTML.indexOf('&lt;img src=x&gt;'));
assert.ok(content.innerHTML.indexOf('Review social draft') < content.innerHTML.indexOf('News check'));
assert.match(content.innerHTML, /Dismiss notification/);
assert.match(content.innerHTML, /data-commitments-attention="dismiss" data-commitments-id="c2" data-attention-id="failed-1"/);
assert.match(content.innerHTML, /Show decision and notification history \(5\)/);
assert.equal((content.innerHTML.match(/Approved request/g) || []).length, 1); // Terminal items stay in history only.
assert.equal((content.innerHTML.match(/Resolved finding/g) || []).length, 1);
assert.equal((content.innerHTML.match(/<strong>Earlier draft approval<\/strong>/g) || []).length, 1); // Stale approvals appear once, in history.
const staleDecisionCard = content.innerHTML.slice(content.innerHTML.indexOf('Earlier draft approval'));
assert.match(staleDecisionCard, /Needs renewed review/);
assert.match(staleDecisionCard, /Earlier scope — superseded by commitment changes/);
assert.doesNotMatch(staleDecisionCard, /data-commitments-attention="approve"/);
assert.match(staleDecisionCard, /data-commitments-attention="deny"/);
assert.match(staleDecisionCard, /data-commitments-attention="dismiss"/);
assert.match(content.innerHTML, /href="https:\/\/news\.example\/new"/);
assert.doesNotMatch(content.innerHTML, /href="javascript:/);
assert.match(content.innerHTML, /Propose publication for review/);
assert.match(content.innerHTML, /data-commitments-propose="draft-1"/); // Store snapshots use item_id.
assert.match(content.innerHTML, /does not publish the post/);
assert.match(content.innerHTML, /Approve request/);
assert.match(content.innerHTML, /Approval records the decision\. It does not publish/);
const pendingDecisionCard = content.innerHTML.slice(content.innerHTML.indexOf('Review social draft'), content.innerHTML.indexOf('News check'));
assert.match(pendingDecisionCard, /Waiting for approval/);
assert.doesNotMatch(pendingDecisionCard, /Approved for review/);
const approvedDecisionCard = content.innerHTML.slice(content.innerHTML.indexOf('Approved request'), content.innerHTML.indexOf('Denied request'));
assert.match(approvedDecisionCard, /Approved for review\. No post was published/);
assert.match(approvedDecisionCard, /Execution blocked: unsupported connector/);
assert.doesNotMatch(approvedDecisionCard, /data-commitments-attention=/);
const dismissedCard = content.innerHTML.slice(content.innerHTML.indexOf('Old item'), content.innerHTML.indexOf('Approved request'));
assert.match(dismissedCard, />Dismissed</);
assert.doesNotMatch(dismissedCard, /data-commitments-attention=/);

const editedFields = context.commitmentsFormFields({
  objective: 'Objective', preferences: '', priority: '3', endpoint: 'https://example.org/api',
  read_authorized: '', initiative_enabled: '', read_grant_min_interval_seconds: '60',
  read_grant_expires_at: '', schedule_enabled: ''
});
assert.equal(editedFields.read_authorized, false); // Owner can revoke the read grant in update.
assert.equal(editedFields.initiative_enabled, false); // Initiative is an explicit owner choice.
assert.deepEqual(JSON.parse(JSON.stringify(editedFields.read_grant)), { expires_at: null, min_interval_seconds: 60 });

// At a short, narrow viewport, expanded commitments and continuity stay bounded
// and scrollable so the chat and composer retain viewport space.
assert.match(styles, /\.chat-main:has\(#commitments-card > details\[open\]\) #commitments-card \{ max-height: 24vh; \}/);
assert.match(styles, /\.chat-main:has\(#commitments-card > details\[open\]\) #personal-card \{ max-height: 18vh; \}/);
assert.match(styles, /\.commitments-card\s*\{[^}]*overflow:\s*auto;/);
assert.match(personalStyles, /\.personal-card\s*\{[^}]*overflow:\s*auto;/);

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

// Attention actions and publication proposals use the current authenticated scope and source turn.
const runAttentionAction = async (decision, attentionId, commitmentId = 'c"1') => {
  const before = requests.length;
  handlers.click({ target: { closest: () => ({ dataset: {
    commitmentsAttention: decision, attentionId, commitmentsId: commitmentId
  } }) } });
  await new Promise(resolve => setTimeout(resolve, 0));
  const request = requests.slice(before).find(item => item.init.method === 'POST');
  assert.ok(request, `missing POST for ${decision}`);
  return JSON.parse(request.init.body);
};
for (const decision of ['approve', 'deny', 'dismiss']) {
  const actionBody = await runAttentionAction(decision, `attention-${decision}`);
  assert.equal(actionBody.operation, 'decide_attention');
  assert.equal(actionBody.commitment_id, 'c"1');
  assert.equal(actionBody.attention_id, `attention-${decision}`);
  assert.equal(actionBody.decision, decision);
  assert.equal(actionBody.source_seq, 0);
  assert.match(requests.at(-2).url, /^\/api\/commitments\/session-a\?agent_id=agent-a$/);
}
let beforeProposal = requests.length;
handlers.click({ target: { closest: () => ({ dataset: { commitmentsPropose: 'draft-1', commitmentsId: 'c"1' } }) } });
await new Promise(resolve => setTimeout(resolve, 0));
const proposalRequest = requests.slice(beforeProposal).find(item => item.init.method === 'POST');
const proposalBody = JSON.parse(proposalRequest.init.body);
assert.equal(proposalBody.operation, 'propose_publication');
assert.equal(proposalBody.commitment_id, 'c"1');
assert.equal(proposalBody.draft_id, 'draft-1');
assert.equal(proposalBody.source_seq, 0);
assert.equal(proposalBody.expires_at, null);
assert.equal(Object.hasOwn(proposalBody, 'text'), false); // Server binds immutable draft content and sources.

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
