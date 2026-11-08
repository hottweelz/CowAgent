"""Native registered-agent entry point for the opt-in routing experiment.

Only this runtime process opens the registered workspace. Its caller receives
public bindings and a fixed, checked fictional report, never native context.
Normal AgentBridge, initializer, prompt builder and model execution are used.
"""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from . import analysis, contract

KIND = 'cowagent-registered/1'
TARGET = 'testpilot'
ROOT = Path(__file__).resolve().parents[2]


def source_fingerprint():
    """Bind executable source, including the native provider and prompt paths."""
    paths = [ROOT / 'config.py']
    for directory in ('agent', 'bridge', 'common', 'models'):
        paths.extend(sorted((ROOT / directory).rglob('*.py')))
    return contract.digest({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in paths})


class CowAgentNative:
    def __init__(self, config_path, enrollment=None):
        self.config_path = Path(config_path).resolve(strict=True)
        if self.config_path.name != 'config.json':
            raise contract.ProtocolError('Native config.json required')
        # This is a dedicated native runtime process, not a caller-selected
        # replacement registry or copied workspace.
        if Path(os.environ.get('COW_DATA_DIR', '')).resolve() != self.config_path.parent:
            raise contract.ProtocolError('Native data directory differs')
        from config import load_config
        load_config()
        self.bridge = None
        self.enrollment = enrollment
        self._preflight()
        current = self.discover()
        if enrollment is not None and current != {k: v for k, v in enrollment.items() if k != 'probe_sha256'}:
            raise contract.ProtocolError('Native enrollment differs')

    def _profile(self):
        from agent.permission.authority import _current_registry
        return _current_registry().get(TARGET)

    def discover(self):
        from bridge.agent_bridge import AgentLLMModel
        from bridge.bridge import Bridge
        from config import conf
        profile = self._profile()
        model = AgentLLMModel(Bridge())
        model.set_agent_default(profile.bot_type, profile.model)
        env_file = Path.home() / '.cow' / '.env'
        return {
            'runtime_kind': KIND, 'agent_id': profile.id,
            'model': model.model, 'provider': model._primary_provider_id(model.model),
            'profile_sha256': contract.digest(profile.to_dict()),
            'config_sha256': contract.digest({
                'file': hashlib.sha256(self.config_path.read_bytes()).hexdigest(),
                'effective': dict(conf()),
                'environment_file': hashlib.sha256(env_file.read_bytes()).hexdigest() if env_file.exists() else None,
            }),
            'source_sha256': source_fingerprint(),
        }

    def _preflight(self):
        """Refuse unrelated active work before normal native startup.

        This checks state metadata inside the runtime; it does not expose any
        scheduler content, private memory, configuration secrets or history.
        Native memory/index maintenance remains runtime-owned.
        """
        from config import conf
        from agent.permission.authority import _current_registry
        registry = _current_registry()
        if conf().get('self_evolution_enabled', True):
            raise contract.ProtocolError('Experiment requires dormant self-evolution')
        if conf().get('mcp_servers'):
            raise contract.ProtocolError('Configured MCP startup requires review')
        # The normal native daily timer fires at 23:50-23:55. Do not host this
        # bounded experiment across that interval. The service also expires.
        local = time.localtime()
        if local.tm_hour == 23 and local.tm_min >= 45:
            raise contract.ProtocolError('Daily maintenance window is too close')
        for profile in registry.list(include_disabled=True):
            root = Path(profile.workspace)
            if (root / 'mcp.json').exists() or profile.id == TARGET and (root / 'BOOTSTRAP.md').exists():
                raise contract.ProtocolError('Unrelated native startup work requires review')
            for name in ('tasks.json', 'tasks.json.bak'):
                schedule = root / 'scheduler' / name
                if schedule.exists():
                    value = json.loads(schedule.read_text())
                    if not isinstance(value, dict) or value.get('tasks') != {}:
                        raise contract.ProtocolError('Existing scheduler work requires review')
        root = Path(registry.get().workspace)
        recovery = root / 'memory' / 'recovery' / 'tasks.db'
        if recovery.exists():
            with sqlite3.connect(recovery.as_uri() + '?mode=ro', uri=True) as db:
                db.execute('PRAGMA query_only=ON')
                # Even completed rows can have pending independent verification.
                if db.execute('SELECT count(*) FROM recovery_tasks').fetchone()[0]:
                    raise contract.ProtocolError('Existing recovery work requires review')
        # Initialization normally synchronizes these entries into ~/.cow/.env.
        # Refuse a change instead of silently replacing native credentials.
        env_file = Path.home() / '.cow' / '.env'
        existing = {}
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing[key.strip()] = value.strip()
        for setting, key in (
            ('open_ai_api_key', 'OPENAI_API_KEY'), ('open_ai_api_base', 'OPENAI_API_BASE'),
            ('gemini_api_key', 'GEMINI_API_KEY'), ('claude_api_key', 'CLAUDE_API_KEY'),
            ('linkai_api_key', 'LINKAI_API_KEY'),
        ):
            if (conf().get(setting) or '').strip() != existing.get(key, ''):
                raise contract.ProtocolError('Native credential synchronization requires review')

    def prepare(self, session_id):
        if not contract.identifier(session_id):
            raise contract.ProtocolError('Invalid native session')
        if self.enrollment is None or self.discover() != {
                k: v for k, v in self.enrollment.items() if k != 'probe_sha256'}:
            raise contract.ProtocolError('Native enrollment differs')
        self._preflight()
        from bridge.bridge import Bridge
        from common.runtime_identity import RuntimeIdentity, use_identity
        with use_identity(RuntimeIdentity(agent_id=TARGET, session_id=session_id)):
            if self.bridge is None:
                self.bridge = Bridge().get_agent_bridge()
            if self.bridge.get_cached_agent(session_id, TARGET) is not None:
                raise contract.ProtocolError('Native session already exists')
            agent = self.bridge.get_agent(session_id=session_id, agent_id=TARGET,
                                          permission_mode='read-only')
            if (agent.agent_profile != self._profile() or agent.messages
                    or agent.effective_permission_mode() != 'read-only'
                    or getattr(agent, 'authority', None) is not None
                    or agent.memory_manager is None or agent.skip_context_files
                    or agent.model.model != self.enrollment['model']
                    or agent.model._primary_provider_id(agent.model.model) != self.enrollment['provider']):
                raise contract.ProtocolError('Native identity, model or session differs')
        return _Prepared(self, agent, session_id)


