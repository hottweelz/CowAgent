"""Trusted host supervisory API; not a worker tool or an external Agent embed."""
import time

from .contract import ProtocolError, authorize, digest, identifier, normalize_spec, validate_discovery
from .transport import RemoteRejected, TransportUnavailable
from .journal import ExternalBusy


def outcomes(row):
    remote = row['observation'] or {}
    report = row.get('verification') or {}
    acceptance = report.get('acceptance', {}).get('status', 'unverified')
    effects = report.get('external_state', {}).get('status', 'unverified')
    cancelled_unsent = bool(row['cancel_requested']) and not row['submission_started']
    return {'task_id': row['task_id'], 'runtime_id': row['runtime_id'],
            'transport_status': row['transport_status'],
            'execution_status': 'cancelled_before_submission' if cancelled_unsent else remote.get('state', 'unknown'),
            'session_id': remote.get('session_id'), 'revision': remote.get('revision'),
            'runtime_result': remote.get('result'), 'result_provenance': 'authenticated_runtime_claim',
            'cancel_requested': bool(row['cancel_requested']) or remote.get('cancel_requested', False),
            'termination_confirmed': cancelled_unsent or remote.get('termination_confirmed', False),
            'observation_current': row['transport_status'] == 'acknowledged',
            'verification_checked_at': report.get('checked_at'),
            'acceptance_status': acceptance, 'external_state_status': effects,
            'verified': remote.get('state') == 'completed' and acceptance == 'passed' and effects == 'confirmed',
            'last_error': row['last_error']}


