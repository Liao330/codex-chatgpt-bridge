import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ccw.credentials import load_access_token, store_access_token, configure_credentials
from ccw.errors import ValidationError


class HttpCredentialTests(unittest.TestCase):
    def test_environment_only_does_not_read_other_configuration(self):
        with patch.dict(os.environ, {"CCW_CHATGPT_ACCESS_TOKEN": "synthetic-token-for-offline-test"}):
            self.assertEqual(load_access_token(), "synthetic-token-for-offline-test")

    def test_missing_credentials_error_has_no_payload(self):
        with patch.dict(os.environ, {}, clear=True), tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValidationError) as error:
                load_access_token(Path(directory) / "absent")
            self.assertNotIn(directory, str(error.exception))

    def test_noninteractive_setup_refused(self):
        with patch("sys.stdin.isatty", return_value=False):
            with self.assertRaises(ValidationError):
                configure_credentials()

    @unittest.skipUnless(os.name == "nt", "Windows DPAPI")
    def test_current_user_dpapi_roundtrip_without_plaintext(self):
        token = "synthetic-credential-for-dpapi-test"
        with patch.dict(os.environ, {"CCW_CHATGPT_ACCESS_TOKEN": ""}), tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "credential.dpapi"
            store_access_token(token, path)
            self.assertNotIn(token.encode(), path.read_bytes())
            self.assertEqual(load_access_token(path), token)
