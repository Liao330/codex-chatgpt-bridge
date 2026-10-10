"""Independent Turnstile challenge evaluation for the HTTP text transport.

The sentinel ``/chat-requirements/prepare`` endpoint returns a Turnstile
challenge whose ``dx`` field is a challenge program: base64-encoded, XOR-masked
with the same fingerprint token ``p`` sent to prepare, then a JSON array of
``[opcode, ...args]`` instructions. We decode it and evaluate the instructions
in a bounded register machine to produce the Turnstile token that finalize
expects. The instruction set is the observed wire protocol; the code here is an
independent interpreter that never imports another project.

Opcodes and data share one symbol table, because an instruction can hand the
whole table (functions included) back to the program. The machine is bounded by
a step limit, and any instruction failure aborts that instruction only. On any
decode or evaluation failure the solver returns ``None`` so the caller can stop
before finalize.
"""
from __future__ import annotations

import base64
import json
import random
import time

_JS_STRINGS = {
    "window.Math": "[object Math]",
    "window.Reflect": "[object Reflect]",
    "window.performance": "[object Performance]",
    "window.localStorage": "[object Storage]",
    "window.Object": "function Object() { [native code] }",
    "window.Reflect.set": "function set() { [native code] }",
    "window.performance.now": "function () { [native code] }",
    "window.Object.create": "function create() { [native code] }",
    "window.Object.keys": "function keys() { [native code] }",
    "window.Math.random": "function random() { [native code] }",
}

_LOCAL_STORAGE_KEYS = [
    "STATSIG_LOCAL_STORAGE_INTERNAL_STORE_V4",
    "STATSIG_LOCAL_STORAGE_STABLE_ID",
    "client-correlated-secret",
    "oai/apps/capExpiresAt",
    "oai-did",
    "STATSIG_LOCAL_STORAGE_LOGGING_REQUEST",
    "UiState.isNavigationCollapsed.1",
]


def _xor_mask(text, key):
    if not key:
        return text
    return "".join(chr(ord(ch) ^ ord(key[i % len(key)])) for i, ch in enumerate(text))


def _js_string(value):
    if value is None:
        return "undefined"
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        return _JS_STRINGS.get(value, value)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return ",".join(value)
    return str(value)


class _OrderedStore:
    """Insertion-ordered map with overwrite semantics (a JS object stand-in)."""

    def __init__(self):
        self._keys = []
        self._values = {}

    def add(self, key, value):
        if key not in self._values:
            self._keys.append(key)
        self._values[key] = value

    def keys(self):
        return list(self._keys)


