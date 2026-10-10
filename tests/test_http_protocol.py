import json
import unittest

from ccw.http_protocol import text_payloads
from ccw.web_http import BridgeHttpClient


class Response:
    status_code = 200

    def __init__(self, body):
        self.content = body.encode()

    def iter_content(self, chunk_size):
        yield self.content

    def close(self):
        pass


class Session:
    def __init__(self, *bodies):
        self.responses = [Response(body) for body in bodies]
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


class ProtocolTests(unittest.TestCase):
    def locator(self):
        return dict(conversation_id=None, user_message_id='user', parent_message_id='parent',
                    requested_model='gpt-6-pro', account_hash='account')

    def ready(self, **config):
        session = Session('<html data-build="build"><script src="/client.js"></script></html>',
                          '{"prepare_token":"private-prepare"}', '{"token":"private-requirement"}',
                          '{"conduit_token":"private-conduit"}',
                          'data: "v1"\n\ndata: {"v":{"conversation_id":"conversation"}}\n\n',
                          '{"mapping":{}}')
        client = BridgeHttpClient(dict(token='private-token', model='gpt-6-pro', **config), session)
        client.account_hash = 'account'
        return client, session

    def test_complete_handshake_precedes_only_one_dispatch(self):
        client, session = self.ready()
        saved = []
        client.set_locator_callback(saved.append)
        result = client.submit({**self.locator(), 'text': 'Bounded read-only question'})
        paths = [call[1].removeprefix(client.HOST) for call in session.calls]
        self.assertEqual(paths, ['/', '/backend-api/sentinel/chat-requirements/prepare',
                                '/backend-api/sentinel/chat-requirements/finalize',
                                '/backend-api/f/conversation/prepare',
                                '/backend-api/f/conversation', '/backend-api/conversation/conversation'])
        prepare, dispatch = session.calls[3][2], session.calls[4][2]
        self.assertEqual(prepare['json']['partial_query']['id'], dispatch['json']['messages'][0]['id'])
        self.assertEqual(prepare['json']['parent_message_id'], dispatch['json']['parent_message_id'])
        self.assertEqual(dispatch['json']['model'], 'gpt-6-pro')
        self.assertEqual(dispatch['json']['supported_encodings'], ['v1'])
        self.assertEqual(dispatch['headers']['X-Conduit-Token'], 'private-conduit')
        self.assertEqual(dispatch['headers']['OpenAI-Sentinel-Chat-Requirements-Token'], 'private-requirement')
        self.assertEqual(dispatch['headers']['Accept'], 'text/event-stream')
        self.assertEqual(saved[0]['conversation_id'], 'conversation')
        self.assertNotIn('private-requirement', json.dumps(result))

    def test_challenge_stops_before_finalize_prepare_or_dispatch(self):
        for challenge in ('arkose', 'turnstile'):
            with self.subTest(challenge=challenge):
                session = Session('<html></html>', json.dumps({challenge: {'required': True},
                                                              'prepare_token': 'private'}))
                client = BridgeHttpClient({'token': 'private', 'model': 'gpt-6-pro'}, session)
                client.account_hash = 'account'
                result = client.submit({**self.locator(), 'text': 'question'})
                self.assertEqual(result['error_code'], 'challenge_required')
                self.assertEqual(len(session.calls), 2)

    def test_malformed_challenge_flags_cannot_dispatch(self):
        for value in (None, [], {}, {'required': 'true'}, {'required': 1}):
            with self.subTest(value=value):
                client, session = self.ready()
                session.responses[1] = Response(json.dumps({'turnstile': value, 'prepare_token': 'private'}))
                result = client.submit({**self.locator(), 'text': 'question'})
                self.assertEqual(result['error_code'], 'preparation_response_invalid')
                self.assertEqual(len(session.calls), 2)

    def test_proof_of_work_solves_and_feeds_finalize(self):
        session = Session('<html data-build="build"><script src="/client.js"></script></html>',
                          json.dumps({'proofofwork': {'required': True, 'seed': 'seed', 'difficulty': '0f'},
                                      'prepare_token': 'private-prepare'}),
                          '{"token":"private-requirement"}',
                          '{"conduit_token":"private-conduit"}',
                          'data: "v1"\n\ndata: {"v":{"conversation_id":"conversation"}}\n\n',
                          '{"mapping":{}}')
        client = BridgeHttpClient(dict(token='private-token', model='gpt-6-pro'), session)
        client.account_hash = 'account'
        client.submit({**self.locator(), 'text': 'Bounded read-only question'})
        paths = [call[1].removeprefix(client.HOST) for call in session.calls]
        self.assertEqual(paths, ['/', '/backend-api/sentinel/chat-requirements/prepare',
                                 '/backend-api/sentinel/chat-requirements/finalize',
                                 '/backend-api/f/conversation/prepare',
                                 '/backend-api/f/conversation', '/backend-api/conversation/conversation'])
        finalize = session.calls[2][2]
        self.assertTrue(finalize['json']['proof_token'].startswith('gAAAAAB'))
        self.assertEqual(finalize['json']['turnstile_token'], '')

    def test_malformed_proof_of_work_stops_before_finalize(self):
        client, session = self.ready()
        session.responses[1] = Response(json.dumps({'proofofwork': {'required': True, 'seed': 'seed'},
                                                    'prepare_token': 'private'}))
        result = client.submit({**self.locator(), 'text': 'question'})
        self.assertEqual(result['error_code'], 'preparation_response_invalid')
        self.assertEqual(len(session.calls), 2)

    def test_missing_conduit_never_dispatches(self):
        client, session = self.ready()
        session.responses[3] = Response('{}')
        result = client.submit({**self.locator(), 'text': 'question'})
        self.assertEqual(result['error_code'], 'conversation_prepare_failed')
        self.assertEqual(len(session.calls), 4)

    def test_model_fallback_when_requested_model_refused(self):
        session = Session('<html data-build="build"><script src="/client.js"></script></html>',
                          '{"prepare_token":"private-prepare"}', '{"token":"private-requirement"}',
                          '{"conduit_token":null}',
                          '{"conduit_token":"private-conduit"}',
                          'data: "v1"\n\ndata: {"v":{"conversation_id":"conversation"}}\n\n',
                          '{"mapping":{}}')
        client = BridgeHttpClient(dict(token='private-token', model='gpt-6-pro',
                                       fallback_model='gpt-6-thinking'), session)
        client.account_hash = 'account'
        result = client.submit({**self.locator(), 'text': 'Bounded read-only question'})
        paths = [call[1].removeprefix(client.HOST) for call in session.calls]
        self.assertEqual(paths, ['/', '/backend-api/sentinel/chat-requirements/prepare',
                                 '/backend-api/sentinel/chat-requirements/finalize',
                                 '/backend-api/f/conversation/prepare',
                                 '/backend-api/f/conversation/prepare',
                                 '/backend-api/f/conversation', '/backend-api/conversation/conversation'])
        dispatch = session.calls[5][2]
        self.assertEqual(dispatch['json']['model'], 'gpt-6-thinking')
        self.assertEqual(dispatch['headers']['X-Conduit-Token'], 'private-conduit')

    def test_project_binding_must_be_confirmed_by_server(self):
        project = 'g-p-' + 'a' * 32
        prepare, dispatch = text_payloads(self.locator(), 'question', project)
        self.assertEqual(prepare['conversation_mode'], {'kind': 'gizmo_interaction', 'gizmo_id': project})
        self.assertEqual(dispatch['conversation_mode'], prepare['conversation_mode'])
        client, _ = self.ready(project_id=project)
        result = client._observe_data({'gizmo_id': 'other', 'mapping': {}}, self.locator())
        self.assertEqual(result['error_code'], 'project_membership_mismatch')

    def test_preparation_errors_do_not_leak_or_dispatch(self):
        client, session = self.ready()
        session.responses[1] = Response('private malformed body')
        result = client.submit({**self.locator(), 'text': 'question'})
        self.assertEqual(result['error_code'], 'preparation_response_invalid')
        self.assertNotIn('private malformed', json.dumps(result))
        self.assertEqual(len(session.calls), 2)
