import json
import unittest
from unittest.mock import Mock, patch
from ccw.web_http import BridgeHttpClient


class Response:
    def __init__(self, body="", status=200, broken=False):
        self.content = body.encode()
        self.status_code = status
        self.broken = broken
    def iter_content(self, chunk_size):
        yield self.content
        if self.broken:
            raise RuntimeError("secret response")
    def close(self):
        pass


class Client:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


class ChunkResponse(Response):
    def __init__(self, chunks, broken=False):
        super().__init__(broken=broken)
        self.chunks, self.read_count, self.closed = chunks, 0, False
    def iter_content(self, chunk_size):
        for chunk in self.chunks:
            self.read_count += 1
            yield chunk
        if self.broken:
            raise RuntimeError("private failure")
    def close(self):
        self.closed = True


def conversation(model="chat-pro", current="a", finished=True):
    return {"current_node": current, "mapping": {
        "u": {"parent": "p", "message": {"id": "u", "author": {"role": "user"}}},
        "a": {"parent": "u", "message": {"id": "a", "author": {"role": "assistant"},
            "content": {"parts": ["review"]}, "metadata": {"model_slug": model},
            "status": "finished_successfully" if finished else "in_progress", "end_turn": finished}},
        "other": {"parent": None, "message": {"id": "other", "author": {"role": "assistant"}}}}}