class _Prepared:
    def __init__(self, native, agent, session_id):
        self.native, self.agent, self.session_id = native, agent, session_id
        self.used = False

    def run(self, spec, cancel_event):
        if self.used:
            raise contract.ProtocolError('Native attempt cannot replay')
        self.used = True
        from common.runtime_identity import RuntimeIdentity, use_identity
        from common.log import logger
        run_id = uuid.uuid4().hex
        tool_events = []
        def on_event(event):
            # Evidence contains event types/names only, never arguments/results.
            if event.get('type') == 'tool_execution_start':
                tool_events.append(True)
        prompt = ('External caller: Codex. This is a delegated fictional read-only analysis. '
                  'You are the registered receiver; use your existing identity. '
                  'Use only the supplied records. Return only the requested JSON.\n\n'
                  + analysis.build_prompt(spec) + '\n\nOutput schema:\n'
                  + contract.canonical(analysis.output_schema(spec)))
        with use_identity(RuntimeIdentity(agent_id=TARGET, session_id=self.session_id, run_id=run_id)):
            self.agent.model.agent_id = TARGET
            self.agent.model.session_id = self.session_id
            self.agent.model.channel_type = 'external'
            logger.info('[NamedRouting] start caller=codex agent=%s session=%s run=%s model=%s permission=read-only',
                        TARGET, self.session_id, run_id, self.agent.model.model)
            response = self.agent.run_stream(prompt, on_event=on_event, cancel_event=cancel_event)
            # Native fallback remains native-owned. A fallback cannot silently
            # satisfy this experiment's exact enrolled model assertion.
            provider = self.agent.model._primary_provider_id(self.agent.model.model)
            if (self.agent.model.model != self.native.enrollment['model']
                    or provider != self.native.enrollment['provider']
                    or getattr(self.agent.model, '_fallback_depth', 0)
                    or getattr(self.agent.model, '_fallback_model', None)
                    or getattr(self.agent.model, '_fallback_provider', None)):
                raise contract.ProtocolError('Native model changed during execution')
            try:
                value = analysis._strict_json(response)
            except (ValueError, TypeError, RecursionError):
                raise contract.ProtocolError('Native analysis did not match the fixed contract') from None
            if not analysis._valid_report_shape(value, spec['task_id']) or value != analysis.expected_report(spec):
                raise contract.ProtocolError('Native analysis did not match the fixed contract')
            logger.info('[NamedRouting] complete caller=codex agent=%s session=%s run=%s tool_events=%s',
                        TARGET, self.session_id, run_id, len(tool_events))
            return {'report': value, 'receipt': {
                'agent_id': TARGET, 'agent_name': self.agent.agent_profile.name,
                'model': self.agent.model.model, 'provider': provider,
                'session_id': self.session_id, 'native_run_id': run_id,
                'permission_mode': self.agent.effective_permission_mode(),
                'source': 'codex', 'prompt_source': 'native', 'memory_owner': 'runtime',
                'tool_event_count': len(tool_events),
            }}

    def close(self):
        # The process owns native background services and exits at the end of
        # the controlled experiment. Do not delete its state or close a memory
        # database while asynchronous maintenance can still use it.
        pass
