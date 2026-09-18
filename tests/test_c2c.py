import unittest

from ccw.c2c import detect_environment


class C2CTests(unittest.TestCase):
    def test_vendor_is_detected(self):
        env = detect_environment()
        self.assertTrue(env["vendor_present"])
        self.assertTrue(str(env["vendor_root"]).endswith("vendor\\codex-with-chatgpt") or str(env["vendor_root"]).endswith("vendor/codex-with-chatgpt"))
        self.assertIn("built", env)


if __name__ == "__main__":
    unittest.main()
