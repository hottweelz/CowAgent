import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const source = await readFile(new URL('../channel/web/static/js/chat/commitments.js', import.meta.url), 'utf8');
const styles = await readFile(new URL('../channel/web/static/css/commitments.css', import.meta.url), 'utf8');
const personalStyles = await readFile(new URL('../channel/web/static/css/personal.css', import.meta.url), 'utf8');
const handlers = {};
const panelStorage = new Map();
const card = {
  addEventListener(name, handler) { handlers[name] = handler; },
  querySelectorAll() { return []; },
  contains() { return false; }
};
const status = { textContent: '', isError: false, classList: { toggle(name, value) { if (name === 'is-error') status.isError = !!value; } } };
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
    { attention_id: 'specialist-tip', commitment_id: 'c"1', kind: 'finding', status: 'unread', created_at: 9, payload: { action: 'ask_specialist', reason: 'Compare the reported change across the two supplied sources.', source_ids: ['0'] } },
    { attention_id: 'finding-1', commitment_id: 'c"1', kind: 'finding', status: 'unread', created_at: 3, payload: { action: '<img src=x>', reason: 'New story', sources: [{ title: 'safe source', url: 'https://news.example/new' }, { title: 'bad', url: 'javascript:alert(1)' }] } },
    { attention_id: 'decision-1', commitment_id: 'c"1', kind: 'decision', status: 'pending', created_at: 1, payload: { action: 'Review social draft', reason: 'Needs owner approval', scope: 'Prepare a post only', sources: [{ title: 'Decision source', url: 'https://news.example/decision' }] } },
    { attention_id: 'failed-1', commitment_id: 'c2', kind: 'failure', status: 'blocked', created_at: 2, payload: { action: 'News check', reason: 'The check was blocked.' } },
    { attention_id: 'dismissed-1', commitment_id: 'c2', kind: 'finding', status: 'dismissed', dismissed_at: 4, created_at: 0, payload: { action: 'Old item' } },
    { attention_id: 'approved-1', commitment_id: 'c2', kind: 'decision', status: 'approved', created_at: 5, payload: { action: 'Approved request', execution_status: 'blocked', execution_reason: 'unsupported connector' } },
    { attention_id: 'denied-1', commitment_id: 'c2', kind: 'decision', status: 'denied', created_at: 6, payload: { action: 'Denied request' } },
    { attention_id: 'resolved-1', commitment_id: 'c2', kind: 'finding', status: 'resolved', created_at: 7, payload: { action: 'Resolved finding' } },
    { attention_id: 'stale-1', commitment_id: 'c2', kind: 'decision', status: 'pending', stale: true, created_at: 8, payload: { action: 'Earlier draft approval' } }
  ], specialists: [{ agent_id: 'specialist-1', name: 'Source Analyst', description: 'Registered public profile', provider: 'OpenAI', model: 'gpt-6.1-luna' }], research: [
    { research_id: 'research-pending', commitment_id: 'c"1', revision: 2, status: 'pending', target: { agent_id: 'specialist-1', name: 'Source Analyst', description: 'Registered public profile', provider: 'OpenAI', model: 'gpt-6.1-luna' }, question: 'Compare the source reports.', sources: [{ source_id: '0', headline: 'Story "zero"', publisher: 'Wire A', source_url: 'https://news.example/story/0', description: 'Delivered <script>metadata</script>', content: 'Exact useful excerpt & source text.' }], source_ids: ['0'], expires_at: 1799999999 },
    { research_id: 'research-approved', commitment_id: 'c"1', revision: 2, status: 'approved', target: { agent_id: 'specialist-1', name: 'Source Analyst', provider: 'OpenAI', model: 'gpt-6.1-luna' }, question: 'Approved question.', sources: [{ id: 0, title: 'Story "zero"', url: 'https://news.example/story/0' }], source_ids: ['0'] },
    { research_id: 'research-completed', commitment_id: 'c"1', revision: 2, status: 'completed', target: { agent_id: 'specialist-1', name: 'Source Analyst', provider: 'OpenAI', model: 'gpt-6.1-luna' }, question: 'Completed question.', sources: [{ id: 0, title: 'Story "zero"', url: 'https://news.example/story/0' }], source_ids: ['0'], result: { findings: [{ source_id: '0', excerpt: 'The source reports a verified change.', classification: 'material_update', priority: 4, publisher: 'Wire A', source_url: 'https://wire-a.example/article/1' }], verification: 'source references validated' }, receipt: { status: 'completed', target: { agent_id: 'specialist-1', name: 'Source Analyst' }, session_id: 'private-session', run_id: 'private-run', tool_count: 0 } },
    { research_id: 'research-history', commitment_id: 'c"1', revision: 2, status: 'pending', can_mutate: false, source_session_id: 'origin-session', target: { agent_id: 'specialist-1', name: 'Source Analyst' }, question: 'History question.', sources: [], source_ids: [] },
    { research_id: 'research-denied', commitment_id: 'c"1', revision: 2, status: 'denied', target: { agent_id: 'specialist-1', name: 'Source Analyst' }, question: 'Denied question.', sources: [], source_ids: [] },
    { research_id: 'research-failed', commitment_id: 'c"1', revision: 2, status: 'failed', target: { agent_id: 'specialist-1', name: 'Source Analyst' }, question: 'Failed question.', sources: [], source_ids: [] },
    { research_id: 'research-uncertain', commitment_id: 'c"1', revision: 2, status: 'uncertain', target: { agent_id: 'specialist-1', name: 'Source Analyst' }, question: 'Uncertain question.', sources: [], source_ids: [] },
    { research_id: 'research-expired', commitment_id: 'c"1', revision: 2, status: 'expired', target: { agent_id: 'specialist-1', name: 'Source Analyst' }, question: 'Expired question.', sources: [], source_ids: [] }
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
  localStorage: { getItem: key => panelStorage.get(key) ?? null, setItem: (key, value) => panelStorage.set(key, value) },
  FormData: class { constructor(form) { this.values = form.values || {}; } entries() { return Object.entries(this.values); } },
  document: { getElementById: id => elements.get(id) || null, querySelectorAll: () => [], visibilityState: 'visible', activeElement: null },
  escapeHtml: value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;'),
  requestAuthGatedStart: fn => fn(), fetch: (...args) => fetchImpl(...args)
};
vm.createContext(context);
vm.runInContext(source, context, { filename: 'commitments.js' });
vm.runInContext(`globalThis.setPanelHarness = (dialog, toggle, summary) => { _commitmentsPanelDialog = dialog; _commitmentsPanelToggle = toggle; _commitmentsPanelSummary = summary; _commitmentsPanelAgent = commitmentsOwnerId(); }; globalThis.updatePanelSummary = snapshot => { _commitmentsSnapshot = snapshot; commitmentsUpdatePanelSummary(); }; globalThis.setPanelOpen = commitmentsSetPanelOpen; globalThis.restorePanelState = commitmentsRestorePanelState; globalThis.setPanelReady = value => { _commitmentsPanelReady = value; }; globalThis.panelPreferenceKey = commitmentsPanelPreferenceKey;`, context);

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
assert.match(content.innerHTML, /Registered specialist/);
assert.match(content.innerHTML, /Source Analyst — OpenAI \/ gpt-6\.1-luna/);
assert.match(content.innerHTML, /Prepare request for owner review/);
assert.match(content.innerHTML, /Only verified source excerpts and classifications return/);
assert.match(content.innerHTML, /Exact sources shared/);
assert.match(content.innerHTML, /Exact useful excerpt &amp; source text\./);
assert.match(content.innerHTML, /Delivered &lt;script&gt;metadata&lt;\/script&gt;/);
assert.doesNotMatch(content.innerHTML, /<script>metadata/);
assert.match(content.innerHTML, /Draft request for owner review/);
assert.match(content.innerHTML, /This suggestion only fills a draft\. It does not approve or execute research/);
assert.match(content.innerHTML, /Source-backed findings/);
assert.match(content.innerHTML, /The source reports a verified change\./);
assert.match(content.innerHTML, /Classification: material_update · Priority: 4/);
assert.match(content.innerHTML, /href="https:\/\/wire-a\.example\/article\/1"[^>]*>Open cited source<\/a>/);
assert.doesNotMatch(content.innerHTML, /private-session|private-run/);
assert.match(content.innerHTML, /data-research-decision="approve" data-research-id="research-pending"/);
assert.match(content.innerHTML, /data-research-decision="deny" data-research-id="research-pending"/);
assert.equal((content.innerHTML.match(/data-research-execute=/g) || []).length, 1);
assert.match(content.innerHTML, /data-research-execute="research-approved"/);
assert.match(content.innerHTML, /This request belongs to another conversation/);
assert.match(content.innerHTML, /data-research-open-session="origin-session" data-agent="agent-a">Open original conversation/);
assert.doesNotMatch(content.innerHTML, /data-research-decision="approve" data-research-id="research-history"/);
assert.doesNotMatch(content.innerHTML, /data-research-execute="research-history"/);
assert.match(content.innerHTML, /Denied\. The specialist was not asked to run this request/);
assert.match(content.innerHTML, /The research request failed\. It was not retried/);
assert.match(content.innerHTML, /The execution outcome is uncertain\. It was not retried/);
assert.match(content.innerHTML, /This request expired without further execution/);
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

