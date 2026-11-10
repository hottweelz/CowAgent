/* Owner-confirmed personal commitments for the native web conversation. */
let _commitmentsGeneration = 0;
let _commitmentsPersistedTurn = false;
let _commitmentsBusy = false;
let _commitmentsSnapshot = null;
let _commitmentsShownSession = '';
let _commitmentsPanelDialog = null;
let _commitmentsPanelToggle = null;
let _commitmentsPanelSummary = null;
let _commitmentsPanelAgent = '';
let _commitmentsPanelReady = false;
let _commitmentsPanelRestoredAgent = null;

function commitmentsOwnerId() {
    return activeAgentId || defaultAgentId || '';
}

function commitmentsOwnerAuthReady() {
    return !!(appConfig && appConfig.web_password_masked);
}

function commitmentsPanelPreferenceKey(agentId = commitmentsOwnerId()) {
    return `cowagent:owner-panel:commitments:${encodeURIComponent(agentId || 'default')}`;
}

function commitmentsSavePanelOpen(open, agentId = _commitmentsPanelAgent) {
    try { localStorage.setItem(commitmentsPanelPreferenceKey(agentId), open ? 'open' : 'closed'); } catch (_) { /* Storage can be disabled. */ }
}

function commitmentsSetPanelOpen(open, persist = true) {
    if (!_commitmentsPanelDialog || !_commitmentsPanelToggle) return;
    const wasOpen = _commitmentsPanelDialog.open;
    if (open) {
        const current = window.__cowOwnerDialog;
        if (current && current.panel !== 'commitments') current.close();
        window.__cowOwnerDialog = { panel: 'commitments', close: () => commitmentsSetPanelOpen(false) };
        if (!_commitmentsPanelDialog.open) _commitmentsPanelDialog.showModal();
    } else if (_commitmentsPanelDialog.open) {
        _commitmentsPanelDialog.close();
    }
    _commitmentsPanelToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (persist) commitmentsSavePanelOpen(open);
    if (!open) {
        if (window.__cowOwnerDialog && window.__cowOwnerDialog.panel === 'commitments') window.__cowOwnerDialog = null;
        if (wasOpen) _commitmentsPanelToggle.focus();
    }
}

function commitmentsRestorePanelState() {
    const agentId = commitmentsOwnerId();
    if (!_commitmentsPanelReady || !commitmentsOwnerAuthReady()) return;
    const view = document.getElementById('view-chat');
    if (view && view.classList && !view.classList.contains('active')) return;
    if (_commitmentsPanelRestoredAgent === agentId) return;
    if (agentId !== _commitmentsPanelAgent) {
        if (_commitmentsPanelDialog && _commitmentsPanelDialog.open) commitmentsSetPanelOpen(false, false);
        _commitmentsPanelAgent = agentId;
    }
    commitmentsApplyPanelPreference(agentId);
}

function commitmentsApplyPanelPreference(agentId = commitmentsOwnerId()) {
    const view = document.getElementById('view-chat');
    if (!_commitmentsPanelReady || !commitmentsOwnerAuthReady() || (view && view.classList && !view.classList.contains('active'))) return;
    _commitmentsPanelAgent = agentId;
    let open = false;
    try { open = localStorage.getItem(commitmentsPanelPreferenceKey(agentId)) === 'open'; } catch (_) { /* Default closed. */ }
    commitmentsSetPanelOpen(open, false);
    _commitmentsPanelRestoredAgent = agentId;
}

function commitmentsSetupPanel() {
    const card = document.getElementById('commitments-card');
    if (!card || typeof document.createElement !== 'function' || !card.appendChild) return;
    const editor = card.querySelector('details');
    if (!editor) return;
    const dialog = document.createElement('dialog');
    dialog.id = 'commitments-dialog';
    dialog.className = 'commitments-dialog';
    dialog.setAttribute('aria-labelledby', 'commitments-title');
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'commitments-panel-toggle';
    toggle.setAttribute('aria-controls', dialog.id);
    toggle.setAttribute('aria-expanded', 'false');
    const title = document.createElement('span');
    title.className = 'commitments-panel-title';
    title.textContent = 'Personal commitments';
    const summary = document.createElement('span');
    summary.className = 'commitments-panel-summary';
    summary.textContent = 'Waiting for saved commitments';
    toggle.append(title, summary);
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'commitments-refresh commitments-dialog-close';
    close.textContent = 'Close';
    close.setAttribute('aria-label', 'Close personal commitments');
    close.addEventListener('click', () => commitmentsSetPanelOpen(false));
    dialog.appendChild(close);
    editor.open = true;
    while (card.firstChild && card.firstChild !== editor) card.removeChild(card.firstChild);
    dialog.appendChild(editor);
    card.append(toggle, dialog);
    toggle.addEventListener('click', () => commitmentsSetPanelOpen(!dialog.open));
    dialog.addEventListener('close', () => {
        if (dialog.open) return;
        toggle.setAttribute('aria-expanded', 'false');
        toggle.focus();
    });
    dialog.addEventListener('cancel', event => {
        event.preventDefault();
        commitmentsSetPanelOpen(false);
    });
    _commitmentsPanelDialog = dialog;
    _commitmentsPanelToggle = toggle;
    _commitmentsPanelSummary = summary;
    _commitmentsPanelAgent = commitmentsOwnerId();
    commitmentsSetPanelOpen(false, false);
}

function commitmentsUpdatePanelSummary() {
    if (!_commitmentsPanelSummary) return;
    const snapshot = _commitmentsSnapshot;
    if (!snapshot) {
        _commitmentsPanelSummary.textContent = 'Waiting for saved commitments';
        return;
    }
    const attention = Array.isArray(snapshot.attention) ? snapshot.attention
        : Array.isArray(snapshot.attention_history) ? snapshot.attention_history : [];
    const actionableAttention = attention.filter(item => item && !item.stale && !item.dismissed_at
        && ['pending', 'unread', 'blocked', 'uncertain'].includes(item.status));
    const research = Array.isArray(snapshot.research_requests) ? snapshot.research_requests
        : Array.isArray(snapshot.research) ? snapshot.research : [];
    const pendingResearch = research.filter(item => item && item.can_mutate !== false
        && ['pending', 'approved', 'executing'].includes(item.status)).length;
    const commitments = Array.isArray(snapshot.commitments) ? snapshot.commitments : [];
    const now = Date.now();
    const due = commitments.filter(item => {
        if (!item || item.status !== 'active' || item.schedule_status !== 'scheduled') return false;
        const nextRun = item.scheduler_next_run || item.next_run_at;
        if (!nextRun) return false;
        const timestamp = typeof nextRun === 'number' ? nextRun * 1000 : new Date(nextRun).getTime();
        return Number.isFinite(timestamp) && timestamp <= now;
    }).length;
    const parts = [];
    if (actionableAttention.length) parts.push(`${actionableAttention.length} need attention`);
    if (pendingResearch) parts.push(`${pendingResearch} research request${pendingResearch === 1 ? '' : 's'} open`);
    if (due) parts.push(`${due} check${due === 1 ? '' : 's'} due`);
    if (!parts.length) {
        const active = commitments.filter(item => item && item.status === 'active').length;
        parts.push(`${active} active commitment${active === 1 ? '' : 's'}`);
    }
    _commitmentsPanelSummary.textContent = parts.join(' · ');
}

