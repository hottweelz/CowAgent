/* Owner-confirmed personal commitments for the native web conversation. */
let _commitmentsGeneration = 0;
let _commitmentsPersistedTurn = false;
let _commitmentsBusy = false;
let _commitmentsSnapshot = null;
let _commitmentsShownSession = '';

function commitmentsOwnerId() {
    return activeAgentId || defaultAgentId || '';
}

function commitmentsOwnerAuthReady() {
    return !!(appConfig && appConfig.web_password_masked);
}

function commitmentsEscape(value) {
    return escapeHtml(value == null ? '' : String(value))
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function commitmentsText(value) {
    return value == null ? '' : String(value);
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
        approved: 'Approved for review', denied: 'Denied', resolved: 'Resolved', dismissed: 'Dismissed', expired: 'Expired'
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
}

function commitmentsBusy(disabled) {
    const card = document.getElementById('commitments-card');
    if (!card) return;
    card.querySelectorAll('button').forEach(button => {
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
      ${brief ? `<p class="commitments-briefing-text">${commitmentsEscape(brief)}</p>` : ''}${sources}${decisionOutcome}${executionBlock}${decisionButtons}
    </li>`;
}

function commitmentsRender(snapshot) {
    const content = document.getElementById('commitments-content');
    const identity = document.getElementById('commitments-identity');
    if (!content || !identity) return;
    _commitmentsSnapshot = snapshot;
    const identityInfo = snapshot.identity || {};
    identity.textContent = `${identityInfo.name || 'Owner'} · this agent`;
    const commitments = Array.isArray(snapshot.commitments) ? snapshot.commitments : [];
    const attention = Array.isArray(snapshot.attention) ? snapshot.attention : [];
    const historyRecords = Array.isArray(snapshot.attention_history) ? snapshot.attention_history : attention;
    const attentionHistory = [...new Map(historyRecords.filter(Boolean).map(item => [item.attention_id || `${item.commitment_id}:${item.kind}:${item.created_at}`, item])).values()];
    const approvedEndpoints = commitmentsApprovedEndpointList(snapshot.approved_endpoints);
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
    const payload = { operation, commitment_id: commitmentId, source_seq: sourceSeq, ...extra };
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
        const statusText = operation === 'run' ? 'Check started. Refresh to see its current status.'
            : operation === 'decide_attention' ? 'Decision saved. No external action was performed.'
                : operation === 'propose_publication' ? 'Publication request saved for review. Nothing was published.'
                    : 'Owner commitment change saved.';
        commitmentsStatus(statusText);
        return true;
    } catch (error) {
        if (generation !== _commitmentsGeneration || currentSession !== sessionId || currentAgent !== commitmentsOwnerId()) return false;
        commitmentsStatus(error.message || 'Could not save the owner change.', true);
        return false;
    } finally {
        _commitmentsBusy = false;
        const current = generation === _commitmentsGeneration && currentSession === sessionId && currentAgent === commitmentsOwnerId();
        commitmentsBusy(false);
        if (current && _commitmentsPersistedTurn && commitmentsOwnerAuthReady()) refreshCommitments();
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
window.addEventListener('load', () => requestAuthGatedStart(() => refreshCommitments()));
setInterval(commitmentsPollVisibleSnapshot, 30000);