// An ask_specialist attention item only prefills a draft. It does not choose a target or execute.
const formValues = { commitment_id: 'c"1', target_agent_id: 'specialist-1', question: '', attention_id: '' };
const questionField = { get value() { return formValues.question; }, set value(value) { formValues.question = value; }, focus() { this.focused = true; } };
const attentionField = { get value() { return formValues.attention_id; }, set value(value) { formValues.attention_id = value; } };
const sourceOption = { value: '0', selected: false };
const sourceSelect = { options: [sourceOption], get selectedOptions() { return this.options.filter(option => option.selected); } };
const researchDetails = { open: false };
const researchForm = {
  values: formValues,
  dataset: { commitmentsForm: 'prepare_research' },
  closest: selector => selector === 'form[data-commitments-form]' ? researchForm : selector === 'details' ? researchDetails : null,
  querySelector(selector) {
    if (selector === '[name="commitment_id"]') return { value: formValues.commitment_id };
    if (selector === '[name="question"]') return questionField;
    if (selector === '[name="attention_id"]') return attentionField;
    if (selector === '[name="source_ids"]') return sourceSelect;
    return null;
  }
};
context.document.querySelectorAll = () => [researchForm];
handlers.click({ target: { closest: () => ({ dataset: { researchSuggestion: 'specialist-tip', commitmentsId: 'c"1' } }) } });
assert.equal(formValues.question, 'Compare the reported change across the two supplied sources.');
assert.equal(formValues.attention_id, 'specialist-tip');
assert.equal(sourceOption.selected, true);
assert.equal(researchDetails.open, true);
assert.equal(questionField.focused, true);

