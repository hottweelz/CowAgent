"""Execution gateway checks with disposable workspaces and no external services."""
import threading
import pytest
from types import SimpleNamespace


@pytest.fixture(autouse=True)
def private_registry(monkeypatch):
    import agent.permission.authority
    monkeypatch.setattr(agent.permission.authority, "_registry_profiles", lambda: [])

from agent.permission import Authority, authorize, derive_authority, resolve_authority
from agent.protocol.agent_stream import AgentStreamExecutor
from agent.tools.base_tool import BaseTool, ToolResult
from agent.tools.bash.bash import Bash
from agent.tools.current_time.current_time import TimeTool


class AgentFixture:
    def __init__(self, root, mode='workspace-write', authority=None):
        self.root = str(root)
        self.mode = mode
        self.authority = authority

    def effective_cwd(self):
        return self.root

    def effective_permission_mode(self):
        return self.mode


def test_authority_intersects_and_read_only_cannot_write(tmp_path):
    root = str(tmp_path)
    sub = str(tmp_path / 'sub')
    a = Authority('workspace-write', frozenset({'fs.read', 'fs.write'}), (root,), (root,))
    b = Authority('read-only', frozenset({'fs.read', 'fs.write'}), (sub,), (sub,))
    result = derive_authority(a, b)
    assert result.restricted and result.read_roots == (sub,)
    assert result.write_roots == () and result.capabilities == frozenset({'fs.read'})
    assert resolve_authority(AgentFixture(tmp_path, 'read-only', a)).capabilities == frozenset({'fs.read'})


def test_wrapper_denies_subprocess_unknown_and_missing_context(tmp_path, monkeypatch):
    class Unknown(BaseTool):
        name = 'time'
        def execute(self, params):
            raise AssertionError('unknown tool executed')
    agent = AgentFixture(tmp_path)
    bash = Bash()
    bash.context = agent
    monkeypatch.setattr(bash, 'execute', lambda _: (_ for _ in ()).throw(AssertionError('bash executed')))
    assert bash.execute_tool({'command': 'python -c pass'}).status == 'error'
    unknown = Unknown()
    unknown.context = AgentFixture(tmp_path, 'full-access')
    assert unknown.execute_tool({}).status == 'error'
    assert TimeTool().execute_tool({}).status == 'error'


def test_permission_errors_and_stream_override_fail_closed(tmp_path, monkeypatch):
    agent = AgentFixture(tmp_path)
    executor = object.__new__(AgentStreamExecutor)
    executor.agent = agent
    executor.cancel_event = None
    executor.tools = {'time': TimeTool()}
    class Unknown(BaseTool):
        name = 'time'
        def execute(self, params):
            return ToolResult.success('must not run')
    assert executor._permission_denial('time', {}, Unknown())
    monkeypatch.setattr(agent, 'effective_permission_mode', lambda: 1 / 0)
    decision, _ = authorize(TimeTool(), {}, agent)
    assert not decision.allowed and 'evaluation failed' in decision.reason
    assert executor._permission_denial('time', {})


def test_cancelled_tool_does_not_execute(tmp_path, monkeypatch):
    tool = TimeTool()
    tool.context = AgentFixture(tmp_path)
    tool.cancel_event = threading.Event()
    tool.cancel_event.set()
    monkeypatch.setattr(tool, 'execute', lambda _: (_ for _ in ()).throw(AssertionError('executed')))
    assert tool.execute_tool({}).status == 'error'


def test_stream_denial_reports_error_without_arguments(tmp_path):
    executor = object.__new__(AgentStreamExecutor)
    executor.agent = AgentFixture(tmp_path)
    executor.cancel_event = None
    executor.tools = {'bash': Bash()}
    events = []
    executor._emit_event = lambda name, data: events.append((name, data))
    result = executor._execute_tool({'id': 'x', 'name': 'bash',
                                     'arguments': {'command': 'secret-value'}})
    assert result['status'] == 'error'
    assert all('secret-value' not in str(data) for _, data in events)
    assert events[-1][1]['permission_denied']


def test_restricted_file_wrapper_uses_broker(tmp_path):
    from agent.tools.write.write import Write
    from agent.tools.read.read import Read
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    agent = AgentFixture(workspace)
    writer = Write()
    writer.context = agent
    assert writer.execute_tool({'path': 'output.txt', 'content': 'fixture'}).status == 'success'
    assert (workspace / 'output.txt').read_text() == 'fixture'
    outside = tmp_path / 'outside.txt'
    assert writer.execute_tool({'path': str(outside), 'content': 'no'}).status == 'error'
    assert not outside.exists()
    reader = Read()
    reader.context = agent
    assert 'fixture' in reader.execute_tool({'path': 'output.txt'}).result['output']
    agent.mode = 'read-only'
    assert writer.execute_tool({'path': 'output.txt', 'content': 'no'}).status == 'error'
    assert (workspace / 'output.txt').read_text() == 'fixture'



def test_mcp_read_name_cannot_authorize_remote_client(tmp_path):
    from agent.tools.mcp.mcp_tool import McpTool
    from types import SimpleNamespace
    client = SimpleNamespace(call_tool=lambda *a: (_ for _ in ()).throw(AssertionError('remote call')))
    tool = McpTool(client, {'name': 'read', 'inputSchema': {}, 'annotations': {'readOnlyHint': True}}, 'fixture')
    for mode in ('read-only', 'workspace-write', 'full-access'):
        tool.context = AgentFixture(tmp_path, mode)
        result = tool.execute_tool({'path': 'fictional'})
        assert result.status == 'error' and result.ext_data['code'] == 'unknown_tool'


