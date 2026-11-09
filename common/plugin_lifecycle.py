"""Narrow source and handler contract for the reviewed built-in plugins.

A changed or replaced plugin must be reviewed and the contract updated. This is
not a sandbox against code with the process owner's authority.
"""
import hashlib
import inspect
import types
from functools import lru_cache
from pathlib import Path

from plugins.event import Event

_ROOT = Path(__file__).resolve().parent.parent
_FILES = {
    'plugins/cow_cli/cow_cli.py': 'dff0d074a29781ed7825cc14f3cb17b41d95b9d603de2fa15298da0c050f461b',
    'plugins/godcmd/godcmd.py': '2547d17ba8582e649810588aa531bc365fda497c1095efad8bdeb3c21dfa38c2',
    'plugins/keyword/keyword.py': 'bf01f7e669a227de177c55d4c71dacc6604a0c1d1765bf7c39a572ce536e8ef6',
    'plugins/banwords/banwords.py': 'b5eca186bff59545a8b12fda23433403191b3608a8ba4291bc3094a3d1b0f634',
    'plugins/linkai/linkai.py': '664bc28ecdec3f3fcd191369a4c33eb3b5c7eeed1f219ba4f0fb33afc367377a',
    'plugins/linkai/midjourney.py': 'e7b22ab78db0da40e8bb7a61ad87c679251423c0a5081fcee1701069ee06124b',
    'plugins/linkai/summary.py': 'b45893a5826a73eb6bbf68f7f7b9893ab4ad7c76cd403dd9938f42350f3f667e',
    'plugins/linkai/utils.py': 'ba51a8d8405187b3b561172e3eacba1d01b794d5e31873572b7fb966c353148b',
    'plugins/role/role.py': 'ae586f46d27bdf2195f8690492c96d8f8c4bb163e3bb02e79ff86e7431b558b9',
    'plugins/finish/finish.py': 'cc7534eaeb1841172fb74fcf9cfd776ff258d0706c5ea3ebbceb805752d6af33',
}
_CLASSES = {
    'COW_CLI': ('plugins.cow_cli.cow_cli', 'CowCliPlugin'),
    'GODCMD': ('plugins.godcmd.godcmd', 'Godcmd'),
    'KEYWORD': ('plugins.keyword.keyword', 'Keyword'),
    'BANWORDS': ('plugins.banwords.banwords', 'Banwords'),
    'LINKAI': ('plugins.linkai.linkai', 'LinkAI'),
    'ROLE': ('plugins.role.role', 'Role'),
    'FINISH': ('plugins.finish.finish', 'Finish'),
}


_IMPORT_FILES = {'plugins/cow_cli/__init__.py': '9facfa863283ae51e69c257a7c882b327e64bd2586365cb991c5da53e105ac10', 'plugins/cow_cli/cow_cli.py': 'dff0d074a29781ed7825cc14f3cb17b41d95b9d603de2fa15298da0c050f461b', 'plugins/godcmd/__init__.py': '0aa6a61a3c8f165f287720c2a14f5cd0f09105619ce702e7eaf60137d637a985', 'plugins/godcmd/godcmd.py': '2547d17ba8582e649810588aa531bc365fda497c1095efad8bdeb3c21dfa38c2', 'plugins/keyword/__init__.py': '3c983a79f96d052e904887a21e00ff9d90df50760aa8d71f34028a0a2bb92c6c', 'plugins/keyword/keyword.py': 'bf01f7e669a227de177c55d4c71dacc6604a0c1d1765bf7c39a572ce536e8ef6', 'plugins/banwords/__init__.py': '12c3b4efb9fa25cb41cd898f31e388772d3474c62631afb8a30eaf9dd2417aa6', 'plugins/banwords/banwords.py': 'b5eca186bff59545a8b12fda23433403191b3608a8ba4291bc3094a3d1b0f634', 'plugins/banwords/lib/WordsSearch.py': '7af8d2c6ece83be6cb3b808c250177e8b6f2287976eff2bb3321819f523c8dfa', 'plugins/linkai/__init__.py': 'b4ed2be749cc3e66815c999896b5f40235cadd463068e756a1d7ce9f0c89e071', 'plugins/linkai/linkai.py': '664bc28ecdec3f3fcd191369a4c33eb3b5c7eeed1f219ba4f0fb33afc367377a', 'plugins/linkai/midjourney.py': 'e7b22ab78db0da40e8bb7a61ad87c679251423c0a5081fcee1701069ee06124b', 'plugins/linkai/summary.py': 'b45893a5826a73eb6bbf68f7f7b9893ab4ad7c76cd403dd9938f42350f3f667e', 'plugins/linkai/utils.py': 'ba51a8d8405187b3b561172e3eacba1d01b794d5e31873572b7fb966c353148b', 'plugins/role/__init__.py': 'cb25d7370762d1d3969171f47e2a465bcb528fb4b3de40d33345981efeaaceda', 'plugins/role/role.py': 'ae586f46d27bdf2195f8690492c96d8f8c4bb163e3bb02e79ff86e7431b558b9', 'plugins/finish/__init__.py': '379c8e9122b9467eb8c35426bd9b182ba45557ee9e86cbb87fb047a7d8877770', 'plugins/finish/finish.py': 'cc7534eaeb1841172fb74fcf9cfd776ff258d0706c5ea3ebbceb805752d6af33', 'plugins/dungeon/__init__.py': 'a5fd108547b290e18e81e0d60b1176d26ac9d537679e05f93ed5f189139ec608', 'plugins/dungeon/dungeon.py': '1eb28cb5c7772956e8b6ed6b0c66d4c4f18b40b4b26a8e48f3501d706f0baa33', 'plugins/hello/__init__.py': '9cf566a9f3eb3b5688e358c68744b2f60596397755a18e8ab41c17be79da2e44', 'plugins/hello/hello.py': '22b1b5272fc55ca4537e4b707409e1b3e8218bbfbefc59762c3c5e1f162bde9f'}