const beforeResearchPrepare = requests.length;
context.commitmentsHandleSubmit({ target: { closest: () => researchForm }, preventDefault() {} });
await new Promise(resolve => setTimeout(resolve, 0));
const prepareRequest = requests.slice(beforeResearchPrepare).find(item => item.init.method === 'POST');
assert.ok(prepareRequest);
const prepareBody = JSON.parse(prepareRequest.init.body);
assert.equal(prepareBody.operation, 'prepare_research');
assert.equal(prepareBody.commitment_id, 'c"1');
assert.equal(prepareBody.source_seq, 0);
assert.equal(prepareBody.target_agent_id, 'specialist-1');
assert.deepEqual(prepareBody.source_ids, ['0']);
assert.equal(prepareBody.question, 'Compare the reported change across the two supplied sources.');
assert.equal(prepareBody.attention_id, 'specialist-tip');
assert.deepEqual(Object.keys(prepareBody).sort(), ['attention_id', 'commitment_id', 'operation', 'question', 'source_ids', 'source_seq', 'target_agent_id']);

// Approval and execution are distinct owner operations; terminal records expose no execute control.
const researchAction = async (operation, extra) => {
  const before = requests.length;
  await context.commitmentsSubmit(operation, { extra });
  const request = requests.slice(before).find(item => item.init.method === 'POST');
  assert.ok(request);
  return JSON.parse(request.init.body);
};
const approveResearchBody = await researchAction('decide_research', { research_id: 'research-pending', decision: 'approve' });
assert.deepEqual(approveResearchBody, { operation: 'decide_research', source_seq: 0, research_id: 'research-pending', decision: 'approve' });
const denyResearchBody = await researchAction('decide_research', { research_id: 'research-pending', decision: 'deny' });
assert.deepEqual(denyResearchBody, { operation: 'decide_research', source_seq: 0, research_id: 'research-pending', decision: 'deny' });
const executeResearchBody = await researchAction('execute_research', { research_id: 'research-approved' });
assert.deepEqual(executeResearchBody, { operation: 'execute_research', source_seq: 0, research_id: 'research-approved' });

