import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from agent.memory.commitments import CommitmentStore
from agent.memory.conversation_store import ConversationStore


def setup_store(tmp_path):
    native = ConversationStore(tmp_path / 'index.db', agent_id='owner')
    native.append_messages('session', [{'role':'user','content':'Track news'}])
    store = CommitmentStore(native)
    record = store.create('session', {'objective':'Track news','endpoint':'https://tyl.ee/api/news',
        'read_authorized':True,'initiative_enabled':True,
        'read_grant':{'expires_at':None,'min_interval_seconds':60}}, 0)
    return native, store, record


def test_atomic_frequency_quiet_and_expiry(tmp_path):
    native, store, record = setup_store(tmp_path)
    cid = record['commitment_id']
    peer = CommitmentStore(ConversationStore(tmp_path / 'index.db', agent_id='owner'))
    with ThreadPoolExecutor(max_workers=2) as pool:
        runs = list(pool.map(lambda x: x[0].claim_run(cid,x[1]), [(store,'a'),(peer,'b')]))
    assert sum(r['claimed'] for r in runs) == 1
    run = next(r for r in runs if r['claimed'])
    done = store.complete_run(run['run_id'], [], [], '', {'etag':'x'}, notify=False, evaluation={'verified':True})
    assert done['status'] == 'completed' and done['evaluation']['verified']
    assert store.get_cache(cid) == {'etag':'x'} and store.get(cid)['last_success']
    assert native._connect().execute("SELECT COUNT(*) FROM messages WHERE role='assistant'").fetchone()[0] == 0
    blocked = store.claim_run(cid,'limit')
    assert blocked['status'] == 'blocked' and blocked['error'] == 'read grant frequency limit'
    assert store.claim_run(cid,'limit')['run_id'] == blocked['run_id']
    updated = store.update('session',cid,{'read_grant':{'expires_at':int(time.time())-1,'min_interval_seconds':0}},0,1)
    assert updated['grant']['grant_id'] == record['grant']['grant_id']
    assert store.claim_run(cid,'expired')['error'] == 'read grant expired'
    with pytest.raises(ValueError, match='expired'):
        store.assert_active(cid,2)
    store.update('session',cid,{'read_authorized':False},0,2)
    with pytest.raises(ValueError):
        store.claim_run(cid,'revoked')


def test_decisions_persist_deduplicate_and_isolate(tmp_path):
    native, store, record = setup_store(tmp_path)
    cid = record['commitment_id']
    store.update('session',cid,{'read_grant':{'expires_at':None,'min_interval_seconds':0}},0,1)
    article = {'id':'story','headline':'A story'}
    proposal = {'action':'track_story','reason':'Relevant','source_ids':['story']}
    run = store.claim_run(cid,'first')
    store.complete_run(run['run_id'],[article],[article],'News',{},proposals=[proposal])
    items = store.attention_snapshot()
    decision = next(x for x in items if x['kind'] == 'decision')
    assert store.decide_attention('session',cid,decision['attention_id'],'deny',0)['status'] == 'denied'
    second = store.claim_run(cid,'second')
    store.complete_run(second['run_id'],[article],[article],'News again',{},proposals=[proposal])
    restarted = CommitmentStore(ConversationStore(tmp_path / 'index.db',agent_id='owner'))
    assert len(restarted.attention_snapshot()) == 2
    assert next(x for x in restarted.attention_snapshot() if x['kind']=='decision')['status'] == 'denied'
    finding = next(x for x in items if x['kind']=='finding')
    restarted.decide_attention('session',cid,finding['attention_id'],'dismiss',0)
    assert len(restarted.attention_snapshot()) == 1
    assert len(restarted.attention_snapshot(True)) == 2
    assert len(restarted.get_coverage(cid)) == 2
    other = CommitmentStore(ConversationStore(tmp_path / 'index.db',agent_id='other'))
    assert other.attention_snapshot() == []
    with pytest.raises(ValueError):
        other.decide_attention('session',cid,decision['attention_id'],'approve',0)
    draft = store.save_draft('session',cid,'Draft',['story'],['Claim'],0)
    pub = store.propose_publication('session',cid,draft['item_id'],0)
    assert store.propose_publication('session',cid,draft['item_id'],0)['attention_id'] == pub['attention_id']
    approved = store.decide_attention('session',cid,pub['attention_id'],'approve',0)
    assert approved['payload']['execution_status'] == 'blocked'
    assert approved['payload']['text'] == 'Draft'


