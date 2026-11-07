"""Immutable, attenuable tool authority for in-process agent execution.

This is a fail-closed capability boundary, not an OS process sandbox.
"""
from dataclasses import dataclass
import os

from agent.permission.policy import FULL_ACCESS, READ_ONLY, WORKSPACE_WRITE, MODES

SAFE_CAPABILITIES = frozenset({'fs.read', 'fs.write', 'time', 'subagent.spawn', 'delegate.local'})


@dataclass(frozen=True)
class Authority:
    mode: str
    capabilities: frozenset[str]
    read_roots: tuple[str, ...]
    write_roots: tuple[str, ...]
    denied_paths: tuple[str, ...] = ()
    restricted: bool = True
    version: int = 1

    def __post_init__(self):
        if self.version != 1 or self.mode not in MODES:
            raise ValueError('Invalid authority')
        # Freeze and reject unsupported capabilities; unknown grants cannot be ignored.
        caps = frozenset(self.capabilities)
        if not caps <= SAFE_CAPABILITIES:
            raise ValueError('Unknown capability')
        object.__setattr__(self, 'capabilities', caps)
        for field in ('read_roots', 'write_roots', 'denied_paths'):
            object.__setattr__(self, field, tuple(os.path.realpath(os.path.abspath(p)) for p in getattr(self, field)))


def _roots_intersection(left, right):
    result = set()
    for a in left:
        for b in right:
            try:
                common = os.path.commonpath((a, b))
            except ValueError:
                continue
            if common == a:
                result.add(b)
            elif common == b:
                result.add(a)
    return tuple(sorted(result))


def _mode_intersection(a, b):
    rank = {READ_ONLY: 0, WORKSPACE_WRITE: 1, FULL_ACCESS: 2}
    return min((a, b), key=rank.__getitem__)


def derive_authority(parent: Authority, receiver: Authority) -> Authority:
    """Intersect authority; a delegated receiver is always restricted."""
    mode = _mode_intersection(parent.mode, receiver.mode)
    caps = parent.capabilities & receiver.capabilities & SAFE_CAPABILITIES
    if mode == READ_ONLY:
        caps -= {'fs.write'}
    return Authority(mode, caps, _roots_intersection(parent.read_roots, receiver.read_roots),
                     _roots_intersection(parent.write_roots, receiver.write_roots) if mode != READ_ONLY else (),
                     tuple(sorted(set(parent.denied_paths) | set(receiver.denied_paths))), True)


def _current_registry():
    """Load the roster without the UI's permissive corrupt-file fallback."""
    import json
    from config import conf
    from agent import team
    from agent.registry import AgentRegistry
    settings = dict(conf())
    roster_path = team.team_file(settings)
    try:
        raw = roster_path.read_text(encoding='utf-8-sig')
    except FileNotFoundError:
        pass
    else:
        roster = json.loads(raw)
        if not isinstance(roster, dict):
            raise ValueError('Invalid roster')
        settings.update({key: roster[key] for key in team.TEAM_KEYS if key in roster})
    return AgentRegistry.from_config(settings)


def _registry_profiles():
    return _current_registry().list(include_disabled=True)


def resolve_authority(agent) -> Authority:
    if agent is None:
        raise ValueError('Missing agent authority')
    mode = agent.effective_permission_mode()
    if mode not in MODES:
        raise ValueError('Invalid permission mode')
    root = agent.effective_cwd()
    if not isinstance(root, str) or not os.path.isabs(root):
        raise ValueError('Missing workspace root')
    supplied = getattr(agent, 'authority', None)
    denied = list(agent.protected_paths()) if callable(getattr(agent, 'protected_paths', None)) else []
    # Each profile is protected even when a project grant is an ancestor of a
    # custom sibling workspace. Never guess ownership from a project path.
    profiles = _registry_profiles()
    owner = getattr(agent, '_current_agent_id', None)
    own_workspace = getattr(agent, 'workspace_dir', None)
    if not owner and own_workspace:
        canonical = os.path.realpath(os.path.abspath(own_workspace))
        matches = [p.id for p in profiles if os.path.realpath(p.workspace) == canonical]
        owner = matches[0] if len(matches) == 1 else None
    denied.extend(p.workspace for p in profiles if p.id != owner)
    if supplied is not None and not isinstance(supplied, Authority):
        raise ValueError('Invalid authority')
    read_roots = supplied.read_roots if supplied is not None else (root,)
    write_roots = supplied.write_roots if supplied is not None else (root,)
    baseline = Authority(mode, SAFE_CAPABILITIES - ({'fs.write'} if mode == READ_ONLY else set()),
                         read_roots, write_roots if mode != READ_ONLY else (),
                         tuple(denied), mode != FULL_ACCESS)
    if supplied is None:
        return baseline
    if not isinstance(supplied, Authority):
        raise ValueError('Invalid authority')
    # A supplied worker authority is always bounded by the live session mode and root.
    return derive_authority(baseline, supplied)


def restricted_authority(agent) -> Authority:
    """Attenuate an agent's current authority for a new worker."""
    auth = resolve_authority(agent)
    mode = WORKSPACE_WRITE if auth.mode == FULL_ACCESS else auth.mode
    return Authority(mode, auth.capabilities & SAFE_CAPABILITIES, auth.read_roots,
                     auth.write_roots if mode != READ_ONLY else (), auth.denied_paths, True)
