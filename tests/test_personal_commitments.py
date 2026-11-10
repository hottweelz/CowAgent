import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from agent.memory.commitments import CommitmentStore, LEASE_SECONDS
from agent.memory.conversation_store import ConversationStore


def setup(tmp_path, agent='owner'):
    native = ConversationStore(tmp_path / 'index.db', agent_id=agent)
    native.append_messages('session', [{'role': 'user', 'content': 'Please track news.'}])
    return native, CommitmentStore(native)


def fields(**changes):
    return {'objective': 'Track news', 'preferences': ['Bitcoin'], 'priority': 2,
            'endpoint': 'https://tyl.ee/api/news', 'read_authorized': True, **changes}


def test_persistence_owner_isolation_and_existing_memory(tmp_path):
    native, store = setup(tmp_path)
    store.save_goal('session', {'goal': 'Existing goal'}, 0, 0)
    one = store.create('session', fields(), 0)
    two = store.create('session', fields(objective='Another task'), 0)
    store.update('session', one['commitment_id'], {'priority': 5}, 0, 1)
    restarted = CommitmentStore(ConversationStore(tmp_path / 'index.db', agent_id='owner'))
    assert {x['objective'] for x in restarted.snapshot()} == {'Track news', 'Another task'}
    assert restarted.get(one['commitment_id'])['priority'] == 5
    assert restarted._goal_dict(native._connect().execute('SELECT goal,progress,pending_decision,next_step,revision,source_seq,source_time,updated_at FROM personal_goals').fetchone())['goal'] == 'Existing goal'
    _, other = setup(tmp_path, 'other')
    assert other.snapshot() == []
    with pytest.raises(ValueError):
        other.get(two['commitment_id'])
    with pytest.raises(ValueError):
        store.create('missing', fields(), 0)
    with pytest.raises(ValueError):
        store.create('session', fields(), 99)
    with pytest.raises(ValueError):
        store.update('session', one['commitment_id'], {'priority': 2}, 0, 1)


def test_atomic_delivery_provenance_and_duplicate(tmp_path):
    native, store = setup(tmp_path)
    cid = store.create('session', fields(), 0)['commitment_id']
    run = store.claim_run(cid, 'first')
    article = {'id': 'article-1', 'title': 'News'}
    delivered = store.complete_run(run['run_id'], [article], [article], 'News briefing', {'etag': 'x'})
    assert delivered['status'] == 'delivered'
    assert store.claim_run(cid, 'first')['claimed'] is False
    assert store.complete_run(run['run_id'], [], [], 'duplicate', {})['briefing'] == 'News briefing'
    assert store.get_coverage(cid) == [article]
    assert store.get_cache(cid) == {'etag': 'x'}
    assert store.followup('session', cid, 'Watch it', ['article-1'], 0)['text'] == 'Watch it'
    assert store.save_draft('session', cid, 'Draft', ['article-1'], ['Claim'], 0)['status'] == 'awaiting_publication_approval'
    with pytest.raises(ValueError):
        store.followup('session', cid, 'Bad source', ['fake'], 0)
    conn = native._connect()
    assert conn.execute("SELECT COUNT(*) FROM messages WHERE role='assistant'").fetchone()[0] == 1
    assert conn.execute('SELECT msg_count FROM sessions').fetchone()[0] == 2
    conn.close()
    assert json.loads(store.context())['commitments'][0]['followups'][0]['text'] == 'Watch it'


def test_concurrency_expiry_failure_pause_and_rollback(tmp_path):
    native, store = setup(tmp_path)
    cid = store.create('session', fields(), 0)['commitment_id']
    peer = CommitmentStore(ConversationStore(tmp_path / 'index.db', agent_id='owner'))
    with ThreadPoolExecutor(max_workers=2) as pool:
        runs = list(pool.map(lambda pair: pair[0].claim_run(cid, pair[1]), [(store,'a'),(peer,'b')]))
    assert sum(r['claimed'] for r in runs) == 1
    assert len({r['run_id'] for r in runs}) == 1
    rid = runs[0]['run_id']
    store.fail_run(rid, 'remote secret', {'retry_after': 10})
    assert store.claim_run(cid, 'a' if runs[0]['occurrence_key'] == 'a' else 'b')['status'] == 'failed'
    assert store.get(cid)['last_success'] is None
    next_run = store.claim_run(cid, 'next')
    store.update('session',cid,{'status':'paused'},0,1)
    with pytest.raises(ValueError):
        store.complete_run(next_run['run_id'], [], [], 'Must not deliver', {})
    conn = native._connect()
    assert conn.execute("SELECT COUNT(*) FROM messages WHERE role='assistant'").fetchone()[0] == 0
    conn.execute('UPDATE personal_commitment_runs SET started_at=? WHERE run_id=?',(int(time.time())-LEASE_SECONDS-1,next_run['run_id']))
    conn.commit()
    conn.close()
    uncertain = store.claim_run(cid,'new')
    assert uncertain['status'] == 'uncertain' and not uncertain['claimed']
    assert store.complete_run(next_run['run_id'],[],[],'No replay',{})['status'] == 'uncertain'


