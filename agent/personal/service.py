"""Owner-only continuity service and single-use native file actions."""
import hashlib
import os

from agent.memory.conversation_store import get_conversation_store
from agent.memory.personal import PersonalStore
from agent.permission.authority import Authority, resolve_authority
from agent.permission.filesystem import FileBroker, FileDenied
from agent.permission.policy import WORKSPACE_WRITE, authorize, invoke
from agent.registry import get_agent_registry
from agent.tools.read.read import Read
from agent.tools.write.write import Write


class PersonalNotFound(ValueError):
    pass


class _OwnerAction:
    """Transient host-created authority; never supplied to a model."""
    def __init__(self, profile):
        self._current_agent_id = profile.id
        self.workspace_dir = profile.workspace
        self.authority = Authority(WORKSPACE_WRITE, frozenset({'fs.read', 'fs.write'}),
                                   (profile.workspace,), (profile.workspace,))

    def effective_permission_mode(self):
        return WORKSPACE_WRITE

    def effective_cwd(self):
        return self.workspace_dir

    def protected_paths(self):
        from agent.protocol.agent import Agent
        return Agent.protected_paths(self)


class PersonalService:
    def __init__(self, agent_id, session_id):
        if not isinstance(agent_id, str) or not agent_id.strip() or not isinstance(session_id, str) or not session_id:
            raise PersonalNotFound('Agent and session are required')
        try:
            self.profile = get_agent_registry().get_addressed(agent_id)
        except (KeyError, ValueError):
            raise PersonalNotFound('Agent not found') from None
        self.session_id = session_id
        store = get_conversation_store(self.profile.workspace)
        if session_id not in store.list_session_ids():
            raise PersonalNotFound('Session not found')
        self.store = PersonalStore(store)

    def snapshot(self):
        data = self.store.snapshot(self.session_id)
        data.update(status='success', identity={'agent_id': self.profile.id, 'name': self.profile.name},
                    capabilities=self._capabilities(),
                    memory_retention_note='Forgotten or corrected facts leave active personal memory. Original conversation history is retained separately.')
        return data

    def _capabilities(self):
        # Do not initialize an agent or a model to answer an observational request.
        try:
            from bridge.bridge import Bridge
            bridge = Bridge()
            ab = bridge._agent_bridge
            runtime = ab.get_cached_agent(self.session_id, self.profile.id) if ab else None
            if runtime is not None:
                from agent.tools.base_tool import is_tool_available
                tools = []
                for tool in runtime.tools:
                    available = is_tool_available(tool)
                    decision, _ = authorize(tool, {}, runtime)
                    tools.append({'name': tool.name, 'allowed': available and decision.allowed,
                                  'reason': ('Tool is unavailable' if not available else
                                             decision.reason or 'Allowed by current capability policy')})
                manager = getattr(runtime, 'skill_manager', None)
                skills = []
                for entry in manager.list_skills() if manager else []:
                    skill = entry.get('skill', entry) if isinstance(entry, dict) else getattr(entry, 'skill', entry)
                    name = skill.get('name') if isinstance(skill, dict) else getattr(skill, 'name', None)
                    description = (skill.get('description', '') if isinstance(skill, dict)
                                   else getattr(skill, 'description', ''))
                    if name and (self.profile.skills is None or name in self.profile.skills):
                        skills.append({'name': name, 'description': description})
                return {'status': 'loaded', 'tools': tools, 'skills': skills,
                        'permission_mode': runtime.effective_permission_mode(),
                        'limits': 'Tool capability policy is checked now. File paths and other call-specific limits are checked at execution.'}
        except Exception:
            pass
        return {'status': 'not_loaded', 'tools': [], 'skills': [],
                'limits': 'Runtime capabilities are not loaded; no tool access is implied.'}

    def mutate(self, body):
        op = body.get('operation')
        sid = self.session_id
        if op == 'save_goal':
            self.store.save_goal(sid, body.get('fields'), body.get('source_seq'), body.get('revision'))
        elif op == 'remember':
            self.store.remember(sid, body.get('text'), body.get('source_seq'))
        elif op == 'correct_memory':
            self.store.correct_memory(sid, body.get('memory_id'), body.get('text'), body.get('source_seq'), body.get('revision'))
        elif op == 'forget_memory':
            self.store.forget_memory(sid, body.get('memory_id'), body.get('revision'))
        elif op == 'propose_write':
            self._validate_target(body.get('path'), body.get('content'))
            self.store.propose_action(sid, body.get('path'), body.get('content'), body.get('source_seq'), body.get('expires_at'), os.path.realpath(self.profile.workspace))
        elif op == 'decide_action':
            self.store.decide_action(sid, body.get('action_id'), body.get('decision'))
        elif op == 'execute_action':
            self.execute(body.get('action_id'))
        else:
            raise ValueError('Unknown operation')
        return self.snapshot()

    def _validate_target(self, path, content):
        if not isinstance(path, str) or not path or not isinstance(content, str):
            raise ValueError('Invalid path or content')
        context = _OwnerAction(self.profile)
        authority = resolve_authority(context)
        try:
            FileBroker(authority, context.effective_cwd()).locate(path, write=True)
        except FileDenied:
            raise ValueError('Invalid path') from None
        # Native broker rejects oversized or binary content before side effects.
        from agent.permission.filesystem import MAX_FILE_BYTES
        if '\0' in content or len(content.encode('utf-8')) > MAX_FILE_BYTES:
            raise ValueError('Invalid content')

    def execute(self, action_id):
        # The durable claim is committed before any filesystem operation.
        action = self.store.claim_action(self.session_id, action_id)
        try:
            path, content = action['path'], action['content']
            current_profile = get_agent_registry().get_addressed(self.profile.id)
            if (action['workspace_root'] != os.path.realpath(self.profile.workspace) or
                    action['workspace_root'] != os.path.realpath(current_profile.workspace)):
                raise RuntimeError('workspace_changed')
            if hashlib.sha256(content.encode('utf-8')).hexdigest() != action['content_sha256']:
                raise RuntimeError('binding_mismatch')
            self._validate_target(path, content)
            context = _OwnerAction(self.profile)
            write = invoke(Write({'cwd': context.workspace_dir}), {'path': path, 'content': content}, context)
            if write.status != 'success':
                raise RuntimeError('write_failed')
            read = invoke(Read({'cwd': context.workspace_dir}), {'path': path}, context)
            if read.status != 'success':
                raise RuntimeError('readback_failed')
            # Read tool output is display-truncated; broker reads the actual full bytes.
            actual = FileBroker(resolve_authority(context), context.effective_cwd()).read(path).encode('utf-8')
            expected_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            actual_hash = hashlib.sha256(actual).hexdigest()
            if actual_hash != expected_hash:
                raise RuntimeError('readback_mismatch')
            self.store.finish_action(self.session_id, action_id, 'completed',
                                     {'path': path, 'sha256': actual_hash, 'bytes': len(actual), 'readback': 'verified'})
        except Exception:
            # A failed write can have had effects. Never retry this claim automatically.
            self.store.finish_action(self.session_id, action_id, 'failed',
                                     {'error': 'Action failed or its result could not be verified; review the target.'})
