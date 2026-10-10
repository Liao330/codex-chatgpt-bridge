import base64
import hashlib
import json
import unittest

from ccw.http_pow import solve, proof_from_requirements


class ProofTests(unittest.TestCase):
    def test_proof_satisfies_server_difficulty_and_preserves_fingerprint(self):
        original = list(range(25))
        token = solve('seed', '0f', original)
        encoded = token[len('gAAAAAB'):].encode()
        self.assertLessEqual(hashlib.sha3_512(b'seed' + encoded).digest()[:1], b'\x0f')
        payload = json.loads(base64.b64decode(encoded))
        self.assertEqual(payload[:3], original[:3])
        self.assertEqual(payload[4:9], original[4:9])
        self.assertEqual(payload[10:], original[10:])
        self.assertEqual(original, list(range(25)))

    def test_invalid_parameters_and_bounded_exhaustion(self):
        for difficulty in ('', 'xyz', 'f', '00' * 65):
            with self.assertRaises(ValueError):
                solve('seed', difficulty, list(range(25)))
        with self.assertRaises(RuntimeError):
            solve('seed', '00' * 64, list(range(25)), limit=1)

    def test_proof_from_requirements_only_when_required(self):
        self.assertEqual(proof_from_requirements({}, list(range(25))), '')
        self.assertEqual(proof_from_requirements({'proofofwork': {'required': False}}, list(range(25))), '')
        token = proof_from_requirements(
            {'proofofwork': {'required': True, 'seed': 'seed', 'difficulty': '0f'}}, list(range(25)))
        self.assertTrue(token.startswith('gAAAAAB'))


if __name__ == "__main__":
    unittest.main()
