import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from agent.memory.conversation_store import ConversationStore
from agent.memory import personal as personal_module
from agent.memory.personal import PersonalStore


def _personal(tmp_path, agent_id="owner", session_id="session"):
    store = ConversationStore(tmp_path / "index.db", agent_id=agent_id)
    store.append_messages(session_id, [
        {"role": "user", "content": "Please remember the Cedar workshop preference."},
        {"role": "assistant", "content": "I will remember it."},
    ])
    return store, PersonalStore(store)


def test_state_persists_and_is_scoped_by_agent_and_session(tmp_path):
    store, personal = _personal(tmp_path)
    goal = personal.save_goal("session", {
        "goal": "Prepare Cedar workshop", "progress": "Outline started",
        "pending_decision": "Venue capacity", "next_step": "Draft checklist",
    }, source_seq=0, revision=0)
    memory = personal.remember("session", "Plans should be brief.", source_seq=0)
    conn = store._connect()
    try:
        source_time = conn.execute(
            "SELECT created_at FROM messages WHERE agent_id='owner' AND session_id='session' AND seq=0"
        ).fetchone()[0]
    finally:
        conn.close()
    assert goal["source_time"] == memory["source_time"] == source_time

    restarted = PersonalStore(ConversationStore(tmp_path / "index.db", agent_id="owner"))
    other_session_store = ConversationStore(tmp_path / "index.db", agent_id="owner")
    other_session_store.append_messages("other", [{"role": "user", "content": "Another session."}])
    other_session = PersonalStore(other_session_store)
    other_agent_store = ConversationStore(tmp_path / "index.db", agent_id="other")
    other_agent_store.append_messages("session", [{"role": "user", "content": "Different agent."}])
    other_agent = PersonalStore(other_agent_store)

    snap = restarted.snapshot("session")
    assert snap["continuity"]["revision"] == goal["revision"] == 1
    assert snap["memories"][0]["memory_id"] == memory["memory_id"]
    assert snap["memories"][0]["source_session_id"] == "session"
    assert snap["latest_source_seq"] == 0
    assert other_session.snapshot("other")["continuity"]["revision"] == 0
    assert other_session.snapshot("other")["memories"][0]["text"] == "Plans should be brief."
    assert other_agent.snapshot("session")["memories"] == []
    other_session.save_goal("other", {"goal": "Call the venue"}, source_seq=0, revision=0)
    recent = restarted.snapshot("session")["recent_goals"]
    assert {item["session_id"] for item in recent} == {"session", "other"}
    assert {item["goal"] for item in recent} == {"Prepare Cedar workshop", "Call the venue"}
    assert {item["session_id"] for item in json.loads(restarted.context("session"))["recent_goals"]} == {
        "session", "other"
    }


def test_memory_correction_replaces_active_text_and_forget_clears_it(tmp_path):
    store, personal = _personal(tmp_path)
    first = personal.remember("session", "The workshop is on Thursday.", 0)
    corrected = personal.correct_memory(
        "session", first["memory_id"], "The workshop is on Friday.", source_seq=0, revision=1,
    )
    assert corrected["revision"] == 2
    assert corrected["created_at"] == first["created_at"]
    assert corrected["updated_at"] >= corrected["created_at"]
    assert [item["text"] for item in personal.snapshot("session")["memories"]] == [
        "The workshop is on Friday."
    ]
    with pytest.raises(ValueError, match="stale"):
        personal.correct_memory("session", first["memory_id"], "stale", 0, revision=1)
    personal.forget_memory("session", first["memory_id"], revision=2)
    assert personal.snapshot("session")["memories"] == []
    conn = store._connect()
    try:
        text, forgotten = conn.execute(
            "SELECT text,forgotten FROM personal_memories WHERE memory_id=?", (first["memory_id"],)
        ).fetchone()
    finally:
        conn.close()
    assert text == "" and forgotten == 1
    assert "Thursday" not in personal.context("session")
    assert "Friday" not in personal.context("session")


