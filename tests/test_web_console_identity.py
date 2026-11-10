"""Configured instance identity reaches the shell and stays text, not markup."""

import json

import pytest
import web

from channel.web.api import config as config_api, pages
from channel.web.core import template


@pytest.mark.parametrize('settings, expected', [
    ({'default_agent_name': 'BullGod'}, 'BullGod'),
    ({'default_agent_name': '  '}, 'CowAgent'),
    ({}, 'CowAgent'),
    ({'agent': False, 'default_agent_name': 'BullGod'}, 'AI Assistant'),
])
def test_console_name_matches_shell_and_config(monkeypatch, settings, expected):
    monkeypatch.setattr(pages, 'conf', lambda: settings)
    monkeypatch.setattr(config_api, 'conf', lambda: settings)
    monkeypatch.setattr(config_api, '_require_auth', lambda: None)
    app = web.application(('/', 'Chat', '/config', 'Config'),
                          {'Chat': pages.ChatHandler, 'Config': config_api.ConfigHandler},
                          autoreload=False)
    html = app.request('/').data.decode()
    assert f'<title>{expected} Console</title>' in html
    assert f'alt="{expected}"' in html
    assert f'>{expected}</span>' in html
    assert json.loads(app.request('/config').data)['title'] == expected


def test_display_name_cannot_break_html_or_attributes():
    name = 'Bull"</title><script>alert(1)</script>'
    html = template.render('chat.html', title=name)
    assert name not in html
    assert 'Bull&quot;&lt;/title&gt;&lt;script&gt;alert(1)&lt;/script&gt;' in html
    assert '{{CONSOLE_NAME}}' not in html
