"""Read-only observations of an already initialized, server-owned runtime.

The private hooks run during normal initialization and reply execution. They
are not an API for registering arbitrary objects or caller dictionaries. This
is an application boundary, not protection from code in this address space.
No file-backed authority fallback, model/memory/journal initialization or lazy
runtime getter is used here. Existing authority helpers canonicalize paths.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import json
import os
import uuid

from agent.external import contract
from agent.registry import AgentRegistry
from .contracts import AdmissionObservation, Candidate, DiscoveryError, token
from .sources import NativeSource, _attach, _public_route


@dataclass(frozen=True)
class _Anchor:
    owner: object
    bridge: object
    pid: int
    epoch: str


@dataclass(frozen=True)
class _AppliedSession:
    owner: object
    agent: object
    session: str
    owner_id: str
    members: tuple | None


@dataclass
class _Caller:
    anchor: _Anchor
    agent: object
    tool: object
    context: object
    applied: _AppliedSession
    registry: object
    session: str
    owner_id: str
    speaker_id: str
    run_id: str
    identity: object
    context_binding: str
    root: bool
    active: bool = True


_caller = ContextVar('cow_discovery_active_caller', default=None)
_CONTEXT_KEYS = ('session_id', 'agent_id', 'speaker_agent_id',
                 'delegation_root_session', 'delegation_host_id',
                 'delegation_members', 'delegation_trace', 'delegation_depth',
                 'parent_run_id')


def _context_binding(context):
    return contract.digest({key: context.kwargs.get(key) for key in _CONTEXT_KEYS})


def _install_runtime_anchor(owner):
    """Only called at the end of successful normal AgentBridge initialization."""
    owner._discovery_runtime_anchor = _Anchor(owner, owner.bridge, os.getpid(), uuid.uuid4().hex)


def _record_applied_session(owner, agent, session, owner_id, prefs):
    """Retain only metadata from the existing successful prefs application.

    This is applied runtime state, not authenticated filesystem evidence. A
    failed/repeated application clears the previous receipt before any reads.
    """
    members = prefs.get('members', [])
    if not isinstance(members, (list, tuple)) or not all(token(v) for v in members):
        members = None
    else:
        members = tuple(sorted(set(members)))
    agent._discovery_applied_session = _AppliedSession(owner, agent, session, owner_id, members)


@contextmanager
def _active_reply(owner, agent, context, session, owner_id, speaker_id, run_id, parent_run):
    """Bind actual reply objects; invalidate even copied thread contexts."""
    scope = None
    try:
        runtime = InitializedRuntime(owner)
        from agent.tools.agent_delegate.agent_delegate import AgentDelegateTool
        from bridge.context import Context
        from common.runtime_identity import current_identity
        applied = getattr(agent, '_discovery_applied_session', None)
        tools = [tool for tool in agent.tools if isinstance(tool, AgentDelegateTool)]
        if (isinstance(context, Context) and isinstance(context.kwargs, dict)
                and isinstance(applied, _AppliedSession) and len(tools) == 1
                and token(session) and token(owner_id) and token(speaker_id)
                and token(run_id) and current_identity().run_id == run_id):
            root = (not parent_run and _caller.get() is None
                    and not any(context.kwargs.get(key) for key in _CONTEXT_KEYS[3:]))
            scope = _Caller(runtime.anchor, agent, tools[0], context, applied,
                            owner.agent_registry, session, owner_id, speaker_id,
                            run_id, current_identity(), _context_binding(context), root)
    except Exception:
        # Observation must not change execution when metadata is unavailable.
        pass
    reset = _caller.set(scope)
    try:
        yield
    finally:
        if scope is not None:
            scope.active = False
        _caller.reset(reset)


class InitializedRuntime:
    """A view of one normal initialization, never a replacement registry."""
    def __init__(self, owner):
        self.owner = owner
        self.anchor = getattr(owner, '_discovery_runtime_anchor', None)
        self.epoch = getattr(self.anchor, 'epoch', None)
        self.validate()

    def validate(self):
        from bridge.agent_bridge import AgentBridge
        from bridge.agent_initializer import AgentInitializer
        from bridge.bridge import Bridge
        from agent.routing import AgentRouter
        owner, anchor = self.owner, self.anchor
        if (type(owner) is not AgentBridge or not isinstance(anchor, _Anchor)
                or anchor.owner is not owner or anchor.bridge is not owner.bridge
                or anchor.pid != os.getpid() or anchor.epoch != self.epoch
                or getattr(owner, '_discovery_runtime_anchor', None) is not anchor
                or not isinstance(owner.bridge, Bridge.__wrapped__)
                or getattr(owner.bridge, '_agent_bridge', None) is not owner
                or not isinstance(owner.agent_registry, AgentRegistry)
                or not isinstance(owner.agent_router, AgentRouter)
                or owner.agent_router.registry is not owner.agent_registry
                or not isinstance(owner.initializer, AgentInitializer)
                or owner.initializer.bridge is not owner.bridge
                or owner.initializer.agent_bridge is not owner):
            raise DiscoveryError('initialized_runtime_unavailable')

    def registry(self):
        self.validate()
        return self.owner.agent_registry

    def settings(self):
        self.validate()
        from config import Config, conf
        settings = conf()
        if not isinstance(settings, Config):
            raise DiscoveryError('initialized_configuration_unavailable')
        return json.loads(contract.canonical(dict(settings)))

    def caller(self):
        self.validate()
        from agent.protocol.agent import Agent
        from common.runtime_identity import current_identity
        scope = _caller.get()
        if not isinstance(scope, _Caller) or not scope.active or scope.anchor is not self.anchor:
            return None
        agent, tool, context, applied = scope.agent, scope.tool, scope.context, scope.applied
        with self.owner._agents_lock:
            cached = self.owner._agent_instances.get((scope.speaker_id, scope.session))
        if (not isinstance(agent, Agent) or cached is not agent
                or scope.registry is not self.owner.agent_registry
                or getattr(agent, '_discovery_applied_session', None) is not applied
                or applied.owner is not self.owner or applied.agent is not agent
                or applied.session != scope.session or applied.owner_id != scope.owner_id
                or getattr(agent, '_execution_agent_id', None) != scope.speaker_id
                or getattr(agent, '_current_agent_id', None) != scope.owner_id
                or getattr(agent, '_current_session_id', None) != scope.session
                or tool not in agent.tools or getattr(tool, 'context', None) is not agent
                or getattr(tool, 'agent_bridge', None) is not self.owner
                or getattr(tool, 'current_context', None) is not context
                or context.kwargs.get('session_id') != scope.session
                or context.kwargs.get('agent_id') != scope.owner_id
                or (context.kwargs.get('speaker_agent_id') or scope.owner_id) != scope.speaker_id
                or _context_binding(context) != scope.context_binding
                or current_identity() != scope.identity
                or current_identity().run_id != scope.run_id):
            return None
        return scope

    @staticmethod
    def cached_route(scope):
        from bridge.agent_bridge import AgentLLMModel
        model = getattr(scope.agent, 'model', None)
        if not isinstance(model, AgentLLMModel):
            return {'model': None, 'provider': None, 'origin': 'unknown'}
        selected = model.model
        provider = model._fallback_provider or model._primary_provider_id(selected)
        return {'model': _public_route(selected, model=True), 'provider': _public_route(provider),
                'origin': 'cached_fallback' if model._fallback_model else 'cached_session'}


class InitializedNativeSource:
    """Native declarations and genuine active-root policy, without file fallback.

    There is no installed native isolated capability proof provider or retained
    isolated receiver authority snapshot. Neither is invented from source code,
    an unrelated persistent Agent or successful registry/config inspection.
    """
    def __init__(self, runtime):
        self.runtime = runtime

    def candidates(self, registry, task, now):
        from agent.tools.agent_delegate.agent_delegate import DelegationPolicy
        from agent.permission.authority import restricted_authority
        runtime = self.runtime
        settings = runtime.settings()
        if registry is not runtime.registry():
            raise DiscoveryError('initialized_runtime_changed')
        snapshot = contract.digest({'settings': settings, 'registry': [
            profile.to_dict() for profile in registry.list(include_disabled=True)]})
        policy = DelegationPolicy.from_config(settings.get('agent_delegation', {}))
        scope = runtime.caller()
        route = runtime.cached_route(scope) if scope else None
        turn_policy = scope.tool._policy() if scope else None
        source_auth = None
        if scope:
            try:
                source_auth = restricted_authority(scope.agent, registry=registry)
            except Exception:
                pass
        result = []
        for profile in registry.list(include_disabled=True):
            model, provider = NativeSource._route(profile, registry, settings)
            identity = contract.digest(profile.to_dict())
            config = contract.digest({'identity': identity, 'mechanism': 'native_isolated',
                                      'instance_epoch': runtime.epoch, 'state': snapshot,
                                      'model': model, 'provider': provider, 'caller_route': route})
            candidate = Candidate(profile.id, 'registered', 'native_isolated', identity, config,
                                  contract.digest({'target': profile.id, 'epoch': runtime.epoch,
                                                   'receiver_authority': 'unknown'}),
                                  model=model, provider=provider, max_concurrency=1,
                                  reasons=['native_receiver_authority_unknown',
                                           'native_capability_proof_unavailable'])
            if not profile.enabled:
                candidate.reasons.append('identity_disabled')
            candidate.expires_at = now + 5
            candidate.runtime_state = {
                'registered': True, 'enabled': profile.enabled, 'enrolled': 'not_applicable',
                'authorized': 'unknown', 'exact_task_approval': 'not_applicable',
                'health': 'unknown', 'availability': 'unknown', 'capacity': 'unknown',
                'instance_epoch': runtime.epoch, 'loaded_source_attestation': 'unknown'}
            candidate.native_policy = {
                'runtime_source': 'initialized_in_process', 'context': 'unavailable',
                'caller_scope': 'unknown', 'team': 'unknown', 'receiver_authority': 'unknown',
                'contract_proof': 'unavailable', 'persistent_context': False, 'persistent_memory': False,
                'enabled': policy.enabled, 'max_depth': policy.max_depth,
                'timeout_seconds': policy.timeout_seconds, 'configured_model': model,
                'configured_provider': provider, 'effective_route': 'declared',
                'cancellation': 'cooperative', 'recovery': 'frozen_authority',
                'hard_termination': False, 'supported_verified_contracts': []}
            if scope is None:
                candidate.reasons.append('native_active_caller_unavailable')
            else:
                self._caller_policy(candidate, scope, registry, policy, turn_policy, source_auth, route, task, now)
                self._admission(candidate, scope, now)
            result.append(_attach(candidate, None, candidate.admission, now))
        # A registry/configuration/caller replacement during the read cannot
        # leave an apparently coherent observation from the former objects.
        runtime.validate()
        current = contract.digest({'settings': runtime.settings(), 'registry': [
            profile.to_dict() for profile in runtime.registry().list(include_disabled=True)]})
        if (current != snapshot or runtime.caller() is not scope
                or scope is not None and (runtime.cached_route(scope) != route
                                          or scope.tool._policy() != turn_policy)):
            raise DiscoveryError('initialized_runtime_changed')
        return result

    @staticmethod
    def _caller_policy(candidate, scope, registry, policy, turn, source_auth, route, task, now):
        from agent.tools.agent_delegate.agent_delegate import DelegationPolicy
        native = candidate.native_policy
        native.update(context='active', source_agent_id=scope.speaker_id,
                      owner_agent_id=scope.owner_id, caller_model=route['model'],
                      caller_provider=route['provider'], effective_route=route['origin'])
        if not scope.root:
            candidate.reasons.append('native_delegation_lineage_unknown')
            return
        native.update(caller_scope='root', delegation_depth=0, delegation_trace=[scope.speaker_id])
        if not isinstance(turn, DelegationPolicy):
            raise DiscoveryError('native_policy_unavailable')
        members = scope.applied.members
        team = None if members is None else set(members) | {scope.owner_id}
        team_allowed = None if team is None else scope.speaker_id in team and candidate.target_id in team
        source = registry.get(scope.speaker_id, require_enabled=False)
        receiver_allowed = policy.allows(source.id, candidate.target_id) and turn.allows(source.id, candidate.target_id)
        cycle = candidate.target_id == source.id
        depth_allowed = 1 <= min(policy.max_depth, turn.max_depth)
        native.update(enabled=policy.enabled and turn.enabled,
                      max_depth=min(policy.max_depth, turn.max_depth), timeout_seconds=turn.timeout_seconds,
                      team='applied_session_state' if team is not None else 'unknown',
                      receiver_allowed=receiver_allowed, team_allowed=team_allowed,
                      cycle_denied=cycle, depth_allowed=depth_allowed,
                      caller_authority='resolved' if source_auth is not None else 'unknown')
        if team is not None:
            native['team_members'] = sorted(team)
        if team is None:
            candidate.reasons.append('native_team_unknown')
        if not source.enabled or not receiver_allowed or team_allowed is False or cycle or not depth_allowed:
            candidate.reasons.append('native_team_policy_or_cycle_denied')
        if source_auth is None:
            candidate.reasons.append('native_caller_authority_unknown')
        candidate.execution_budget_seconds = turn.timeout_seconds
        if turn.timeout_seconds > task.timeout_seconds or now + turn.timeout_seconds > task.deadline:
            candidate.reasons.append('execution_budget_incompatible')
        candidate.boundary_fingerprint = contract.digest({
            'target': candidate.target_id, 'epoch': scope.anchor.epoch,
            'session': scope.session, 'run': scope.run_id, 'source': source.id,
            'owner': scope.owner_id, 'team': sorted(team) if team is not None else None,
            'native_policy': native, 'source_authority': NativeSource._authority_dict(source_auth)
            if source_auth is not None else None, 'receiver_authority': 'unknown'})

    def _admission(self, candidate, scope, now):
        # Borrow liveness and existing locks only. Never open a recovery store,
        # infer free capacity from an unlocked mutex, or reserve a receiver.
        from agent.recovery.service import RecoveryService
        from agent.tools.agent_delegate.agent_delegate import _relay_locks_guard, _relay_locks
        service = getattr(self.runtime.owner, 'recovery_service', None)
        if not isinstance(service, RecoveryService) or service._thread is None:
            return
        health = 'healthy' if (service._thread.is_alive() and not service._stop.is_set()
                               and service.last_error is None) else 'unavailable'
        busy = False
        if scope.root:
            session = scope.tool._session_id(scope.speaker_id, candidate.target_id, scope.session)
            with _relay_locks_guard:
                lock = _relay_locks.get(session)
                busy = lock is not None and lock.locked()
        candidate.runtime_state.update(health=health, availability='at_capacity' if busy else 'unknown',
                                       capacity='at_capacity' if busy else 'unknown')
        candidate.admission = AdmissionObservation(candidate.boundary_fingerprint,
            contract.digest({'epoch': self.runtime.epoch, 'health': health, 'busy': busy}),
            now, now + 5, health, 0 if busy else None, None)
