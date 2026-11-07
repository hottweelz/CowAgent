"""Sent-request freshness and schema-aware budgets; synthetic data only."""
import copy
from unittest.mock import patch

from agent.protocol.agent import Agent
from agent.protocol.agent_stream import AgentStreamExecutor, build_tools_schema
from agent.protocol.accounting import fingerprint, request_snapshot, schema_tokens
from bridge.agent_bridge import AgentLLMModel


class Tool:
    name = 'synthetic'
    description = 'Synthetic tool'
    params = {'type': 'object', 'properties': {'query': {'type': 'string'}}}

    def get_json_schema(self):
        return {'parameters': self.params}


class Model:
    model = 'requested-model'

    def __init__(self):
        self.requests = []

    def call_stream(self, request):
        self.requests.append(copy.deepcopy(request))
        yield {'model': 'returned-model', 'provider': 'synthetic-provider',
               'choices': [{'delta': {'content': 'Synthetic response'}, 'finish_reason': 'stop'}]}
        yield {'choices': [], 'usage': {'prompt_tokens': 9967, 'completion_tokens': 80,
                                       'prompt_tokens_details': {'cached_tokens': 0}}}


def make_agent():
    agent = Agent('cached initialization', model=Model(), enable_skills=False,
                  max_context_tokens=10000, output_mode='logger')
    agent.tools = [Tool()]
    agent.messages = [{'role': 'user', 'content': 'Synthetic question'}]
    return agent


def test_final_request_is_shared_by_diagnostic_chart_and_actual_usage(caplog):
    agent = make_agent()
    executor = AgentStreamExecutor(agent, agent.model, 'Current sent prompt', agent.tools,
                                   messages=agent.messages)
    with caplog.at_level('INFO'):
        executor._call_llm_stream()
    sent = agent.model.requests[0]
    expected = request_snapshot(agent, sent.system, sent.messages, sent.tools, agent.model.model)
    assert agent.request_accounting['request_fingerprint'] == expected['request_fingerprint']
    assert expected['breakdown']['tools'] > 0
    assert f"estimate input~={expected['estimated_input_tokens']}" in caplog.text
    assert 'tools~=' in caplog.text
    assert agent.last_usage['model'] == 'returned-model'
    assert agent.last_usage['provider'] == 'synthetic-provider'
    agent.messages = executor.messages  # Agent.run_stream performs this synchronization.
    chart = agent.get_context_usage()
    assert chart['estimated']  # The generated assistant message is new context.
    assert chart['last_request']['usage']['prompt_tokens'] == 9967
    agent.messages = sent.messages
    chart = agent.get_context_usage()
    assert chart['used'] == 9967
    assert not chart['estimated']
    assert chart['breakdown_estimated']
    assert chart['last_request']['usage']['prompt_tokens'] == 9967
    assert 'Current sent prompt' not in repr(chart)
    assert 'Synthetic question' not in repr(chart)


def test_changed_history_tools_model_or_prompt_invalidates_provider_total():
    for change in ('history', 'tools', 'model', 'prompt'):
        agent = make_agent()
        snapshot = request_snapshot(agent, agent.system_prompt, agent.messages,
                                    build_tools_schema(agent.tools), agent.model.model)
        agent.record_request_accounting(snapshot, build_tools_schema(agent.tools))
        agent.last_usage = {'prompt_tokens': 1234, 'prompt_tokens_reported_calls': 1,
                            'request_fingerprint': snapshot['request_fingerprint']}
        assert not agent.get_context_usage()['estimated']
        if change == 'history':
            # Same estimated length still changes the actual request.
            agent.messages[0]['content'] = 'Different question'
        elif change == 'tools':
            agent.tools[0].description = 'Changed synthetic schema'
        elif change == 'model':
            agent.model.model = 'other-model'
        else:
            agent.system_prompt = 'Changed prompt'
        chart = agent.get_context_usage()
        assert chart['estimated'], change
        assert chart['last_request']['usage']['prompt_tokens'] == 1234


def test_current_chart_uses_selected_schema_instead_of_all_available_tools():
    agent = make_agent()
    selected = []
    snapshot = request_snapshot(agent, agent.system_prompt, agent.messages, selected, agent.model.model)
    agent.record_request_accounting(snapshot, selected)
    assert agent.get_context_usage()['breakdown']['tools'] == 0


