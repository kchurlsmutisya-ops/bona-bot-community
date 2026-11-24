import json
import unittest
from unittest.mock import patch

from bona_bot.gemini_client import GeminiClient, GeminiError


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self, size: int) -> bytes:
        return self.payload[:size]


class GeminiClientTests(unittest.TestCase):
    @patch("bona_bot.gemini_client.urlopen")
    def test_sends_key_in_header_and_returns_generated_text(self, open_url):
        open_url.return_value = FakeResponse(
            {"candidates": [{"content": {"parts": [{"text": "Suggested change"}]}}]}
        )
        contents = [{"role": "user", "parts": [{"text": "Review this snippet"}]}]

        answer = GeminiClient().generate("test-secret", "gemini-2.5-flash", contents)

        self.assertEqual(answer, "Suggested change")
        request = open_url.call_args.args[0]
        self.assertEqual(request.get_header("X-goog-api-key"), "test-secret")
        self.assertNotIn("test-secret", request.full_url)

    def test_rejects_invalid_model_id_before_network_call(self) -> None:
        with self.assertRaises(GeminiError):
            GeminiClient().generate("key", "model?key=value", [{"role": "user"}])

    @patch("bona_bot.gemini_client.urlopen")
    def test_rejects_malformed_response_shape(self, open_url):
        open_url.return_value = FakeResponse({"candidates": ["not an object"]})

        with self.assertRaisesRegex(GeminiError, "invalid response"):
            GeminiClient().generate("key", "gemini-2.5-flash", [{"role": "user"}])


if __name__ == "__main__":
    unittest.main()