def test_model_failure_keeps_evidence_and_no_coverage(tmp_path):
    _, store, record = setup_store(tmp_path)
    cid = record['commitment_id']
    run = store.claim_run(cid,'first')
    result = store.fail_run(run['run_id'],'model timeout',evaluation={'observed':'articles','verified':False})
    assert result['status'] == 'failed' and result['error'] == 'model timeout'
    assert result['evaluation']['verified'] is False and store.get_coverage(cid) == []
    assert store.attention_snapshot()[0]['kind'] == 'failure'


def test_event_identity_ignores_fetch_and_assessment_metadata(tmp_path):
    _, store, record = setup_store(tmp_path)
    cid = record['commitment_id']
    store.update('session',cid,{'read_grant':{'expires_at':None,'min_interval_seconds':0}},0,1)
    article = {'article_id':'a', 'cluster_id':'event', 'headline':'News', 'content':'Original content',
               'fetched_at':'today', 'matched_preferences':['crypto'], 'sources':[{'source_id':'a'}]}
    first = store.claim_run(cid,'first')
    store.complete_run(first['run_id'],[article],[article],'News',{})
    finding = store.attention_snapshot()[0]
    changed = {**article, 'fetched_at':'tomorrow', 'matched_preferences':['finance'],
               'status':'updated', 'reason':'different assessment', 'sources':list(reversed(article['sources']))}
    second = store.claim_run(cid,'second')
    store.complete_run(second['run_id'],[changed],[changed],'News',{})
    assert [x['attention_id'] for x in store.attention_snapshot()] == [finding['attention_id']]
    updated = {**changed,'content':'Original content and material new facts'}
    third = store.claim_run(cid,'third')
    store.complete_run(third['run_id'],[updated],[updated],'News',{})
    assert len(store.attention_snapshot()) == 2


def test_later_session_decisions_and_hidden_terminal_outcomes(tmp_path):
    native, store, record = setup_store(tmp_path)
    cid = record['commitment_id']
    article = {'id':'story','headline':'Story'}
    run = store.claim_run(cid,'one')
    store.complete_run(run['run_id'],[article],[article],'News',{},proposals=[
        {'action':'track_story','reason':'Useful','source_ids':['story']},
        {'action':'draft_post','reason':'Useful','source_ids':['story']}])
    decisions = [x for x in store.attention_snapshot() if x['kind']=='decision']
    native.append_messages('later', [{'role':'user','content':'Review'}])
    approved = store.decide_attention('later',cid,decisions[0]['attention_id'],'approve',0)
    assert approved['decision_session_id'] == 'later' and approved['source_session_id'] == 'session'
    hidden = store.decide_attention('later',cid,approved['attention_id'],'dismiss',0)
    assert hidden['status'] == 'approved' and hidden['dismissed_at'] is not None
    assert hidden['decision_session_id'] == 'later'
    store.update('session',cid,{'priority':4},0,1)
    with pytest.raises(ValueError,match='stale'):
        store.decide_attention('later',cid,decisions[1]['attention_id'],'approve',0)
    assert store.decide_attention('later',cid,decisions[1]['attention_id'],'deny',0)['status'] == 'denied'
    assert hidden['attention_id'] not in [x['attention_id'] for x in store.attention_snapshot()]
    assert hidden['attention_id'] in [x['attention_id'] for x in store.attention_snapshot(True)]


def test_grant_status_and_failure_episodes(tmp_path):
    _, store, record = setup_store(tmp_path)
    cid = record['commitment_id']
    assert record['grant']['status'] == 'active'
    run = store.claim_run(cid,'one')
    store.fail_run(run['run_id'],'model timeout')
    failure = store.attention_snapshot()[0]
    # Repeated failures in one episode share one attention item.
    store.update('session',cid,{'read_grant':{'expires_at':None,'min_interval_seconds':0}},0,1)
    second = store.claim_run(cid,'two')
    store.fail_run(second['run_id'],'model timeout')
    assert len(store.attention_snapshot()) == 1
    third = store.claim_run(cid,'three')
    store.complete_run(third['run_id'],[],[],'',{},notify=False)
    assert store.attention_snapshot()[0]['status'] == 'resolved'
    fourth = store.claim_run(cid,'four')
    store.fail_run(fourth['run_id'],'model timeout')
    assert len(store.attention_snapshot()) == 2
    store.decide_attention('session',cid,failure['attention_id'],'dismiss',0)
    updated = store.update('session',cid,{'read_grant':{'expires_at':int(time.time())-1,'min_interval_seconds':0}},0,2)
    assert updated['grant']['status'] == 'expired' and not updated['grant']['authorized']
    blocked = store.claim_run(cid,'expired')
    attention = next(x for x in store.attention_snapshot() if x['run_id'] == blocked['run_id'])
    assert store.decide_attention('session',cid,attention['attention_id'],'dismiss',0)['dismissed_at']
    revoked = store.update('session',cid,{'read_authorized':False},0,3)
    assert revoked['grant']['status'] == 'revoked'


