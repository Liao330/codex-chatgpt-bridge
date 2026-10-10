"""Independent, conservative ChatGPT text transport. No POST retries.

Config and private locators must not be logged. Results never contain raw HTTP
responses. An injected client implements request(method, url, **kwargs), with
response.status_code, headers, iter_content() and/or content.
"""
import codecs
import hashlib
import json
import time
import uuid
from urllib.parse import quote
from .http_protocol import USER_AGENT, text_payloads, requirements_payload
from .http_pow import proof_from_requirements
from .http_turnstile import solve_turnstile_token


class _StreamError(Exception):
    pass


class _SSEParser:
    """Dispatch only blank-line-terminated events, even across byte chunks."""
    def __init__(self, callback):
        self.callback = callback
        self.decoder = codecs.getincrementaldecoder("utf-8")()
        self.line, self.data, self.after_cr = "", [], False

    def feed(self, chunk, final=False):
        for char in self.decoder.decode(chunk, final=final):
            if self.after_cr and char == "\n":
                self.after_cr = False
                continue
            self.after_cr = char == "\r"
            if char in "\r\n":
                line, self.line = self.line, ""
                if not line and self.data:
                    body, self.data = "\n".join(self.data), []
                    if body != "[DONE]":
                        events = BridgeHttpClient.parse_sse("data: " + body.replace("\n", "\ndata: ") + "\n\n")
                        for event in events:
                            self.callback(event)
                elif line.startswith("data:"):
                    self.data.append(line[5:].lstrip(" "))
            else:
                self.line += char
        if final and (self.data or self.line.startswith("data:")):
            raise ValueError("incomplete_event")


