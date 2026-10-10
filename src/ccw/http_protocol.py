"""Independent text request preparation, based on observed website wire fields."""
import base64
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import json
import re
import secrets
import time
import uuid


USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
              'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36')


class _Resources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.build = ''

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'html':
            self.build = values.get('data-build', '')
        if tag == 'script' and values.get('src'):
            self.scripts.append(values['src'])


def requirements_payload(html):
    resources = _Resources()
    resources.feed(html)
    timestamp = datetime.now(timezone(timedelta(hours=-5)))
    ticks = time.perf_counter() * 1000
    fingerprint = [
        3000, timestamp.strftime('%a %b %d %Y %H:%M:%S') + ' GMT-0500 (Eastern Standard Time)',
        4294705152, 1, USER_AGENT,
        resources.scripts[0] if resources.scripts else 'https://chatgpt.com/backend-api/sentinel/sdk.js',
        resources.build, 'en-US', 'en-US', secrets.randbelow(1000000) / 1000000,
        'language\u2212en-US', 'location', 'window', ticks, str(uuid.uuid4()), '',
        8, time.time() * 1000 - ticks, 0, 0, 0, 0, 0, 0, 0,
    ]
    encoded = base64.b64encode(json.dumps(fingerprint, separators=(',', ':')).encode()).decode('ascii')
    return {'p': 'gAAAAAC' + encoded, '_fingerprint': fingerprint}


def conversation_mode(project_id=None):
    if project_id:
        if not isinstance(project_id, str) or not re.fullmatch(r'g-p-[0-9a-f]{32}', project_id):
            raise ValueError('invalid_project')
        return {'kind': 'gizmo_interaction', 'gizmo_id': project_id}
    return {'kind': 'primary_assistant'}


def text_payloads(locator, text, project_id=None):
    common = {
        'action': 'next', 'parent_message_id': locator['parent_message_id'],
        'model': locator['requested_model'], 'timezone': 'Asia/Shanghai',
        'timezone_offset_min': -480, 'conversation_mode': conversation_mode(project_id),
        'supports_buffering': True, 'supported_encodings': ['v1'],
        'client_contextual_info': {'app_name': 'chatgpt.com'},
    }
    if locator.get('conversation_id'):
        common['conversation_id'] = locator['conversation_id']
    message = {'id': locator['user_message_id'], 'author': {'role': 'user'},
               'content': {'content_type': 'text', 'parts': [text]}}
    prepare = {**common, 'client_prepare_state': 'success', 'fork_from_shared_post': False,
               'partial_query': message}
    submit = {**common, 'client_prepare_state': 'sent', 'enable_message_followups': True,
              'messages': [{**message, 'create_time': time.time(),
                            'metadata': {'serialization_metadata': {'custom_symbol_offsets': []}}}]}
    return prepare, submit
