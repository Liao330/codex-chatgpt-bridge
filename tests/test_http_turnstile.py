import base64
import json
import unittest

from ccw.http_turnstile import solve_turnstile_token, _xor_mask


def make_dx(program, p):
    encoded = json.dumps(program)
    masked = _xor_mask(encoded, p)
    return base64.b64encode(masked.encode()).decode()


class TurnstileTests(unittest.TestCase):
    def test_simple_program_emits_base64(self):
        p = "gAAAAABtest-key"
        dx = make_dx([[3, "hi"]], p)
        self.assertEqual(solve_turnstile_token(dx, p), "aGk=")

    def test_op2_and_op3_sequence(self):
        p = "key"
        # op2 stores a literal, op3 base64-encodes a literal.
        dx = make_dx([[2, 5, "ignored"], [3, "result"]], p)
        self.assertEqual(solve_turnstile_token(dx, p), base64.b64encode(b"result").decode())

    def test_invalid_input_returns_none(self):
        self.assertIsNone(solve_turnstile_token("", "p"))
        self.assertIsNone(solve_turnstile_token("not-base64!!", "p"))
        self.assertIsNone(solve_turnstile_token(make_dx([[3, "hi"]], "k"), None))

    def test_xor_mask_roundtrip(self):
        self.assertEqual(_xor_mask(_xor_mask("hello world", "key"), "key"), "hello world")
        self.assertEqual(_xor_mask("text", ""), "text")


if __name__ == "__main__":
    unittest.main()