def known_import(name, directory):
    expected = {path: digest for path, digest in _IMPORT_FILES.items() if path.startswith("plugins/" + name + "/")}
    try:
        root = Path(directory).resolve()
        if not expected or root != (_ROOT / "plugins" / name).resolve():
            return False
        paths = {p.relative_to(_ROOT).as_posix(): p for p in root.rglob("*.py")}
        if set(paths) != set(expected):
            return False
        for key, path in paths.items():
            path.resolve().relative_to(root)
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected[key]:
                return False
        return True
    except (OSError, ValueError):
        return False


def _code_signature(code):
    constants = tuple(_code_signature(item) if isinstance(item, types.CodeType) else item
                      for item in code.co_consts)
    return (code.co_code, constants, code.co_names, code.co_varnames,
            code.co_freevars, code.co_cellvars, code.co_argcount,
            code.co_kwonlyargcount, code.co_flags)


@lru_cache(maxsize=7)
def _source_methods(path, class_name, digest):
    source = (_ROOT / path).read_bytes()
    if hashlib.sha256(source).hexdigest() != digest:
        return None
    module = compile(source, str(_ROOT / path), 'exec')
    matches = [c for c in module.co_consts if isinstance(c, types.CodeType) and c.co_name == class_name]
    if len(matches) != 1:
        return None
    return {c.co_name: _code_signature(c) for c in matches[0].co_consts
            if isinstance(c, types.CodeType)}


def known_class(name, cls):
    expected = _CLASSES.get(name)
    if expected != (getattr(cls, '__module__', None), getattr(cls, '__qualname__', None)):
        return False
    constructor = getattr(cls, "__init__", None)
    code = getattr(constructor, "__code__", None)
    expected_file = (_ROOT / (expected[0].replace(".", "/") + ".py")).resolve()
    if code is None or Path(code.co_filename).resolve() != expected_file:
        return False
    files = [expected[0].replace('.', '/') + '.py']
    if name == 'LINKAI':
        files += ['plugins/linkai/midjourney.py', 'plugins/linkai/summary.py', 'plugins/linkai/utils.py']
    try:
        if not all(hashlib.sha256((_ROOT / path).read_bytes()).hexdigest() == _FILES[path] for path in files):
            return False
        expected_methods = _source_methods(files[0], expected[1], _FILES[files[0]])
        actual = {}
        for key, value in vars(cls).items():
            if isinstance(value, (staticmethod, classmethod)):
                value = value.__func__
            if isinstance(value, types.FunctionType):
                if name == 'COW_CLI' and key == 'execute':
                    # This is the only reviewed decorated method. Verify the
                    # actual runtime wrapper and its closed-over target/category.
                    from common import runtime_drain
                    expected_wrapper = runtime_drain.tracked('plugins')(lambda: None)
                    closure = inspect.getclosurevars(value).nonlocals
                    target = closure.get('target')
                    if (value.__code__ is not expected_wrapper.__code__
                            or value.__globals__ is not runtime_drain.__dict__
                            or set(closure) != {'category', 'target'}
                            or closure['category'] != 'plugins'
                            or not isinstance(target, types.FunctionType)
                            or getattr(value, '__wrapped__', None) is not target):
                        return False
                    value = target
                actual[key] = _code_signature(value.__code__)
        return actual == expected_methods
    except (OSError, KeyError, ValueError, TypeError, SyntaxError):
        return False


def known_handlers(name, instance):
    expected = {Event.ON_HANDLE_CONTEXT: 'on_handle_context'}
    if name == 'BANWORDS' and Event.ON_DECORATE_REPLY in instance.handlers:
        expected[Event.ON_DECORATE_REPLY] = 'on_decorate_reply'
    if set(instance.handlers) != set(expected):
        return False
    return all(getattr(instance.handlers[event], '__self__', None) is instance
               and getattr(instance.handlers[event], '__func__', None) is getattr(type(instance), method, None)
               for event, method in expected.items())
