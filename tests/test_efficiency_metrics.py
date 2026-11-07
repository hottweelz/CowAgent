import hashlib
import json
from types import SimpleNamespace

import pytest
import tiktoken

from agent.prompt import builder as prompt_builder_module
from agent.prompt.builder import PromptBuilder
from agent.prompt.workspace import ContextFile
from agent.protocol.agent import Agent
from scripts.efficiency_metrics import (
    capture_sections,
    context_file_metrics,
    prefix_metrics,
    text_metrics,
    model_template_metrics,
    model_template_prefix_metrics,
)


def test_text_metrics_match_utf8_hash_and_cowagent_heuristic():
    text = "Synthetic prompt 你好"
    result = text_metrics(text)

    assert result["chars"] == len(text)
    assert result["utf8_bytes"] == len(text.encode("utf-8"))
    assert result["sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert result["cowagent_estimated_tokens"] == Agent._estimate_text_tokens(text)
    assert result["tiktoken_cl100k_base_proxy_tokens"] == len(
        tiktoken.get_encoding("cl100k_base").encode(text)
    )
    assert "provider" not in result
    assert text not in repr(result)


def test_prefix_metrics_measure_byte_and_local_token_prefix_without_text():
    left = "Synthetic prefix 你好 left"
    right = "Synthetic prefix 你们 right"
    expected_prefix = "Synthetic prefix 你".encode("utf-8")
    result = prefix_metrics(left, right)

    assert result["utf8_common_prefix_bytes"] == len(expected_prefix)
    assert result["utf8_common_prefix_sha256"] == hashlib.sha256(expected_prefix).hexdigest()
    assert isinstance(
        result["tiktoken_cl100k_base_proxy_common_prefix_tokens"], int
    )
    assert left not in repr(result)
    assert right not in repr(result)


def test_context_file_metrics_return_body_sizes_and_basename_only():
    content = "Synthetic context body"
    result = context_file_metrics([
        SimpleNamespace(path="/private/synthetic/AGENT.md", content=content)
    ])

    assert result[0]["label"] == "AGENT.md"
    assert result[0]["chars"] == len(content)
    assert "/private" not in repr(result)
    assert content not in repr(result)


def test_capture_sections_rejoins_exact_builder_output_without_raw_summary():
    class Tool:
        name = "read"
        description = "Synthetic file reader"
        params = {"type": "object", "properties": {}}

    class Skills:
        def build_skills_prompt(self, skill_filter=None):
            return "<available_skills>synthetic skill</available_skills>"

    class Memory:
        pass

    context = [ContextFile(path="AGENT.md", content="Synthetic identity body")]
    runtime = {
        "workspace": "/snapshot/workspace",
        "_get_model": lambda: "synthetic-model",
        "_get_current_time": lambda: {
            "date": "2026-01-02",
            "weekday": "Friday",
            "timezone": "UTC",
        },
        "_get_teammates": lambda: [],
    }
    with capture_sections(prompt_builder_module) as sections:
        prompt = PromptBuilder("/snapshot/workspace", language="en").build(
            tools=[Tool(), SimpleNamespace(name="memory_search")],
            context_files=context,
            skill_manager=Skills(),
            memory_manager=Memory(),
            runtime_info=runtime,
            permission_mode="read-only",
        )

    rejoined = "\n".join(
        part for section in sections for part in section["parts"]
    )
    assert rejoined == prompt
    assert sections
    assert "permissions" in [section["name"] for section in sections]
    assert all(set(section) == {"name", "parts"} for section in sections)
    assert all(isinstance(part, str) for section in sections for part in section["parts"])

    summaries = [
        {"name": section["name"], **text_metrics("\n".join(section["parts"]))}
        for section in sections
    ]
    assert "Synthetic identity body" not in repr(summaries)
    assert "/snapshot/workspace" not in repr(summaries)


def test_public_template_metrics_count_full_prompt_without_exposing_content(tmp_path):
    tokenizers = pytest.importorskip('tokenizers')
    pytest.importorskip('jinja2')
    tokenizer = tokenizers.Tokenizer(tokenizers.models.WordLevel({'[UNK]': 0}, unk_token='[UNK]'))
    tokenizer.pre_tokenizer = tokenizers.pre_tokenizers.Whitespace()
    tokenizer_path = tmp_path / 'tokenizer.json'
    tokenizer.save(str(tokenizer_path))
    template = tmp_path / 'template.jinja'
    template.write_text(
        "{{ messages[0].content }}\n<tools>"
        "{% for tool in tools %}{{ '\\n<function>\\n' }}{{ tool.function.name }}\n</function>{% endfor %}"
        "\n</tools>"
    )
    body = {
        'messages': [{'role': 'user', 'content': 'PrivateSyntheticContent 你好'}],
        'tools': [{'type': 'function', 'function': {'name': 'synthetic_tool'}}],
    }
    result = model_template_metrics(body, tokenizer_path, template)
    assert result['estimated_tokens'] > result['tool_blocks_estimated_tokens'] > 0
    assert result['estimated_tokens'] == result['tool_blocks_estimated_tokens'] + result['tokens_outside_tool_blocks']
    assert result['tool_blocks'][0]['name'] == 'synthetic_tool'
    assert not result['exact_provider_template_verified']
    assert 'PrivateSyntheticContent' not in json.dumps(result)


def test_template_prefix_counts_the_rendered_token_prefix(tmp_path):
    tokenizers = pytest.importorskip('tokenizers')
    pytest.importorskip('jinja2')
    tokenizer = tokenizers.Tokenizer(tokenizers.models.WordLevel(
        {'[UNK]': 0, 'stable': 1, 'before': 2, 'after': 3}, unk_token='[UNK]'))
    tokenizer.pre_tokenizer = tokenizers.pre_tokenizers.Whitespace()
    path = tmp_path / 'tokenizer.json'
    tokenizer.save(str(path))
    template = tmp_path / 'template.jinja'
    template.write_text('{{ messages[0].content }}')
    left = {'messages': [{'role': 'system', 'content': 'stable before'}]}
    right = {'messages': [{'role': 'system', 'content': 'stable after'}]}
    result = model_template_prefix_metrics(left, right, path, template)
    assert result['estimated_common_prefix_tokens'] == 1
    assert result['left_estimated_tokens'] == result['right_estimated_tokens'] == 2
    assert 'stable' not in json.dumps(result)
