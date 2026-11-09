"""Reconstruct and execute durable, restricted workers without loading private state."""
from __future__ import annotations

import os
import math
import time
from dataclasses import asdict

from agent.permission.authority import Authority, derive_authority, restricted_authority, _registry_profiles, _current_registry
from agent.permission.policy import strict_global_mode, strict_mode
from agent.protocol.agent import Agent
from agent.workspace import project_store, session_prefs


def _classes():
    from agent.tools.read.read import Read
    from agent.tools.write.write import Write
    from agent.tools.edit.edit import Edit
    from agent.tools.ls.ls import Ls
    from agent.tools.search_files.search_files import SearchFiles
    from agent.tools.current_time.current_time import TimeTool
    return {cls.__name__: cls for cls in (Read, Write, Edit, Ls, SearchFiles, TimeTool)}


def _profile(agent_id):
    profiles = [p for p in _registry_profiles() if p.id == agent_id]
    if len(profiles) != 1 or not profiles[0].enabled:
        raise ValueError('Recovery principal unavailable')
    return profiles[0]


def _agent_defaults(profile):
    # The default Agent follows global routing, even when its profile has pins.
    if profile.id == _current_registry().default_agent_id:
        return None, None
    return profile.bot_type, profile.model


def _current(spec):
    from config import conf
    owner = _profile(spec['owner_id'])
    source = _profile(spec['source_agent_id'])
    target = _profile(spec['target_agent_id'])
    if spec['kind'] == 'subagent':
        from agent.subagent.runner import SubagentSettings
        if not SubagentSettings.from_config().enabled:
            raise ValueError('Recovery subagent execution disabled')
        if source.id != target.id:
            raise ValueError('Invalid subagent principal')
        host_prefs = session_prefs.get_prefs_strict(spec['session_id'], owner.id)
        members = host_prefs.get('members', [])
        if not isinstance(members, (list, tuple)) or not all(isinstance(x, str) for x in members):
            raise ValueError('Invalid conversation roster')
        if source.id != owner.id and source.id not in members:
            raise ValueError('Recovery guest no longer authorized')
    if spec['kind'] == 'delegate':
        from agent.tools.agent_delegate.agent_delegate import DelegationPolicy
        policy = DelegationPolicy.from_config(conf().get('agent_delegation', {}))
        roster = session_prefs.get_prefs_strict(spec['session_id'], spec['owner_id']).get('members', [])
        trace = spec.get('delegation_trace')
        depth = spec.get('delegation_depth')
        if (not isinstance(depth, int) or isinstance(depth, bool) or depth < 1
                or not isinstance(trace, list) or len(trace) != depth
                or not all(isinstance(x, str) and x for x in trace)
                or len(set(trace)) != len(trace) or trace[-1] != source.id
                or target.id in trace
                or not isinstance(roster, (list, tuple)) or not all(isinstance(x, str) for x in roster)
                or source.id not in set(roster) | {spec['owner_id']}
                or target.id not in set(roster) | {spec['owner_id']}
                or spec.get('delegation_depth', 1) > policy.max_depth
                or not policy.allows(source.id, target.id)):
            raise ValueError('Recovery delegation no longer authorized')
    identities = []
    for profile, session in ((source, spec['source_session_id']), (target, spec['target_session_id'])):
        authority_owner = owner.id if spec['kind'] == 'subagent' else profile.id
        prefs = session_prefs.get_prefs_strict(session, authority_owner)
        root = project_store.get_project_dir_strict(session, authority_owner) or profile.workspace
        if not os.path.isdir(root) or not os.path.isabs(root):
            raise ValueError('Recovery project unavailable')
        view = Agent('Recovery authority', workspace_dir=profile.workspace, enable_skills=False,
                     skip_context_files=True)
        view._current_agent_id = profile.id
        view.project_dir = root
        view.permission_mode = strict_mode(prefs['permission']) if prefs.get('permission') else strict_global_mode()
        identities.append((restricted_authority(view), prefs, profile))
    auth = derive_authority(identities[0][0], identities[1][0])
    selected = identities[1] if spec['kind'] == 'delegate' else identities[0]
    prefs, profile = selected[1], selected[2]
    if spec['kind'] == 'delegate' or source.id != owner.id or prefs.get('members'):
        # Delegated worker construction uses the receiver profile, not a
        # receiver conversation's model override. Its permission still applies.
        prefs = {}
    settings = conf()
    agent_provider, agent_model = _agent_defaults(profile)
    fallback = settings.get('chat_fallback') or {}
    if not isinstance(fallback, dict):
        raise ValueError('Invalid fallback configuration')
    chain = fallback.get('chain', [])
    if not isinstance(chain, list) or any(not isinstance(x, dict) for x in chain):
        raise ValueError('Invalid fallback configuration')
    model_ref = {'provider': prefs.get('provider') or agent_provider or settings.get('bot_type') or '',
                 'model': prefs.get('model') or agent_model or settings.get('model') or '',
                 'linkai_active': bool(settings.get('use_linkai') and settings.get('linkai_api_key')),
                 'fallback_enabled': bool(fallback.get('enabled')),
                 'fallback_provider': fallback.get('provider'),
                 'fallback_model': fallback.get('model'),
                 'fallback_chain': [{'provider': x.get('provider'), 'model': x.get('model')} for x in chain]}
    return auth, model_ref, profile, prefs


