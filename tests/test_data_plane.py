import unittest

from ccw.data_plane import validate_data_source


class DataPlaneTests(unittest.TestCase):
    def test_read_only_sqlite_manifest(self):
        value = {"id": "metrics", "kind": "sqlite", "read_only": True, "auth": {"type": "local_only"}, "tools": ["schema", "query_readonly"], "limits": {"max_rows": 1000, "timeout_ms": 5000, "max_bytes": 1048576}}
        self.assertEqual([], validate_data_source(value))

    def test_write_tools_are_rejected(self):
        value = {"id": "bad", "kind": "sqlite", "read_only": True, "auth": {"type": "local_only"}, "tools": ["query_readonly", "drop_table"], "limits": {"max_rows": 1000, "timeout_ms": 5000, "max_bytes": 1048576}}
        self.assertIn("forbidden-write-tool:drop_table", validate_data_source(value))

    def test_http_requires_oauth_https(self):
        value = {"id": "remote", "kind": "http_readonly", "read_only": True, "url": "http://example.com", "auth": {"type": "local_only"}, "tools": ["query_readonly"], "limits": {"max_rows": 1000, "timeout_ms": 5000, "max_bytes": 1048576}}
        issues = validate_data_source(value)
        self.assertIn("http-readonly-requires-oauth2", issues)
        self.assertIn("http-readonly-requires-https", issues)


if __name__ == "__main__":
    unittest.main()
