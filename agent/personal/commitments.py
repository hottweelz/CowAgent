"""Compose owner commitments, approved reads and native local delivery."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
import time
import uuid
from zoneinfo import ZoneInfo

from agent.memory.commitments import CommitmentStore
from agent.memory.personal import PersonalStore
from agent.permission.policy import invoke
from agent.personal.service import PersonalService
from agent.personal.articles import normalize_articles, rank_and_select, render_briefing
from agent.tools.web_fetch.approved_json import ApprovedJsonRead, create_read_context
from agent.tools.base_tool import ToolResult
from config import conf


def _retry_time(value, now):
    if isinstance(value, str):
        try:
            return now + int(value) if value.isdigit() else parsedate_to_datetime(value).timestamp()
        except (ValueError, TypeError, OverflowError):
            pass
    return now + 60


def _cache_policy(header, now):
    directives = {part.strip().lower() for part in (header or '').split(',')}
    if 'no-store' in directives:
        return False, 0
    if 'no-cache' in directives:
        return True, 0
    age = next((value for value in directives if re.fullmatch(r'max-age=\d{1,10}', value)), '')
    return True, now + int(age.split('=')[1]) if age else 0


class CommitmentService(PersonalService):
    def __init__(self, agent_id, session_id):
        super().__init__(agent_id, session_id)
        self.store = CommitmentStore(self.store._store, owner_agent_id=self.profile.id)

    def _endpoints(self):
        endpoints = conf().get('personal_http_endpoints') or {}
        if not isinstance(endpoints, dict):
            raise ValueError('Approved endpoints are unavailable')
        return endpoints

    def _validate_fields(self, fields):
        if not isinstance(fields, dict):
            raise ValueError('Invalid fields')
        if 'endpoint' in fields and fields['endpoint'] not in self._endpoints():
            raise ValueError('Endpoint is not approved by this instance')
        schedule = fields.get('schedule')
        if schedule is not None:
            from agent.tools.scheduler.time_utils import next_cron_occurrence
            if not isinstance(schedule, dict) or set(schedule) != {'cron', 'timezone'}:
                raise ValueError('Invalid schedule')
            zone = ZoneInfo(schedule['timezone'])
            next_cron_occurrence(schedule['cron'], datetime.now(timezone.utc), zone)

    def snapshot(self):
        records = self.store.snapshot()
        from agent.personal.scheduling import scheduling_status
        for record in records:
            record.update(scheduling_status(self.profile, record))
            # Raw fetch payloads belong in the bounded cache, not every UI refresh.
            record['runs'] = [{k: v for k, v in run.items() if k not in ('articles',)}
                              for run in record['runs']]
        personal = PersonalStore.snapshot(self.store, self.session_id)
        return {'status': 'success', 'identity': {'agent_id': self.profile.id, 'name': self.profile.name},
                'source_seq': personal['latest_source_seq'],
                'commitments': records, 'approved_endpoints': list(self._endpoints()),
                'attention': self.store.attention_snapshot(),
                'attention_history': self.store.attention_snapshot(include_dismissed=True),
                'approved_actions': [action for action in personal.get('action_summaries', [])
                                     if action.get('status') in ('approved', 'executing', 'completed', 'failed', 'uncertain')],
                'publication': 'Draft only. External publication requires separate approval and a supported connector.'}

    def mutate(self, body):
        op, cid = body.get('operation'), body.get('commitment_id')
        source = body.get('source_seq')
        result = None
        if op in ('create', 'update'):
            fields = body.get('fields')
            self._validate_fields(fields)
            record = (self.store.create(self.session_id, fields, source) if op == 'create' else
                      self.store.update(self.session_id, cid, fields, source, body.get('revision')))
            from agent.personal.scheduling import sync_commitment
            sync_commitment(self.profile, record)
        elif op == 'run':
            # UI retries can use an explicit request ID. It never selects a URL,
            # authority, model prompt or replacement owner instruction.
            request_id = body.get('request_id') or uuid.uuid4().hex
            if not isinstance(request_id, str) or not request_id or len(request_id) > 100:
                raise ValueError('Invalid request ID')
            result = self.run(cid, 'manual:' + request_id)
        elif op == 'followup':
            self.store.followup(self.session_id, cid, body.get('text'), body.get('article_ids', []), source)
        elif op == 'save_draft':
            self.store.save_draft(self.session_id, cid, body.get('text'), body.get('source_ids'),
                                  body.get('claims'), source)
        elif op == 'acknowledge_run':
            self.store.acknowledge_uncertain(self.session_id, cid, body.get('run_id'), source)
        elif op == 'decide_attention':
            self.store.decide_attention(self.session_id, cid, body.get('attention_id'),
                                        body.get('decision'), source)
        elif op == 'propose_publication':
            self.store.propose_publication(self.session_id, cid, body.get('draft_id'),
                                           source, body.get('expires_at'))
        else:
            raise ValueError('Unknown owner operation')
        response = self.snapshot()
        if result is not None:
            response['execution'] = {k: v for k, v in result.items() if k != 'articles'}
        return response

    def _fetch(self, record, cache):
        endpoints = self._endpoints()
        url = record['endpoint']
        if url not in endpoints:
            raise ValueError('Endpoint no longer approved')
        configured_relays = conf().get('personal_http_relays') or {}
        relays = {url: configured_relays[url]} if url in configured_relays else None
        tool = ApprovedJsonRead({url: endpoints[url]}, relays=relays)
        context = create_read_context(tool, self.profile, read_grant=record['read_authorized'])
        arguments = {'url': url}
        for name in ('etag', 'last_modified'):
            if cache.get(name):
                arguments[name] = cache[name]
        return invoke(tool, arguments, context)

    def _interpret(self, record, selection):
        from agent.personal.interpretation import interpret
        return interpret(self.profile, self.session_id, record, selection)

    def run(self, commitment_id, occurrence_key, expected_revision=None, *, trigger='manual'):
        claim = self.store.claim_run(commitment_id, occurrence_key, expected_revision)
        if not claim['claimed']:
            return claim
        run_id = claim['run_id']
        evaluation = {'initiative_id': run_id, 'trigger': trigger,
                      'classification': 'authorized_read_only', 'observed': {},
                      'executed': [], 'verified': False}
        def failed(error, cache=None):
            evaluation.update(classification='blocked_or_uncertain', error=error)
            return self.store.fail_run(run_id, error, cache, evaluation=evaluation)
        try:
            record = self.store.assert_active(commitment_id, claim['revision'])
            evaluation['observed'] = {'commitment_id': commitment_id, 'revision': claim['revision'],
                                      'grant': record['grant'], 'status': record['status']}
            cache = self.store.get_cache(commitment_id)
            if cache.get('endpoint') != record['endpoint']:
                cache = {'endpoint': record['endpoint']}
            now = int(time.time())
            if cache.get('retry_at', 0) > now:
                return failed('rate limited')
            fresh_cache = cache.get('fresh_until', 0) > now and 'articles' in cache
            result = (ToolResult.success({'status': 'not_modified'}) if fresh_cache else
                      self._fetch(record, cache))
            if result.status != 'success':
                meta = result.ext_data or {}
                if meta.get('http_status') == 429:
                    cache['retry_at'] = _retry_time(meta.get('retry_after'), now)
                    return failed('rate limited', cache)
                return failed('network error')
            response = result.result
            if response.get('status') == 'not_modified':
                if 'articles' not in cache:
                    return failed('invalid response')
                articles = cache['articles']
            else:
                try:
                    articles = normalize_articles(response.get('data'), fetched_at=now)
                except (ValueError, TypeError):
                    return failed('invalid response')
            evaluation['executed'].append('approved_read_or_validated_cache')
            self.store.assert_active(commitment_id, claim['revision'])
            followups = next(r['followups'] for r in self.store.snapshot()
                             if r['commitment_id'] == commitment_id)
            selection = rank_and_select(articles, record['preferences'],
                                        self.store.get_coverage(commitment_id), followups=followups)
            proposals = []
            if record['initiative_enabled'] and selection['selected']:
                from agent.personal.interpretation import InterpretationError
                try:
                    advice = self._interpret({**record, 'followups': followups}, selection)
                except InterpretationError as exc:
                    return failed(exc.code.replace('_', ' '))
                selected_ids = set(advice['selected_ids'])
                selection = {**selection, 'selected': [row for row in selection['selected']
                                                       if row['article_id'] in selected_ids]}
                evaluation['model'] = advice['provenance']
                evaluation['interpretation'] = advice['reasons']
                proposals = advice['proposals']
            self.store.assert_active(commitment_id, claim['revision'])
            notify = trigger != 'scheduled' or bool(selection['selected'])
            evaluation['classification'] = ('new_approval_required' if proposals else
                                             'authorized_bounded_write' if selection['selected'] else
                                             'no_action_necessary')
            evaluation['proposed_actions'] = proposals
            briefing = render_briefing(selection, record['objective'], now)
            if evaluation.get('interpretation'):
                from agent.personal.articles import _markdown_text
                briefing += '\n\nBullGod’s assessment (source-based interpretation):\n' + '\n'.join(
                    '- ' + _markdown_text(evaluation['interpretation'][row['article_id']])
                    for row in selection['selected'])
            if proposals:
                briefing += '\n\nProposed next steps and their current review status are saved in Personal commitments. No new permission or external action was taken.'
            if fresh_cache:
                briefing += '\n\nUsed the source cache within its advertised freshness period.'
            updated_cache = {'endpoint': record['endpoint'], 'articles': articles,
                             'checked_at': now, 'retry_at': 0}
            for field in ('etag', 'last_modified', 'cache_control'):
                updated_cache[field] = response.get(field) or cache.get(field)
            retain, fresh_until = _cache_policy(updated_cache.get('cache_control'), now)
            updated_cache['fresh_until'] = cache.get('fresh_until', 0) if fresh_cache else fresh_until
            if not retain:
                updated_cache = {'endpoint': record['endpoint'], 'checked_at': now, 'retry_at': 0}
            evaluation['executed'].append('record_own_commitment_state')
            evaluation['verified'] = True  # Persisted only with the successful atomic completion below.
            evaluation['notification'] = 'meaningful_finding' if notify else 'quiet_check'
            return self.store.complete_run(run_id, articles, selection['selected'], briefing, updated_cache,
                                            evaluation=evaluation, notify=notify, proposals=proposals)
        except ValueError:
            evaluation['verified'] = False
            return failed('commitment changed')
        except Exception:
            # No response body, exception text, credential or URL enters state.
            evaluation['verified'] = False
            return failed('delivery error')