def _snapshot_authority(auth):
    if not isinstance(auth, Authority) or not auth.restricted:
        raise ValueError('Restricted authority required')
    value = asdict(auth)
    value['capabilities'] = sorted(value['capabilities'])
    return value


def snapshot_child(child, prompt, *, owner_id, session_id, kind, source_agent_id,
                   target_agent_id, parent_run_id='', timeout_seconds=None, verification=None):
    from agent.recovery.verification import normalize_contract
    if timeout_seconds is None:
        timeout_seconds = 300.0
    if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError('Invalid recovery timeout')
    if kind not in ('subagent', 'delegate') or not all(isinstance(v, str) and v for v in
            (owner_id, session_id, source_agent_id, target_agent_id)):
        raise ValueError('Incomplete recovery identity')
    names = []
    classes = _classes()
    for tool in child.tools:
        name = type(tool).__name__
        if classes.get(name) is not type(tool):
            raise ValueError('Unsupported recovery tool')
        names.append(name)
    scratch = getattr(child, 'task_workspace', None)
    if scratch and (not os.path.isabs(scratch) or not os.path.isdir(scratch)):
        raise ValueError('Recovery scratch unavailable')
    spec = {'version': 1, 'owner_id': owner_id, 'session_id': session_id, 'kind': kind,
            'source_agent_id': source_agent_id, 'target_agent_id': target_agent_id,
            'source_session_id': getattr(child, '_recovery_source_session_id', session_id),
            'target_session_id': getattr(child, '_recovery_target_session_id', session_id),
            'parent_run_id': parent_run_id, 'prompt': prompt, 'system_prompt': child.system_prompt,
            'delegation_depth': getattr(child, '_recovery_delegation_depth', 1),
            'delegation_trace': list(getattr(child, '_recovery_delegation_trace', (source_agent_id,))),
            'extra_system_suffix': child.extra_system_suffix, 'description': child.description,
            'name': child.name, 'workspace_dir': child.workspace_dir, 'project_dir': child.project_dir,
            'task_workspace': scratch, 'max_steps': child.max_steps,
            'max_context_tokens': child.max_context_tokens, 'context_reserve_tokens': child.context_reserve_tokens,
            'authority': _snapshot_authority(child.authority), 'tools': names,
            'timeout_seconds': timeout_seconds, 'verification': normalize_contract(verification)}
    _, spec['model_ref'], _, _ = _current(spec)
    return spec


def _attenuate(spec):
    if spec.get('version') != 1:
        raise ValueError('Unsupported recovery envelope')
    auth, model_ref, profile, prefs = _current(spec)
    if model_ref != spec['model_ref']:
        raise ValueError('Recovery model configuration changed')
    scratch = spec.get('task_workspace')
    if scratch and (not os.path.isdir(scratch) or os.path.realpath(scratch) != scratch):
        raise ValueError('Recovery scratch unavailable')
    frozen = Authority(**spec['authority'])
    if not frozen.restricted:
        raise ValueError('Invalid recovery authority')
    return derive_authority(auth, frozen), profile, prefs


def restore_child(spec, bridge):
    authority, profile, prefs = _attenuate(spec)
    from bridge.agent_bridge import AgentLLMModel
    model = AgentLLMModel(bridge)
    model.agent_id = spec['target_agent_id']
    model.session_id = spec['target_session_id']
    model.set_agent_default(*_agent_defaults(profile))
    model.set_session_override(prefs.get('provider'), prefs.get('model'))
    cwd = spec.get('project_dir') or spec.get('workspace_dir')
    if cwd and (not os.path.isdir(cwd) or os.path.realpath(cwd) != cwd):
        raise ValueError('Recovery workspace unavailable')
    tools = []
    classes = _classes()
    for name in spec['tools']:
        cls = classes.get(name)
        if cls is None:
            raise ValueError('Unsupported recovery tool')
        tool = cls() if name == 'TimeTool' else cls({'cwd': cwd})
        if name == 'Read':
            tool._shared_knowledge_path = lambda path: None
        tools.append(tool)
    child = Agent(spec['system_prompt'], description=spec['description'], model=model, tools=tools,
                  output_mode='logger', max_steps=spec['max_steps'],
                  max_context_tokens=spec['max_context_tokens'],
                  context_reserve_tokens=spec.get('context_reserve_tokens'),
                  memory_manager=None, name=spec['name'], workspace_dir=spec.get('workspace_dir'),
                  skill_manager=None, enable_skills=False, runtime_info=None, skip_context_files=True)
    child.extra_system_suffix = spec.get('extra_system_suffix')
    child.task_workspace = spec.get('task_workspace')
    child.project_dir = cwd
    child._current_agent_id = spec['target_agent_id']
    child.permission_mode = authority.mode
    child.authority = authority
    return child