// An uncertain execution result must not claim completion and must use error status.
fetchImpl = async (url, init = {}) => {
  requests.push({ url, init });
  return { ok: true, status: 200, json: async () => ({ status: 'success', research_operation: { status: 'uncertain' }, identity: { name: 'Owner' }, commitments: [], attention: [], specialists: [], research: [] }) };
};
await context.commitmentsSubmit('execute_research', { extra: { research_id: 'research-uncertain' } });
assert.equal(status.textContent, 'Research outcome is uncertain. No automatic retry was made.');
assert.equal(status.isError, true);
assert.doesNotMatch(status.textContent, /completed|Verified findings are shown/);

// An approval request that returns expired must not claim it was approved.
fetchImpl = async (url, init = {}) => {
  requests.push({ url, init });
  return { ok: true, status: 200, json: async () => ({ status: 'success', research_operation: { status: 'expired' }, identity: { name: 'Owner' }, commitments: [], attention: [], specialists: [], research: [] }) };
};
await context.commitmentsSubmit('decide_research', { extra: { research_id: 'research-pending', decision: 'approve' } });
assert.equal(status.textContent, 'Research request expired. No execution was performed.');
assert.equal(status.isError, false);
assert.doesNotMatch(status.textContent, /approved|Execution remains a separate action/);
let openedResearchSession = null;
context.switchSession = (sid, agent) => { openedResearchSession = { sid, agent }; };
handlers.click({ target: { closest: () => ({ dataset: { researchOpenSession: 'origin-session', agent: 'agent-a' } }) } });
assert.deepEqual(openedResearchSession, { sid: 'origin-session', agent: 'agent-a' });

// An unavailable registered target is a visible non-error outcome; it leaves owner analysis available.
fetchImpl = async (url, init = {}) => {
  requests.push({ url, init });
  return { ok: true, status: 200, json: async () => ({ status: 'success', source_seq: 0,
    research_operation: { status: 'unavailable', reason: 'No eligible registered specialist is available.' },
    identity: { name: 'Owner' }, commitments: [], attention: [], specialists: [], research: [] }) };
};
await context.commitmentsSubmit('prepare_research', { commitmentId: 'c1', extra: { target_agent_id: 'missing', source_ids: ['0'], question: 'Question' } });
assert.match(status.textContent, /No eligible registered specialist is available/);
assert.match(status.textContent, /BullGod can continue its own analysis/);

// Compact controls stay content-sized; editor dialogs own scrolling.
assert.match(styles, /\.commitments-panel-toggle\s*\{[^}]*max-width:\s*100%/);
assert.match(styles, /\.commitments-dialog\s*\{[^}]*max-height:\s*calc\(100dvh - 1rem\);[^}]*overflow:\s*auto;/);
assert.match(personalStyles, /\.owner-controls\s*\{[^}]*flex-wrap:\s*wrap/);
assert.match(personalStyles, /\.personal-dialog\s*\{[^}]*max-height:\s*calc\(100dvh - 1rem\);[^}]*overflow:\s*auto;/);