def test_source_must_be_visible_owner_message_and_goal_revision_must_match(tmp_path):
    store, personal = _personal(tmp_path)
    store.append_messages("session", [{
        "role": "user", "content": "Message authored by a teammate.", "extras": {"agent_id": "peer"},
    }])
    with pytest.raises(ValueError, match="visible user"):
        personal.remember("session", "No assistant source", source_seq=1)
    with pytest.raises(ValueError, match="session does not exist"):
        personal.remember("missing", "No session", source_seq=0)
    with pytest.raises(ValueError, match="visible owner"):
        personal.remember("session", "Do not attribute peer input to owner.", source_seq=2)
    with pytest.raises(ValueError, match="stale"):
        personal.save_goal("session", {"goal": "x"}, source_seq=0, revision=1)

    store.clear_context("session")
    with pytest.raises(ValueError, match="visible user"):
        personal.save_goal("session", {"goal": "hidden source"}, source_seq=0, revision=0)
    assert personal.snapshot("session")["latest_source_seq"] is None


def test_action_requires_explicit_approval_is_immutable_and_finishes_once(tmp_path):
    _, personal = _personal(tmp_path)
    action = personal.propose_action("session", "notes/cedar.txt", "draft checklist\n", 0,
                                    int(time.time()) + 300, str(tmp_path))
    with pytest.raises(ValueError, match="not approved"):
        personal.claim_action("session", action["action_id"])
    approved = personal.decide_action("session", action["action_id"], "approve")
    assert approved["status"] == "approved"
    claimed = personal.claim_action("session", action["action_id"])
    assert claimed["status"] == "executing"
    assert claimed["content"] == "draft checklist\n"
    assert claimed["content_sha256"] == action["content_sha256"]
    assert claimed["workspace_root"] == str(tmp_path.resolve())
    assert claimed["source_time"] == action["source_time"]
    result = personal.finish_action("session", action["action_id"], "completed", {"readback": "draft checklist\n"})
    assert result["status"] == "completed"
    assert result["result"] == {"readback": "draft checklist\n"}
    with pytest.raises(ValueError, match="not approved"):
        PersonalStore(ConversationStore(_db_path(tmp_path), agent_id="owner")).claim_action(
            "session", action["action_id"]
        )


def _db_path(tmp_path):
    return tmp_path / "index.db"


def test_denied_and_expired_actions_cannot_be_claimed_and_expiry_persists(tmp_path):
    store, personal = _personal(tmp_path)
    denied = personal.propose_action("session", "a.txt", "A", 0, int(time.time()) + 300, str(tmp_path))
    personal.decide_action("session", denied["action_id"], "deny")
    with pytest.raises(ValueError, match="not approved"):
        personal.claim_action("session", denied["action_id"])

    expired = personal.propose_action("session", "b.txt", "B", 0, int(time.time()) + 300, str(tmp_path))
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE personal_actions SET expires_at=? WHERE action_id=?",
            (int(time.time()) - 1, expired["action_id"]),
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(ValueError, match="expired"):
        personal.decide_action("session", expired["action_id"], "approve")
    statuses = {item["action_id"]: item["status"] for item in personal.snapshot("session")["actions"]}
    assert statuses[expired["action_id"]] == "expired"


def test_only_one_concurrent_claim_succeeds(tmp_path):
    store, personal = _personal(tmp_path)
    action = personal.propose_action("session", "once.txt", "once", 0, int(time.time()) + 300, str(tmp_path))
    personal.decide_action("session", action["action_id"], "approve")
    second = PersonalStore(ConversationStore(tmp_path / "index.db", agent_id="owner"))

    def claim(client):
        try:
            return client.claim_action("session", action["action_id"])["status"]
        except ValueError:
            return "lost"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, (personal, second)))
    assert results.count("executing") == 1
    assert results.count("lost") == 1
    assert personal.snapshot("session")["actions"][0]["status"] == "executing"


def test_claim_uses_full_sync_and_commits_intent_before_return(tmp_path):
    store, personal = _personal(tmp_path)
    action = personal.propose_action("session", "once.txt", "once", 0, int(time.time()) + 300, str(tmp_path))
    personal.decide_action("session", action["action_id"], "approve")

    native_conn = store._connect()
    try:
        assert native_conn.execute("PRAGMA synchronous").fetchone()[0] == 1
    finally:
        native_conn.close()

    seen_sync = []
    original_connect = personal._connect

    def capture_sync(durable=False):
        conn = original_connect(durable=durable)
        seen_sync.append((durable, conn.execute("PRAGMA synchronous").fetchone()[0]))
        return conn

    personal._connect = capture_sync
    claim = personal.claim_action("session", action["action_id"])
    assert claim["status"] == "executing"
    assert seen_sync == [(True, 2)]

    # The caller can start its effect only after claim_action returns. A fresh
    # connection must observe the committed one-way intent at that point.
    observer = ConversationStore(tmp_path / "index.db", agent_id="owner")._connect()
    try:
        status = observer.execute(
            "SELECT status FROM personal_actions WHERE action_id=?", (action["action_id"],)
        ).fetchone()[0]
    finally:
        observer.close()
    assert status == "executing"


