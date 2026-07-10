import unittest
from unittest.mock import patch

import api


class AnalyzerFallbackTests(unittest.TestCase):
    def test_local_fallback_is_used_when_gemini_fails(self):
        failing_client = unittest.mock.Mock()
        failing_client.models.generate_content.side_effect = RuntimeError("service unavailable")

        with patch.object(api, "client", failing_client), patch.object(api, "types", unittest.mock.Mock()):
            result = api.analyze_text("Great service and fast delivery")

        self.assertEqual(result.label, "good")
        self.assertEqual(result.score, 5)
        self.assertEqual(result.theme, "delivery")


if __name__ == "__main__":
    unittest.main()