class _TurnstileMachine:
    def __init__(self, dx, p):
        decoded = base64.b64decode(dx).decode()
        self.program = json.loads(_xor_mask(decoded, p))
        self.result = ""
        self.started = time.time()
        self.memory = {
            1: self._op1, 2: self._op2, 3: self._op3, 5: self._op5, 6: self._op6,
            7: self._op7, 8: self._op8, 11: self._op11, 12: self._op12, 13: self._op13,
            14: self._op14, 15: self._op15, 17: self._op17, 18: self._op18, 19: self._op19,
            20: self._op20, 21: self._op21, 22: self._op22, 23: self._op23, 24: self._op24,
            25: self._noop, 26: self._noop, 27: self._op27, 28: self._noop, 29: self._op29,
            30: self._op30, 33: self._op33, 34: self._op34,
            9: self.program, 10: "window", 16: p,
        }

    def get(self, key, default=None):
        return self.memory.get(key, default)

    def set(self, key, value):
        self.memory[key] = value

    def _prop(self, obj, key):
        if isinstance(obj, _OrderedStore):
            return obj._values.get(str(key))
        if isinstance(obj, dict):
            return obj.get(key)
        if isinstance(obj, (list, tuple)):
            try:
                return obj[int(key)]
            except Exception:
                return None
        if isinstance(obj, str):
            text = _js_string(key)
            if text == "location" and obj == "window.document":
                return "https://chatgpt.com/"
            if text and text not in {"undefined", "None"}:
                return f"{obj}.{text}"
        return None

    def _call(self, target, args):
        if isinstance(target, str):
            if target == "window.performance.now":
                elapsed_ns = time.time_ns() - int(self.started * 1e9)
                return (elapsed_ns + random.random()) / 1e6
            if target == "window.Object.create":
                return _OrderedStore()
            if target == "window.Object.keys":
                if args and args[0] == "window.localStorage":
                    return list(_LOCAL_STORAGE_KEYS)
                if args and isinstance(args[0], _OrderedStore):
                    return args[0].keys()
                if args and isinstance(args[0], dict):
                    return list(args[0].keys())
            if target == "window.Math.random":
                return random.random()
            if target == "window.Reflect.set":
                if len(args) >= 3:
                    obj, key, value = args[:3]
                    if isinstance(obj, _OrderedStore):
                        obj.add(str(key), value)
                        return True
                    if isinstance(obj, dict):
                        obj[str(key)] = value
                        return True
                return False
        if callable(target):
            return target(*args)
        return None

    def _run_queue(self, limit=20000):
        steps = 0
        while isinstance(self.memory.get(9), list) and self.memory[9]:
            steps += 1
            if steps > limit:
                raise RuntimeError("turnstile_vm_step_limit")
            token = self.memory[9].pop(0)
            if not isinstance(token, list) or not token:
                continue
            handler = self.memory.get(token[0])
            if not callable(handler):
                continue
            try:
                handler(*token[1:])
            except Exception:
                continue

    # -- opcodes -------------------------------------------------------------
    def _op1(self, e, t):
        self.set(e, _xor_mask(_js_string(self.get(e)), _js_string(self.get(t))))

    def _op2(self, e, t):
        self.set(e, t)

    def _op3(self, e):
        self.result = base64.b64encode(e.encode()).decode()

    def _op5(self, e, t):
        current = self.get(e)
        incoming = self.get(t)
        if isinstance(current, (list, tuple)):
            self.set(e, list(current) + [incoming])
            return
        if isinstance(current, (str, float)) or isinstance(incoming, (str, float)):
            self.set(e, _js_string(current) + _js_string(incoming))
            return
        self.set(e, "NaN")

    def _op6(self, e, t, n):
        self.set(e, self._prop(self.get(t), self.get(n)))

    def _op7(self, e, *args):
        self._call(self.get(e), [self.get(arg) for arg in args])

    def _op8(self, e, t):
        self.set(e, self.memory[t])

    def _op11(self, e, t):
        self.set(e, None)

    def _op12(self, e):
        self.set(e, self.memory)

    def _op13(self, e, t, *args):
        try:
            self._call(self.get(t), list(args))
        except Exception as exc:
            self.set(e, str(exc))

    def _op14(self, e, t):
        self.set(e, json.loads(self.memory[t]))

    def _op15(self, e, t):
        self.set(e, json.dumps(self.memory[t]))

    def _op17(self, e, t, *args):
        self.set(e, self._call(self.get(t), [self.get(arg) for arg in args]))

    def _op18(self, e):
        self.set(e, base64.b64decode(_js_string(self.memory[e])).decode())

    def _op19(self, e):
        self.set(e, base64.b64encode(_js_string(self.memory[e]).encode()).decode())

    def _op20(self, e, t, n, *args):
        if self.get(e) == self.get(t):
            target = self.get(n)
            if callable(target):
                target(*args)

    def _op21(self, e, t, n, r, *args):
        try:
            delta = float(self.get(e)) - float(self.get(t))
        except Exception:
            delta = 0.0
        if abs(delta) > self._abs(self.get(n)):
            target = self.get(r)
            if callable(target):
                target(*args)

    def _abs(self, value):
        try:
            return abs(float(value))
        except Exception:
            return 0.0

    def _op22(self, e, queue):
        previous = list(self.memory.get(9) or [])
        self.memory[9] = list(queue or [])
        self._run_queue()
        self.set(e, "None")
        self.memory[9] = previous

    def _op23(self, e, t, *args):
        if self.get(e) is not None and callable(self.get(t)):
            self.memory[t](*args)

    def _op24(self, e, t, n):
        self.set(e, self._prop(self.get(t), self.get(n)))

    def _op27(self, e, t):
        current = self.get(e)
        incoming = self.get(t)
        if isinstance(current, list):
            try:
                current.pop(current.index(incoming))
            except ValueError:
                pass
            return
        try:
            self.set(e, current - incoming)
        except Exception:
            self.set(e, 0)

    def _op29(self, e, t, n):
        try:
            self.set(e, self.get(t) < self.get(n))
        except Exception:
            self.set(e, False)

    def _op30(self, e, t, n, r=None):
        is_array = isinstance(r, list)
        capture_keys = n if is_array else []
        queue = list((r if is_array else n) or [])

        def subroutine(*call_args):
            previous = list(self.memory.get(9) or [])
            if is_array:
                for index, key in enumerate(capture_keys):
                    if index < len(call_args):
                        self.memory[key] = call_args[index]
            self.memory[9] = list(queue)
            self._run_queue()
            self.memory[9] = previous

        self.set(e, subroutine)

    def _op33(self, e, t, n):
        try:
            self.set(e, float(self.get(t)) * float(self.get(n)))
        except Exception:
            self.set(e, 0)

    def _op34(self, e, t):
        self.set(e, self.get(t))

    def _noop(self, *args):
        return None

    def run(self):
        self._run_queue()
        return self.result or None


def solve_turnstile_token(dx, p):
    """Return the Turnstile token for a challenge, or None if it cannot be solved."""
    if not isinstance(dx, str) or not dx or not isinstance(p, str) or not p:
        return None
    try:
        return _TurnstileMachine(dx, p).run()
    except Exception:
        return None
