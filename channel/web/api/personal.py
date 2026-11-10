"""Authenticated owner-only personal continuity endpoints."""
import json
from urllib.parse import urlsplit

import web

from agent.personal.service import PersonalNotFound, PersonalService
from channel.web.core._common import (_get_bearer_token, _is_password_enabled,
                                      _verify_auth_token)


def _owner_auth():
    # Password-disabled consoles have no authenticated owner identity.
    if not _is_password_enabled() or not (
        _verify_auth_token(web.cookies().get('cow_auth_token', '')) or
        _verify_auth_token(_get_bearer_token())
    ):
        raise web.HTTPError('401 Unauthorized', {'Content-Type': 'application/json'},
                            json.dumps({'status': 'error', 'message': 'Owner authentication required'}))


def _check_origin():
    env = web.ctx.env
    if (env.get('CONTENT_TYPE') or '').split(';', 1)[0].strip().lower() != 'application/json':
        raise web.HTTPError('415 Unsupported Media Type')
    origin = env.get('HTTP_ORIGIN')
    if origin:
        if origin == 'null' and _verify_auth_token(_get_bearer_token()):
            return
        parsed = urlsplit(origin)
        scheme = env.get('wsgi.url_scheme', 'http')
        if parsed.scheme != scheme or parsed.netloc != env.get('HTTP_HOST') or parsed.path:
            raise web.HTTPError('403 Forbidden')


def _error(status, message):
    raise web.HTTPError(status, {'Content-Type': 'application/json'},
                        json.dumps({'status': 'error', 'message': message}))


class PersonalHandler:
    def GET(self, session_id):
        _owner_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(agent_id='')
            return json.dumps(PersonalService(params.agent_id, session_id).snapshot())
        except PersonalNotFound:
            _error('404 Not Found', 'Agent or session not found')
        except Exception:
            _error('500 Internal Server Error', 'Personal state unavailable')

    def POST(self, session_id):
        _owner_auth()
        _check_origin()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data())
            if not isinstance(body, dict):
                raise ValueError('Invalid request')
            params = web.input(agent_id='')
            agent_id = params.agent_id or body.get('agent_id')
            return json.dumps(PersonalService(agent_id, session_id).mutate(body))
        except PersonalNotFound:
            _error('404 Not Found', 'Agent or session not found')
        except (ValueError, TypeError, KeyError):
            _error('400 Bad Request', 'Invalid request or action state')
        except Exception:
            _error('500 Internal Server Error', 'Personal action unavailable')