function commitmentsEscape(value) {
    return escapeHtml(value == null ? '' : String(value))
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function commitmentsText(value) {
    return value == null ? '' : String(value);
}

function commitmentsPublicReason(value) {
    if (typeof value !== 'string' || value.length > 240 || /^[\s]*[\[{]/.test(value)
        || /(?:traceback|stack|exception|\bat\s+\S+\s*\(|(?:^|\s)[A-Za-z]:\\|(?:^|\s)\/(?:[^\s:]+\/)+)/i.test(value)) return '';
    return value;
}

function commitmentsResearchStatus(status, operation) {
    const messages = {
        pending: operation === 'prepare_research'
            ? 'Research request prepared. Review the target, question, and exact sources before approving or denying it.'
            : 'Research is waiting for owner approval. No execution occurred.',
        approved: 'Research approved. Execution remains a separate action.',
        denied: 'Research denied. The specialist was not asked to run it.',
        expired: 'Research request expired. No execution was performed.',
        executing: 'Research is in progress. No second execution was started.',
        completed: 'Approved research completed. Verified findings are shown in the commitment and owner conversation.',
        failed: 'Research failed. No automatic retry was made.',
        uncertain: 'Research outcome is uncertain. No automatic retry was made.'
    };
    return {
        message: messages[status] || (operation === 'execute_research'
            ? 'Research status is unknown. Completion was not confirmed.'
            : 'Research status is unknown. Review the current request.'),
        error: status === 'failed' || status === 'uncertain'
    };
}

function commitmentsDate(value) {
    if (value == null || value === '') return 'Not recorded';
    const date = typeof value === 'number' ? new Date(value * 1000) : new Date(value);
    return Number.isNaN(date.getTime()) ? commitmentsEscape(value) : commitmentsEscape(date.toLocaleString());
}

function commitmentsDateTimeLocal(value) {
    if (value == null || value === '') return '';
    const date = new Date(typeof value === 'number' ? value * 1000 : value);
    if (Number.isNaN(date.getTime())) return '';
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 16);
}

function commitmentsStatusLabel(value) {
    const labels = {
        delivered: 'Completed', completed: 'Completed', awaiting_approval: 'Waiting for approval',
        waiting_approval: 'Waiting for approval', pending_decision: 'Waiting for approval',
        pending: 'Waiting for approval', scheduled: 'Scheduled', paused: 'Paused',
        failed: 'Failed', uncertain: 'Uncertain', blocked: 'Blocked', active: 'Active', unread: 'Unread',
        approved: 'Approved for review', denied: 'Denied', resolved: 'Resolved', dismissed: 'Dismissed', expired: 'Expired',
        executing: 'In progress', completed: 'Completed'
    };
    return labels[value] || (value ? String(value).replaceAll('_', ' ') : 'Unknown');
}

function commitmentsSourceSeq() {
    const nodes = messagesDiv ? [...messagesDiv.querySelectorAll('.user-message-group[data-seq]')] : [];
    const seqs = nodes.map(node => Number(node.dataset.seq)).filter(Number.isFinite);
    if (seqs.length) return Math.max(...seqs);
    const list = _commitmentsSnapshot && (_commitmentsSnapshot.source_seq ?? _commitmentsSnapshot.latest_source_seq);
    return list == null ? null : Number(list);
}

function commitmentsStatus(message, error = false) {
    const el = document.getElementById('commitments-status');
    if (!el) return;
    el.textContent = message;
    el.classList.toggle('is-error', !!error);
    if (_commitmentsPanelSummary && (error || !_commitmentsSnapshot)) {
        _commitmentsPanelSummary.textContent = error ? 'Commitments unavailable'
            : /loading/i.test(message) ? 'Loading commitments…'
                : /sign in|authenticated/i.test(message) ? 'Sign in to review commitments'
                    : 'Waiting for saved commitments';
    }
}

function commitmentsBusy(disabled) {
    const card = document.getElementById('commitments-card');
    if (!card) return;
    card.querySelectorAll('button').forEach(button => {
        if (button.classList.contains('commitments-panel-toggle') || button.classList.contains('commitments-dialog-close')) return;
        if (disabled) {
            button.dataset.commitmentsDisabledBeforeBusy = button.disabled ? 'true' : 'false';
            button.disabled = true;
        } else if (button.dataset.commitmentsDisabledBeforeBusy !== undefined) {
            button.disabled = button.dataset.commitmentsDisabledBeforeBusy === 'true';
            delete button.dataset.commitmentsDisabledBeforeBusy;
        }
    });
}

function commitmentsCanMutate() {
    return _commitmentsPersistedTurn && commitmentsSourceSeq() != null
        && !!sessionId && !!commitmentsOwnerId() && !_commitmentsBusy;
}

function commitmentsSafeUrl(value) {
    try {
        const url = new URL(String(value || ''), window.location.href);
        return url.protocol === 'https:' ? url.href : '';
    } catch (_) {
        return '';
    }
}

function commitmentsApprovedEndpointList(items) {
    if (!Array.isArray(items)) return [];
    return items.map(item => typeof item === 'string' ? item : item && (item.url || item.endpoint || item.href))
        .filter(value => typeof value === 'string' && commitmentsSafeUrl(value));
}

function commitmentsLink(url, label) {
    const safe = commitmentsSafeUrl(url);
    return safe
        ? `<a href="${commitmentsEscape(safe)}" target="_blank" rel="noopener noreferrer">${commitmentsEscape(label || safe)}</a>`
        : commitmentsEscape(label || url || 'Source unavailable');
}

function commitmentsArticleId(article) {
    if (!article || typeof article !== 'object') return '';
    const value = article.id ?? article.article_id ?? article.identity;
    return value == null ? '' : String(value);
}

function commitmentsSources(items) {
    if (!Array.isArray(items) || !items.length) return '<p class="commitments-muted">No source links recorded.</p>';
    const seen = new Set();
    const sources = [];
    for (const item of items) {
        if (!item || typeof item !== 'object') continue;
        const id = commitmentsArticleId(item);
        const key = id || String(item.url || item.link || item.title || sources.length);
        if (seen.has(key)) continue;
        seen.add(key);
        const title = item.title || item.headline || item.publisher || item.url || item.link || `Source ${sources.length + 1}`;
        const href = item.url || item.link || item.source_url || '';
        const published = item.pubDate || item.pub_date || item.published_at || item.publication_date;
        const nested = Array.isArray(item.sources) ? item.sources : [];
        const nestedLinks = [];
        for (const source of nested) {
            if (!source || typeof source !== 'object') continue;
            const sourceUrl = source.source_url || source.url || source.link || '';
            const safeUrl = commitmentsSafeUrl(sourceUrl);
            if (!safeUrl || safeUrl === commitmentsSafeUrl(href) || nestedLinks.some(entry => entry.url === safeUrl)) continue;
            nestedLinks.push({
                url: safeUrl,
                label: source.publisher || source.source_id || source.title || safeUrl
            });
        }
        sources.push(`<li>${commitmentsLink(href, title)}${item.publisher ? ` <span class="commitments-muted">· ${commitmentsEscape(item.publisher)}</span>` : ''}${published ? ` <span class="commitments-muted">· ${commitmentsEscape(published)}</span>` : ''}${nestedLinks.length ? `<ul class="commitments-source-list">${nestedLinks.map(source => `<li>Additional report: ${commitmentsLink(source.url, source.label)}</li>`).join('')}</ul>` : ''}</li>`);
    }
    return sources.length ? `<ul class="commitments-source-list">${sources.join('')}</ul>` : '<p class="commitments-muted">No source links recorded.</p>';
}

function commitmentsBriefing(run) {
    if (!run) return '<p class="commitments-muted">No briefing recorded yet.</p>';
    const text = run.briefing || run.last_briefing || '';
    const sources = Array.isArray(run.selected) ? run.selected
        : Array.isArray(run.last_selected) ? run.last_selected
            : (Array.isArray(run.articles) ? run.articles : []);
    return `${text ? `<p class="commitments-briefing-text">${commitmentsMarkdown(text)}</p>` : '<p class="commitments-muted">No briefing text was saved.</p>'}${commitmentsSources(sources)}`;
}

function commitmentsMarkdown(value) {
    const text = String(value || '');
    const linkPattern = /\[([^\]\n]{1,500})\]\((https:\/\/[^\s)]+)\)/g;
    let output = '';
    let cursor = 0;
    for (const match of text.matchAll(linkPattern)) {
        const index = match.index ?? 0;
        output += commitmentsEscape(text.slice(cursor, index));
        const href = commitmentsSafeUrl(match[2]);
        output += href ? `<a href="${commitmentsEscape(href)}" target="_blank" rel="noopener noreferrer">${commitmentsEscape(match[1])}</a>`
            : commitmentsEscape(match[0]);
        cursor = index + match[0].length;
    }
    output += commitmentsEscape(text.slice(cursor));
    return output.replaceAll('\n', '<br>');
}

function commitmentsRunState(run) {
    const status = commitmentsEscape(commitmentsStatusLabel(run.status));
    const error = run.error ? `<p class="commitments-error">${commitmentsEscape(run.error)}</p>` : '';
    const acknowledge = run.status === 'uncertain' && run.run_id
        ? `<button type="button" data-commitments-ack="${commitmentsEscape(run.run_id || '')}" data-commitments-id="${commitmentsEscape(run.commitment_id || '')}">Acknowledge uncertain run and allow a fresh read</button><p class="commitments-muted">Acknowledgement does not mark this run delivered.</p>` : '';
    return `<li><strong>${status}</strong><span class="commitments-muted"> · Started ${commitmentsDate(run.started_at)}${run.finished_at ? ` · Finished ${commitmentsDate(run.finished_at)}` : ''}</span>${error}${acknowledge}${commitmentsBriefing(run)}</li>`;
}

function commitmentsAttentionRank(item) {
    if (item.status === 'pending') return item.kind === 'decision' ? 0 : 1;
    if (item.kind === 'failure' || item.status === 'blocked' || item.status === 'uncertain') return 1;
    if (item.kind === 'finding' && item.status === 'unread') return 2;
    return 3;
}

function commitmentsAttentionText(value) {
    if (typeof value === 'string') return value;
    return value == null ? '' : JSON.stringify(value);
}

function commitmentsResearchResult(record) {
    const result = record && record.result;
    if (!result || typeof result !== 'object' || Array.isArray(result)) return '';
    const findings = Array.isArray(result.findings) ? result.findings : [];
    if (!findings.length) return '<p class="commitments-muted">The specialist completed the review and found no source-backed findings.</p>';
    return `<h5>Source-backed findings</h5><ul class="commitments-record-list">${findings.map(finding => {
        if (!finding || typeof finding !== 'object') return '';
        const sourceId = finding.source_id == null ? '' : String(finding.source_id);
        const sourceUrl = finding.source_url || '';
        const publisher = finding.publisher || `Source ${sourceId || 'unavailable'}`;
        return `<li><strong>${commitmentsEscape(publisher)}</strong>${sourceId ? `<span class="commitments-muted"> · Source ID ${commitmentsEscape(sourceId)}</span>` : ''}<p class="commitments-briefing-text">${commitmentsEscape(finding.excerpt || '')}</p><p class="commitments-muted">Classification: ${commitmentsEscape(finding.classification || 'Not provided')} · Priority: ${commitmentsEscape(finding.priority ?? 'Not provided')}</p>${sourceUrl ? commitmentsLink(sourceUrl, 'Open cited source') : '<p class="commitments-muted">Source link unavailable.</p>'}</li>`;
    }).join('')}</ul>`;
}

function commitmentsResearchSources(items) {
    if (!Array.isArray(items) || !items.length) return '<p class="commitments-muted">No source material is available.</p>';
    return `<ul class="commitments-record-list">${items.map(source => {
        if (!source || typeof source !== 'object') return '';
        const sourceId = source.source_id == null ? '' : String(source.source_id);
        const title = source.headline || `Source ${sourceId || 'unavailable'}`;
        const url = source.source_url || '';
        return `<li><strong>${commitmentsEscape(title)}</strong>${sourceId ? `<span class="commitments-muted"> · Source ID ${commitmentsEscape(sourceId)}</span>` : ''}${source.publisher ? `<p class="commitments-muted">Publisher: ${commitmentsEscape(source.publisher)}</p>` : ''}${url ? `<p>${commitmentsLink(url, 'Open delivered source')}</p>` : ''}${source.description ? `<p class="commitments-briefing-text">${commitmentsEscape(source.description)}</p>` : ''}${source.content ? `<p class="commitments-briefing-text">${commitmentsEscape(source.content)}</p>` : ''}</li>`;
    }).join('')}</ul>`;
}

function commitmentsResearchCard(record, canEdit) {
    const target = record.target && typeof record.target === 'object' ? record.target : {};
    const targetLabel = target.name || target.agent_id || 'Registered specialist';
    const sources = Array.isArray(record.sources) ? record.sources : [];
    const sourceList = commitmentsResearchSources(sources);
    const recordCanMutate = record.can_mutate !== false;
    const openOrigin = !recordCanMutate && record.source_session_id
        ? `<button type="button" data-research-open-session="${commitmentsEscape(record.source_session_id)}" data-agent="${commitmentsEscape(commitmentsOwnerId())}">Open original conversation</button>`
        : '';
    const buttons = !recordCanMutate
        ? `<p class="commitments-muted">This request belongs to another conversation. Review or act on it in the original conversation.</p>${openOrigin}`
        : record.status === 'pending'
        ? `<div class="commitments-actions" aria-label="Review specialist request"><button type="button" data-research-decision="approve" data-research-id="${commitmentsEscape(record.research_id || '')}" ${canEdit ? '' : 'disabled'}>Approve request</button><button type="button" data-research-decision="deny" data-research-id="${commitmentsEscape(record.research_id || '')}" ${canEdit ? '' : 'disabled'}>Deny request</button></div><p class="commitments-muted">Approval allows one separate execution. It does not publish or authorize external actions.</p>`
        : record.status === 'approved'
            ? `<div class="commitments-actions"><button type="button" data-research-execute="${commitmentsEscape(record.research_id || '')}" ${canEdit ? '' : 'disabled'}>Run approved research once</button></div><p class="commitments-muted">This is a one-shot request. Failed or uncertain work is not retried automatically.</p>`
            : record.status === 'uncertain' ? '<p class="commitments-error">The execution outcome is uncertain. It was not retried.</p>'
                : record.status === 'failed' ? '<p class="commitments-error">The research request failed. It was not retried.</p>'
                    : record.status === 'expired' ? '<p class="commitments-muted">This request expired without further execution.</p>'
                        : record.status === 'denied' ? '<p class="commitments-muted">Denied. The specialist was not asked to run this request.</p>'
                            : record.status === 'executing' ? '<p class="commitments-muted">The approved research is in progress. Do not submit it again.</p>'
                                : '';
    const outcome = record.status === 'completed' ? commitmentsResearchResult(record) : '';
    return `<li><div class="commitments-record-heading"><strong>${commitmentsEscape(targetLabel)}</strong><span class="commitments-priority">${commitmentsEscape(commitmentsStatusLabel(record.status))}</span></div>
      <p><strong>Question</strong><br>${commitmentsEscape(record.question || '')}</p>
      <p class="commitments-muted">Registered target: ${commitmentsEscape(target.agent_id || 'Unavailable ID')}${target.description ? ` · ${commitmentsEscape(target.description)}` : ''} · Target model: ${commitmentsEscape(target.provider || 'Unspecified provider')} / ${commitmentsEscape(target.model || 'Unspecified model')}${record.expires_at ? ` · Expires ${commitmentsDate(record.expires_at)}` : ''}</p>
      <details class="commitments-details commitments-research-material" open><summary>Exact sources shared</summary>${sourceList}</details><p class="commitments-muted"><strong>Allowed result:</strong> exact excerpts from these sources, with a relevance classification and priority. No tools or external actions.</p>${outcome}${buttons}</li>`;
}

function commitmentsAttentionCard(item, canEdit) {
    const payload = item.payload && typeof item.payload === 'object' ? item.payload : {};
    const commitmentId = item.commitment_id || '';
    const action = commitmentsAttentionText(payload.action) || item.kind || 'Update';
    const reason = commitmentsAttentionText(payload.reason);
    const scope = commitmentsAttentionText(payload.scope);
    const brief = commitmentsAttentionText(payload.briefing || payload.summary || payload.message || payload.text);
    const sources = commitmentsSources(Array.isArray(payload.sources) ? payload.sources : []);
    const decisionButtons = !item.dismissed_at && item.kind === 'decision' && item.status === 'pending'
        ? `<div class="commitments-actions" aria-label="Decision for ${commitmentsEscape(action)}">
            ${item.stale ? '' : `<button type="button" data-commitments-attention="approve" data-commitments-id="${commitmentsEscape(commitmentId)}" data-attention-id="${commitmentsEscape(item.attention_id || '')}" ${canEdit ? '' : 'disabled'}>Approve request</button>`}
            <button type="button" data-commitments-attention="deny" data-commitments-id="${commitmentsEscape(commitmentId)}" data-attention-id="${commitmentsEscape(item.attention_id || '')}" ${canEdit ? '' : 'disabled'}>Deny request</button>
            <button type="button" data-commitments-attention="dismiss" data-commitments-id="${commitmentsEscape(commitmentId)}" data-attention-id="${commitmentsEscape(item.attention_id || '')}" ${canEdit ? '' : 'disabled'}>Dismiss</button>
          </div>${item.stale ? '<p class="commitments-muted">Earlier scope — superseded by commitment changes. Review the current commitment before approving new work.</p>' : '<p class="commitments-muted">Approval records the decision. It does not publish or perform an external action.</p>'}`
        : !item.dismissed_at && (item.status === 'unread' || item.status === 'pending' || item.status === 'blocked')
            ? `<button type="button" data-commitments-attention="dismiss" data-commitments-id="${commitmentsEscape(commitmentId)}" data-attention-id="${commitmentsEscape(item.attention_id || '')}" ${canEdit ? '' : 'disabled'}>Dismiss notification</button>` : '';
    const specialistSuggestion = !item.stale && !item.dismissed_at && ['unread', 'pending', 'blocked'].includes(item.status) && payload.action === 'ask_specialist'
        ? `<button type="button" data-research-suggestion="${commitmentsEscape(item.attention_id || '')}" data-commitments-id="${commitmentsEscape(commitmentId)}">Draft request for owner review</button><p class="commitments-muted">This suggestion only fills a draft. It does not approve or execute research.</p>` : '';
    const decisionOutcome = item.kind !== 'decision' ? ''
        : item.status === 'approved' ? '<p class="commitments-muted">Approved for review. No post was published.</p>'
            : item.status === 'denied' ? '<p class="commitments-muted">Denied. No external action was performed.</p>'
                : item.status === 'expired' ? '<p class="commitments-muted">Expired. No external action was performed.</p>' : '';
    const executionBlock = payload.execution_status === 'blocked'
        ? `<p class="commitments-muted">Execution blocked: ${commitmentsEscape(payload.execution_reason || 'No supported connector is available.')}</p>` : '';
    const runRef = item.run_id || item.run_ref;
    return `<li class="commitments-attention-item">
      <div class="commitments-record-heading"><strong>${commitmentsEscape(action)}</strong><span class="commitments-priority">${commitmentsEscape(item.stale ? 'Needs renewed review' : item.dismissed_at ? 'Dismissed' : commitmentsStatusLabel(item.status))}</span></div>
      <p class="commitments-muted">${commitmentsEscape(item.kind || 'attention')}${item.created_at ? ` · ${commitmentsDate(item.created_at)}` : ''}${item.expires_at ? ` · Expires ${commitmentsDate(item.expires_at)}` : ''}${runRef ? ` · Run ${commitmentsEscape(runRef)}` : ''}</p>
      ${reason ? `<p><strong>Why it needs attention</strong><br>${commitmentsEscape(reason)}</p>` : ''}
      ${scope ? `<p><strong>Requested scope</strong><br>${commitmentsEscape(scope)}</p>` : ''}
      ${brief ? `<p class="commitments-briefing-text">${commitmentsEscape(brief)}</p>` : ''}${sources}${decisionOutcome}${executionBlock}${decisionButtons}${specialistSuggestion}
    </li>`;
}

function commitmentsRender(snapshot) {
    const content = document.getElementById('commitments-content');
    const identity = document.getElementById('commitments-identity');
    if (!content || !identity) return;
    _commitmentsSnapshot = snapshot;
    commitmentsUpdatePanelSummary();
    const identityInfo = snapshot.identity || {};
    identity.textContent = `${identityInfo.name || 'Owner'} · this agent`;
    const commitments = Array.isArray(snapshot.commitments) ? snapshot.commitments : [];
    const attention = Array.isArray(snapshot.attention) ? snapshot.attention : [];
    const historyRecords = Array.isArray(snapshot.attention_history) ? snapshot.attention_history : attention;
    const attentionHistory = [...new Map(historyRecords.filter(Boolean).map(item => [item.attention_id || `${item.commitment_id}:${item.kind}:${item.created_at}`, item])).values()];
    const approvedEndpoints = commitmentsApprovedEndpointList(snapshot.approved_endpoints);
    const specialists = Array.isArray(snapshot.specialists) ? snapshot.specialists.filter(item => item && typeof item === 'object' && typeof item.agent_id === 'string' && item.agent_id) : [];
    const researchRecords = Array.isArray(snapshot.research) ? snapshot.research : [];
    const canEdit = commitmentsCanMutate();
    const visibleAttention = attention.filter(item => item && !item.stale && !item.dismissed_at && ['unread', 'pending', 'blocked'].includes(item.status));
    const dismissedAttention = attentionHistory.filter(item => item && (item.stale || item.dismissed_at || ['approved', 'denied', 'resolved', 'dismissed', 'expired'].includes(item.status)));
    const orderedAttention = [...visibleAttention].sort((a, b) => commitmentsAttentionRank(a) - commitmentsAttentionRank(b)
        || Number(b.created_at || 0) - Number(a.created_at || 0));
    const attentionHtml = `<section class="commitments-section commitments-attention" aria-labelledby="commitments-attention-title">
      <h3 id="commitments-attention-title">Needs your attention <span class="commitments-count">${orderedAttention.length}</span></h3>
      ${orderedAttention.length ? `<ul class="commitments-record-list">${orderedAttention.map(item => commitmentsAttentionCard(item, canEdit)).join('')}</ul>` : '<p class="commitments-muted">No open findings, decisions or failures.</p>'}
      ${dismissedAttention.length ? `<details class="commitments-details"><summary>Show decision and notification history (${dismissedAttention.length})</summary><ul class="commitments-record-list">${dismissedAttention.map(item => commitmentsAttentionCard(item, canEdit)).join('')}</ul></details>` : ''}
    </section>`;
    const preferences = value => Array.isArray(value) ? value.join('\n') : (value || '');
    const commitmentCards = commitments.map((item, index) => {
        const cid = item.commitment_id || item.id || '';
        const schedule = item.schedule || null;
        const grant = item.grant && typeof item.grant === 'object' ? item.grant : {};
        const readGrant = item.read_grant && typeof item.read_grant === 'object' ? item.read_grant : {};
        const grantResource = grant.resource || item.endpoint || approvedEndpoints[0] || '';
        const lastRun = (Array.isArray(item.runs) ? item.runs[0] : null) || (item.last_briefing || item.last_selected
            ? { briefing: item.last_briefing, selected: item.last_selected, status: item.last_status, error: item.last_error }
            : null);
        const allArticles = [...(Array.isArray(item.last_selected) ? item.last_selected : []), ...(Array.isArray(item.runs) ? item.runs : []).flatMap(run =>
            Array.isArray(run.selected) ? run.selected : []
        )];
        const sourceRecords = ids => (Array.isArray(ids) ? ids : []).map(id =>
            allArticles.find(article => commitmentsArticleId(article) === String(id)) || { id, title: `Article ${id}` }
        );
        const itemSources = entry => Array.isArray(entry.sources) && entry.sources.length
            ? entry.sources
            : sourceRecords(entry.source_ids || entry.article_ids);
        const nextRun = item.next_run_at || item.next_action_at || null;
        const runList = Array.isArray(item.runs) && item.runs.length
            ? `<ul class="commitments-record-list">${item.runs.slice(0, 5).map(run => commitmentsRunState({ ...run, commitment_id: cid })).join('')}</ul>`
            : '<p class="commitments-muted">No run history.</p>';
        const followups = Array.isArray(item.followups) && item.followups.length
            ? `<ul class="commitments-record-list">${item.followups.map(entry => `<li>${commitmentsEscape(entry.text || entry)}${entry.source_seq != null ? `<span class="commitments-muted"> · Owner turn #${commitmentsEscape(entry.source_seq)}</span>` : ''}${commitmentsSources(itemSources(entry))}</li>`).join('')}</ul>`
            : '<p class="commitments-muted">No follow-ups saved.</p>';
        const drafts = Array.isArray(item.drafts) && item.drafts.length
            ? `<ul class="commitments-record-list">${item.drafts.map(draft => {
                const draftId = draft.draft_id || draft.item_id || draft.id || '';
                return `<li><strong>Draft only — publication requires separate approval</strong><p>${commitmentsEscape(draft.text || '')}</p>${draft.status ? `<span class="commitments-muted">${commitmentsEscape(draft.status)}</span>` : ''}<h5>Sources</h5>${commitmentsSources(itemSources(draft))}${Array.isArray(draft.claims) && draft.claims.length ? `<h5>Claims</h5><ul>${draft.claims.map(claim => `<li>${commitmentsEscape(claim)}</li>`).join('')}</ul>` : ''}${draftId ? `<button type="button" data-commitments-propose="${commitmentsEscape(draftId)}" data-commitments-id="${commitmentsEscape(cid)}" ${canEdit ? '' : 'disabled'}>Propose publication for review</button><p class="commitments-muted">This saves a sourced approval request. It does not publish the post.</p>` : ''}</li>`;
            }).join('')}</ul>`
            : '<p class="commitments-muted">No saved drafts.</p>';
        const reportedArticles = [
            ...(Array.isArray(lastRun && lastRun.selected) ? lastRun.selected : []),
            ...(Array.isArray(item.last_selected) ? item.last_selected : []),
            ...(Array.isArray(item.runs) ? item.runs.flatMap(run => Array.isArray(run.selected) ? run.selected : []) : []),
            ...(Array.isArray(item.followups) ? item.followups.flatMap(entry => [
                ...(Array.isArray(entry.sources) ? entry.sources : []), ...sourceRecords(entry.source_ids || entry.article_ids)
            ]) : []),
            ...(Array.isArray(item.drafts) ? item.drafts.flatMap(entry => [
                ...(Array.isArray(entry.sources) ? entry.sources : []), ...sourceRecords(entry.source_ids)
            ]) : [])
        ];
        const latestArticleIds = new Set((Array.isArray(lastRun && lastRun.selected) ? lastRun.selected : [])
            .map(commitmentsArticleId).filter(id => id !== ''));
        const pickerById = new Map();
        for (const article of reportedArticles) {
            const id = commitmentsArticleId(article);
            const url = article && (article.url || article.link || article.source_url);
            if (id === '' || !commitmentsSafeUrl(url) || pickerById.has(id)) continue;
            pickerById.set(id, { article, id });
        }
        const renderPickerOptions = articles => articles.map(({ article, id }) =>
            `<option value="${commitmentsEscape(id)}">${commitmentsEscape(article.title || article.headline || `Article ${id}`)}</option>`
        ).join('');
        const latestPickerArticles = [...pickerById.values()].filter(entry => latestArticleIds.has(entry.id));
        const previousPickerArticles = [...pickerById.values()].filter(entry => !latestArticleIds.has(entry.id));
        const sourceOptions = `${latestPickerArticles.length ? `<optgroup label="Latest report">${renderPickerOptions(latestPickerArticles)}</optgroup>` : ''}${previousPickerArticles.length ? `<optgroup label="Previously reported sources">${renderPickerOptions(previousPickerArticles)}</optgroup>` : ''}`;
        const pickerLabel = 'Latest and previously reported sources';
        const deliveredArticles = [
            ...(Array.isArray(item.runs) ? item.runs.filter(run => run && run.status === 'delivered').flatMap(run => Array.isArray(run.selected) ? run.selected : []) : []),
            ...(item.last_status === 'delivered' && Array.isArray(item.last_selected) ? item.last_selected : [])
        ];
        const researchSources = new Map();
        for (const article of deliveredArticles) {
            const id = commitmentsArticleId(article);
            const url = article && (article.url || article.link || article.source_url);
            if (id && commitmentsSafeUrl(url) && !researchSources.has(id)) researchSources.set(id, article);
        }
        const researchSourceOptions = [...researchSources.entries()].map(([id, article]) =>
            `<option value="${commitmentsEscape(id)}">${commitmentsEscape(article.headline || article.title || `Article ${id}`)}${article.publisher ? ` — ${commitmentsEscape(article.publisher)}` : ''}</option>`
        ).join('');
        const commitmentResearch = researchRecords.filter(record => record && record.commitment_id === cid);
        const researchHistory = commitmentResearch.length
            ? `<ul class="commitments-record-list">${commitmentResearch.map(record => commitmentsResearchCard(record, canEdit)).join('')}</ul>`
            : '<p class="commitments-muted">No specialist research requests for this commitment.</p>';
        const specialistOptions = specialists.map(target =>
            `<option value="${commitmentsEscape(target.agent_id)}">${commitmentsEscape(target.name || target.agent_id)}${target.provider || target.model ? ` — ${commitmentsEscape([target.provider, target.model].filter(Boolean).join(' / '))}` : ''}</option>`
        ).join('');
        const researchForm = specialists.length && researchSourceOptions
            ? `<form id="commitments-research-form-${index}" data-commitments-form="prepare_research" class="commitments-form"><input type="hidden" name="commitment_id" value="${commitmentsEscape(cid)}"><input type="hidden" name="attention_id" value=""><label>Registered specialist<select name="target_agent_id" required>${specialistOptions}</select></label><label>Research question<textarea name="question" rows="3" maxlength="2000" required placeholder="Ask one concrete question about the selected sources"></textarea></label><label>Delivered sources to share<select name="source_ids" multiple size="4" required>${researchSourceOptions}</select></label><p class="commitments-muted">Review the named target, question, and exact source selection before submission. Only verified source excerpts and classifications return. The receiver uses its own registered identity, memory and model, with no tools or external actions. BullGod remains your owner agent and can continue its own analysis at any time.</p><button type="submit" ${canEdit ? '' : 'disabled'}>Prepare request for owner review</button></form>`
            : '<p class="commitments-muted">No eligible registered specialist or delivered source is available. BullGod can continue its own analysis; your commitment remains active.</p>';
        return `<article class="commitments-record" aria-labelledby="commitment-title-${index}">
          <div class="commitments-record-heading"><h3 id="commitment-title-${index}">${commitmentsEscape(item.objective || 'Commitment')}</h3><span class="commitments-priority">Priority ${commitmentsEscape(item.priority ?? '—')}</span></div>
          <p class="commitments-muted">${commitmentsEscape(commitmentsStatusLabel(item.status))}${item.commitment_id ? ` · ID ${commitmentsEscape(item.commitment_id)}` : ''} · Revision ${commitmentsEscape(item.revision ?? '—')}</p>
          <p><strong>Preferences</strong><br>${commitmentsEscape(preferences(item.preferences) || 'None recorded.')}</p>
          <p><strong>Next action</strong><br>${commitmentsEscape(item.next_action || 'None recorded.')}</p>
          <p><strong>Pending decisions</strong><br>${commitmentsEscape(item.pending_decisions || 'None recorded.')}</p>
          <p><strong>Last check</strong> ${commitmentsDate(item.last_attempt_at ?? item.last_attempt)} · <strong>Last success</strong> ${commitmentsDate(item.last_success_at ?? item.last_success)}<br><strong>Next check</strong> ${commitmentsDate(nextRun)}${schedule ? ` · ${commitmentsEscape(schedule.cron)} (${commitmentsEscape(schedule.timezone)})` : ' · No schedule enabled'}</p>
          ${item.last_error ? `<p class="commitments-error"><strong>Last error:</strong> ${commitmentsEscape(item.last_error)}</p>` : ''}
          <details class="commitments-details"><summary>Review and edit commitment</summary>
            <form data-commitments-form="update" class="commitments-form">
              <input type="hidden" name="commitment_id" value="${commitmentsEscape(cid)}"><input type="hidden" name="revision" value="${commitmentsEscape(item.revision ?? '')}">
              <label>Objective<input name="objective" maxlength="2000" required value="${commitmentsEscape(item.objective || '')}"></label>
              <label>Preferences, one per line<textarea name="preferences" rows="3" maxlength="4000">${commitmentsEscape(preferences(item.preferences))}</textarea></label>
              <label>Priority<select name="priority">${[1,2,3,4,5].map(value => `<option value="${value}" ${Number(item.priority) === value ? 'selected' : ''}>${value}</option>`).join('')}</select></label>
              <label>Status<select name="status">${['active','paused','completed','cancelled'].map(value => `<option value="${value}" ${item.status === value ? 'selected' : ''}>${value}</option>`).join('')}</select></label>
              <label>Next action<input name="next_action" maxlength="2000" value="${commitmentsEscape(item.next_action || '')}"></label>
              <label>Pending decisions<textarea name="pending_decisions" rows="2" maxlength="2000">${commitmentsEscape(item.pending_decisions || '')}</textarea></label>
              <label>Approved HTTPS endpoint<input name="endpoint" type="url" list="commitment-endpoints-${index}" maxlength="2000" required value="${commitmentsEscape(item.endpoint || approvedEndpoints[0] || '')}" placeholder="https://tyl.ee/api/news"><datalist id="commitment-endpoints-${index}">${approvedEndpoints.map(endpoint => `<option value="${commitmentsEscape(endpoint)}"></option>`).join('')}</datalist></label>
              <label class="commitments-check"><input name="read_authorized" type="checkbox" ${item.read_authorized ? 'checked' : ''}> I explicitly authorize read-only access to this endpoint</label>
              <label class="commitments-check"><input name="initiative_enabled" type="checkbox" ${item.initiative_enabled ? 'checked' : ''}> Enable proactive follow-through on this commitment</label>
              <fieldset class="commitments-grant"><legend>Standing read grant limits</legend><label>Minimum time between reads (seconds)<input name="read_grant_min_interval_seconds" type="number" min="0" step="1" value="${commitmentsEscape(readGrant.min_interval_seconds ?? 0)}"></label><label>Grant expiry (optional)<input name="read_grant_expires_at" type="datetime-local" value="${commitmentsEscape(commitmentsDateTimeLocal(readGrant.expires_at))}"></label><p><strong>Derived grant contract</strong></p><ul class="commitments-grant-contract"><li>Grant status: ${commitmentsEscape(grant.status || (grant.authorized ? 'authorized' : 'not authorized'))}${grant.effective_status ? ` (${commitmentsEscape(grant.effective_status)})` : ''}</li><li>Owner agent: ${commitmentsEscape(grant.agent_id || identityInfo.agent_id || identityInfo.id || 'current agent')}</li><li>Commitment: ${commitmentsEscape(grant.commitment_id || cid || 'this commitment')}</li><li>Operation: ${commitmentsEscape(grant.operation || 'read')}</li><li>Exact resource: ${commitmentsLink(grant.resource || grantResource, grant.resource || grantResource || 'No endpoint saved')}</li><li>Allowed: read this resource and update this commitment's own state only${grant.internal_writes ? ` (${commitmentsEscape(grant.internal_writes)})` : ''}</li><li>External publication: not allowed</li><li>Individual approval: ${grant.individual_approval_required ? 'required' : 'not required for the granted read'}</li><li>Read only: ${grant.read_only === false ? 'no' : 'yes'}</li><li>Conditions: explicit read authorization${item.initiative_enabled ? '; initiative enabled' : '; initiative disabled'}${schedule ? '; scheduled checks enabled' : ''}</li><li>Expiry: ${commitmentsEscape(commitmentsDate(grant.expires_at))}; frequency: at most once per ${commitmentsEscape(readGrant.min_interval_seconds ?? 0)} seconds</li></ul></fieldset>
              <label class="commitments-check"><input name="schedule_enabled" type="checkbox" ${schedule ? 'checked' : ''}> Enable a recurring read-only schedule</label>
              <label>Morning cron<input name="schedule_cron" maxlength="128" value="${commitmentsEscape(schedule && schedule.cron || '0 8 * * *')}" placeholder="0 8 * * *"></label>
              <label>Timezone<input name="schedule_timezone" maxlength="128" value="${commitmentsEscape(schedule && schedule.timezone || 'America/New_York')}" placeholder="America/New_York"></label>
              <button type="submit" ${canEdit ? '' : 'disabled'}>Save commitment</button>
            </form>
          </details>
          <div class="commitments-actions"><button type="button" data-commitments-run="${commitmentsEscape(cid)}" ${canEdit && item.status === 'active' && item.read_authorized ? '' : 'disabled'}>Check now</button></div>
          <details class="commitments-details"><summary>Latest briefing and run history</summary>${lastRun ? `<p class="commitments-muted">Latest run: ${commitmentsEscape(commitmentsStatusLabel(lastRun.status))}${lastRun.error ? ` · ${commitmentsEscape(lastRun.error)}` : ''}</p>` : ''}${commitmentsBriefing(lastRun)}${runList}</details>
          <details class="commitments-details"><summary>Follow-ups and drafts</summary><h4>Follow-ups</h4>${followups}<h4>Saved drafts</h4>${drafts}</details>
          <details class="commitments-details"><summary>Optional specialist research</summary><p class="commitments-muted">Specialist help is optional. Request, approval and execution are separate owner actions.</p>${researchHistory}${researchForm}</details>
          <details class="commitments-details"><summary>Add a follow-up or save a draft</summary>
            <form data-commitments-form="followup" class="commitments-form"><input type="hidden" name="commitment_id" value="${commitmentsEscape(cid)}"><label>Follow-up request<textarea name="text" rows="2" maxlength="2000" required></textarea></label><label>Article IDs, comma separated (optional)<input name="article_ids" maxlength="2000" placeholder="0, article-id"></label><button type="submit" ${canEdit ? '' : 'disabled'}>Save follow-up</button></form>
            <form data-commitments-form="save_draft" class="commitments-form"><input type="hidden" name="commitment_id" value="${commitmentsEscape(cid)}"><label>Draft text<textarea name="text" rows="4" maxlength="4000" required></textarea></label><label>${commitmentsEscape(pickerLabel)}<select name="source_ids" multiple size="3">${sourceOptions || '<option disabled>No reported sources available</option>'}</select></label><label>Claims, one per line<textarea name="claims" rows="2" maxlength="2000"></textarea></label><p class="commitments-muted">Draft only — publication requires separate approval.</p><button type="submit" ${canEdit && sourceOptions ? '' : 'disabled'}>Save draft only</button></form>
          </details>
        </article>`;
    }).join('');

    content.innerHTML = `${attentionHtml}<section class="commitments-section"><h3>New commitment</h3>
      <form data-commitments-form="create" class="commitments-form">
        <label>Objective<input name="objective" maxlength="2000" required placeholder="e.g. Track developments that matter to me"></label>
        <label>Preferences, one per line<textarea name="preferences" rows="3" maxlength="4000" placeholder="Add topics or priorities for this commitment"></textarea></label>
        <label>Priority<select name="priority">${[1,2,3,4,5].map(value => `<option value="${value}" ${value === 3 ? 'selected' : ''}>${value}</option>`).join('')}</select></label>
        <label>Approved HTTPS endpoint<input name="endpoint" type="url" list="commitment-endpoints-new" maxlength="2000" required value="${commitmentsEscape(approvedEndpoints[0] || 'https://tyl.ee/api/news')}" placeholder="https://tyl.ee/api/news"><datalist id="commitment-endpoints-new">${approvedEndpoints.map(endpoint => `<option value="${commitmentsEscape(endpoint)}"></option>`).join('')}</datalist></label>
        <label class="commitments-check"><input name="read_authorized" type="checkbox"> I explicitly authorize read-only access to this endpoint</label>
        <label class="commitments-check"><input name="initiative_enabled" type="checkbox"> Enable proactive follow-through on this commitment</label>
        <fieldset class="commitments-grant"><legend>Standing read grant limits</legend><label>Minimum time between reads (seconds)<input name="read_grant_min_interval_seconds" type="number" min="0" step="1" value="60"></label><label>Grant expiry (optional)<input name="read_grant_expires_at" type="datetime-local"></label><p class="commitments-muted">Read only for this agent, commitment and exact endpoint. BullGod can read and update this commitment's own state. It cannot publish externally. The interval and expiry apply.</p></fieldset>
        <label class="commitments-check"><input name="schedule_enabled" type="checkbox"> Enable a recurring read-only schedule</label>
        <label>Morning cron<input name="schedule_cron" maxlength="128" value="0 8 * * *" placeholder="0 8 * * *"></label>
        <label>Timezone<input name="schedule_timezone" maxlength="128" value="America/New_York" placeholder="America/New_York"></label>
        <label>Next action<input name="next_action" maxlength="2000"></label><label>Pending decisions<textarea name="pending_decisions" rows="2" maxlength="2000"></textarea></label>
        <p class="commitments-muted">The commitment is saved from your latest persisted message. Agent suggestions do not change owner intent.</p><button type="submit" ${canEdit ? '' : 'disabled'}>Create commitment</button>
      </form></section><section class="commitments-section"><h3>Your commitments</h3>${commitmentCards || '<p class="commitments-muted">No commitments saved for this agent yet.</p>'}</section>`;
}

async function refreshCommitments() {
    if (_commitmentsBusy) {
        commitmentsStatus('A commitment change is in progress.');
        return;
    }
    const currentSession = sessionId;
    const currentAgent = commitmentsOwnerId();
    if (!commitmentsOwnerAuthReady()) {
        commitmentsStatus('Commitments need an authenticated console. Sign in; no request was sent.');
        return;
    }
    if (_commitmentsPanelReady) commitmentsRestorePanelState();
    if (!_commitmentsPersistedTurn || !currentSession || !currentAgent) {
        commitmentsStatus('Send a message in this conversation to enable commitment changes.');
        return;
    }
    const generation = ++_commitmentsGeneration;
    commitmentsStatus('Loading commitments…');
    try {
        const response = await fetch(`/api/commitments/${encodeURIComponent(currentSession)}?agent_id=${encodeURIComponent(currentAgent)}`);
        const data = await response.json();
        if (generation !== _commitmentsGeneration || currentSession !== sessionId || currentAgent !== commitmentsOwnerId()) return;
        if (!response.ok || data.status !== 'success') throw new Error(data.message || data.error || `Request failed (${response.status})`);
        commitmentsRender(data);
        commitmentsStatus('Saved owner commitments. Review sources and status here.');
    } catch (error) {
        if (generation !== _commitmentsGeneration) return;
        commitmentsStatus(error.message || 'Could not load commitments.', true);
    }
}

function commitmentsSwitchSession() {
    _commitmentsGeneration++;
    _commitmentsPersistedTurn = false;
    _commitmentsSnapshot = null;
    const identity = document.getElementById('commitments-identity');
    const content = document.getElementById('commitments-content');
    if (identity) identity.textContent = '';
    if (content) content.innerHTML = '<p class="commitments-muted">Start or reopen a conversation to review its owner commitments.</p>';
    commitmentsUpdatePanelSummary();
    commitmentsStatus('Send a message in this conversation to enable commitment changes.');
}

function commitmentsBeginSession(sid) {
    const key = `${commitmentsOwnerId()}::${sid}`;
    if (_commitmentsShownSession === key) return;
    _commitmentsShownSession = key;
    commitmentsSwitchSession();
}

function commitmentsMarkPersistedTurn(sid) {
    if (sid !== sessionId) return;
    _commitmentsShownSession = `${commitmentsOwnerId()}::${sid}`;
    _commitmentsPersistedTurn = true;
    refreshCommitments();
}

function commitmentsLineList(value) {
    return String(value || '').split(/\r?\n/).map(item => item.trim()).filter(Boolean);
}

function commitmentsFormFields(values) {
    const schedule = values.schedule_enabled
        ? { cron: values.schedule_cron || '0 8 * * *', timezone: values.schedule_timezone || 'America/New_York' }
        : null;
    const minInterval = Number(values.read_grant_min_interval_seconds);
    const expiry = values.read_grant_expires_at ? new Date(values.read_grant_expires_at).getTime() / 1000 : null;
    return {
        objective: values.objective,
        preferences: commitmentsLineList(values.preferences),
        priority: Number(values.priority),
        status: values.status || 'active',
        endpoint: values.endpoint || '',
        read_authorized: values.read_authorized === 'on',
        initiative_enabled: values.initiative_enabled === 'on',
        read_grant: {
            expires_at: Number.isFinite(expiry) ? Math.floor(expiry) : null,
            min_interval_seconds: Number.isInteger(minInterval) && minInterval >= 0 ? minInterval : 0
        },
        schedule,
        next_action: values.next_action || '',
        pending_decisions: values.pending_decisions || ''
    };
}

async function commitmentsSubmit(operation, { commitmentId = '', revision, fields, extra = {} } = {}) {
    if (_commitmentsBusy) return false;
    if (!commitmentsCanMutate()) {
        commitmentsStatus('Send a persisted message first. Owner changes must cite that turn.', true);
        return false;
    }
    if (!commitmentsOwnerAuthReady()) {
        commitmentsStatus('Sign in to the authenticated console before changing commitments.', true);
        return false;
    }
    const currentSession = sessionId;
    const currentAgent = commitmentsOwnerId();
    const sourceSeq = commitmentsSourceSeq();
    if (sourceSeq == null) {
        commitmentsStatus('No persisted owner turn is available for this change.', true);
        return false;
    }
    let payload;
    if (operation === 'prepare_research') {
        payload = { operation, commitment_id: commitmentId, source_seq: sourceSeq, ...extra };
    } else if (operation === 'decide_research' || operation === 'execute_research') {
        payload = { operation, source_seq: sourceSeq, ...extra };
    } else {
        payload = { operation, commitment_id: commitmentId, source_seq: sourceSeq, ...extra };
    }
    if (operation === 'run') payload.request_id = crypto.randomUUID();
    if (revision !== undefined) payload.revision = revision;
    if (fields !== undefined) payload.fields = fields;
    const generation = ++_commitmentsGeneration;
    _commitmentsBusy = true;
    commitmentsBusy(true);
    commitmentsStatus('Saving owner commitment change…');
    try {
        const response = await fetch(`/api/commitments/${encodeURIComponent(currentSession)}?agent_id=${encodeURIComponent(currentAgent)}`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok || data.status !== 'success') throw new Error(data.message || data.error || `Request failed (${response.status})`);
        if (generation !== _commitmentsGeneration || currentSession !== sessionId || currentAgent !== commitmentsOwnerId()) return false;
        _commitmentsBusy = false;
        commitmentsBusy(false);
        commitmentsRender(data);
        const researchOperation = data.research_operation && typeof data.research_operation === 'object' ? data.research_operation : null;
        const researchStatus = researchOperation && typeof researchOperation.status === 'string' ? researchOperation.status : '';
        const researchResult = operation === 'prepare_research' || operation === 'decide_research' || operation === 'execute_research'
            ? researchStatus === 'unavailable'
                ? { message: `Specialist research is unavailable: ${commitmentsPublicReason(researchOperation.reason) || 'No eligible registered specialist is available.'} BullGod can continue its own analysis; the commitment remains active.`, error: false }
                : commitmentsResearchStatus(researchStatus, operation)
            : null;
        const statusText = researchResult ? researchResult.message
            : operation === 'run' ? 'Check started. Refresh to see its current status.'
                : operation === 'decide_attention' ? 'Decision saved. No external action was performed.'
                    : operation === 'propose_publication' ? 'Publication request saved for review. Nothing was published.'
                        : 'Owner commitment change saved.';
        commitmentsStatus(statusText, !!(researchResult && researchResult.error));
        if (operation === 'execute_research' && typeof reloadHistoryView === 'function'
            && generation === _commitmentsGeneration && currentSession === sessionId && currentAgent === commitmentsOwnerId()) reloadHistoryView();
        return true;
    } catch (error) {
        if (generation !== _commitmentsGeneration || currentSession !== sessionId || currentAgent !== commitmentsOwnerId()) return false;
        const isResearch = operation === 'prepare_research' || operation === 'decide_research' || operation === 'execute_research';
        commitmentsStatus(isResearch ? (commitmentsPublicReason(error.message) || 'Could not complete the specialist research action. No automatic retry was made.')
            : (error.message || 'Could not save the owner change.'), true);
        return false;
    } finally {
        _commitmentsBusy = false;
        commitmentsBusy(false);
    }
}

function commitmentsHandleSubmit(event) {
    const form = event.target.closest('form[data-commitments-form]');
    if (!form) return;
    event.preventDefault();
    if (_commitmentsBusy) return;
    const values = Object.fromEntries(new FormData(form).entries());
    const action = form.dataset.commitmentsForm;
    if (action === 'create') {
        commitmentsSubmit('create', { fields: commitmentsFormFields(values) });
    } else if (action === 'update') {
        commitmentsSubmit('update', { commitmentId: values.commitment_id, revision: Number(values.revision), fields: commitmentsFormFields(values) });
    } else if (action === 'followup') {
        commitmentsSubmit('followup', { commitmentId: values.commitment_id, extra: { text: values.text, article_ids: String(values.article_ids || '').split(',').map(item => item.trim()).filter(item => item !== '') } });
    } else if (action === 'save_draft') {
        const sourceIds = [...form.querySelector('[name="source_ids"]')?.selectedOptions || []].map(option => option.value).filter(value => value !== '');
        commitmentsSubmit('save_draft', { commitmentId: values.commitment_id, extra: { text: values.text, source_ids: sourceIds, claims: commitmentsLineList(values.claims) } });
    } else if (action === 'prepare_research') {
        const sourceIds = [...form.querySelector('[name="source_ids"]')?.selectedOptions || []].map(option => option.value).filter(value => value !== '');
        if (!sourceIds.length || !values.target_agent_id || !String(values.question || '').trim()) {
            commitmentsStatus('Choose a registered target, at least one delivered source, and a question.', true);
            return;
        }
        const extra = { target_agent_id: values.target_agent_id, source_ids: sourceIds, question: String(values.question).trim() };
        if (values.attention_id) extra.attention_id = values.attention_id;
        commitmentsSubmit('prepare_research', { commitmentId: values.commitment_id, extra });
    }
}

function commitmentsHandleClick(event) {
    const button = event.target.closest('button');
    if (!button || _commitmentsBusy) return;
    if (button.id === 'commitments-refresh') {
        refreshCommitments();
        return;
    }
    if (button.dataset.commitmentsAck) {
        commitmentsSubmit('acknowledge_run', {
            commitmentId: button.dataset.commitmentsId,
            extra: { run_id: button.dataset.commitmentsAck }
        });
        return;
    }
    if (button.dataset.commitmentsAttention) {
        commitmentsSubmit('decide_attention', {
            commitmentId: button.dataset.commitmentsId,
            extra: { attention_id: button.dataset.attentionId, decision: button.dataset.commitmentsAttention }
        });
        return;
    }
    if (button.dataset.researchDecision) {
        commitmentsSubmit('decide_research', { extra: { research_id: button.dataset.researchId, decision: button.dataset.researchDecision } });
        return;
    }
    if (button.dataset.researchSuggestion) {
        const attention = (_commitmentsSnapshot && Array.isArray(_commitmentsSnapshot.attention) ? _commitmentsSnapshot.attention : [])
            .find(item => item && item.attention_id === button.dataset.researchSuggestion && item.commitment_id === button.dataset.commitmentsId);
        const form = [...document.querySelectorAll('form[data-commitments-form="prepare_research"]')]
            .find(entry => entry.querySelector('[name="commitment_id"]')?.value === button.dataset.commitmentsId);
        if (!attention || !form) {
            commitmentsStatus('Open the commitment research form to review this suggestion.', true);
            return;
        }
        const payload = attention.payload && typeof attention.payload === 'object' ? attention.payload : {};
        form.querySelector('[name="question"]').value = typeof payload.reason === 'string' ? payload.reason.slice(0, 2000) : '';
        form.querySelector('[name="attention_id"]').value = attention.attention_id;
        const selected = new Set(Array.isArray(payload.source_ids) ? payload.source_ids.map(String) : []);
        [...form.querySelector('[name="source_ids"]').options].forEach(option => { option.selected = selected.has(option.value); });
        const details = form.closest('details');
        if (details) details.open = true;
        form.querySelector('[name="question"]').focus();
        commitmentsStatus('Suggestion copied into a draft. Choose the registered target and review all fields before submitting.');
        return;
    }
    if (button.dataset.researchExecute) {
        commitmentsSubmit('execute_research', { extra: { research_id: button.dataset.researchExecute } });
        return;
    }
    if (button.dataset.researchOpenSession && typeof switchSession === 'function') {
        switchSession(button.dataset.researchOpenSession, button.dataset.agent || commitmentsOwnerId());
        return;
    }
    if (button.dataset.commitmentsPropose) {
        commitmentsSubmit('propose_publication', {
            commitmentId: button.dataset.commitmentsId,
            extra: { draft_id: button.dataset.commitmentsPropose, expires_at: null }
        });
        return;
    }
    if (button.dataset.commitmentsRun) commitmentsSubmit('run', { commitmentId: button.dataset.commitmentsRun });
}

function commitmentsPollVisibleSnapshot() {
    const card = document.getElementById('commitments-card');
    const active = document.activeElement;
    if (!card || document.visibilityState !== 'visible' || !_commitmentsPersistedTurn || _commitmentsBusy) return;
    if (active && card.contains(active)) return;
    refreshCommitments();
}

const _commitmentsCard = document.getElementById('commitments-card');
if (_commitmentsCard) {
    _commitmentsCard.addEventListener('submit', commitmentsHandleSubmit);
    _commitmentsCard.addEventListener('click', commitmentsHandleClick);
}
commitmentsSetupPanel();
window.addEventListener('load', () => requestAuthGatedStart(() => {
    _commitmentsPanelReady = true;
    commitmentsRestorePanelState();
    refreshCommitments();
}));
setInterval(commitmentsPollVisibleSnapshot, 30000);