def test_post_process_dispatch_cannot_bypass_authorization(tmp_path):
    from agent.protocol.agent import Agent
    from agent.tools.base_tool import ToolStage
    class UnknownPost(BaseTool):
        name = 'unknown_post'
        stage = ToolStage.POST_PROCESS
        def execute(self, args):
            raise AssertionError('post-process implementation executed')
    agent = Agent('fixture', tools=[UnknownPost()], workspace_dir=str(tmp_path),
                  enable_skills=False, output_mode='logger')
    agent.permission_mode = 'full-access'
    captured = []
    agent.capture_tool_use = lambda **kwargs: captured.append(kwargs)
    agent._execute_post_process_tools()
    assert captured[0]['status'] == 'error'


def test_authorization_diagnostics_exclude_arguments(tmp_path, caplog):
    tool = Bash({'cwd': str(tmp_path)})
    tool.context = AgentFixture(tmp_path)
    assert tool.execute_tool({'command': 'FICTIONAL_PRIVATE_CREDENTIAL'}).status == 'error'
    assert 'tool_authorization' in caplog.text
    assert 'FICTIONAL_PRIVATE_CREDENTIAL' not in caplog.text


def test_scheduled_tool_denied_before_constructor(tmp_path, monkeypatch):
    from agent.tools.scheduler.integration import _execute_tool_call, _task_permission_mode
    monkeypatch.setattr('agent.tools.tool_manager.ToolManager',
                        lambda: (_ for _ in ()).throw(AssertionError('tool constructor')))
    task = {'id': 'fixture', 'action': {'tool_name': 'bash', 'receiver': 'fixture',
                                      'tool_params': {'command': 'fictional'}}}
    assert _execute_tool_call(task, object()) is False
    monkeypatch.setattr('agent.workspace.session_prefs.get_prefs_strict',
                        lambda *a: (_ for _ in ()).throw(ValueError('FICTIONAL_SECRET')))
    task['action']['origin_session_id'] = 'fixture'
    import pytest
    with pytest.raises(ValueError):
        _task_permission_mode(task)


def test_invalid_configuration_and_legacy_unknown_fail_closed(monkeypatch):
    from agent.permission import policy
    from config import conf
    monkeypatch.setattr(conf(), 'get', lambda key: (_ for _ in ()).throw(RuntimeError('secret')))
    assert policy.global_mode() == policy.READ_ONLY
    assert not policy.check_tool_call('full-access', 'unknown').allowed
    assert not policy.check_tool_call('invalid', 'bash').allowed


def test_worker_prompt_does_not_load_shared_context(monkeypatch, tmp_path):
    from agent.protocol.agent import Agent
    import agent.prompt
    monkeypatch.setattr(agent.prompt, 'PromptBuilder', lambda **kwargs: (_ for _ in ()).throw(AssertionError('shared prompt loaded')))
    worker = object.__new__(Agent)
    worker.authority = Authority('read-only', frozenset(), (str(tmp_path),), ())
    worker.system_prompt = 'Explicit task'
    worker.extra_system_suffix = 'Bounded work'
    assert worker.get_full_system_prompt() == 'Explicit task\n\nBounded work'


def test_unknown_capability_rejected(tmp_path):
    with pytest.raises(ValueError):
        Authority('read-only', frozenset({'network'}), (str(tmp_path),), ())


def test_actual_agent_config_error_denies(tmp_path, monkeypatch):
    from agent.protocol.agent import Agent
    from config import conf
    from agent.tools.current_time.current_time import TimeTool
    agent = object.__new__(Agent)
    agent.permission_mode = None
    agent.workspace_dir = str(tmp_path)
    agent.project_dir = None
    monkeypatch.setattr(conf(), 'get', lambda key: (_ for _ in ()).throw(RuntimeError('private')))
    tool = TimeTool()
    tool.context = agent
    result = tool.execute_tool({})
    assert result.status == 'error' and result.ext_data['code'] == 'evaluation_failed'
    agent.permission_mode = 'invalid'
    result = tool.execute_tool({})
    assert result.status == 'error' and result.ext_data['code'] == 'evaluation_failed'


def test_sibling_and_protected_paths_are_excluded(tmp_path, monkeypatch):
    import agent.permission.authority
    from agent.tools.read.read import Read
    root = tmp_path / 'project'
    sibling = root / 'custom-sibling'
    sibling.mkdir(parents=True)
    (sibling / 'private.txt').write_text('private')
    protected = root / 'protected.txt'
    protected.write_text('private')
    profiles = [SimpleNamespace(id='owner', workspace=str(tmp_path / 'owner')),
                SimpleNamespace(id='sibling', workspace=str(sibling))]
    monkeypatch.setattr(agent.permission.authority, '_registry_profiles', lambda: profiles)
    agent = AgentFixture(root)
    agent._current_agent_id = 'owner'
    agent.protected_paths = lambda: [str(protected)]
    reader = Read()
    reader.context = agent
    assert reader.execute_tool({'path': str(protected)}).status == 'error'
    assert reader.execute_tool({'path': str(sibling / 'private.txt')}).status == 'error'
    agent.protected_paths = lambda: (_ for _ in ()).throw(RuntimeError('private'))
    assert reader.execute_tool({'path': 'public.txt'}).ext_data['code'] == 'evaluation_failed'


def test_supplied_multi_root_authority_survives_cwd(tmp_path):
    scratch = tmp_path / 'scratch'
    work = tmp_path / 'work'
    scratch.mkdir()
    work.mkdir()
    supplied = Authority('workspace-write', frozenset({'fs.read', 'fs.write'}),
                         (str(scratch), str(work)), (str(scratch), str(work)))
    agent = AgentFixture(scratch, authority=supplied)
    result = resolve_authority(agent)
    assert set(result.read_roots) == {str(scratch), str(work)}
    agent.mode = 'read-only'
    assert resolve_authority(agent).write_roots == ()