class ExternalSupervisor:
    """Explicitly enrolled host caller. No global registration or background send."""
    def __init__(self, journal, transport, *, owner_id, source_id, conversation_id, verifier=None):
        if not all(identifier(v) for v in (owner_id, source_id, conversation_id)):
            raise ProtocolError('Invalid supervisor caller identity')
        self.journal, self.transport, self.verifier = journal, transport, verifier
        self.owner_id, self.source_id, self.conversation_id = owner_id, source_id, conversation_id

    def _owned(self, task_id):
        row = self.journal.get(task_id)
        self._identity(row['spec'])
        if row['supervisor_id'] != self.transport.credential.supervisor_id:
            raise ProtocolError('Task belongs to another supervisor')
        return row

    def _identity(self, spec):
        if (spec['owner_id'] != self.owner_id or spec['source_id'] != self.source_id
                or spec['conversation_id'] != self.conversation_id
                or spec['runtime_id'] != self.transport.credential.runtime_id):
            raise ProtocolError('Task is outside enrolled caller identity')

    def discover(self):
        return validate_discovery(self.transport.discover(), self.transport.credential)

    def prepare(self, spec):
        spec = normalize_spec(spec)
        self._identity(spec)
        if spec['task']['operation'] == 'analyze_records':
            from .approved_dispatch import ApprovalJournal
            if not isinstance(self.journal, ApprovalJournal):
                raise ProtocolError('Analysis requires an approval journal')
        return self.journal.create(self.transport.credential.supervisor_id, spec)

    def approve(self, task_id, *, approved_by, expires_at):
        row = self._owned(task_id)
        if row['spec']['task']['operation'] == 'analyze_records':
            raise ProtocolError('Analysis requires an operator decision')
        approval = {'approved_by': approved_by, 'expires_at': expires_at, 'task_hash': digest(row['spec'])}
        authorize(row['spec'], self.transport.credential, approval)
        with self.journal.lock(task_id):
            self.journal.approve(task_id, approval)
        return outcomes(self._owned(task_id))

    def delegate(self, spec):
        row = self.prepare(spec)
        return self.submit(row['task_id'])

    def submit(self, task_id):
        self._owned(task_id)
        try:
            with self.journal.lock(task_id) as row:
                if row['submission_started'] or row['cancel_requested']:
                    # Includes a crash after send intent. Only status can reconcile it.
                    return outcomes(row)
                if row['spec']['task']['operation'] == 'analyze_records':
                    from .approved_dispatch import ApprovalJournal
                    if not isinstance(self.journal, ApprovalJournal):
                        raise ProtocolError('Analysis requires an approval journal')
                    row = self.journal.begin_submit(task_id, self.transport.credential)
                else:
                    authorize(row['spec'], self.transport.credential, row['approval'])
                    self.journal.event(task_id, 'submit_intent', {'task_hash': row['spec_hash']}, transport_status='sending')
                try:
                    observation = self.transport.submit(row['spec'], row['approval'])
                    return outcomes(self.journal.observe(task_id, observation))
                except RemoteRejected:
                    self.journal.event(task_id, 'submit_rejected', {'error': 'runtime_rejected_submission'}, transport_status='rejected')
                except (TransportUnavailable, ProtocolError, ValueError):
                    self.journal.event(task_id, 'submit_uncertain', {'error': 'submission_outcome_unknown'}, transport_status='uncertain')
                return outcomes(self._owned(task_id))
        except ExternalBusy:
            return outcomes(self._owned(task_id))

    def _query(self, task_id, action):
        self._owned(task_id)
        with self.journal.lock(task_id) as row:
            if action == 'cancel':
                self.journal.event(task_id, 'cancel_requested', {'requested_at': time.time()})
                if hasattr(self.journal, 'claim_cancel'):
                    self.journal.claim_cancel(task_id)
            if not row['submission_started']:
                return outcomes(self._owned(task_id))
            try:
                value = getattr(self.transport, action)(row['spec'])
                return outcomes(self.journal.observe(task_id, value))
            except RemoteRejected as exc:
                self.journal.event(task_id, action + '_rejected', {'error': 'runtime_rejected_' + str(exc)}, transport_status='rejected')
                return outcomes(self._owned(task_id))
            except (TransportUnavailable, ProtocolError, ValueError):
                # Preserve last authenticated observation; loss of contact isn't death.
                self.journal.event(task_id, action + '_unavailable', {'error': 'authenticated_observation_unavailable'}, transport_status='unreachable')
                return outcomes(self._owned(task_id))

    def status(self, task_id):
        return self._query(task_id, 'status')

    def cancel(self, task_id):
        return self._query(task_id, 'cancel')

    def result(self, task_id):
        return self._query(task_id, 'result')

    def flush_pending_cancellations(self):
        """Claim once before IPC; a lost reply requires an explicit retry."""
        if not hasattr(self.journal, 'pending_cancellations'):
            return []
        results = []
        for row in self.journal.pending_cancellations(self.transport.credential.supervisor_id, self.transport.credential.runtime_id):
            spec = row['spec']
            if (spec['owner_id'], spec['source_id'], spec['conversation_id']) != (self.owner_id, self.source_id, self.conversation_id):
                continue
            try:
                with self.journal.lock(row['task_id']):
                    if self.journal.claim_cancel(row['task_id']):
                        try:
                            value = self.transport.cancel(spec)
                            results.append(outcomes(self.journal.observe(row['task_id'], value)))
                        except (RemoteRejected, TransportUnavailable, ProtocolError, ValueError):
                            self.journal.event(row['task_id'], 'cancel_unavailable', {'error': 'cancellation_outcome_unknown'}, transport_status='unreachable')
                            results.append(outcomes(self._owned(row['task_id'])))
            except ExternalBusy:
                continue
        return results

    def reconcile(self):
        """After host restart, query existing IDs only. Never submit or restart."""
        results = self.flush_pending_cancellations()
        for row in self.journal.pending(self.transport.credential.supervisor_id, self.transport.credential.runtime_id):
            spec = row['spec']
            if (spec['owner_id'], spec['source_id'], spec['conversation_id']) != (self.owner_id, self.source_id, self.conversation_id):
                continue
            if row['submission_started']:
                results.append(self.status(row['task_id']))
        return results

    def verify(self, task_id):
        self._owned(task_id)
        with self.journal.lock(task_id) as row:
            if not row['observation'] or row['observation']['state'] != 'completed':
                raise ProtocolError('Execution is not completed')
            if self.verifier is None:
                return outcomes(row)
            report = self.verifier.verify(row)
            row = self.journal.verify(task_id, row['observation']['revision'], report)
            return outcomes(row)
