"""Read only audit-owned task results and metadata. Never reads private memory."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sqlite3

HERE = Path(__file__).resolve().parent
WORKSPACE = Path('/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime/workspace')


def connect(path):
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    return db


def reconcile(receipt, event_receipt, tasks):
    """Reconcile retained evidence without trusting result identity claims."""
    assert receipt['session_id'] == event_receipt['session_id']
    assert receipt['request_id'] == event_receipt['request_id']
    assert event_receipt['stream_ended']
    assert hashlib.sha256((HERE / 'tasks.json').read_bytes()).hexdigest() == event_receipt['dataset_sha256']
    expected = {t['agent_id']: t for t in tasks}
    workers = receipt['workers']
    assert len(workers) == len(expected) == 2
    assert {w['target_agent_id'] for w in workers} == set(expected)
    assert len({w['task_id'] for w in workers}) == 2
    assert len({w['attempt_id'] for w in workers}) == 2
    events = event_receipt['events']
    starts = [e for e in events if e['type'] == 'tool_start']
    assert len(starts) == 2 and all(e['tool'] == 'agent_delegate' for e in starts)
    correlations = []
    for worker in workers:
        target = worker['target_agent_id']
        assert worker['owner_id'] == worker['source_agent_id'] == 'default'
        assert worker['session_id'] == receipt['session_id']
        assert worker['state'] == 'completed' and worker['attempt_count'] == 1
        assert len(worker['attempts']) == 1
        attempt = worker['attempts'][0]
        assert attempt['attempt_id'] == worker['attempt_id'] and attempt['state'] == 'completed'
        matches = [e for e in starts if e['target_agent_id'] == target]
        assert len(matches) == 1
        start = matches[0]
        assert start['task_identifier'] == worker['result']['task_id'] == expected[target]['task_id']
        related = [e for e in events if e.get('card_id', e.get('tool_call_id')) == start['tool_call_id']]
        assert [e['type'] for e in related] == ['tool_start', 'peer_start', 'peer_end', 'tool_end']
        _, peer_start, peer_end, end = related
        assert peer_start['agent_id'] == peer_end['agent_id'] == target
        assert peer_start['source_id'] == 'default'
        assert peer_end['status'] == 'done' and end['status'] == 'success'
        times = [datetime.fromisoformat(attempt[k].replace('Z', '+00:00')).timestamp()
                 for k in ('started_at', 'ended_at')]
        assert start['observed_at'] <= times[0] <= times[1] <= end['observed_at']
        expected_result = expected[target]['expected']
        identity_matches = worker['result'].get('agent_id') == target
        result_matches = worker['result'] == expected_result
        arithmetic_matches = {k: v for k, v in worker['result'].items() if k != 'agent_id'} == {
            k: v for k, v in expected_result.items() if k != 'agent_id'}
        assert arithmetic_matches
        assert worker['arithmetic_and_exclusions_match'] == arithmetic_matches
        assert worker['claimed_identity_matches_target'] == identity_matches
        assert worker['result_matches_expected'] == result_matches
        correlations.append({'target': target, 'task_identifier': start['task_identifier'],
                             'task_id': worker['task_id'], 'attempt_id': worker['attempt_id'],
                             'tool_call_id': start['tool_call_id'], 'identity_matches': identity_matches})
    return {'status': 'passed', 'workers': correlations,
            'basis': 'same isolated parent session, unique target and task identifier, matching time window',
            'limit': 'The retained SSE projection has no durable task ID; correlation is not a shared-key join.',
            'identity_claims_match': all(c['identity_matches'] for c in correlations)}


def main():
    event_receipt = json.loads((HERE / 'live-events.json').read_text())
    session = event_receipt['session_id']
    if not session.startswith('audit-routing-002-'):
        raise ValueError('Audit session required')
    tasks = json.loads((HERE / 'tasks.json').read_text())['tasks']
    expected = {t['agent_id']: t['expected'] for t in tasks}
    receipt = {'session_id': session, 'request_id': event_receipt['request_id'], 'workers': []}
    with connect(WORKSPACE / 'memory/recovery/tasks.db') as db:
        # Select metadata explicitly. Do not export spec.prompt/system_prompt.
        rows = db.execute('''SELECT task_id,owner_id,session_id,kind,state,attempt_id,attempt_count,
          generation,created_at,updated_at,
          json_extract(spec,'$.source_agent_id') AS source_agent_id,
          json_extract(spec,'$.target_agent_id') AS target_agent_id,
          json_extract(spec,'$.target_session_id') AS target_session_id,
          json_extract(spec,'$.model_ref') AS model_ref,
          json_extract(spec,'$.authority') AS authority,
          json_extract(spec,'$.tools') AS tools,
          json_extract(spec,'$.description') AS worker_description,
          json_extract(spec,'$.system_prompt') = ? AS generic_worker_prompt,
          json_extract(result,'$.summary') AS summary
          FROM recovery_tasks WHERE owner_id='default' AND session_id=? AND kind='delegate'
          ORDER BY created_at,task_id''',
          ('You are a delegated worker. Complete only the assigned task.', session)).fetchall()
        for row in rows:
            item = dict(row)
            summary = item.pop('summary') or ''
            item['summary_sha256'] = hashlib.sha256(summary.encode()).hexdigest()
            for key in ('model_ref', 'authority', 'tools'):
                item[key] = json.loads(item[key])
            match = re.fullmatch(r'\s*(?:```(?:json)?\s*)?(\{.*\})(?:\s*```)?\s*', summary, re.S)
            try:
                result = json.loads(match.group(1)) if match else None
            except ValueError:
                result = None
            item['result_matches_expected'] = result == expected.get(item['target_agent_id'])
            target_result = expected.get(item['target_agent_id'], {})
            item['arithmetic_and_exclusions_match'] = isinstance(result, dict) and {
                k: v for k, v in result.items() if k != 'agent_id'
            } == {k: v for k, v in target_result.items() if k != 'agent_id'}
            item['claimed_identity_matches_target'] = isinstance(result, dict) and result.get('agent_id') == item['target_agent_id']
            # Preserve the observed identity defect instead of correcting it.
            # Only known public roster names/IDs plus exactly matching fictional
            # calculation fields are eligible for publication.
            safe_identity = isinstance(result, dict) and result.get('agent_id') in {
                'CowAgent', 'default', 'TestPilot', 'testpilot', 'TestPilot2', 'testpilot2'}
            item['result'] = result if item['arithmetic_and_exclusions_match'] and safe_identity else None
            item['attempts'] = [dict(r) for r in db.execute(
                'SELECT attempt_id,number,state,started_at,ended_at FROM recovery_attempts WHERE task_id=? ORDER BY number',
                (item['task_id'],))]
            item['effects'] = [dict(r) for r in db.execute('''SELECT e.name,e.mutating,e.call_id,e.recorded_at,e.completed_at
                FROM recovery_effects e JOIN recovery_attempts a ON e.attempt_id=a.attempt_id WHERE a.task_id=?''',
                (item['task_id'],))]
            item['verification_records'] = [dict(r) for r in db.execute('''SELECT verification_id,attempt_id,
                contract_hash,recorded_at,json_extract(report,'$.acceptance.status') AS acceptance,
                json_extract(report,'$.external_state.status') AS external_state
                FROM recovery_verifications WHERE task_id=?''', (item['task_id'],))]
            receipt['workers'].append(item)
    related_sessions = [session] + [w['target_session_id'] for w in receipt['workers']]
    receipt['session_records'], receipt['run_records'], receipt['message_counts'] = {}, {}, {}
    for aid in ('default', 'testpilot', 'testpilot2'):
        # Native conversation storage is global and scoped by agent_id. Each
        # receiver's private index is not a second conversation database.
        db_path = WORKSPACE / 'memory/long-term/index.db'
        with connect(db_path) as db:
            marks = ','.join('?' for _ in related_sessions)
            owner_ids = ('', 'default') if aid == 'default' else (aid,)
            owners = ','.join('?' for _ in owner_ids)
            where = f'session_id IN ({marks}) AND agent_id IN ({owners})'
            parameters = [*related_sessions, *owner_ids]
            # Scope every query to the new session/relay IDs. Message contents
            # and prior sessions are neither selected nor counted here.
            receipt['session_records'][aid] = [dict(r) for r in db.execute(
                f'SELECT agent_id,session_id,created_at,last_active,msg_count FROM sessions WHERE {where}', parameters)]
            receipt['run_records'][aid] = [dict(r) for r in db.execute(
                f'SELECT run_id,agent_id,session_id,parent_run_id,status,started_at,ended_at FROM runs WHERE {where}', parameters)]
            receipt['message_counts'][aid] = [dict(r) for r in db.execute(
                f'SELECT agent_id,session_id,role,count(*) AS count FROM messages WHERE {where} GROUP BY agent_id,session_id,role', parameters)]
    windows = [(w['target_agent_id'], a['started_at'], a['ended_at']) for w in receipt['workers'] for a in w['attempts']]
    receipt['attempt_windows'] = windows
    receipt['overlap'] = bool(len(windows) == 2 and all(w[2] for w in windows)
                              and max(w[1] for w in windows) < min(w[2] for w in windows))
    (HERE / 'native-results.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'workers': [{k: w[k] for k in ('target_agent_id', 'task_id', 'state', 'result_matches_expected')}
                                 for w in receipt['workers']], 'overlap': receipt['overlap'],
                      'message_counts': receipt['message_counts']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true', help='Reconcile retained JSON only; no database access')
    args = parser.parse_args()
    if not args.offline:
        main()
    result = reconcile(json.loads((HERE / 'native-results.json').read_text()),
                       json.loads((HERE / 'live-events.json').read_text()),
                       json.loads((HERE / 'tasks.json').read_text())['tasks'])
    (HERE / 'reconciliation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
