"""Safe, local metrics for prompt and request accounting.

The functions in this module return counts and hashes only. They do not log or
return the text that they measure. ``tiktoken`` counts are a local
``cl100k_base`` proxy, not a provider tokenizer or a billable token count.
"""

from __future__ import annotations

import hashlib
import copy
import json
import re
from contextlib import ExitStack
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterable, Optional
from unittest.mock import patch


@lru_cache(maxsize=1)
def _tiktoken_encoding():
    """Return the local cl100k encoding, or None when tiktoken is unavailable."""
    try:
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")
    except (ImportError, LookupError):
        return None


def _cowagent_token_estimate(text: str) -> int:
    """Replicate Agent._estimate_text_tokens without importing Agent."""
    if not text:
        return 0
    non_ascii = sum(1 for char in text if ord(char) > 127)
    ascii_count = len(text) - non_ascii
    return int(non_ascii * 1.5 + ascii_count * 0.25) + 1


def text_metrics(text: str) -> dict[str, Any]:
    """Return safe size, digest, and token-proxy metrics for ``text``."""
    if not isinstance(text, str):
        raise TypeError("text must be str")
    encoded = text.encode("utf-8")
    encoding = _tiktoken_encoding()
    return {
        "chars": len(text),
        "utf8_bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "cowagent_estimated_tokens": _cowagent_token_estimate(text),
        "tiktoken_cl100k_base_proxy_tokens": (
            len(encoding.encode(text)) if encoding is not None else None
        ),
    }


def _common_prefix_length(left: bytes, right: bytes) -> int:
    limit = min(len(left), len(right))
    index = 0
    while index < limit and left[index] == right[index]:
        index += 1
    return index


def prefix_metrics(left: str, right: str) -> dict[str, Any]:
    """Compare two strings without returning either text or their prefix.

    UTF-8 byte-prefix length is exact. The token-prefix metric compares local
    ``cl100k_base`` token IDs and is only a tokenizer proxy. Prefix hashes are
    included for stable, content-free comparison across snapshots.
    """
    if not isinstance(left, str) or not isinstance(right, str):
        raise TypeError("left and right must be str")
    left_bytes, right_bytes = left.encode("utf-8"), right.encode("utf-8")
    prefix_bytes = _common_prefix_length(left_bytes, right_bytes)
    byte_prefix = left_bytes[:prefix_bytes]
    encoding = _tiktoken_encoding()
    token_prefix_count: Optional[int] = None
    token_prefix_sha256: Optional[str] = None
    if encoding is not None:
        left_tokens, right_tokens = encoding.encode(left), encoding.encode(right)
        token_prefix_count = 0
        for left_token, right_token in zip(left_tokens, right_tokens):
            if left_token != right_token:
                break
            token_prefix_count += 1
        token_bytes = ",".join(map(str, left_tokens[:token_prefix_count])).encode("ascii")
        token_prefix_sha256 = hashlib.sha256(token_bytes).hexdigest()
    return {
        "utf8_common_prefix_bytes": prefix_bytes,
        "utf8_common_prefix_sha256": hashlib.sha256(byte_prefix).hexdigest(),
        "tiktoken_cl100k_base_proxy_common_prefix_tokens": token_prefix_count,
        "tiktoken_cl100k_base_proxy_common_prefix_sha256": token_prefix_sha256,
    }


def context_file_metrics(context_files: Iterable[Any]) -> list[dict[str, Any]]:
    """Measure context-file bodies, returning only a safe basename label."""
    results = []
    for item in context_files:
        path = str(getattr(item, "path", "context"))
        content = getattr(item, "content", "")
        results.append({
            "label": path.replace("\\", "/").rsplit("/", 1)[-1],
            **text_metrics(content),
        })
    return results


def _render_model_template(body: dict, template_path) -> str:
    """Render in memory only; callers must never persist the returned prompt."""
    from jinja2.sandbox import ImmutableSandboxedEnvironment

    messages = copy.deepcopy(body['messages'])
    for message in messages:
        for call in message.get('tool_calls', []):
            args = call.get('function', {}).get('arguments')
            if isinstance(args, str):
                call['function']['arguments'] = json.loads(args)
    template_text = template_path.read_text()
    environment = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
    environment.filters['tojson'] = lambda value, **kwargs: json.dumps(value, ensure_ascii=False, **kwargs)
    return environment.from_string(template_text).render(
        messages=messages, tools=body.get('tools', []), add_generation_prompt=True,
    )