def test_external_context_edit_marks_cached_counts_stale_without_prompt_rebuild(tmp_path):
    agent = make_agent()
    agent.workspace_dir = str(tmp_path)
    source = tmp_path / 'AGENT.md'
    source.write_text('Synthetic initial identity')
    agent._remember_system_accounting('Current assembled system')
    snapshot = request_snapshot(agent, 'Current assembled system', agent.messages,
                                build_tools_schema(agent.tools), agent.model.model)
    agent.record_request_accounting(snapshot, build_tools_schema(agent.tools))
    agent.last_usage = {'prompt_tokens': 1234, 'prompt_tokens_reported_calls': 1,
                        'request_fingerprint': snapshot['request_fingerprint']}
    source.write_text('Synthetic edited identity, longer')
    with patch('agent.prompt.PromptBuilder') as builder:
        chart = agent.get_context_usage()
    builder.assert_not_called()
    assert chart['estimated'] and chart['context_state_changed']


def test_schema_space_is_reserved_in_proactive_and_overflow_budgets():
    agent = make_agent()
    agent._get_model_context_window = lambda: 1000
    agent._get_output_reserve_tokens = lambda: 100
    agent.max_context_tokens = 700
    agent.tools[0].description = 'x' * 1000
    executor = AgentStreamExecutor(agent, agent.model, 'system', agent.tools,
                                   messages=agent.messages)
    schema = executor._schema_for_budget()
    fixed = executor._fixed_input_tokens(schema)
    assert fixed == agent._estimate_text_tokens('system') + schema_tokens(agent, schema)
    assert executor._input_limits() == 700
    assert executor._overflow_input_budget('maximum context length is 1000 tokens') == int((700 - fixed) * .9)
    agent.model.catalog_model_meta = lambda: {'max_output_tokens': 500}
    assert executor._input_limits() == 500
    chart = agent.get_context_usage()
    assert chart['window'] == 1000
    assert chart['configured_budget'] == 700
    assert chart['input_limit'] == 500
    assert chart['output_reserve'] == 500


def test_saved_qualified_model_capacity_does_not_change_request_output_cap():
    model = AgentLLMModel.__new__(AgentLLMModel)
    model._fallback_provider = model._fallback_model = None
    model._session_provider = model._session_model = None
    model._agent_model = None
    cfg = {'bot_type': 'custom', 'model': 'vendor/model'}
    catalog = {'deepseek': [{'name': 'vendor/model', 'context_window': 1000000,
                            'max_output_tokens': 131072}]}
    with patch('bridge.agent_bridge.conf', return_value=cfg), \
         patch('models.model_catalog.resolve_model_meta', return_value={}), \
         patch('models.model_catalog.get_catalog_map', return_value=catalog):
        assert model.catalog_context_meta() == {'context_window': 1000000}
        agent = make_agent()
        agent.model = model
        assert agent._get_model_context_window() == 1000000
        assert agent.get_context_usage()['limit'] == 10000
        executor = AgentStreamExecutor(agent, model, '', [])
        assert executor._catalog_max_output_tokens() is None
        catalog['another'] = [{'name': 'vendor/model', 'context_window': 200000}]
        assert model.catalog_context_meta() == {}
        assert agent._get_model_context_window() == 128000
        with patch.object(model, 'catalog_model_meta', side_effect=RuntimeError('unavailable')):
            assert agent.get_context_usage()['window'] == 128000


def test_snapshot_does_not_keep_private_text():
    agent = make_agent()
    snapshot = request_snapshot(agent, 'PrivateSystemText', [{'role': 'user', 'content': 'PrivateUserText'}], [], 'model')
    assert snapshot['fingerprints']['system'] == fingerprint('PrivateSystemText')
    assert 'PrivateSystemText' not in repr(snapshot)
    assert 'PrivateUserText' not in repr(snapshot)


