"""Deterministic discovery, eligibility and selection. This module never dispatches."""
import time

from agent.external.contract import digest, finite
from agent.permission.authority import _current_registry
from agent.registry import AgentRegistry

from .contracts import (
    Candidate, DiscoveryError, MECHANISMS, SelectionPolicy, TaskRequirements, VERSION,
)


class DiscoveryService:
    def __init__(self, registry_source=_current_registry, *, native_source=None,
                 external_source=None, policy=None, clock=time.time):
        self.registry_source = registry_source
        self.native_source = native_source
        self.external_source = external_source
        self.policy = policy or SelectionPolicy()
        self.clock = clock
        if not isinstance(self.policy, SelectionPolicy):
            raise DiscoveryError('invalid_policy')

    def discover(self, task):
        """List all derived candidates with the same deterministic policy as select."""
        return self.select(task)

    def select(self, requirements):
        now = self.clock()
        result = {'protocol': VERSION, 'status': 'denied', 'selected': None,
                  'candidates': [], 'rejected_alternatives': [], 'reasons': [],
                  'policy_id': self.policy.policy_id,
                  'policy_revision': self.policy.revision,
                  'policy_fingerprint': self.policy.fingerprint,
                  'task_fingerprint': None, 'selection_time': now if finite(now) else None, 'expires_at': None,
                  'dispatch_permitted': False, 'execution_revalidation_required': True,
                  'ranking_rationale': [], 'audit': None}
        try:
            if not finite(now):
                raise DiscoveryError('invalid_clock')
            task = requirements if isinstance(requirements, TaskRequirements) else TaskRequirements.from_dict(requirements)
            result['task_fingerprint'] = task.fingerprint
            if task.policy_id != self.policy.policy_id:
                raise DiscoveryError('policy_mismatch')
            if task.deadline <= now:
                raise DiscoveryError('task_expired')
            registry = self.registry_source()
            if not isinstance(registry, AgentRegistry):
                raise DiscoveryError('authoritative_registry_unavailable')
            candidates = self._candidates(registry, task, now)
            keys = [candidate.key for candidate in candidates]
            if len(keys) != len(set(keys)):
                raise DiscoveryError('ambiguous_identity_binding')
        except DiscoveryError as exc:
            reason = str(exc)
            if reason not in {
                'invalid_requirements', 'conflicting_requirements', 'policy_mismatch', 'task_expired',
                'invalid_clock', 'authoritative_registry_unavailable', 'ambiguous_identity_binding',
                'invalid_candidate_source', 'invalid_external_binding',
            }:
                reason = 'authoritative_state_unavailable'
            result['status'] = 'invalid_request' if reason in {
                'invalid_requirements', 'conflicting_requirements', 'policy_mismatch', 'task_expired',
            } else 'denied'
            result['reasons'] = [reason]
            return self._audit(result)
        except Exception:
            result['reasons'] = ['authoritative_state_unavailable']
            return self._audit(result)

        evaluated = [(candidate, self._eligibility(candidate, task, now)) for candidate in candidates]
        persistent_denials = {
            candidate.target_id for candidate, reasons in evaluated
            if candidate.mechanism == 'persistent_named'
            and 'persistent_named' in set(task.permitted_mechanisms) - set(task.prohibited_mechanisms)
            and set(reasons) - {'mechanism_not_permitted', 'requested_identity_mismatch'}
        }
        eligible, approval = [], []
        for candidate, reasons in evaluated:
            if (candidate.mechanism != 'persistent_named' and candidate.target_id in persistent_denials
                    and task.requested_agent_id == candidate.target_id
                    and task.persistent_memory != 'prohibited'):
                reasons.append('persistent_denial_no_fallback')
            reasons = sorted(set(reasons))
            public = candidate.public()
            public.update({'reasons': reasons, 'eligible_for_admission': not reasons,
                           'verification_status': 'verified' if candidate.proof else 'unverified',
                           'dispatch_permitted': False, 'execution_revalidation_required': True})
            result['candidates'].append(public)
            if not reasons:
                eligible.append((candidate, public))
            elif reasons == ['approval_required']:
                approval.append(public)
            if reasons:
                result['rejected_alternatives'].append({
                    'target_id': candidate.target_id, 'mechanism': candidate.mechanism, 'reasons': reasons,
                })
        result['candidates'].sort(key=lambda row: (row['target_id'], row['mechanism']))
        result['rejected_alternatives'].sort(key=lambda row: (row['target_id'], row['mechanism']))
        if eligible:
            eligible.sort(key=lambda item: self._rank(item[0]))
            selected, public = eligible[0]
            result.update(status='selected', selected=public,
                          expires_at=min(task.deadline, selected.expires_at or task.deadline),
                          ranking_rationale=['configured_target_preference', 'known_load_before_unknown',
                                             'lower_known_load', 'configured_model_preference',
                                             'stable_target_and_mechanism'])
            result['ranked_candidates'] = [row for _, row in eligible]
        elif approval:
            result['status'] = 'approval_required'
            result['reasons'] = ['approval_required']
            result['approvals_required'] = [
                {'target_id': row['target_id'], 'mechanism': row['mechanism'], 'approval': 'task'}
                for row in approval]
        else:
            result['reasons'] = ['no_eligible_candidate']
        return self._audit(result)

    def _candidates(self, registry, task, now):
        if self.native_source is None:
            candidates = [Candidate(
                profile.id, 'registered', 'native_isolated', digest(profile.to_dict()),
                digest({'profile': profile.to_dict(), 'mechanism': 'native_isolated'}),
                digest({'target': profile.id, 'admission': 'unknown'}),
                reasons=['native_context_unavailable'] + ([] if profile.enabled else ['identity_disabled']),
                max_concurrency=1,
            ) for profile in registry.list(include_disabled=True)]
        else:
            candidates = list(self.native_source.candidates(registry, task, now))
        if self.external_source:
            candidates.extend(self.external_source.candidates(registry, task, now))
        # Custom host sources cannot promote an unregistered native identity.
        for candidate in candidates:
            if not isinstance(candidate, Candidate) or candidate.mechanism not in MECHANISMS:
                raise DiscoveryError('invalid_candidate_source')
            if candidate.identity_kind == 'registered':
                try:
                    profile = registry.get(candidate.target_id, require_enabled=False)
                    if not profile.enabled:
                        candidate.reasons.append('identity_disabled')
                    if digest(profile.to_dict()) != candidate.identity_fingerprint:
                        candidate.reasons.append('identity_changed')
                except (KeyError, ValueError):
                    candidate.reasons.append('identity_unavailable')
            elif candidate.identity_kind != 'external' or candidate.mechanism != 'external_runtime':
                candidate.reasons.append('identity_kind_mismatch')
        return candidates

    @staticmethod
    def _eligibility(candidate, task, now):
        reasons = list(candidate.reasons)
        if candidate.mechanism not in set(task.permitted_mechanisms) - set(task.prohibited_mechanisms):
            reasons.append('mechanism_not_permitted')
        if task.requested_agent_id is not None and candidate.target_id != task.requested_agent_id:
            reasons.append('requested_identity_mismatch')
        persistent = candidate.mechanism == 'persistent_named'
        isolated = candidate.mechanism == 'native_isolated'
        if task.persistent_memory == 'required' or task.persistent_context == 'required':
            if not persistent:
                reasons.append('persistent_context_required')
        if task.persistent_memory == 'prohibited' or task.persistent_context == 'prohibited':
            if not isolated:
                # External runtimes own their context; no verified stateless
                # mode exists in the supported adapter contract.
                reasons.append('persistent_context_prohibited')
        proof = candidate.proof
        if proof is None:
            reasons.append('capability_unverified')
        else:
            contract = proof.contract
            if (proof.configuration_fingerprint != candidate.configuration_fingerprint
                    or not proof.issued_at <= now < proof.expires_at):
                reasons.append('capability_unverified')
                candidate.proof = None
            if (task.category not in contract.categories or task.input_contract not in contract.input_contracts
                    or task.output_contract not in contract.output_contracts):
                reasons.append('capability_contract_mismatch')
            if not set(task.required_tools) <= set(contract.tools) & set(candidate.authority):
                reasons.append('required_tools_unavailable')
            if task.verification != 'none' and task.verification != contract.verification:
                reasons.append('verification_insufficient')
            if task.recovery != 'none' and task.recovery != contract.recovery:
                reasons.append('recovery_insufficient')
            if task.cancellation != 'none' and task.cancellation != contract.cancellation:
                reasons.append('cancellation_insufficient')
            budget = candidate.execution_budget_seconds
            if not finite(budget) or budget <= 0:
                reasons.append('execution_budget_unknown')
            else:
                if budget > task.timeout_seconds or now + budget > task.deadline:
                    reasons.append('execution_budget_incompatible')
                if budget > contract.timeout_ceiling:
                    reasons.append('timeout_unsupported')
        if not set(candidate.authority) <= set(task.max_authority):
            reasons.append('authority_exceeds_task_limit')
        if candidate.model is None or candidate.provider is None:
            reasons.append('effective_model_unknown')
        if task.model is not None and candidate.model != task.model:
            reasons.append('model_constraint_mismatch')
        if task.provider is not None and candidate.provider != task.provider:
            reasons.append('provider_constraint_mismatch')
        if candidate.mechanism != 'native_isolated':
            if task.approval == 'prohibited':
                reasons.append('approval_policy_incompatible')
        elif task.approval == 'required':
            reasons.append('approval_contract_unavailable')
        observation = candidate.admission
        if observation is None:
            reasons.append('runtime_admission_unknown')
        elif (observation.boundary_fingerprint != candidate.boundary_fingerprint
              or not observation.issued_at <= now < observation.expires_at
              or now - observation.issued_at >= 30 or observation.expires_at - observation.issued_at > 30):
            reasons.append('runtime_admission_stale')
        else:
            if observation.health != 'healthy':
                reasons.append('runtime_unavailable' if observation.health == 'unavailable' else 'runtime_health_unknown')
            if observation.available_slots is None:
                reasons.append('runtime_admission_unknown')
            elif observation.available_slots < task.concurrency:
                reasons.append('concurrency_limit')
        if candidate.max_concurrency is not None and task.concurrency > candidate.max_concurrency:
            reasons.append('concurrency_limit')
        if candidate.expires_at is not None and candidate.expires_at <= now:
            reasons.append('candidate_state_expired')
        return reasons

    def _rank(self, candidate):
        def preference(value, options):
            return options.index(value) if value in options else len(options)
        load = candidate.admission.active_load
        return (preference(candidate.target_id, self.policy.preferred_targets),
                load is None, load if load is not None else 0,
                preference(candidate.model, self.policy.preferred_models),
                candidate.target_id, candidate.mechanism)

    def revalidate(self, selection, task):
        """Rebuild authority/evidence and compare; never authorize or dispatch."""
        current = self.select(task)
        valid = False
        if isinstance(selection, dict) and selection.get('status') == 'selected' and current['status'] == 'selected':
            old, new = selection.get('selected'), current['selected']
            valid = (isinstance(old, dict) and selection.get('task_fingerprint') == current['task_fingerprint']
                     and selection.get('policy_fingerprint') == current['policy_fingerprint']
                     and finite(selection.get('expires_at')) and self.clock() < selection['expires_at']
                     and all(old.get(key) == new.get(key) for key in (
                         'target_id', 'mechanism', 'identity_fingerprint', 'configuration_fingerprint',
                         'state_fingerprint')))
        return {'protocol': VERSION, 'valid': valid, 'dispatch_permitted': False,
                'execution_revalidation_required': True,
                'reasons': [] if valid else ['selection_invalidated'], 'current': current}

    @staticmethod
    def mechanisms():
        return list(MECHANISMS)

    @staticmethod
    def _audit(result):
        """An allowlisted record for the host's existing logs; no persistence."""
        selected = result['selected']
        result['audit'] = {
            'protocol': VERSION, 'event': 'selection_evaluated',
            'status': result['status'], 'selected_target': selected['target_id'] if selected else None,
            'selected_mechanism': selected['mechanism'] if selected else None,
            'task_fingerprint': result['task_fingerprint'],
            'policy_fingerprint': result['policy_fingerprint'],
            'state_fingerprint': selected['state_fingerprint'] if selected else None,
            'selection_time': result['selection_time'], 'dispatch_permitted': False,
        }
        result['decision_fingerprint'] = digest(result['audit'])
        return result