def test_delivery_rollback_after_message_insert(tmp_path, monkeypatch):
    native, store = setup(tmp_path)
    cid = store.create('session', fields(), 0)['commitment_id']
    run = store.claim_run(cid, 'one')
    monkeypatch.setattr(store, '_save_cache', lambda *args: (_ for _ in ()).throw(ValueError('failure')))
    with pytest.raises(ValueError):
        store.complete_run(run['run_id'], [], [], 'Empty briefing', {})
    conn = native._connect()
    assert conn.execute("SELECT COUNT(*) FROM messages WHERE role='assistant'").fetchone()[0] == 0
    assert conn.execute('SELECT msg_count FROM sessions').fetchone()[0] == 1
    assert store.get(cid)['last_success'] is None
    conn.close()


def test_empty_delivery_and_context_boundary(tmp_path):
    native, store = setup(tmp_path)
    cid = store.create('session', fields(), 0)['commitment_id']
    run = store.claim_run(cid, 'empty')
    native.clear_context('session')
    result = store.complete_run(run['run_id'], [], [], 'No relevant stories.', {})
    assert result['status'] == 'delivered'
    assert result['message_seq'] >= native.get_context_start_seq('session')
    assert store.get_coverage(cid) == []


def test_topic_followup_nested_sources_and_draft_context(tmp_path):
    _, store = setup(tmp_path)
    cid = store.create('session', fields(), 0)['commitment_id']
    topic = store.followup('session', cid, 'Watch regulation', [], 0)
    assert topic['article_ids'] == []
    run = store.claim_run(cid, 'briefing')
    representative = {'article_id':'one', 'headline':'Headline', 'description':'D' * 600,
                      'publisher':'Pub', 'pub_date':'2026-01-01', 'source_url':'https://example.com/one',
                      'sources':[{'publisher':'Other', 'source_id':'other-id', 'source_url':'https://example.com/two'}]}
    related = {'article_id':'two', 'publisher':'Other', 'source_id':'other-id', 'source_url':'https://example.com/two'}
    store.complete_run(run['run_id'], [representative, related], [representative], 'Briefing', {})
    for ref in ('one', 'two', 'other-id', 'https://example.com/two'):
        assert store.save_draft('session', cid, 'Draft', [ref], ['Claim'], 0)['status'] == 'awaiting_publication_approval'
    for refs in ([], ['not-delivered']):
        with pytest.raises(ValueError):
            store.save_draft('session', cid, 'Draft', refs, [], 0)
    summary = json.loads(store.context())['commitments'][0]
    assert summary['latest_run_status'] == 'delivered'
    assert summary['previously_reported_sources'][0]['article_id'] == 'one'
    assert len(summary['previously_reported_sources'][0]['description']) == 500


def test_uncertain_recovery_requires_scoped_owner_source(tmp_path):
    native, store = setup(tmp_path)
    cid = store.create('session', fields(), 0)['commitment_id']
    run = store.claim_run(cid, 'original')
    conn = native._connect()
    conn.execute('UPDATE personal_commitment_runs SET started_at=? WHERE run_id=?',
                 (int(time.time())-LEASE_SECONDS-1, run['run_id']))
    conn.commit()
    conn.close()
    assert store.snapshot()[0]['runs'][0]['status'] == 'uncertain'
    _, other = setup(tmp_path, 'other')
    with pytest.raises(ValueError):
        other.acknowledge_uncertain('session', cid, run['run_id'], 0)
    with pytest.raises(ValueError):
        store.acknowledge_uncertain('session', cid, run['run_id'], 99)
    recovered = store.acknowledge_uncertain('session', cid, run['run_id'], 0)
    assert recovered['status'] == 'failed'
    assert recovered['recovery']['previous_error'] == 'run lease expired'
    assert recovered['recovery']['source_seq'] == 0
    assert store.claim_run(cid, 'original')['claimed'] is False
    assert store.claim_run(cid, 'new')['claimed'] is True


