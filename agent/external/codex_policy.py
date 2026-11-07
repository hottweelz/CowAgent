"""Candidate Codex configuration checks; EXTERNAL-002 execution gate remains blocked.

Matching configuration does not prove the model-facing tool surface is confined.
Existing authentication and model settings stay owned by Codex.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib

VERSION = '0.165.0'
PROFILE = 'cow-external-002'
DISABLED_FEATURES = (
    'shell_tool', 'apps', 'plugins', 'remote_plugin', 'hooks', 'memories',
    'chronicle', 'goals', 'multi_agent', 'multi_agent_v2', 'browser_use',
    'browser_use_external', 'computer_use', 'in_app_browser',
    'in_app_local_automation', 'code_mode', 'code_mode_host', 'image_generation',
    'skill_search', 'skill_mcp_dependency_install', 'shell_snapshot',
    'shell_snapshot_v2', 'daemon_auto_start', 'view_image', 'request_permissions_tool',
)


class SafetyGateError(RuntimeError):
    pass


class CodexPolicy:
    """Trusted operator enrollment, not task/model-provided arguments."""
    def __init__(self, executable):
        self.executable = Path(executable)
        if not self.executable.is_absolute():
            raise SafetyGateError('Codex executable must be an enrolled absolute path')
        self.codex_home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))

    def launch(self):
        if sys.platform != 'darwin':
            raise SafetyGateError('This adapter has only been validated on macOS')
        try:
            result = subprocess.run([str(self.executable), '--version'], capture_output=True,
                                    text=True, timeout=10, check=True)
            config = tomllib.loads((self.codex_home / 'config.toml').read_text())
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            raise SafetyGateError('Codex or its existing configuration is unavailable') from exc
        if result.stdout.strip() != 'codex-cli ' + VERSION:
            raise SafetyGateError('Unvalidated Codex version')
        servers = tuple(config.get('mcp_servers', {}))
        if any(not re.fullmatch(r'[A-Za-z0-9_-]+', name) for name in servers):
            raise SafetyGateError('MCP server key cannot be safely overridden')
        private_roots = {str(self.codex_home), str(self.codex_home.resolve()),
                         str(Path.home() / '.ssh'), str(Path.home() / '.cow')}
        denials = ', '.join(json.dumps(path) + '="deny"' for path in sorted(private_roots))
        settings = [
            f'permissions.{PROFILE}.extends=":workspace"',
            f'permissions.{PROFILE}.filesystem={{":root"="deny", ":minimal"="read", '
            '":slash_tmp"="deny", ":tmpdir"="deny", ":workspace_roots"={"."="write", '
            '".git"="read", ".codex"="deny", ".agents"="deny", "AGENTS.md"="read", ".env"="deny"}, '
            + denials + '}',
            f'permissions.{PROFILE}.network.enabled=false',
            'notify=[]', 'web_search="disabled"',
            'shell_environment_policy.inherit="none"', 'shell_environment_policy.set={}',
        ]
        settings.extend('mcp_servers.' + name + '.enabled=false' for name in servers)
        for key in config.get('shell_environment_policy', {}).get('set', {}):
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key):
                raise SafetyGateError('Shell environment key cannot be safely overridden')
            settings.append('shell_environment_policy.set.' + key + '=""')
        argv = [str(self.executable), 'app-server', '--stdio']
        for setting in settings:
            argv += ['-c', setting]
        for feature in DISABLED_FEATURES:
            argv += ['--disable', feature]
        # Only Codex's selected provider environment credential, when already
        # present, can pass through. Never persist or log the environment.
        env = {k: v for k, v in os.environ.items()
               if k in ('HOME', 'PATH', 'LANG', 'LC_ALL', 'TMPDIR', 'CODEX_HOME')}
        selected = config.get('model_providers', {}).get(config.get('model_provider'), {})
        key = selected.get('env_key')
        if isinstance(key, str) and key in os.environ:
            env[key] = os.environ[key]
        expected = {'model': config.get('model'), 'modelProvider': config.get('model_provider'),
                    'reasoningEffort': config.get('model_reasoning_effort'), 'mcp_servers': servers}
        return argv, env, expected

    def initialize(self, client):
        return client.request('initialize', {
            'clientInfo': {'name': 'cowagent_external_002', 'version': '0.1.0'},
            'capabilities': {'experimentalApi': True},
        }, timeout=20)

    def start_thread(self, client, cwd):
        profiles = client.request('permissionProfile/list', {'cwd': str(cwd)}, timeout=20)
        if not any(p.get('id') == PROFILE and p.get('allowed') is True for p in profiles['data']):
            raise SafetyGateError('Required permission profile unavailable')
        result = client.request('thread/start', {
            'cwd': str(cwd), 'permissions': PROFILE, 'approvalPolicy': 'on-request',
            'approvalsReviewer': 'user', 'allowProviderModelFallback': False,
        }, timeout=20)
        sandbox = result.get('sandbox', {})
        if (result.get('activePermissionProfile', {}).get('id') != PROFILE
                or result.get('approvalPolicy') != 'on-request'
                or result.get('approvalsReviewer') != 'user'
                or Path(result.get('cwd', '')) != Path(cwd)
                or sandbox.get('type') != 'workspaceWrite'
                or sandbox.get('networkAccess') is not False
                or sandbox.get('excludeSlashTmp') is not True
                or sandbox.get('excludeTmpdirEnvVar') is not True
                or sandbox.get('writableRoots')):
            raise SafetyGateError('Effective Codex permission policy differs from enrollment')
        return result

    def inspect(self, client, cwd, thread_id):
        """Return only capability metadata, never raw configuration or secrets."""
        config = client.request('config/read', {'cwd': str(cwd), 'includeLayers': False}, timeout=20)['config']
        mcp = client.request('mcpServerStatus/list', {'threadId': thread_id}, timeout=20)
        features = client.request('experimentalFeature/list', {'limit': 200}, timeout=20)
        return {
            'features': {f['name']: f['enabled'] for f in features['data']
                         if f['name'] in DISABLED_FEATURES},
            'mcp': [{'name': s['name'], 'runtimeStatus': s.get('runtimeStatus'),
                     'tool_count': len(s['tools']), 'resource_count': len(s['resources'])}
                    for s in mcp['data']],
            'mcp_enabled': {k: v.get('enabled') for k, v in config.get('mcp_servers', {}).items()},
            'shell_inherit': config.get('shell_environment_policy', {}).get('inherit'),
            'shell_set_nonempty_keys': [k for k, v in config.get('shell_environment_policy', {}).get('set', {}).items() if v],
            'notify_configured': bool(config.get('notify')),
            'web_search': config.get('web_search'),
        }

    def attest_configuration(self, client, cwd, thread, expected):
        """Check effective settings only. This does not approve task execution."""
        for key in ('model', 'modelProvider'):
            if expected[key] is not None and thread.get(key) != expected[key]:
                raise SafetyGateError('Codex selected model differs from its existing configuration')
        if (expected['reasoningEffort'] is not None
                and thread['thread'].get('reasoningEffort') != expected['reasoningEffort']):
            raise SafetyGateError('Codex reasoning configuration differs from enrollment')
        value = self.inspect(client, cwd, thread['thread']['id'])
        if (set(value['features']) != set(DISABLED_FEATURES)
                or any(value['features'].values())
                or set(value['mcp_enabled']) != set(expected['mcp_servers'])
                or any(v is not False for v in value['mcp_enabled'].values())
                or any(s['runtimeStatus'] != 'disabled' or s['tool_count'] or s['resource_count'] for s in value['mcp'])
                or value['shell_inherit'] != 'none' or value['shell_set_nonempty_keys']
                or value['notify_configured'] or value['web_search'] != 'disabled'):
            raise SafetyGateError('Effective Codex configuration differs from enrollment')
        return value