class BridgeHttpClient:
    HOST = "https://chatgpt.com"

    def __init__(self, config, client=None):
        self.config = dict(config)
        self.client = client
        self.account_hash = None
        self._deadline = None
        self._bytes_left = None
        self._locator_callback = None
        self._device_id = str(uuid.uuid4())
        self._session_id = str(uuid.uuid4())

    def set_locator_callback(self, callback):
        self._locator_callback = callback

    def _result(self, state="unknown", **fields):
        result = dict(state=state, acknowledged=False, complete=False, text="",
                      actual_model=None, account_hash=self.account_hash,
                      identity_verified=bool(self.account_hash), tool_evidence=[],
                      terminal_evidence=None, route_evidence=None, locator=None,
                      error_code=None)
        result.update(fields)
        return result

    def _request(self, method, path, payload=None, event_callback=None, *, extra_headers=None):
        token = self.config.get("access_token") or self.config.get("token")
        if not isinstance(token, str) or not token or "\r" in token or "\n" in token:
            return None, "authentication_required"
        if not path.startswith("/") or path.startswith("//"):
            return None, "invalid_endpoint"
        if self.client is None:
            try:
                from curl_cffi import requests
                self.client = requests.Session(impersonate="chrome", retry=0)
                proxy = self.config.get("proxy")
                if proxy:
                    self.client.proxies = {"http": proxy, "https": proxy}
            except ImportError:
                return None, "http_client_unavailable"
        try:
            timeout = min(max(float(self.config.get("timeout_seconds", 60)), 1), 300)
            if self._deadline is not None:
                timeout = min(timeout, self._deadline - time.monotonic())
                if timeout <= 0:
                    return None, "response_deadline"
            headers = {"Authorization": "Bearer " + token, "User-Agent": USER_AGENT,
                       "Origin": self.HOST, "Referer": self.HOST + "/",
                       "OAI-Device-Id": self._device_id, "OAI-Session-Id": self._session_id,
                       "OAI-Language": "zh-CN", "X-OpenAI-Target-Path": path,
                       "X-OpenAI-Target-Route": path, "Content-Type": "application/json",
                       "Accept": "text/event-stream" if event_callback else "application/json"}
            headers.update(extra_headers or {})
            response = self.client.request(method, self.HOST + path, headers=headers,
                json=payload, allow_redirects=False,
                timeout=timeout, stream=True)
            status = response.status_code
            if 300 <= status < 400:
                return None, "redirect_rejected"
            if status in (401, 403):
                return None, "authentication_or_challenge_required"
            if status != 200:
                return None, "http_status_" + str(status)
            deadline = time.monotonic() + timeout
            if self._deadline is not None:
                deadline = min(deadline, self._deadline)
            limit = min(max(int(self.config.get("max_response_bytes", 2_000_000)), 1), 8_000_000)
            chunks, size = [], 0
            parser = _SSEParser(event_callback) if event_callback else None
            iterator = response.iter_content(chunk_size=8192) if hasattr(response, "iter_content") else [response.content]
            for chunk in iterator:
                if time.monotonic() > deadline:
                    return None, "response_deadline"
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8")
                size += len(chunk)
                if self._bytes_left is not None:
                    self._bytes_left -= len(chunk)
                    if self._bytes_left < 0:
                        return None, "response_too_large"
                if size > limit:
                    return None, "response_too_large"
                if parser:
                    parser.feed(chunk)
                else:
                    chunks.append(chunk)
            if parser:
                parser.feed(b"", final=True)
            return b"".join(chunks).decode("utf-8"), None
        except _StreamError as error:
            return None, str(error)
        except (ValueError, UnicodeError):
            return None, "unsupported_or_invalid_sse" if event_callback else "transport_error"
        except Exception:
            return None, "transport_error"
        finally:
            if "response" in locals() and hasattr(response, "close"):
                try:
                    response.close()
                except Exception:
                    pass

    def probe(self):
        self.account_hash = None
        raw, error = self._request("GET", "/backend-api/me")
        if error:
            return self._result(error_code=error, models=[])
        try:
            session = json.loads(raw)
            # An actual server account identity, never a token fingerprint.
            user = session.get("user", session)
            identity = user.get("id")
            if not isinstance(identity, str) or not identity:
                return self._result(error_code="identity_unverified", models=[])
            self.account_hash = hashlib.sha256(identity.encode()).hexdigest()
            expected = self.config.get("account_hash")
            if expected and expected != self.account_hash:
                self.account_hash = None
                return self._result(error_code="account_mismatch", models=[])
            raw, error = self._request("GET", "/backend-api/models")
            if error:
                return self._result(error_code=error, models=[])
            data = json.loads(raw)
            models = [m.get("slug") for m in data.get("models", []) if isinstance(m, dict) and isinstance(m.get("slug"), str)]
            model = self.config.get("model")
            return self._result(state="ready" if model in models else "unsupported",
                models=models, model_verified=model in models,
                error_code=None if model in models else "model_unavailable")
        except (ValueError, TypeError, AttributeError):
            return self._result(error_code="invalid_probe_response", models=[])

    @staticmethod
    def parse_sse(raw):
        """Return complete JSON events. DONE is transport metadata, not completion.

        Patch events are deliberately unsupported until a captured protocol defines
        their exact semantics; applying guessed patches could fabricate evidence.
        """
        events, data = [], []
        for line in raw.replace("\r\n", "\n").split("\n") + [""]:
            if line == "":
                if data:
                    body = "\n".join(data)
                    data = []
                    if body == "[DONE]":
                        continue
                    item = json.loads(body)
                    if item == "v1":
                        continue
                    if not isinstance(item, dict):
                        raise ValueError("invalid_event")
                    if any(k in item for k in ("patch", "patches", "op")) or item.get("type") in ("patch", "delta"):
                        raise ValueError("unsupported_patch")
                    events.append(item)
            elif line.startswith("data:"):
                data.append(line[5:].lstrip(" "))
        return events

    def _prepare_submission(self, locator, text):
        html, error = self._request("GET", "/")
        if error:
            return None, None, error
        requirements_request = requirements_payload(html)
        fingerprint = requirements_request.pop('_fingerprint')
        p_token = requirements_request['p']
        raw, error = self._request("POST", "/backend-api/sentinel/chat-requirements/prepare",
                                   requirements_request)
        if error:
            return None, None, error
        try:
            requirements = json.loads(raw)
            if not isinstance(requirements, dict):
                raise ValueError()
            for key in ("arkose", "turnstile", "proofofwork"):
                if key in requirements and (not isinstance(requirements[key], dict)
                                           or not isinstance(requirements[key].get("required"), bool)):
                    return None, None, "preparation_response_invalid"
            # Arkose is an interactive challenge this transport cannot evaluate.
            if (requirements.get("arkose") or {}).get("required") is True:
                return None, None, "challenge_required"
            turnstile_token = ""
            if (requirements.get("turnstile") or {}).get("required") is True:
                dx = requirements["turnstile"].get("dx")
                turnstile_token = solve_turnstile_token(dx, p_token) or ""
                if not turnstile_token:
                    return None, None, "challenge_required"
            try:
                proof_token = proof_from_requirements(requirements, fingerprint)
            except RuntimeError:
                return None, None, "challenge_required"
            prepared_token = requirements.get("prepare_token")
            if not isinstance(prepared_token, str) or not prepared_token:
                return None, None, "requirements_invalid"
            raw, error = self._request("POST", "/backend-api/sentinel/chat-requirements/finalize",
                                      {"prepare_token": prepared_token, "proof_token": proof_token, "turnstile_token": turnstile_token})
            if error:
                return None, None, error
            token = json.loads(raw).get("token")
            if not isinstance(token, str) or not token:
                return None, None, "requirements_invalid"
            headers = {"OpenAI-Sentinel-Chat-Requirements-Token": token}
            if proof_token:
                headers["OpenAI-Sentinel-Proof-Token"] = proof_token
            # Try the requested model, then the configured fallback when the
            # server refuses it (for example a Pro model on a non-Pro account).
            candidates = [locator["requested_model"]]
            fallback = self.config.get("fallback_model")
            if fallback and fallback != locator["requested_model"]:
                candidates.append(fallback)
            conduit = None
            prepare = payload = None
            for model in candidates:
                locator["requested_model"] = model
                prepare, payload = text_payloads(locator, text, self.config.get("project_id"))
                raw, error = self._request("POST", "/backend-api/f/conversation/prepare", prepare,
                                           extra_headers=headers)
                if error:
                    return None, None, error
                conduit = json.loads(raw).get("conduit_token")
                if isinstance(conduit, str) and conduit:
                    break
                conduit = None
            if not isinstance(conduit, str) or not conduit:
                return None, None, "conversation_prepare_failed"
            headers.update({"X-Conduit-Token": conduit, "X-Oai-Turn-Trace-Id": str(uuid.uuid4())})
            return payload, headers, None
        except (ValueError, TypeError, AttributeError):
            return None, None, "preparation_response_invalid"

    def submit(self, intent, prompt=None):
        intent = dict(intent)
        text = prompt if prompt is not None else intent.get("text")
        project = intent.get("project_id") or self.config.get("project_id")
        from .http_protocol import conversation_mode
        try:
            conversation_mode(project)
        except ValueError:
            return self._result(state="unsupported", error_code="project_context_protocol_unverified")
        if self.config.get("context") or intent.get("context"):
            return self._result(state="unsupported", error_code="project_context_protocol_unverified")
        if not self.account_hash:
            return self._result(error_code="identity_unverified")
        uid, parent = intent.get("user_message_id"), intent.get("parent_message_id")
        model = intent.get("model") or intent.get("requested_model") or self.config.get("model")
        if not all(isinstance(v, str) and v for v in (uid, parent, model, text)):
            return self._result(error_code="invalid_intent")
        locator = dict(conversation_id=intent.get("conversation_id"), user_message_id=uid,
            parent_message_id=parent, requested_model=model, account_hash=self.account_hash,
            expected_connector=intent.get("expected_connector") or self.config.get("expected_connector"),
            expected_tool=intent.get("expected_tool") or self.config.get("expected_tool"))
        if project != self.config.get("project_id"):
            return self._result(state="unsupported", error_code="project_context_protocol_unverified")
        payload, headers, error = self._prepare_submission(locator, text)
        if error:
            return self._result(error_code=error, locator=locator)
        def on_event(event):
            nested = event.get("v")
            cid = event.get("conversation_id") or (nested.get("conversation_id") if isinstance(nested, dict) else None)
            if cid is None:
                return
            if not isinstance(cid, str) or not cid:
                raise _StreamError("conversation_unverified")
            if locator["conversation_id"] and locator["conversation_id"] != cid:
                raise _StreamError("conversation_mismatch")
            if locator["conversation_id"] != cid:
                updated = dict(locator, conversation_id=cid)
                if self._locator_callback:
                    try:
                        self._locator_callback(updated)
                    except Exception:
                        raise _StreamError("locator_persistence_failed") from None
                locator.update(updated)

        raw, error = self._request("POST", "/backend-api/f/conversation", payload, on_event,
                                   extra_headers=headers)
        if error:
            return self._result(error_code=error, locator=locator)
        try:
            if not locator["conversation_id"]:
                return self._result(error_code="conversation_unverified", locator=locator)
            # Only the persisted exact branch can establish acknowledgment/completion.
            return self.observe(locator)
        except (ValueError, TypeError):
            return self._result(error_code="unsupported_or_invalid_sse", locator=locator)

    def observe(self, locator):
        locator = dict(locator)
        if not self.account_hash or locator.get("account_hash") != self.account_hash:
            return self._result(error_code="account_unverified", locator=locator)
        cid = locator.get("conversation_id")
        if not isinstance(cid, str) or not cid:
            return self._result(error_code="conversation_unverified", locator=locator)
        raw, error = self._request("GET", "/backend-api/conversation/" + quote(cid, safe=""))
        if error:
            return self._result(error_code=error, locator=locator)
        try:
            return self._observe_data(json.loads(raw), locator)
        except (ValueError, TypeError, KeyError, AttributeError):
            return self._result(error_code="invalid_conversation_response", locator=locator)

    def _observe_data(self, data, locator):
        if self.config.get("project_id") and data.get("gizmo_id") != self.config["project_id"]:
            return self._result(error_code="project_membership_mismatch", locator=locator)
        mapping = data.get("mapping", {})
        uid = locator["user_message_id"]
        node = mapping.get(uid, {})
        message = node.get("message") or {}
        if (message.get("id") != uid or message.get("author", {}).get("role") != "user"
                or node.get("parent") != locator["parent_message_id"]):
            return self._result(error_code="user_branch_unverified", locator=locator)
        # Follow only the server's current branch, never the most recent text.
        current = data.get("current_node")
        branch, seen = [], set()
        while current and current != uid:
            if current in seen or current not in mapping:
                return self._result(error_code="assistant_branch_unverified", locator=locator)
            seen.add(current)
            candidate = mapping[current]
            role = (candidate.get("message") or {}).get("author", {}).get("role")
            # A descendant user starts another turn. Its assistant/model/tool
            # evidence cannot establish anything about this original request.
            if role not in ("assistant", "tool", "system"):
                return self._result(error_code="assistant_branch_unverified", locator=locator)
            branch.append(candidate)
            current = mapping[current].get("parent")
        if current != uid:
            return self._result(error_code="assistant_branch_unverified", locator=locator)
        assistants = [n.get("message") for n in reversed(branch) if (n.get("message") or {}).get("author", {}).get("role") == "assistant"]
        if not assistants:
            return self._result(acknowledged=True, locator=locator, state="partial")
        final = assistants[-1]
        meta = final.get("metadata") or {}
        actual = meta.get("model_slug")
        evidence = []
        for item in branch:
            msg = item.get("message") or {}
            tool = (msg.get("metadata") or {}).get("tool_metadata")
            if (msg.get("author", {}).get("role") == "tool" and isinstance(tool, dict)
                    and locator.get("expected_connector") and locator.get("expected_tool")
                    and tool.get("connector_id") == locator["expected_connector"]
                    and tool.get("tool_name") == locator["expected_tool"]
                    and tool.get("read_only") is True):
                evidence.append(dict(source="http-server", connector=tool["connector_id"],
                    tool=tool["tool_name"], read_only=True,
                    message_id=msg.get("id"), provenance="conversation_mapping_tool_metadata"))
        parts = final.get("content", {}).get("parts", [])
        text = "\n".join(p for p in parts if isinstance(p, str))
        terminal = final.get("status") == "finished_successfully" and final.get("end_turn") is True
        model_ok = actual == locator["requested_model"]
        complete = terminal and model_ok and bool(text)
        return self._result(state="complete" if complete else "partial", acknowledged=True,
            complete=complete, text=text, actual_model=actual, locator=locator, tool_evidence=evidence,
            terminal_evidence={"message_id": final.get("id"), "status": final.get("status"), "end_turn": final.get("end_turn")},
            route_evidence={"requested_model": locator["requested_model"], "actual_model": actual, "provenance": "conversation_mapping_metadata"},
            error_code=None if model_ok else "model_unverified_or_mismatch")

    def recover(self, locator):
        locator = dict(locator)
        self._deadline = time.monotonic() + min(max(float(self.config.get("timeout_seconds", 60)), 1), 300)
        self._bytes_left = min(max(int(self.config.get("max_response_bytes", 2_000_000)), 1), 8_000_000)
        try:
            if locator.get("conversation_id"):
                return self.observe(locator)
            if not self.account_hash or locator.get("account_hash") != self.account_hash:
                return self._result(error_code="account_unverified", locator=locator)
            if not all(isinstance(locator.get(k), str) and locator[k] for k in ("user_message_id", "parent_message_id", "requested_model")):
                return self._result(error_code="invalid_locator", locator=locator)
            raw, error = self._request("GET", "/backend-api/conversations?offset=0&limit=20&order=updated")
            if error:
                return self._result(error_code=error, locator=locator)
            listing = json.loads(raw)
            items = listing.get("items")
            if not isinstance(items, list):
                return self._result(error_code="unsupported_conversation_listing", locator=locator)
            matches, ids = [], set()
            for item in items[:20]:
                if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
                    return self._result(error_code="unsupported_conversation_listing", locator=locator)
                cid = item["id"]
                if cid in ids:
                    continue
                ids.add(cid)
                raw, error = self._request("GET", "/backend-api/conversation/" + quote(cid, safe=""))
                if error:
                    return self._result(error_code=error, locator=locator)
                data = json.loads(raw)
                node = data.get("mapping", {}).get(locator["user_message_id"], {})
                message = node.get("message") or {}
                if (message.get("id") == locator["user_message_id"]
                        and message.get("author", {}).get("role") == "user"
                        and node.get("parent") == locator["parent_message_id"]):
                    matches.append((cid, data))
            if len(matches) != 1:
                return self._result(error_code="conversation_identity_ambiguous" if matches else "conversation_not_located", locator=locator)
            cid, data = matches[0]
            locator["conversation_id"] = cid
            return self._observe_data(data, locator)
        except (ValueError, TypeError, KeyError, AttributeError):
            return self._result(error_code="invalid_recovery_response", locator=locator)
        finally:
            self._deadline = None
            self._bytes_left = None


WebHttpClient = BridgeHttpClient