def test_claim_rejects_action_whose_source_is_no_longer_visible(tmp_path):
    store, personal = _personal(tmp_path)
    action = personal.propose_action("session", "once.txt", "once", 0, int(time.time()) + 300, str(tmp_path))
    personal.decide_action("session", action["action_id"], "approve")
    store.clear_context("session")
    with pytest.raises(ValueError, match="visible user"):
        personal.claim_action("session", action["action_id"])
    assert personal.snapshot("session")["actions"][0]["status"] == "approved"


def test_expired_approved_action_transitions_during_claim(tmp_path):
    store, personal = _personal(tmp_path)
    action = personal.propose_action("session", "once.txt", "once", 0, int(time.time()) + 300, str(tmp_path))
    personal.decide_action("session", action["action_id"], "approve")
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE personal_actions SET expires_at=? WHERE action_id=?",
            (int(time.time()) - 1, action["action_id"]),
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(ValueError, match="expired"):
        personal.claim_action("session", action["action_id"])
    status = {item["action_id"]: item["status"] for item in personal.snapshot("session")["actions"]}
    assert status[action["action_id"]] == "expired"


@pytest.mark.parametrize("operation", ("decide", "claim"))
def test_action_expiry_uses_time_after_database_writer_lock(tmp_path, monkeypatch, operation):
    store, personal = _personal(tmp_path)
    action = personal.propose_action("session", "once.txt", "once", 0, int(time.time()) + 300, str(tmp_path))
    if operation == "claim":
        personal.decide_action("session", action["action_id"], "approve")

    other_store = ConversationStore(tmp_path / "index.db", agent_id="owner")
    other_personal = PersonalStore(other_store)
    begin_seen = threading.Event()
    original_connect = other_store._connect

    def traced_connect():
        conn = original_connect()
        conn.set_trace_callback(
            lambda statement: begin_seen.set()
            if statement.strip().upper().startswith("BEGIN IMMEDIATE") else None
        )
        return conn

    other_store._connect = traced_connect
    clock = [int(time.time())]
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE personal_actions SET expires_at=? WHERE action_id=?",
            (clock[0] + 1, action["action_id"]),
        )
        conn.commit()
    finally:
        conn.close()
    blocker = store._raw_connect()
    blocker.execute("BEGIN IMMEDIATE")
    monkeypatch.setattr(personal_module.time, "time", lambda: clock[0])

    outcome = []
    done = threading.Event()

    def invoke_operation():
        try:
            if operation == "decide":
                outcome.append(other_personal.decide_action("session", action["action_id"], "approve"))
            else:
                outcome.append(other_personal.claim_action("session", action["action_id"]))
        except Exception as exc:
            outcome.append(exc)
        finally:
            done.set()

    worker = threading.Thread(target=invoke_operation)
    worker.start()
    try:
        reached_writer = begin_seen.wait(3)
        clock[0] += 2
    finally:
        blocker.rollback()
        blocker.close()
    finished = done.wait(3)
    worker.join(timeout=3)
    assert reached_writer, "action did not reach its SQLite writer transaction"
    assert finished, "action did not finish after the writer lock was released"
    assert len(outcome) == 1 and isinstance(outcome[0], ValueError)
    assert "expired" in str(outcome[0])
    statuses = {item["action_id"]: item["status"] for item in personal.snapshot("session")["actions"]}
    assert statuses[action["action_id"]] == "expired"


def test_context_is_json_for_new_session_and_excludes_action_content(tmp_path):
    _, personal = _personal(tmp_path)
    personal.remember("session", "Accepted preference.", 0)
    context = personal.context("new-session")
    data = json.loads(context)
    assert data["memories"][0]["text"] == "Accepted preference."
    assert data["continuity"]["revision"] == 0
    assert "not authority" in data["notice"]
    action = personal.propose_action("session", "secret.txt", "private draft content", 0,
                                    int(time.time()) + 300, str(tmp_path))
    assert "private draft content" not in personal.context("session")
    assert action["content"] == "private draft content"