class RecoveryAttempt:
    """A durable lease attached to one worker and checked by the tool gateway."""
    def __init__(self, store, claim, child, spec, cancel):
        self.store, self.claim, self.child, self.spec, self.cancel = store, claim, child, spec, cancel
        self.guard_failed = False

    def before_tool(self, name, mutating, call_id=None):
        try:
            if self.guard_failed:
                raise RuntimeError('Recovery guard already failed')
            if self.cancel.is_set():
                raise RuntimeError('Recovery attempt stopped')
            authority, _, _ = _attenuate(self.spec)
            self.child.authority = derive_authority(self.child.authority, authority)
            self.child.permission_mode = self.child.authority.mode
            return self.store.before_tool(self.claim, name, mutating=mutating, call_id=call_id)
        except Exception:
            self.guard_failed = True
            raise

    def after_tool(self, effect_id, result):
        try:
            if not self.store.after_tool(self.claim, effect_id, result):
                raise RuntimeError('Recovery effect receipt lost')
        except Exception:
            self.guard_failed = True
            raise

    def record_denial(self, name, code, call_id=None):
        self.record_failure(name, code, call_id, permission_denied=True)

    def record_failure(self, name, code, call_id=None, *, permission_denied=False):
        # A denied call has no mutating intent, but must not disappear from
        # independent acceptance assessment after a reassuring worker summary.
        try:
            task = self.store.get(self.claim.task_id)
            attempt = next(a for a in task['attempts'] if a['attempt_id'] == self.claim.attempt_id)
            if any(e['name'] == name and e['call_id'] == call_id and isinstance(e['result'], dict)
                   and e['result'].get('status') == 'error'
                   and (e['mutating'] or e['result'].get('permission_denied') or e['result'].get('execution_rejected'))
                   for e in attempt['effects']):
                return
            effect = self.before_tool(name, mutating=False, call_id=call_id)
            self.after_tool(effect, {'status': 'error', 'permission_denied': permission_denied,
                                    'execution_rejected': True, 'code': code})
        except Exception:
            self.guard_failed = True
            raise


def get_task_store():
    from common.state_dir import shared_root
    from agent.recovery.store import TaskStore
    return TaskStore(shared_root() / 'memory' / 'recovery' / 'tasks.db')


def _completed_result(store, task, *, claim=None, wait=True):
    from agent.recovery.verification import VerificationBusy, task_result, verify_task
    deadline = time.monotonic() + float(task['spec'].get('timeout_seconds') or 300)
    try:
        while task.get('verification') is None:
            try:
                task = verify_task(store, task['task_id'], claim=claim)
            except VerificationBusy:
                if not wait or time.monotonic() >= deadline:
                    raise
                time.sleep(.05)
                task = store.get(task['task_id'])
        return task_result(task)
    except Exception:
        from common.log import logger
        logger.error('[Verification] Independent result unavailable; execution remains completed')
        result = task_result(dict(task, verification=None))
        result['verification_error'] = 'Independent verification unavailable'
        return result


from common.runtime_drain import current, tracked

