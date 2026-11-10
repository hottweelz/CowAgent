"""Authenticated owner controls; model text cannot establish a commitment."""
import json

import web

from agent.personal.commitments import CommitmentService
from agent.personal.service import PersonalNotFound
from channel.web.api.personal import _owner_auth, _check_origin, _error


class CommitmentsHandler:
    def GET(self, session_id):
        _owner_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(agent_id='')
            return json.dumps(CommitmentService(params.agent_id, session_id).snapshot())
        except PersonalNotFound:
            _error('404 Not Found', 'Agent or conversation not found')
        except Exception:
            _error('500 Internal Server Error', 'Commitments unavailable')

    def POST(self, session_id):
        _owner_auth()
        _check_origin()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            raw = web.data()
            if len(raw) > 65536:
                raise ValueError('Request exceeds limit')
            body = json.loads(raw)
            if not isinstance(body, dict):
                raise ValueError('Invalid request')
            params = web.input(agent_id='')
            service = CommitmentService(params.agent_id, session_id)
            return json.dumps(service.mutate(body))
        except PersonalNotFound:
            _error('404 Not Found', 'Agent or conversation not found')
        except (ValueError, TypeError, KeyError):
            _error('400 Bad Request', 'Invalid owner request, source, endpoint or commitment state')
        except Exception:
            _error('500 Internal Server Error', 'Commitment operation unavailable; refresh its status')