// Status labels use current owner data and a due label only when the scheduler
// supplies a valid schedule pointer and its next run has passed.
const panelSummary = { textContent: '' };
let dialogOpen = false;
let focusCount = 0;
const panelDialog = { get open() { return dialogOpen; }, showModal() { dialogOpen = true; }, close() { dialogOpen = false; } };
const panelToggle = { attrs: {}, setAttribute(name, value) { this.attrs[name] = value; }, focus() { focusCount++; } };
context.setPanelHarness(panelDialog, panelToggle, panelSummary);
context.updatePanelSummary({
  source_seq: 0,
  attention: [{ status: 'unread' }, { status: 'pending', stale: true }],
  research_requests: [{ status: 'pending' }, { status: 'pending', can_mutate: false }],
  commitments: [{ status: 'active', schedule_status: 'scheduled', next_run_at: '2000-01-01T00:00:00+00:00' }]
});
assert.equal(panelSummary.textContent, '1 need attention · 1 research request open · 1 check due');
context.updatePanelSummary({ source_seq: 0, commitments: [{ status: 'active', schedule_status: 'unavailable', next_run_at: '2000-01-01T00:00:00+00:00' }] });
assert.equal(panelSummary.textContent, '1 active commitment', 'an unavailable scheduler pointer must not be reported as due');
assert.notEqual(context.panelPreferenceKey('agent-a'), context.panelPreferenceKey('agent-b'), 'panel preference keys must be agent scoped');
panelStorage.set(context.panelPreferenceKey('agent-a'), 'open');
context.restorePanelState();
assert.equal(dialogOpen, false, 'saved state must not open before authenticated panel readiness');
context.setPanelReady(true);
context.restorePanelState();
assert.equal(dialogOpen, true);
assert.equal(panelToggle.attrs['aria-expanded'], 'true');
assert.equal(panelStorage.get(context.panelPreferenceKey('agent-a')), 'open');
context.setPanelOpen(false);
assert.equal(dialogOpen, false);
assert.equal(panelToggle.attrs['aria-expanded'], 'false');
assert.equal(panelStorage.get(context.panelPreferenceKey('agent-a')), 'closed');
assert.equal(focusCount, 1, 'closing an open editor returns focus to its header');

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

// A late research response from an old conversation cannot replace the switched view.
context.document.visibilityState = 'visible';
context.sessionId = 'session-a';
context.commitmentsBeginSession('session-a');
fetchImpl = async (url, init = {}) => {
  requests.push({ url, init });
  if (init.method === 'POST') return new Promise(resolve => { releaseResearchPost = resolve; });
  return { ok: true, status: 200, json: async () => ({ status: 'success', source_seq: 0, identity: { name: 'Owner' }, commitments: [], attention: [], specialists: [], research: [] }) };
};
let releaseResearchPost;
context.commitmentsMarkPersistedTurn('session-a');
await new Promise(resolve => setTimeout(resolve, 0));
const staleResearch = context.commitmentsSubmit('execute_research', { extra: { research_id: 'research-old' } });
await new Promise(resolve => setTimeout(resolve, 0));
context.sessionId = 'session-b';
context.commitmentsBeginSession('session-b');
const switchedResearchContent = content.innerHTML;
releaseResearchPost({ ok: true, status: 200, json: async () => ({ status: 'success', identity: { name: 'Old owner' }, commitments: [] }) });
await staleResearch;
assert.equal(content.innerHTML, switchedResearchContent);
assert.match(status.textContent, /Send a message in this conversation/);

// With no registered target or delivered source, the form is unavailable and the commitment stays intact.
context.commitmentsRender({ identity: { name: 'Owner' }, commitments: [{ commitment_id: 'c-active', objective: 'Continue research', status: 'active', revision: 1 }], specialists: [], research: [], attention: [] });
assert.match(content.innerHTML, /No eligible registered specialist or delivered source is available/);
assert.match(content.innerHTML, /BullGod can continue its own analysis; your commitment remains active/);
assert.doesNotMatch(content.innerHTML, /data-research-execute=/);

console.log('Commitments UI checks passed.');
