/* Owner-controlled personal continuity for the native web chat.
   This script uses only the authenticated /api/personal owner routes. */
let _personalGeneration = 0;
let _personalHasPersistedTurn = false;
let _personalSnapshot = null;
let _personalBusy = false;

function personalOwnerId() {
    return activeAgentId || defaultAgentId || '';
}

function personalOwnerAuthReady() {
    return !!(appConfig && appConfig.web_password_masked);
}

function personalEscape(value) {
    // core/utils.js escapes &, < and >, but not quotes. Most API text is
    // inserted as HTML text; this helper also feeds quoted input and data
    // attributes, so encode both quote characters at this boundary.
    return escapeHtml(value == null ? '' : String(value))
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function personalDate(value) {
    if (!value) return 'time unavailable';
    const date = typeof value === 'number' ? new Date(value * 1000) : new Date(value);
    return Number.isNaN(date.getTime()) ? personalEscape(value) : date.toLocaleString();
}

function personalSource(item) {
    const seq = item && (item.source_seq ?? item.sourceSeq);
    const when = item && (item.source_time ?? item.updated_at ?? item.created_at ?? item.createdAt);
    const sourceSession = item && item.source_session_id && item.source_session_id !== sessionId
        ? ` · conversation ${personalEscape(item.source_session_id)}` : '';
    return `<span class="personal-provenance">Owner turn ${seq == null ? 'unknown' : `#${personalEscape(seq)}`} · ${personalDate(when)}${sourceSession}</span>`;
}

function personalResultText(result) {
    if (!result) return '';
    if (typeof result === 'string') return result;
    const summary = [result.path, result.summary, result.readback ? `Readback: ${result.readback}` : '', result.error]
        .filter(Boolean).join(' · ');
    return summary || JSON.stringify(result);
}

function personalSetStatus(message, error = false) {
    const el = document.getElementById('personal-status');
    if (!el) return;
    el.textContent = message;
    el.classList.toggle('is-error', !!error);
}

function personalSetBusy(disabled) {
    const card = document.getElementById('personal-card');
    if (!card) return;
    card.querySelectorAll('button').forEach(button => {
        if (disabled) {
            button.dataset.personalDisabledBeforeBusy = button.disabled ? 'true' : 'false';
            button.disabled = true;
        } else if (button.dataset.personalDisabledBeforeBusy !== undefined) {
            button.disabled = button.dataset.personalDisabledBeforeBusy === 'true';
            delete button.dataset.personalDisabledBeforeBusy;
        }
    });
}

function personalLatestUserSeq() {
    const nodes = messagesDiv ? [...messagesDiv.querySelectorAll('.user-message-group[data-seq]')] : [];
    const seqs = nodes.map(node => Number(node.dataset.seq)).filter(Number.isFinite);
    if (seqs.length) return Math.max(...seqs);
    return _personalSnapshot && _personalSnapshot.latest_source_seq != null
        ? Number(_personalSnapshot.latest_source_seq) : null;
}

function personalRender(snapshot) {
    const content = document.getElementById('personal-content');
    const identity = document.getElementById('personal-identity');
    if (!content || !identity) return;
    _personalSnapshot = snapshot;
    const name = snapshot.identity && snapshot.identity.name || 'Owner';
    identity.textContent = `${name} · this agent and conversation`;
    const continuity = snapshot.continuity || {};
    const goal = continuity.goal || '';
    const progress = continuity.progress || '';
    const pending = continuity.pending_decision || '';
    const next = continuity.next_step || '';
    const latestSeq = personalLatestUserSeq();
    const editable = latestSeq != null && Number.isFinite(Number(latestSeq)) && !_personalBusy;
    const memories = Array.isArray(snapshot.memories) ? snapshot.memories : [];
    const goals = Array.isArray(snapshot.recent_goals) ? snapshot.recent_goals : [];
    const actions = Array.isArray(snapshot.actions) ? snapshot.actions : [];
    const caps = snapshot.capabilities || {};
    const list = (values, toolList = false) => values.length
        ? `<ul>${values.map(item => {
            if (typeof item === 'string') return `<li>${personalEscape(item)}</li>`;
            const permission = toolList && typeof item.allowed === 'boolean'
                ? ` — ${item.allowed ? 'allowed in current mode' : 'not allowed in current mode'}${item.reason ? `: ${personalEscape(item.reason)}` : ''}` : '';
            return `<li>${personalEscape(item.name || item.id || JSON.stringify(item))}${permission}</li>`;
        }).join('')}</ul>`
        : '<p class="personal-muted">None reported.</p>';

    content.innerHTML = `
      <section class="personal-section" aria-labelledby="personal-goal-title">
        <h3 id="personal-goal-title">Goal and next step</h3>
        <form data-personal-form="save_goal" class="personal-form">
          <label>Goal<input name="goal" maxlength="2000" value="${personalEscape(goal)}" required></label>
          <label>Progress<textarea name="progress" rows="2" maxlength="4000">${personalEscape(progress)}</textarea></label>
          <label>Pending decision<textarea name="pending_decision" rows="2" maxlength="2000">${personalEscape(pending)}</textarea></label>
          <label>Next step<input name="next_step" maxlength="2000" value="${personalEscape(next)}"></label>
          <div class="personal-form-footer"><span>${latestSeq != null ? `Save from your latest persisted message, turn #${personalEscape(latestSeq)}.` : 'Send a message before saving owner state.'}</span><button class="personal-button personal-primary" type="submit" ${editable ? '' : 'disabled'}>Save goal</button></div>
        </form>
        ${continuity.source_seq != null || continuity.source_time ? personalSource(continuity) : '<p class="personal-muted">No goal saved for this conversation.</p>'}
      </section>
      <section class="personal-section"><h3>Recent goals</h3>
        ${goals.length ? `<ul class="personal-record-list">${goals.map(item => `<li><strong>${personalEscape(item.goal || item.text || 'Goal')}</strong><span>${personalEscape(item.progress || '')}</span>${personalSource(item)}${item.session_id && item.session_id !== sessionId ? `<button class="personal-link" type="button" data-personal-open-session="${personalEscape(item.session_id)}" data-agent="${personalEscape(item.agent_id || '')}">Open conversation</button>` : ''}</li>`).join('')}</ul>` : '<p class="personal-muted">No saved goals yet.</p>'}
      </section>
      <section class="personal-section"><h3>Remember an explicit fact</h3>
        <form data-personal-form="remember" class="personal-form personal-inline-form">
          <label>Fact<textarea name="text" rows="2" maxlength="2000" required placeholder="Enter the fact you want this agent to remember"></textarea></label>
          <div class="personal-form-footer"><span>Saved only when you submit. Source: owner turn #${latestSeq == null ? '—' : personalEscape(latestSeq)}.</span><button class="personal-button personal-primary" type="submit" ${editable ? '' : 'disabled'}>Remember</button></div>
        </form>
        ${memories.length ? `<ul class="personal-record-list personal-memory-list">${memories.map(item => `<li><form data-personal-form="correct_memory" class="personal-form"><label>Current fact<input name="text" maxlength="2000" value="${personalEscape(item.text || item.fact || '')}" required></label><input type="hidden" name="memory_id" value="${personalEscape(item.memory_id || item.id || '')}"><input type="hidden" name="revision" value="${personalEscape(item.revision ?? '')}"><div class="personal-record-actions">${personalSource(item)}<button class="personal-button" type="submit" ${editable ? '' : 'disabled'}>Correct</button><button class="personal-button personal-danger" type="button" data-personal-forget="${personalEscape(item.memory_id || item.id || '')}" data-revision="${personalEscape(item.revision ?? '')}" ${_personalBusy ? 'disabled' : ''}>Forget</button></div></form></li>`).join('')}</ul>` : '<p class="personal-muted">No current accepted facts. Forgotten facts are not shown.</p>'}
      </section>
      <section class="personal-section"><h3>Available tools and skills</h3>
        <p class="personal-muted">Permission mode: ${personalEscape(caps.permission_mode || 'unknown')}. ${personalEscape(caps.limits || 'Runtime capability details are not loaded.')}</p>
        <div class="personal-capabilities"><div><h4>Tools</h4>${list(Array.isArray(caps.tools) ? caps.tools : [], true)}</div><div><h4>Skills</h4>${list(Array.isArray(caps.skills) ? caps.skills : [])}</div></div>
        ${caps.status === 'not_loaded' ? '<p class="personal-muted">Names do not grant permission. Use the chat permission controls and the action approval shown below.</p>' : ''}
      </section>
      <section class="personal-section"><h3>Proposed actions and results</h3>
        ${actions.length ? `<ul class="personal-record-list">${actions.map(action => `<li class="personal-action"><div class="personal-action-title"><strong>${personalEscape(action.path || action.action_id || 'Action')}</strong><span class="personal-state">${personalEscape(action.status || 'unknown')}</span></div>${personalSource(action)}${action.content != null ? `<details><summary>Review exact file content</summary><pre>${personalEscape(action.content)}</pre></details>` : ''}${action.result ? `<p><strong>Result:</strong> ${personalEscape(personalResultText(action.result))}</p>` : ''}${action.error ? `<p class="personal-error"><strong>Error:</strong> ${personalEscape(action.error)}</p>` : ''}${action.status === 'executing' ? '<p class="personal-error">Execution state is unresolved. Review the workspace before taking another action.</p>' : ''}${action.status === 'failed' ? '<p class="personal-error">This action failed or has an uncertain effect. It will not be retried here; inspect the target before creating a new proposal.</p>' : ''}${action.status === 'proposed' || action.status === 'pending' ? `<p class="personal-muted">Path and content are fixed for this proposal. Expires ${personalDate(action.expires_at)}.</p><div class="personal-record-actions"><button class="personal-button personal-primary" type="button" data-personal-approve="${personalEscape(action.action_id)}" ${_personalBusy ? 'disabled' : ''}>Approve and execute once</button><button class="personal-button personal-danger" type="button" data-personal-deny="${personalEscape(action.action_id)}" ${_personalBusy ? 'disabled' : ''}>Deny</button></div>` : ''}${action.status === 'approved' ? `<p class="personal-muted">Approved by you, not yet executed.</p><button class="personal-button personal-primary" type="button" data-personal-execute="${personalEscape(action.action_id)}" ${_personalBusy ? 'disabled' : ''}>Execute approved action once</button>` : ''}</li>`).join('')}</ul>` : '<p class="personal-muted">No proposed or completed actions.</p>'}
        <details class="personal-propose"><summary>Propose a workspace text file</summary>
          <form data-personal-form="propose_write" class="personal-form">
            <label>Workspace path<input name="path" maxlength="1000" required placeholder="projects/example/notes.txt"></label>
            <label>Exact file content<textarea name="content" rows="4" maxlength="20000" required></textarea></label>
            <p class="personal-muted">This only creates a proposal. Review the path and exact content above, then approve it explicitly. The normal permission boundary still applies.</p>
            <button class="personal-button" type="submit" ${editable ? '' : 'disabled'}>Create proposal from owner turn #${latestSeq == null ? '—' : personalEscape(latestSeq)}</button>
          </form>
        </details>
      </section>
      <p class="personal-retention">${personalEscape(snapshot.memory_retention_note || 'Owner continuity is separate from retained conversation transcripts.')}</p>`;
}

async function refreshPersonalContinuity(force = false) {
    if (_personalBusy) {
        personalSetStatus('An owner change is in progress.');
        return;
    }
    const currentSession = sessionId;
    const currentAgent = personalOwnerId();
    if (!personalOwnerAuthReady()) {
        personalSetStatus('Owner continuity needs an authenticated console. Set a console password and sign in; no personal request was sent.');
        return;
    }
    if (!_personalHasPersistedTurn || !currentSession || !currentAgent) {
        personalSetStatus('This conversation has no saved owner turn yet. Send a message to enable continuity.');
        return;
    }
    const generation = ++_personalGeneration;
    personalSetStatus('Loading saved owner context…');
    try {
        const response = await fetch(`/api/personal/${encodeURIComponent(currentSession)}?agent_id=${encodeURIComponent(currentAgent)}`);
        const data = await response.json();
        if (generation !== _personalGeneration || currentSession !== sessionId || currentAgent !== personalOwnerId()) return;
        if (!response.ok || data.status !== 'success') throw new Error(data.message || data.error || `Request failed (${response.status})`);
        personalRender(data);
        personalSetStatus('Saved owner state. Review sources and make changes here.');
    } catch (error) {
        if (generation !== _personalGeneration) return;
        personalSetStatus(error.message || 'Could not load owner continuity.', true);
    }
}

function personalSwitchSession() {
    _personalGeneration++;
    _personalHasPersistedTurn = false;
    _personalSnapshot = null;
    const identity = document.getElementById('personal-identity');
    const content = document.getElementById('personal-content');
    if (identity) identity.textContent = '';
    if (content) content.innerHTML = '<p class="personal-muted">Start or reopen a conversation to see its saved goal, memory, and action results.</p>';
    personalSetStatus('This conversation has no saved owner turn yet. Send a message to enable continuity.');
}

async function personalSubmit(operation, fields) {
    if (_personalBusy) return false;
    if (!sessionId || !personalOwnerId()) return false;
    if (!personalOwnerAuthReady()) {
        personalSetStatus('Owner continuity needs an authenticated console. Set a console password and sign in; no personal change was sent.', true);
        return false;
    }
    const currentSession = sessionId;
    const currentAgent = personalOwnerId();
    const payload = { operation, ...fields };
    if (operation === 'save_goal' || operation === 'remember' || operation === 'correct_memory' || operation === 'propose_write') {
        const seq = personalLatestUserSeq();
        if (seq == null || Number.isNaN(seq)) {
            personalSetStatus('Send a message first. The owner record must cite a persisted user turn.', true);
            return false;
        }
        if (operation !== 'correct_memory' && operation !== 'propose_write') payload.source_seq = seq;
        else payload.source_seq = seq;
    }
    _personalBusy = true;
    const mutationGeneration = ++_personalGeneration;
    personalSetBusy(true);
    personalSetStatus('Saving owner change…');
    try {
        const response = await fetch(`/api/personal/${encodeURIComponent(currentSession)}?agent_id=${encodeURIComponent(currentAgent)}`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok || data.status !== 'success') throw new Error(data.message || data.error || `Request failed (${response.status})`);
        if (mutationGeneration !== _personalGeneration
            || currentSession !== sessionId || currentAgent !== personalOwnerId()) return false;
        if (data.identity && Array.isArray(data.memories)) personalRender(data);
        personalSetStatus('Owner change saved.');
        return true;
    } catch (error) {
        if (mutationGeneration !== _personalGeneration
            || currentSession !== sessionId || currentAgent !== personalOwnerId()) return false;
        personalSetStatus(error.message || 'Could not save owner change.', true);
        return false;
    } finally {
        _personalBusy = false;
        const stillCurrent = mutationGeneration === _personalGeneration
            && currentSession === sessionId && currentAgent === personalOwnerId();
        if (stillCurrent && _personalSnapshot) personalRender(_personalSnapshot);
        else {
            personalSetBusy(false);
            if (_personalHasPersistedTurn && personalOwnerAuthReady()) refreshPersonalContinuity();
        }
    }
}

function personalHandleSubmit(event) {
    const form = event.target.closest('form[data-personal-form]');
    if (!form) return;
    event.preventDefault();
    if (_personalBusy) return;
    const operation = form.dataset.personalForm;
    const values = Object.fromEntries(new FormData(form).entries());
    if (operation === 'save_goal') {
        const revision = _personalSnapshot && _personalSnapshot.continuity && _personalSnapshot.continuity.revision;
        personalSubmit(operation, { fields: { goal: values.goal, progress: values.progress, pending_decision: values.pending_decision, next_step: values.next_step }, revision });
    } else if (operation === 'remember') {
        personalSubmit(operation, { text: values.text });
    } else if (operation === 'correct_memory') {
        personalSubmit(operation, { memory_id: values.memory_id, text: values.text, revision: values.revision === '' ? undefined : Number(values.revision) });
    } else if (operation === 'propose_write') {
        personalSubmit(operation, { path: values.path, content: values.content, expires_at: Math.floor(Date.now() / 1000) + 15 * 60 });
    }
}

function personalHandleClick(event) {
    const button = event.target.closest('button');
    if (!button) return;
    if (_personalBusy && button.id !== 'personal-refresh') return;
    if (button.id === 'personal-refresh') { refreshPersonalContinuity(true); return; }
    if (button.dataset.personalForget) {
        personalSubmit('forget_memory', { memory_id: button.dataset.personalForget, revision: button.dataset.revision === '' ? undefined : Number(button.dataset.revision) });
    } else if (button.dataset.personalDeny) {
        personalSubmit('decide_action', { action_id: button.dataset.personalDeny, decision: 'deny' });
    } else if (button.dataset.personalApprove) {
        personalSubmit('decide_action', { action_id: button.dataset.personalApprove, decision: 'approve' }).then(approved => {
            if (!approved) return;
            const action = _personalSnapshot && (_personalSnapshot.actions || []).find(item => item.action_id === button.dataset.personalApprove);
            if (action && action.status === 'approved') personalSubmit('execute_action', { action_id: button.dataset.personalApprove });
        });
    } else if (button.dataset.personalExecute) {
        personalSubmit('execute_action', { action_id: button.dataset.personalExecute });
    } else if (button.dataset.personalOpenSession && typeof switchSession === 'function') {
        switchSession(button.dataset.personalOpenSession, button.dataset.agent || undefined);
    }
}

let _personalShownSession = '';
function personalBeginSession(sid) {
    const ownerKey = `${personalOwnerId()}::${sid}`;
    if (_personalShownSession === ownerKey) return;
    _personalShownSession = ownerKey;
    personalSwitchSession();
}

function personalMarkPersistedTurn(sid) {
    if (sid !== sessionId) return;
    _personalShownSession = `${personalOwnerId()}::${sid}`;
    _personalHasPersistedTurn = true;
    refreshPersonalContinuity();
}

const _personalCard = document.getElementById('personal-card');
if (_personalCard) {
    _personalCard.addEventListener('submit', personalHandleSubmit);
    _personalCard.addEventListener('click', personalHandleClick);
}
window.addEventListener('load', () => requestAuthGatedStart(() => refreshPersonalContinuity()));
