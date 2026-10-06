import contextlib
import io
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import anthropic_connection_test
from worker import WorkerError


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"ANTHROPIC_IDENTITY_TOKEN_FILE": "/tmp/test-token"}, clear=True)
        factory = patch("anthropic_connection_test.AnthropicProvider")
        env.start()
        self.factory = factory.start()
        self.addCleanup(env.stop)
        self.addCleanup(factory.stop)
        self.provider = self.factory.return_value
        self.provider.sdk.AnthropicError = RuntimeError
        self.provider.client.messages.create.return_value = SimpleNamespace(
            stop_reason="end_turn", content=[SimpleNamespace(type="text", text="Hello!")],
        )
        self.stdout, self.stderr = io.StringIO(), io.StringIO()

    def run_command(self):
        with contextlib.redirect_stdout(self.stdout), contextlib.redirect_stderr(self.stderr):
            return anthropic_connection_test.main()

    def test_exchange_and_greeting_without_github_or_openai_tokens(self):
        self.assertEqual(self.run_command(), 0)
        self.provider.client.messages.create.assert_called_once_with(
            model="claude-sonnet-4-6", max_tokens=1024,
            messages=[{"role": "user", "content": "Hello, Claude"}],
        )
        self.assertIn("succeeded", self.stdout.getvalue())
        self.assertIn("Hello!", self.stdout.getvalue())
        self.provider.close.assert_called_once()

    def test_model_override(self):
        os.environ["ANTHROPIC_MODEL"] = "custom-claude"
        self.assertEqual(self.run_command(), 0)
        self.assertEqual(self.provider.client.messages.create.call_args.kwargs["model"], "custom-claude")

    def test_no_api_key_fallback_without_identity_file(self):
        os.environ.clear()
        os.environ["ANTHROPIC_API_KEY"] = "test-placeholder"
        self.assertEqual(self.run_command(), 1)
        self.factory.assert_not_called()
        self.assertIn("ANTHROPIC_IDENTITY_TOKEN_FILE", self.stderr.getvalue())

    def test_configuration_failure(self):
        self.factory.side_effect = WorkerError("Missing federation settings.")
        self.assertEqual(self.run_command(), 1)
        self.assertIn("Missing federation settings", self.stderr.getvalue())

    def test_auth_failure_is_nonzero_and_sanitized(self):
        self.provider.client.messages.create.side_effect = RuntimeError("sensitive response")
        self.assertEqual(self.run_command(), 1)
        self.assertNotIn("sensitive", self.stderr.getvalue())
        self.assertNotIn("succeeded", self.stdout.getvalue())
        self.provider.close.assert_called_once()

    def test_unreadable_token_is_nonzero(self):
        self.provider.client.messages.create.side_effect = WorkerError("Cannot read token.")
        self.assertEqual(self.run_command(), 1)
        self.provider.close.assert_called_once()

    def test_truncated_and_empty_greetings_fail(self):
        for message in (
            SimpleNamespace(stop_reason="max_tokens", content=[SimpleNamespace(type="text", text="Partial")]),
            SimpleNamespace(stop_reason="end_turn", content=[]),
        ):
            self.provider.client.messages.create.return_value = message
            with self.subTest(message=message):
                self.assertEqual(self.run_command(), 1)
        self.assertEqual(self.provider.close.call_count, 2)


if __name__ == "__main__":
    unittest.main()
