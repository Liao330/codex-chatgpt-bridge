"""Bounded browser-fingerprint proof-of-work for the HTTP text transport.

The sentinel ``/chat-requirements/prepare`` endpoint may return a
``proofofwork`` challenge with a ``seed`` and a hex ``difficulty``. The proof
token is the base64 fingerprint payload with two integer nonces substituted at
slots 3 and 9 so that ``sha3_512(seed + encoded)`` starts with bytes not greater
than the difficulty. The serialization matches
``http_protocol.requirements_payload`` exactly (``ensure_ascii=True``), so the
solved payload equals the fingerprint sent to ``prepare`` apart from the two
nonce slots. The search is bounded and never touches the supplied fingerprint.
"""
import base64
import hashlib
import json


def solve(seed, difficulty, fingerprint, limit=500000):
    if not isinstance(seed, str) or not isinstance(difficulty, str):
        raise ValueError("invalid_pow_parameters")
    if not isinstance(fingerprint, list) or len(fingerprint) < 10:
        raise ValueError("invalid_pow_fingerprint")
    try:
        target = bytes.fromhex(difficulty)
    except ValueError as exc:
        raise ValueError("invalid_pow_difficulty") from exc
    if not target or len(target) > 64:
        raise ValueError("invalid_pow_difficulty")
    prefix = (json.dumps(fingerprint[:3], separators=(",", ":"))[:-1] + ",").encode()
    middle = ("," + json.dumps(fingerprint[4:9], separators=(",", ":"))[1:-1] + ",").encode()
    suffix = ("," + json.dumps(fingerprint[10:], separators=(",", ":"))[1:]).encode()
    seed_bytes = seed.encode()
    for nonce in range(min(max(int(limit), 1), 500000)):
        candidate = prefix + str(nonce).encode() + middle + str(nonce >> 1).encode() + suffix
        encoded = base64.b64encode(candidate)
        digest = hashlib.sha3_512(seed_bytes + encoded).digest()
        if digest[:len(target)] <= target:
            return "gAAAAAB" + encoded.decode("ascii")
    raise RuntimeError("pow_limit_exhausted")


def proof_from_requirements(requirements, fingerprint):
    challenge = requirements.get("proofofwork")
    if not isinstance(challenge, dict) or challenge.get("required") is not True:
        return ""
    seed = challenge.get("seed")
    difficulty = challenge.get("difficulty")
    return solve(seed, difficulty, fingerprint)