class HttpTests(unittest.TestCase):
    def make(self, *responses):
        client = Client(*responses)
        bridge = BridgeHttpClient({"token": "secret-token", "model": "chat-pro"}, client)
        bridge.account_hash = "account"
        from ccw.http_protocol import text_payloads
        bridge._prepare_submission = lambda locator, text: (text_payloads(locator, text)[1], {}, None)
        self.client = client
        return bridge
    def locator(self):
        return dict(conversation_id="c", user_message_id="u", parent_message_id="p",
            requested_model="chat-pro", account_hash="account")
    def test_precise_completion(self):
        result = self.make(Response(json.dumps(conversation()))).recover(self.locator())
        self.assertTrue(result["complete"])
        self.assertTrue(result["acknowledged"])
        self.assertEqual(result["actual_model"], "chat-pro")
        self.assertEqual(self.client.calls[0][0], "GET")
    def test_wrong_branch(self):
        result = self.make(Response(json.dumps(conversation(current="other")))).observe(self.locator())
        self.assertFalse(result["complete"])
        self.assertFalse(result["acknowledged"])
    def test_later_user_turn_cannot_supply_evidence(self):
        data = conversation(finished=False)
        data["current_node"] = "assistant2"
        data["mapping"]["user2"] = {"parent": "a", "message": {"id": "user2", "author": {"role": "user"}}}
        data["mapping"]["tool2"] = {"parent": "user2", "message": {"id": "tool2", "author": {"role": "tool"},
            "metadata": {"tool_metadata": {"connector_id": "bridge", "tool_name": "read", "read_only": True}}}}
        data["mapping"]["assistant2"] = {"parent": "tool2", "message": {"id": "assistant2", "author": {"role": "assistant"},
            "content": {"parts": ["later review"]}, "metadata": {"model_slug": "chat-pro"},
            "status": "finished_successfully", "end_turn": True}}
        locator = dict(self.locator(), expected_connector="bridge", expected_tool="read")
        result = self.make(Response(json.dumps(data))).observe(locator)
        self.assertEqual(result["state"], "unknown")
        self.assertFalse(result["complete"])
        self.assertFalse(result["acknowledged"])
        self.assertEqual(result["text"], "")
        self.assertIsNone(result["actual_model"])
        self.assertEqual(result["tool_evidence"], [])
    def test_unknown_branch_role_is_rejected(self):
        data = conversation()
        data["mapping"]["a"]["parent"] = "unknown"
        data["mapping"]["unknown"] = {"parent": "u", "message": {"id": "unknown", "author": {"role": "unexpected"}}}
        result = self.make(Response(json.dumps(data))).observe(self.locator())
        self.assertEqual(result["error_code"], "assistant_branch_unverified")
        self.assertFalse(result["complete"])
    def test_model_mismatch(self):
        result = self.make(Response(json.dumps(conversation(model="other")))).observe(self.locator())
        self.assertFalse(result["complete"])
        self.assertEqual(result["actual_model"], "other")
    def test_done_not_completion(self):
        bridge = self.make(Response('data: {"conversation_id":"c"}\n\ndata: [DONE]\n\n'),
            Response(json.dumps(conversation(finished=False))))
        result = bridge.submit({"user_message_id": "u", "parent_message_id": "p", "text": "review"})
        self.assertFalse(result["complete"])
        self.assertEqual(result["state"], "partial")
        self.assertEqual([c[0] for c in self.client.calls], ["POST", "GET"])
    def test_broken_stream_no_retry(self):
        bridge = self.make(Response('data: {"conversation_id":"c"}\n\n', broken=True))
        result = bridge.submit({"conversation_id": "c", "user_message_id": "u", "parent_message_id": "p", "text": "review"})
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(result["locator"]["conversation_id"], "c")
        self.assertEqual(len(self.client.calls), 1)
        self.assertNotIn("secret", json.dumps(result))
    def test_cid_persisted_at_complete_event_before_disconnect(self):
        stream = ChunkResponse([b'data: {"conversation_', b'id":"c"}\r', b'\n\r', b'\n'], broken=True)
        bridge = self.make(stream)
        saved = []
        bridge.set_locator_callback(lambda locator: saved.append((dict(locator), stream.read_count)))
        result = bridge.submit({"user_message_id": "u", "parent_message_id": "p", "text": "review"})
        self.assertEqual(saved[0][0]["conversation_id"], "c")
        self.assertEqual(saved[0][1], 3)
        self.assertEqual(result["locator"]["conversation_id"], "c")
        self.assertEqual(result["error_code"], "transport_error")
        self.assertTrue(stream.closed)
        self.assertEqual([call[0] for call in self.client.calls], ["POST"])
    def test_incomplete_event_cannot_persist_cid(self):
        for broken in (True, False):
            bridge = self.make(ChunkResponse([b'data: {"conversation_id":"c"}\n'], broken=broken))
            saved = []
            bridge.set_locator_callback(saved.append)
            result = bridge.submit({"user_message_id": "u", "parent_message_id": "p", "text": "review"})
            self.assertEqual(saved, [])
            self.assertIsNone(result["locator"]["conversation_id"])
            self.assertFalse(result["complete"])
    def test_conflicting_cids_abort_without_observation(self):
        for original in (None, "original"):
            stream = ChunkResponse([b'data: {"conversation_id":"c"}\n\n', b'data: {"conversation_id":"other"}\n\n'])
            bridge = self.make(stream)
            saved = []
            bridge.set_locator_callback(saved.append)
            result = bridge.submit({"conversation_id": original, "user_message_id": "u", "parent_message_id": "p", "text": "review"})
            self.assertEqual(result["error_code"], "conversation_mismatch")
            self.assertFalse(result["complete"])
            self.assertEqual(len(saved), 1 if original is None else 0)
            self.assertEqual([call[0] for call in self.client.calls], ["POST"])
    def test_persistence_failure_stops_reading_and_closes_stream(self):
        stream = ChunkResponse([b'data: {"conversation_id":"c"}\n\n', b'data: [DONE]\n\n'])
        bridge = self.make(stream)
        def fail(locator):
            raise OSError("private identity and token")
        bridge.set_locator_callback(fail)
        result = bridge.submit({"user_message_id": "u", "parent_message_id": "p", "text": "review"})
        self.assertEqual(result["error_code"], "locator_persistence_failed")
        self.assertEqual(stream.read_count, 1)
        self.assertTrue(stream.closed)
        self.assertFalse(result["complete"])
        self.assertNotIn("private identity", json.dumps(result))
    def test_production_session_disables_retries(self):
        requests = Mock()
        requests.Session.return_value.request.return_value = Response('{}')
        with patch.dict("sys.modules", {"curl_cffi": Mock(requests=requests)}):
            BridgeHttpClient({"token": "token"})._request("GET", "/backend-api/me")
        requests.Session.assert_called_once_with(impersonate="chrome", retry=0)

    def test_proxy_config_is_applied_to_production_session(self):
        requests = Mock()
        session = requests.Session.return_value
        session.request.return_value = Response('{}')
        with patch.dict("sys.modules", {"curl_cffi": Mock(requests=requests)}):
            BridgeHttpClient({"token": "token", "proxy": "http://127.0.0.1:7897"})._request("GET", "/backend-api/me")
        self.assertEqual(session.proxies, {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"})
    def test_redirect_and_auth_never_leak(self):
        for status, expected in [(302, "redirect_rejected"), (401, "authentication_or_challenge_required"), (403, "authentication_or_challenge_required")]:
            bridge = self.make(Response("secret-token", status))
            result = bridge.observe(self.locator())
            self.assertEqual(result["error_code"], expected)
            self.assertNotIn("secret-token", json.dumps(result))
            self.assertFalse(self.client.calls[0][2]["allow_redirects"])
            self.assertTrue(self.client.calls[0][1].startswith("https://chatgpt.com/"))
    def test_multiline_sse_and_patch(self):
        self.assertEqual(BridgeHttpClient.parse_sse('data: {\n data ignored\ndata: "conversation_id": "c"}\n\n')[0]["conversation_id"], "c")
        with self.assertRaises(ValueError):
            BridgeHttpClient.parse_sse('data: {"op":"replace","value":"complete"}\n\n')
    def test_project_unsupported_without_request(self):
        bridge = self.make()
        result = bridge.submit({"project_id": "project", "text": "review"})
        self.assertEqual(result["state"], "unsupported")
        self.assertEqual(self.client.calls, [])
    def test_probe_identity_not_token(self):
        client = Client(Response(json.dumps({"id": "actual-account", "email": "ignored@example.test"})),
            Response(json.dumps({"models": [{"slug": "gpt-5-2-pro"}]})))
        bridge = BridgeHttpClient({"token": "secret-token", "model": "gpt-5-2-pro"}, client)
        result = bridge.probe()
        self.assertTrue(result["identity_verified"])
        import hashlib
        self.assertEqual(result["account_hash"], hashlib.sha256(b"actual-account").hexdigest())
        self.assertNotIn("secret-token", json.dumps(result))
        self.assertTrue(client.calls[0][1].endswith("/backend-api/me"))
        self.assertTrue(result["model_verified"])
    def test_identity_missing_or_mismatch(self):
        for body, config in [({"email": "ignored"}, {}), ({"id": "other-account"}, {"account_hash": "expected"})]:
            client = Client(Response(json.dumps(body)))
            bridge = BridgeHttpClient(dict(token="secret-token", model="gpt-5-2-pro", **config), client)
            bridge.account_hash = "old-account"
            result = bridge.probe()
            self.assertFalse(result["identity_verified"])
            self.assertIsNone(bridge.account_hash)
            self.assertEqual(len(client.calls), 1)
    def test_real_model_slug_submit(self):
        bridge = self.make(Response('data: {"conversation_id":"c"}\n\n'),
            Response(json.dumps(conversation(model="gpt-5-2-pro"))))
        bridge.config["model"] = "gpt-5-2-pro"
        result = bridge.submit({"user_message_id": "u", "parent_message_id": "p", "text": "review"})
        self.assertTrue(result["complete"])
        self.assertEqual(self.client.calls[0][2]["json"]["model"], "gpt-5-2-pro")
    def test_recover_missing_cid_exact_identity(self):
        bridge = self.make(Response(json.dumps({"items": [{"id": "other"}, {"id": "found"}]})),
            Response(json.dumps({"mapping": {}})), Response(json.dumps(conversation())))
        locator = self.locator()
        locator["conversation_id"] = None
        result = bridge.recover(locator)
        self.assertTrue(result["complete"])
        self.assertEqual(result["locator"]["conversation_id"], "found")
        self.assertEqual([c[0] for c in self.client.calls], ["GET", "GET", "GET"])
    def test_recovery_no_match_remains_unknown(self):
        data = conversation()
        data["mapping"]["u"]["parent"] = "different-parent"
        bridge = self.make(Response(json.dumps({"items": [{"id": "candidate"}]})), Response(json.dumps(data)))
        result = bridge.recover(dict(self.locator(), conversation_id=None))
        self.assertEqual(result["state"], "unknown")
        self.assertFalse(result["acknowledged"])
        self.assertEqual(result["error_code"], "conversation_not_located")
    def test_recovery_ambiguous_remains_unknown(self):
        bridge = self.make(Response(json.dumps({"items": [{"id": "one"}, {"id": "two"}]})),
            Response(json.dumps(conversation())), Response(json.dumps(conversation())))
        result = bridge.recover(dict(self.locator(), conversation_id=None))
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(result["error_code"], "conversation_identity_ambiguous")
    def test_recovery_candidate_limit(self):
        listing = {"items": [{"id": str(i)} for i in range(25)]}
        bridge = self.make(Response(json.dumps(listing)), *[Response('{"mapping": {}}') for _ in range(20)])
        result = bridge.recover(dict(self.locator(), conversation_id=None))
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(len(self.client.calls), 21)
    def test_recovery_shared_size_limit(self):
        listing = json.dumps({"items": [{"id": "one"}]})
        bridge = self.make(Response(listing), Response(json.dumps(conversation())))
        bridge.config["max_response_bytes"] = len(listing.encode()) + 10
        result = bridge.recover(dict(self.locator(), conversation_id=None))
        self.assertEqual(result["error_code"], "response_too_large")
    def test_mcp_requires_server_metadata(self):
        data = conversation()
        data["mapping"]["a"]["parent"] = "tool"
        data["mapping"]["tool"] = {"parent": "u", "message": {"id": "tool", "author": {"role": "tool"},
            "metadata": {"tool_metadata": {"connector_id": "bridge", "tool_name": "read", "read_only": True}}}}
        locator = dict(self.locator(), expected_connector="bridge", expected_tool="read")
        result = self.make(Response(json.dumps(data))).observe(locator)
        self.assertEqual(result["tool_evidence"][0]["source"], "http-server")
        data["mapping"]["tool"]["message"]["metadata"] = {}
        result = self.make(Response(json.dumps(data))).observe(locator)
        self.assertEqual(result["tool_evidence"], [])
    def test_missing_terminal_evidence(self):
        data = conversation()
        del data["mapping"]["a"]["message"]["end_turn"]
        self.assertFalse(self.make(Response(json.dumps(data))).observe(self.locator())["complete"])
    def test_size_limit(self):
        bridge = self.make(Response("1234"))
        bridge.config["max_response_bytes"] = 2
        self.assertEqual(bridge.observe(self.locator())["error_code"], "response_too_large")


if __name__ == "__main__":
    unittest.main()