def test_finding_compact_source_and_unchanged_body_title_edit(tmp_path):
    _, store, record = setup_store(tmp_path)
    cid = record['commitment_id']
    store.update('session',cid,{'read_grant':{'expires_at':None,'min_interval_seconds':0}},0,1)
    article = {'article_id':'id-1','headline':'Original title','content':'long body ' * 10000,
               'description':'Summary', 'publisher':'Publisher', 'source_url':'https://example.com/story',
               'sources':[{'publisher':'Second publisher','source_url':'https://example.com/second'}]}
    run = store.claim_run(cid,'one')
    store.complete_run(run['run_id'],[article],[article],'Brief',{},evaluation={'interpretation':{'id-1':'Relevant to saved goals'}})
    finding = store.attention_snapshot()[0]
    assert finding['payload']['reason'] == 'Relevant to saved goals'
    assert 'content' not in finding['payload']['sources'][0]
    assert finding['payload']['sources'][1]['publisher'] == 'Second publisher'
    assert len(str(finding['payload'])) < 2000
    revised = {**article,'headline':'Updated title','fetched_at':'later'}
    second = store.claim_run(cid,'two')
    store.complete_run(second['run_id'],[revised],[revised],'Brief',{})
    assert [x['attention_id'] for x in store.attention_snapshot()] == [finding['attention_id']]


def test_proposal_material_version_and_pending_dedup(tmp_path):
    _, store, record = setup_store(tmp_path)
    cid = record['commitment_id']
    store.update('session',cid,{'read_grant':{'expires_at':None,'min_interval_seconds':0}},0,1)
    proposal = {'action':'track_story','reason':'Useful','source_ids':['story']}
    article = {'article_id':'story','headline':'Original','content':'Original body'}
    def deliver(key, row):
        run = store.claim_run(cid,key)
        store.complete_run(run['run_id'],[row],[row],'News',{},proposals=[proposal])
    deliver('first',article)
    first = next(x for x in store.attention_snapshot() if x['kind']=='decision')
    store.decide_attention('session',cid,first['attention_id'],'deny',0)
    deliver('same',{**article,'headline':'New headline','fetched_at':'later'})
    assert len([x for x in store.attention_snapshot() if x['kind']=='decision']) == 1
    updated = {**article,'content':'Original body plus new material'}
    deliver('updated',updated)
    decisions = [x for x in store.attention_snapshot() if x['kind']=='decision']
    assert len(decisions) == 2 and {x['status'] for x in decisions} == {'pending','denied'}
    pending = next(x for x in decisions if x['status']=='pending')
    deliver('another-update',{**updated,'content':'More new material'})
    assert [x['attention_id'] for x in store.attention_snapshot() if x['kind']=='decision' and x['status']=='pending'] == [pending['attention_id']]


def test_resolve_blocked_and_publication_from_later_session(tmp_path):
    import json
    native, store, record = setup_store(tmp_path)
    cid = record['commitment_id']
    run = store.claim_run(cid,'first')
    article = {'article_id':'story','headline':'Story'}
    store.complete_run(run['run_id'],[article],[article],'News',{})
    blocked = store.claim_run(cid,'blocked')
    attention = next(x for x in store.attention_snapshot() if x['run_id']==blocked['run_id'])
    assert attention['status'] == 'blocked'
    current = store.update('session',cid,{'read_grant':{'expires_at':None,'min_interval_seconds':0}},0,1)
    next_run = store.claim_run(cid,'success')
    store.complete_run(next_run['run_id'],[],[],'',{},notify=False)
    assert next(x for x in store.attention_snapshot() if x['attention_id']==attention['attention_id'])['status'] == 'resolved'
    assert json.loads(store.context())['commitments'][0]['read_grant'] == current['read_grant']
    draft = store.save_draft('session',cid,'Draft',['story'],['Claim'],0)
    native.append_messages('later',[{'role':'user','content':'Request approval'}])
    publication = store.propose_publication('later',cid,draft['item_id'],0)
    assert publication['payload']['draft_id'] == draft['item_id']