def test_proactive_trim_keeps_less_history_when_schemas_consume_input_space():
    messages = [{'role': role, 'content': f'{index} ' + 'x' * 40}
                for index in range(5) for role in ('user', 'assistant')]
    counts = []
    for has_tools in (False, True):
        agent = make_agent()
        agent._get_model_context_window = lambda: 1000
        agent._get_output_reserve_tokens = lambda: 100
        agent.max_context_tokens = 500
        agent.tools[0].description = 'x' * 1600
        executor = AgentStreamExecutor(agent, agent.model, 'system', agent.tools if has_tools else [],
                                       messages=copy.deepcopy(messages))
        executor._trim_messages()
        counts.append(len(executor.messages))
        assert executor.messages[-1]['content'] == messages[-1]['content']
    assert counts[0] == 10
    assert counts[1] < counts[0]


def test_unreported_request_does_not_inherit_previous_actual_usage_or_cache():
    agent = make_agent()
    executor = AgentStreamExecutor(agent, agent.model, 'system', agent.tools,
                                   messages=agent.messages)
    executor._call_llm_stream()
    def without_usage(request):
        yield {'choices': [{'delta': {'content': 'Unknown usage response'}, 'finish_reason': 'stop'}]}
    agent.model.call_stream = without_usage
    executor._call_llm_stream()
    assert executor.run_usage['calls'] == 2
    assert executor.run_usage['prompt_tokens'] == 9967
    assert executor.run_usage['prompt_tokens_reported_calls'] == 1
    assert executor.run_usage['prompt_cache_hit_tokens_reported_calls'] == 1
    assert 'prompt_tokens_reported_calls' not in agent.last_usage
    assert agent.get_context_usage()['estimated']


def test_runtime_callback_failure_cannot_replace_fresh_prompt_or_block_request():
    agent = make_agent()
    def unavailable():
        raise RuntimeError('Synthetic callback failure')
    agent.runtime_info = {'_get_current_time': unavailable, '_get_teammates': unavailable}
    with patch('agent.prompt.PromptBuilder') as builder:
        builder.return_value.build.return_value = 'Fresh assembled prompt'
        prompt = agent.get_full_system_prompt()
    assert prompt == 'Fresh assembled prompt'
    executor = AgentStreamExecutor(agent, agent.model, prompt, agent.tools, messages=agent.messages)
    executor._call_llm_stream()
    assert agent.model.requests[0].system == prompt


def test_mcp_preview_does_not_retain_pretrim_selection():
    agent = make_agent()
    old_tool, new_tool = Tool(), Tool()
    old_tool.name, new_tool.name = 'old_history_tool', 'current_tool'
    agent.tools = [old_tool, new_tool]
    messages = [{'role': 'user', 'content': 'old'}, {'role': 'assistant', 'content': 'old answer'},
                {'role': 'user', 'content': 'current'}]
    executor = AgentStreamExecutor(agent, agent.model, 'system', agent.tools,
                                   messages=messages, max_context_turns=1)
    def select():
        name = 'old_history_tool' if len(executor.messages) > 1 else 'current_tool'
        executor._retrieved_mcp_names.add(name)
        return [t for t in agent.tools if t.name in executor._retrieved_mcp_names]
    executor._retrieved_mcp_names = set()
    executor._select_tools_for_injection = select
    executor._trim_messages()
    assert executor._retrieved_mcp_names == set()
    executor._call_llm_stream()
    assert [t['name'] for t in agent.model.requests[0].tools] == ['current_tool']


def test_newly_synced_tool_schema_rebudgets_before_first_request():
    agent = make_agent()
    agent.max_context_tokens = 600
    messages = [{'role': role, 'content': f'{index} ' + 'x' * 100}
                for index in range(8) for role in ('user', 'assistant')]
    executor = AgentStreamExecutor(agent, agent.model, 'system', agent.tools, messages=messages)
    executor._trim_messages()
    before = len(executor.messages)
    large = Tool()
    large.name, large.description = 'late_mcp', 'x' * 1500
    def sync(target):
        target.tools[large.name] = large
    with patch('agent.tools.ToolManager') as manager:
        manager.return_value.sync_mcp_into_agent.side_effect = sync
        executor._call_llm_stream()
    sent = agent.model.requests[0]
    assert 'late_mcp' in [t['name'] for t in sent.tools]
    assert len(sent.messages) < before
    assert executor.request_accounting['estimated_input_tokens'] <= 600