@tracked("recovery_execution")
def execute_task(store, task_id, build_child=None, *, bridge=None, cancel_event=None,
                 on_event=None, steer_inbox=None, wait_for_existing=True):
    """Claim once, run with its lock held, and commit a terminal result by CAS."""
    import threading
    from common.runtime_identity import identity_scope

    deadline = None
    initial = store.get(task_id)
    if initial is None:
        raise ValueError('Recovery task not found')
    generation = initial['generation']
    watched_attempt = initial['attempt_id'] if initial['state'] == 'running' else None
    claim = store.claim(task_id, expected_generation=generation)
    if claim is None:
        # Another process owns the flock. Never steal its attempt; a caller
        # awaiting the result observes the durable row until it settles.
        while True:
            task = store.get(task_id)
            if task is None:
                raise ValueError('Recovery task not found')
            if task['generation'] != generation or (watched_attempt and task['attempt_id'] != watched_attempt):
                from agent.recovery.verification import task_result
                result = task_result(task)
                result.update(status='superseded', wait_status='superseded', error='Waiting attempt was replaced')
                return result
            if task['state'] == 'running' and watched_attempt is None:
                watched_attempt = task['attempt_id']
            if task['state'] == 'completed' and isinstance(task.get('result'), dict):
                return _completed_result(store, task, wait=wait_for_existing)
            if task['state'] not in ('running', 'queued') or not wait_for_existing:
                from agent.recovery.verification import task_result
                return task_result(task)
            timeout = task['spec'].get('timeout_seconds') or 300.0
            if deadline is None:
                timeout = float(timeout)
                if not math.isfinite(timeout) or timeout <= 0:
                    raise ValueError('Invalid recovery timeout')
                deadline = time.monotonic() + timeout
            stopped = cancel_event is not None and cancel_event.is_set()
            expired = deadline is not None and time.monotonic() >= deadline
            if stopped or expired:
                status = 'cancelled' if stopped else 'timed_out'
                snapshot = store.request_stop(
                    task_id, status, expected_generation=generation,
                    attempt_id=task['attempt_id'] if task['state'] == 'running' else None,
                    expected_state='running' if task['state'] == 'running' else None,
                    return_snapshot=True)
                if snapshot:
                    from agent.recovery.verification import task_result
                    return task_result(snapshot)
                # A completion or replacement won the CAS. Re-read it rather
                # than attributing our unsuccessful stop to that execution.
                continue
            else:
                if task['state'] == 'queued':
                    # A different task may own this receiver/session. Retry the
                    # claim after its owner exits, without needing a service.
                    claim = store.claim(task_id, expected_generation=generation)
                    if claim is not None:
                        break
                time.sleep(0.05)
    timer = None
    timer_started = False
    try:
        spec = claim.task['spec']
        # Revalidate even a prepared child: queue time may have changed its grants.
        authority, _, _ = _attenuate(spec)
        child = build_child() if build_child else restore_child(spec, bridge)
        child.authority = derive_authority(child.authority, authority)
        child.permission_mode = child.authority.mode
        timeout = float(spec.get('timeout_seconds') or 300.0)
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('Invalid recovery timeout')
        deadline = deadline or time.monotonic() + timeout
        attempt = None

        class Cancel:
            def is_set(self):
                if attempt is not None and attempt.guard_failed:
                    return True
                if time.monotonic() >= deadline:
                    store.request_stop(task_id, 'timed_out', attempt_id=claim.attempt_id)
                    return True
                if cancel_event is not None and cancel_event.is_set():
                    store.request_stop(task_id, 'cancelled', attempt_id=claim.attempt_id)
                    return True
                row = store.get(task_id)
                return not row or row['state'] != 'running' or row['attempt_id'] != claim.attempt_id

        cancel = Cancel()
        attempt = RecoveryAttempt(store, claim, child, spec, cancel)
        child.recovery_attempt = attempt
        def expire():
            try:
                store.request_stop(task_id, 'timed_out', attempt_id=claim.attempt_id)
            except Exception:
                from common.log import logger
                logger.error('[Recovery] Timeout could not be persisted; next checkpoint will retry')
        timer = threading.Timer(max(0, deadline - time.monotonic()), expire)
        timer.daemon = True
        timer.start()
        timer_started = True
        with identity_scope(agent_id=spec['target_agent_id'], session_id=spec['target_session_id'],
                            run_id=claim.attempt_id):
            summary = child.run_stream(spec['prompt'], clear_history=True, cancel_event=cancel,
                                       on_event=on_event, steer_inbox=steer_inbox)
        result = {'task_id': task_id, 'attempt_id': claim.attempt_id, 'status': 'completed',
                  'summary': summary or '', 'task_workspace': spec.get('task_workspace')}
        if attempt.guard_failed:
            store.finish(claim, 'needs_review', error='Durable tool receipt failed')
        elif not cancel.is_set():
            store.finish(claim, 'completed', result=result)
        task = store.get(task_id)
        if task['state'] == 'completed':
            return _completed_result(store, task, claim=claim)
        from agent.recovery.verification import task_result
        return task_result(task)
    except Exception:
        attempt = locals().get('attempt')
        status = 'needs_review' if attempt and attempt.guard_failed else 'failed'
        store.finish(claim, status, error='Worker initialization or execution failed')
        task = store.get(task_id)
        from agent.recovery.verification import task_result
        return task_result(task)
    finally:
        if timer:
            timer.cancel()
            if timer_started and current() is not None:
                timer.join()
        claim.close()


execute = execute_task