def test_stale_proposals_replaced_after_revision_and_remain_inspectable(tmp_path):
    _, store, record = setup_store(tmp_path)
    cid = record['commitment_id']
    store.update('session',cid,{'read_grant':{'expires_at':None,'min_interval_seconds':0}},0,1)
    article = {'article_id':'story','headline':'Story','content':'body'}
    proposal = {'action':'track_story','reason':'Useful','source_ids':['story']}
    first_run = store.claim_run(cid,'first')
    store.complete_run(first_run['run_id'],[article],[article],'News',{},proposals=[proposal])
    old = next(x for x in store.attention_snapshot() if x['kind']=='decision')
    draft = store.save_draft('session',cid,'Draft',['story'],['Claim'],0)
    old_pub = store.propose_publication('session',cid,draft['item_id'],0)
    assert not old_pub['stale']
    store.update('session',cid,{'priority':4},0,2)
    second_run = store.claim_run(cid,'second')
    updated = {**article,'content':'body and material update'}
    store.complete_run(second_run['run_id'],[updated],[updated],'News',{},proposals=[proposal])
    decisions = [x for x in store.attention_snapshot() if x['payload'].get('action')=='track_story']
    assert len(decisions) == 2
    old_item = next(x for x in decisions if x['attention_id']==old['attention_id'])
    current = next(x for x in decisions if x['attention_id']!=old['attention_id'])
    assert old_item['stale'] and not current['stale']
    assert store.decide_attention('session',cid,current['attention_id'],'approve',0)['status']=='approved'
    assert store.decide_attention('session',cid,old['attention_id'],'deny',0)['status']=='denied'
    current_pub = store.propose_publication('session',cid,draft['item_id'],0)
    assert current_pub['attention_id'] != old_pub['attention_id'] and not current_pub['stale']
    assert store.propose_publication('session',cid,draft['item_id'],0)['attention_id'] == current_pub['attention_id']
    assert next(x for x in store.attention_snapshot() if x['attention_id']==old_pub['attention_id'])['stale']


def test_context_distinguishes_check_history_and_scoped_conversation_failure(tmp_path):
    import json
    native, store, record = setup_store(tmp_path)
    cid = record['commitment_id']
    store.update('session', cid, {'read_grant': {'expires_at': None, 'min_interval_seconds': 0}}, 0, 1)
    source = {'article_id': 'a', 'headline': 'Source report', 'publisher': 'Publisher',
              'source_url': 'https://publisher.example/story', 'content': 'Original source facts'}
    first = store.claim_run(cid, 'live')
    store.complete_run(first['run_id'], [source], [source], 'Earlier source-backed briefing', {})
    updated = {**source, 'content': 'Fictional controlled addition'}
    second = store.claim_run(cid, 'fixture')
    store.complete_run(second['run_id'], [updated], [updated], 'CONTROLLED ACCEPTANCE FIXTURE', {})
    for rid, owner, session in [('mine', 'owner', 'session'), ('peer', 'peer', 'session'), ('other-session', 'owner', 'elsewhere')]:
        native.create_run(rid, agent_id=owner, session_id=session)
        native.finish_run(rid, status='failed', error='TimeoutError: DO_NOT_INCLUDE_RAW_ERROR')
    context = json.loads(store.context('session'))
    checks = context['commitments'][0]['recent_checks']
    assert [x['run_id'] for x in checks] == [second['run_id'], first['run_id']]
    assert checks[0]['briefing_excerpt'].startswith('CONTROLLED')
    assert checks[1]['briefing_excerpt'] == 'Earlier source-backed briefing'
    failures = context['recent_conversation_failures']
    assert [x['run_id'] for x in failures] == ['mine']
    assert failures[0]['reason'] == 'conversation response timeout'
    assert 'DO_NOT_INCLUDE_RAW_ERROR' not in json.dumps(context)