def model_template_metrics(body: dict, tokenizer_json, template_path) -> dict:
    """Count a public model-family template locally, without executing model code.

    This is an offline estimate. A provider can use another template/revision.
    Tool blocks are attributed by each token's starting character offset in the
    complete rendered prompt, so their counts share the same tokenization.
    """
    from tokenizers import Tokenizer

    rendered = _render_model_template(body, template_path)
    tokenizer = Tokenizer.from_file(str(tokenizer_json))
    encoded = tokenizer.encode(rendered, add_special_tokens=False)
    tool_region = rendered.split('</tools>', 1)[0]
    spans = list(re.finditer(r'\n<function>\n.*?\n</function>', tool_region, re.S))
    tools = body.get('tools', [])
    if len(spans) != len(tools):
        raise ValueError('Template tool-block mapping is incomplete')
    tool_rows = []
    for tool, span in zip(tools, spans):
        tool_rows.append({
            'name': tool['function']['name'],
            'estimated_template_tokens': sum(span.start() <= start < span.end() for start, _ in encoded.offsets),
        })
    return {
        'estimated_tokens': len(encoded.ids),
        'rendered_sha256': hashlib.sha256(rendered.encode()).hexdigest(),
        'template_sha256': hashlib.sha256(template_path.read_bytes()).hexdigest(),
        'tool_blocks': tool_rows,
        'tool_blocks_estimated_tokens': sum(row['estimated_template_tokens'] for row in tool_rows),
        'tokens_outside_tool_blocks': len(encoded.ids) - sum(row['estimated_template_tokens'] for row in tool_rows),
        'exact_provider_template_verified': False,
    }


def model_template_prefix_metrics(left: dict, right: dict, tokenizer_json, template_path) -> dict:
    """Count common tokens in complete rendered requests, returning no text."""
    from tokenizers import Tokenizer

    tokenizer = Tokenizer.from_file(str(tokenizer_json))
    a = tokenizer.encode(_render_model_template(left, template_path), add_special_tokens=False).ids
    b = tokenizer.encode(_render_model_template(right, template_path), add_special_tokens=False).ids
    common = 0
    for x, y in zip(a, b):
        if x != y:
            break
        common += 1
    return {
        'estimated_common_prefix_tokens': common,
        'left_estimated_tokens': len(a),
        'right_estimated_tokens': len(b),
        'common_prefix_sha256': hashlib.sha256(','.join(map(str, a[:common])).encode()).hexdigest(),
        'exact_provider_template_verified': False,
    }


def _flatten_fragments(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [fragment for item in value for fragment in _flatten_fragments(item)]
    return []


class PromptSectionCapture:
    """Temporarily wrap prompt section builders and retain their raw fragments.

    Raw prompt fragments remain only in this in-memory capture object. Callers
    should pass measured or normalized text to ``text_metrics`` and must not
    serialize, print, or log ``sections``. Permission text is captured through
    its separate ``agent.permission.describe_mode`` helper at its actual place
    in the builder sequence.
    """

    def __init__(self, module=None):
        if module is None:
            from agent.prompt import builder as module
        self.module = module
        self.sections: list[dict[str, Any]] = []
        self._stack: Optional[ExitStack] = None
        self._depth = 0

    def __enter__(self) -> "PromptSectionCapture":
        self._stack = ExitStack()
        for name, original in vars(self.module).items():
            if not (name.startswith("_build_") and name.endswith("_section") and callable(original)):
                continue

            def wrapped(*args, __name=name, __original=original, **kwargs):
                outermost = self._depth == 0
                self._depth += 1
                try:
                    result = __original(*args, **kwargs)
                finally:
                    self._depth -= 1
                if outermost:
                    self.sections.append({
                        "name": __name.removeprefix("_build_").removesuffix("_section"),
                        "parts": _flatten_fragments(result),
                    })
                return result

            self._stack.enter_context(patch.object(self.module, name, wrapped))

        # Permission text is inserted directly by build_agent_system_prompt,
        # not by a _build_*_section function. Patch its source helper too so
        # the section list preserves the real order and exact newline join.
        from agent import permission

        describe_mode = permission.describe_mode

        def wrapped_permissions(*args, **kwargs):
            outermost = self._depth == 0
            self._depth += 1
            try:
                result = describe_mode(*args, **kwargs)
            finally:
                self._depth -= 1
            if outermost:
                self.sections.append({
                    "name": "permissions",
                    "parts": _flatten_fragments(result),
                })
            return result

        self._stack.enter_context(
            patch.object(permission, "describe_mode", wrapped_permissions)
        )
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        if self._stack is not None:
            self._stack.close()
            self._stack = None
        return False

    def rejoined_text(self) -> str:
        """Rejoin captured section fragments using the builder's newline rule."""
        return "\n".join(
            fragment for section in self.sections for fragment in section["parts"]
        )

    def section_metrics(self) -> list[dict[str, Any]]:
        """Return labels and text metrics only; omit captured fragment text."""
        return [
            {"label": section["name"], **text_metrics("\n".join(section["parts"]))}
            for section in self.sections
        ]


@contextmanager
def capture_sections(module=None):
    """Yield ``[{name, parts}, ...]`` while capturing builder sections.

    The list contains raw prompt text in memory for the duration of the
    caller's scope. Do not log or serialize it. Permission text is included
    when a non-full-access ``permission_mode`` is active.
    """
    capture = PromptSectionCapture(module)
    with capture:
        yield capture.sections
