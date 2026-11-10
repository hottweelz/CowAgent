import os
import threading
from types import SimpleNamespace

import pytest
import plugins
from common import runtime_drain as drain
from plugins.event import Event, EventContext
from plugins.plugin_manager import PluginManager


@pytest.fixture
def coordinator(monkeypatch):
    monkeypatch.setattr(drain, '_installed', None)
    monkeypatch.setattr(drain, '_validate_owner', lambda owner: SimpleNamespace(validate=lambda: None))
    result = drain.RuntimeDrain()
    result.bind_owner(object())
    drain.install(result)
    return result


def test_callback_is_held_and_closed_admission_rejects(coordinator):
    manager = PluginManager.new_instance()
    entered, release = threading.Event(), threading.Event()
    def callback(context):
        entered.set()
        assert release.wait(5)
    manager.plugins['FAKE'] = SimpleNamespace(priority=0, enabled=True)
    manager.instances['FAKE'] = SimpleNamespace(handlers={Event.ON_HANDLE_CONTEXT: callback})
    manager.listening_plugins[Event.ON_HANDLE_CONTEXT] = ['FAKE']
    context = EventContext(Event.ON_HANDLE_CONTEXT, {})
    thread = threading.Thread(target=manager.emit_event, args=(context,))
    thread.start()
    try:
        assert entered.wait(5)
        coordinator.close_admission()
        assert coordinator.wait(0)['active'] == {'plugins': 1}
        with pytest.raises(drain.AdmissionClosed):
            manager.emit_event(context)
    finally:
        release.set()
        thread.join(5)
    assert 'plugin_runtime_untracked' in coordinator.wait(1)['blockers']


def test_midjourney_child_includes_publication(coordinator):
    old = plugins.instance.current_plugin_path
    plugins.instance.current_plugin_path = os.path.join(os.getcwd(), "plugins", "linkai")
    try:
        from plugins.linkai.midjourney import MJBot
    finally:
        plugins.instance.current_plugin_path = old
    entered, release, published = threading.Event(), threading.Event(), threading.Event()
    bot = MJBot.__new__(MJBot)
    def poll(task, context):
        entered.set()
        assert release.wait(5)
        published.set()
    bot.check_task_sync = poll
    bot._do_check_task(object(), object())
    try:
        assert entered.wait(5)
        coordinator.close_admission()
        assert coordinator.wait(0)['active'] == {'plugins': 1}
        with pytest.raises(drain.AdmissionClosed):
            bot._do_check_task(object(), object())
    finally:
        release.set()
    assert coordinator.wait(5)['drained']
    assert published.is_set()


def test_timed_out_skill_install_stays_tracked(coordinator, monkeypatch):
    old = plugins.instance.current_plugin_path
    plugins.instance.current_plugin_path = os.path.join(os.getcwd(), 'plugins', 'cow_cli')
    try:
        import importlib
        importlib.import_module("plugins.cow_cli.cow_cli")  # registers the class
        CowCliPlugin = plugins.instance.plugins["COW_CLI"]
    finally:
        plugins.instance.current_plugin_path = old
    entered, release = threading.Event(), threading.Event()
    def install(name, agent_id):
        entered.set()
        assert release.wait(5)
        return SimpleNamespace(error='fictional')
    monkeypatch.setattr('cli.commands.skill.install_skill', install)
    monkeypatch.setattr(CowCliPlugin, '_INSTALL_TIMEOUT', 0.01)
    try:
        CowCliPlugin()._skill_install('fictional-lifecycle-test')
        assert entered.wait(5)
        coordinator.close_admission()
        assert coordinator.wait(0)['active'] == {'plugins': 1}
    finally:
        release.set()
    assert coordinator.wait(5)['drained']


def test_enabled_unknown_plugin_remains_unsupported(coordinator):
    manager = PluginManager.new_instance()
    class Unknown:
        enabled = True
        priority = 0
        def __init__(self):
            self.handlers = {}
    manager.plugins['UNKNOWN'] = Unknown
    manager.activate_plugins()
    coordinator.close_admission()
    assert 'plugin_runtime_untracked' in coordinator.wait(1)['blockers']


def test_seven_builtin_constructors_and_idle_drain(coordinator, monkeypatch, tmp_path):
    import importlib
    from plugins.plugin import Plugin
    names = ['cow_cli', 'godcmd', 'keyword', 'banwords', 'linkai', 'role', 'finish']
    old = plugins.instance.current_plugin_path
    try:
        for name in names:
            plugins.instance.current_plugin_path = os.path.join(os.getcwd(), 'plugins', name)
            importlib.import_module('plugins.' + name)
    finally:
        plugins.instance.current_plugin_path = old
    keyword = importlib.import_module('plugins.keyword.keyword')
    (tmp_path / 'config.json').write_text('{"keyword": {}}')
    monkeypatch.setattr(keyword, '__file__', str(tmp_path / 'keyword.py'))
    godcmd = importlib.import_module('plugins.godcmd.godcmd')
    monkeypatch.setattr(godcmd, 'conf', lambda: {})
    monkeypatch.setattr(Plugin, 'load_config', lambda self: {
        'GODCMD': {'password': 'fictional', 'admin_users': []},
        'BANWORDS': {'action': 'ignore'},
        'LINKAI': {'midjourney': None, 'summary': {}},
    }.get(self.name.upper(), {}))
    midjourney = importlib.import_module('plugins.linkai.midjourney')
    monkeypatch.setattr(midjourney, 'conf', lambda: {'linkai_api_key': 'fictional'})
    manager = PluginManager.new_instance()
    for name in names:
        cls = plugins.instance.plugins[name.upper()]
        cls.enabled = True
        manager.plugins[name.upper()] = cls
    assert manager.activate_plugins() == []
    assert len(manager.instances) == 7
    coordinator.close_admission()
    assert coordinator.wait(1)['drained']