def test_native_count_failure_rolls_back_message_and_run(tmp_path, monkeypatch):
    native, store = setup(tmp_path)
    cid = store.create('session', fields(), 0)['commitment_id']
    run = store.claim_run(cid, 'one')
    monkeypatch.setattr(native, '_adjust_msg_count', lambda *args: (_ for _ in ()).throw(RuntimeError('fault')))
    with pytest.raises(RuntimeError):
        store.complete_run(run['run_id'], [], [], 'Briefing', {})
    peer = CommitmentStore(ConversationStore(tmp_path / 'index.db', agent_id='owner'))
    assert peer.claim_run(cid, 'one')['status'] == 'running'
    assert peer.get(cid)['last_success'] is None
    assert peer.get_cache(cid) == {}
    conn = native._connect()
    assert conn.execute("SELECT COUNT(*) FROM messages WHERE role='assistant'").fetchone()[0] == 0
    assert conn.execute('SELECT msg_count FROM sessions').fetchone()[0] == 1
    conn.close()


def test_empty_check_preserves_previous_sources_after_restart(tmp_path):
    _, store = setup(tmp_path)
    cid = store.create('session', fields(), 0)['commitment_id']
    article = {'article_id': 'institutional', 'headline': 'Institutional story',
               'publisher': 'Publisher', 'source_url': 'https://example.com/news',
               'description': 'Details', 'pub_date': '2026-01-01'}
    first = store.claim_run(cid, 'first')
    store.complete_run(first['run_id'], [article], [article], 'First story briefing', {})
    empty = store.claim_run(cid, 'empty')
    store.complete_run(empty['run_id'], [], [], 'No new stories.', {})
    restarted = CommitmentStore(ConversationStore(tmp_path / 'index.db', agent_id='owner'))
    record = restarted.snapshot()[0]
    assert record['last_briefing'] == 'No new stories.'
    assert record['last_story_briefing'] == 'First story briefing'
    assert record['last_story_report_at'] is not None
    assert record['last_selected'][0]['article_id'] == 'institutional'
    context = json.loads(restarted.context())['commitments'][0]
    assert context['last_report'] == 'No new stories.'
    assert context['last_story_briefing'] == 'First story briefing'
    assert context['previously_reported_sources'][0]['article_id'] == 'institutional'
    assert restarted.save_draft('session', cid, 'Draft', ['institutional'], [], 0)['status'] == 'awaiting_publication_approval'


def test_old_item_sources_survive_later_reports_and_run_limit(tmp_path):
    native, store = setup(tmp_path)
    cid = store.create('session', fields(), 0)['commitment_id']
    old = {'article_id':'old', 'headline':'Old story', 'publisher':'Pub',
           'source_url':'https://example.com/old', 'pub_date':'2026-01-01'}
    first = store.claim_run(cid, 'first')
    store.complete_run(first['run_id'], [old], [old], 'Old briefing', {})
    follow = store.followup('session', cid, 'Follow old story', ['old'], 0)
    draft = store.save_draft('session', cid, 'Draft old story', ['old'], ['A claim'], 0)
    newer = {'article_id':'new', 'headline':'New story', 'publisher':'Pub',
             'source_url':'https://example.com/new'}
    run = store.claim_run(cid, 'new')
    store.complete_run(run['run_id'], [newer], [newer], 'New briefing', {})
    for i in range(25):
        run = store.claim_run(cid, f'empty-{i}')
        store.complete_run(run['run_id'], [], [], 'No new stories', {})
    # Exercise the existing-item fallback as well as stored source snapshots.
    conn = native._connect()
    row = conn.execute('SELECT data FROM personal_commitment_items WHERE item_id=?', (follow['item_id'],)).fetchone()
    data = json.loads(row[0])
    del data['sources']
    conn.execute('UPDATE personal_commitment_items SET data=? WHERE item_id=?', (json.dumps(data), follow['item_id']))
    conn.commit()
    conn.close()
    record = CommitmentStore(ConversationStore(tmp_path / 'index.db', agent_id='owner')).snapshot()[0]
    assert len(record['runs']) == 25
    assert record['last_selected'][0]['article_id'] == 'new'
    assert record['followups'][0]['sources'][0]['source_url'] == 'https://example.com/old'
    assert record['drafts'][0]['item_id'] == draft['item_id']
    assert record['drafts'][0]['sources'][0]['source_url'] == 'https://example.com/old'
    context = json.loads(store.context())['commitments'][0]
    assert context['drafts'][0]['claims'] == ['A claim']
    assert context['drafts'][0]['sources'][0]['source_url'] == 'https://example.com/old'
    assert context['followups'][0]['sources'][0]['source_url'] == 'https://example.com/old'