def test_replaced_builtin_method_fails_qualification(monkeypatch):
    import importlib
    from common.plugin_lifecycle import known_class
    old = plugins.instance.current_plugin_path
    plugins.instance.current_plugin_path = os.path.join(os.getcwd(), 'plugins', 'finish')
    try:
        importlib.import_module('plugins.finish.finish')
    finally:
        plugins.instance.current_plugin_path = old
    cls = plugins.instance.plugins['FINISH']
    assert known_class('FINISH', cls)
    monkeypatch.setattr(cls, 'on_handle_context', lambda self, event: None)
    assert not known_class('FINISH', cls)


def test_unknown_disabled_package_import_is_denied(coordinator, monkeypatch, tmp_path):
    from plugins import plugin_manager
    package = tmp_path / 'extra'
    package.mkdir()
    (package / '__init__.py').write_text('')
    manager = PluginManager.new_instance()
    manager.pconf = {'plugins': {}}
    monkeypatch.setattr(plugin_manager, '_plugins_resource_dir', lambda: str(tmp_path))
    monkeypatch.setattr(plugin_manager.importlib, 'import_module', lambda name: object())
    manager.scan_plugins()
    coordinator.close_admission()
    assert 'plugin_import_untracked' in coordinator.wait(1)['blockers']
    with pytest.raises(drain.AdmissionClosed):
        manager.scan_plugins()


def test_constructor_failure_stays_blocked_after_disable(coordinator, monkeypatch):
    from common import plugin_lifecycle
    manager = PluginManager.new_instance()
    class Broken:
        enabled = True
        priority = 0
        name = "FINISH"
        def __init__(self):
            raise RuntimeError("fictional failure")
    manager.plugins['FINISH'] = Broken
    manager.pconf = {'plugins': {'FINISH': {'enabled': True, 'priority': 0}}}
    monkeypatch.setattr(manager, 'save_config', lambda: None)
    monkeypatch.setattr(plugin_lifecycle, 'known_class', lambda name, cls: True)
    assert manager.activate_plugins() == ['FINISH']
    assert not Broken.enabled
    coordinator.close_admission()
    receipt = coordinator.wait(1)
    assert not receipt['drained']
    assert 'plugin_initialization_failed' in receipt['blockers']


def test_wrapped_builtin_handler_fails_qualification(monkeypatch):
    import functools
    import importlib
    from common.plugin_lifecycle import known_class
    old = plugins.instance.current_plugin_path
    plugins.instance.current_plugin_path = os.path.join(os.getcwd(), 'plugins', 'finish')
    try:
        importlib.import_module('plugins.finish.finish')
    finally:
        plugins.instance.current_plugin_path = old
    cls = plugins.instance.plugins['FINISH']
    original = cls.on_handle_context
    @functools.wraps(original)
    def replacement(*args, **kwargs):
        return original(*args, **kwargs)
    assert known_class('FINISH', cls)
    monkeypatch.setattr(cls, 'on_handle_context', replacement)
    assert not known_class('FINISH', cls)


def test_known_source_import_failure_blocks_receipt(coordinator, monkeypatch, tmp_path):
    from common import plugin_lifecycle
    from plugins import plugin_manager
    package = tmp_path / 'finish'
    package.mkdir()
    (package / '__init__.py').write_text('')
    manager = PluginManager.new_instance()
    manager.pconf = {'plugins': {}}
    monkeypatch.setattr(plugin_manager, '_plugins_resource_dir', lambda: str(tmp_path))
    monkeypatch.setattr(plugin_lifecycle, 'known_import', lambda *args: True)
    def fail_import(name):
        raise ImportError('fictional')
    monkeypatch.setattr(plugin_manager.importlib, 'import_module', fail_import)
    manager.scan_plugins()
    assert manager.current_plugin_path is None
    coordinator.close_admission()
    receipt = coordinator.wait(1)
    assert not receipt['drained']
    assert 'plugin_import_failed' in receipt['blockers']


def test_missing_enabled_plugin_blocks_receipt(coordinator, monkeypatch):
    manager = PluginManager.new_instance()
    manager.pconf = {'plugins': {'Missing': {'enabled': True, 'priority': 0}}}
    monkeypatch.setattr(manager, 'load_config', lambda: None)
    monkeypatch.setattr(manager, 'scan_plugins', lambda: None)
    monkeypatch.setattr(manager, '_load_all_config', lambda: None)
    manager.load_plugins()
    coordinator.close_admission()
    assert 'plugin_enabled_missing' in coordinator.wait(1)['blockers']


def test_replaced_cow_cli_tracked_wrapper_fails_qualification(monkeypatch):
    import functools
    import importlib
    from common.plugin_lifecycle import known_class
    old = plugins.instance.current_plugin_path
    plugins.instance.current_plugin_path = os.path.join(os.getcwd(), 'plugins', 'cow_cli')
    try:
        importlib.import_module('plugins.cow_cli.cow_cli')
    finally:
        plugins.instance.current_plugin_path = old
    cls = plugins.instance.plugins['COW_CLI']
    original = cls.execute
    @functools.wraps(original)
    def replacement(*args, **kwargs):
        return original(*args, **kwargs)
    assert known_class('COW_CLI', cls)
    monkeypatch.setattr(cls, 'execute', replacement)
    assert not known_class('COW_CLI', cls)
