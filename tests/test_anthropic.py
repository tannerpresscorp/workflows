import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import worker


def response(content, stop_reason="end_turn"):
    result = MagicMock()
    result.model_dump.return_value = {"content": content, "stop_reason": stop_reason}
    return result


def text(value):
    return {"type": "text", "text": value}


def tool_use(identifier, name, arguments):
    return {"type": "tool_use", "id": identifier, "name": name, "input": arguments}


class AnthropicTests(unittest.TestCase):
    def setUp(self):
        self.sdk = MagicMock()
        self.sdk.AnthropicError = RuntimeError
        self.client = self.sdk.Anthropic.return_value
        modules = patch.dict("sys.modules", {"anthropic": self.sdk})
        env = patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True)
        modules.start()
        env.start()
        self.addCleanup(modules.stop)
        self.addCleanup(env.stop)

    def run_agent(self, provider, github=None, max_turns=10):
        return worker.run_agent(
            "Manage CI", github or MagicMock(repo="owner/repo"), None,
            "claude-sonnet-4-6", max_turns=max_turns, completion=provider,
        )

    def test_api_key_configuration_and_text_response(self):
        provider = worker.AnthropicProvider()
        self.sdk.Anthropic.assert_called_once_with(
            api_key="test-key", base_url="https://api.anthropic.com",
            timeout=30, max_retries=0,
        )
        self.client.messages.create.return_value = response([text("Ready."), text("No actions taken.")])
        self.assertEqual(self.run_agent(provider), "Ready.\nNo actions taken.")
        kwargs = self.client.messages.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "claude-sonnet-4-6")
        self.assertEqual(kwargs["max_tokens"], 1024)
        self.assertIn("Repository: owner/repo.", kwargs["system"])
        self.assertEqual(kwargs["messages"], [{"role": "user", "content": [text("Manage CI")]}])
        self.assertEqual(kwargs["tools"][0]["input_schema"], worker.TOOLS[0]["function"]["parameters"])
        self.assertNotIn("test-key", json.dumps(kwargs))
        provider.close()
        self.client.close.assert_called_once()

    def test_workload_identity_configuration_and_rotating_token(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "token"
            path.write_text(" first-token\n", encoding="utf-8")
            os.environ.update({
                "ANTHROPIC_IDENTITY_TOKEN_FILE": str(path),
                "ANTHROPIC_FEDERATION_RULE_ID": "test-federation",
                "ANTHROPIC_ORGANIZATION_ID": "test-organization",
                "ANTHROPIC_SERVICE_ACCOUNT_ID": "test-service-account",
                "ANTHROPIC_WORKSPACE_ID": "test-workspace",
            })
            provider = worker.AnthropicProvider()
            kwargs = self.sdk.WorkloadIdentityCredentials.call_args.kwargs
            self.assertEqual(kwargs["federation_rule_id"], "test-federation")
            self.assertEqual(kwargs["organization_id"], "test-organization")
            self.assertEqual(kwargs["service_account_id"], "test-service-account")
            self.assertEqual(kwargs["workspace_id"], "test-workspace")
            callback = kwargs["identity_token_provider"]
            self.assertEqual(callback(), "first-token")
            path.write_text("second-token", encoding="utf-8")
            self.assertEqual(callback(), "second-token")
            self.assertNotIn("api_key", self.sdk.Anthropic.call_args.kwargs)
            self.assertIs(
                self.sdk.Anthropic.call_args.kwargs["credentials"],
                self.sdk.WorkloadIdentityCredentials.return_value,
            )
            self.client.messages.create.return_value = response([text("Ready.")])
            self.run_agent(provider)
            payload = json.dumps(self.client.messages.create.call_args.kwargs)
            self.assertNotIn("second-token", payload)
            self.assertNotIn("test-organization", payload)
            path.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(worker.WorkerError, "empty"):
                callback()
            path.unlink()
            with self.assertRaisesRegex(worker.WorkerError, "Cannot read"):
                callback()
            provider.close()

    def test_missing_workload_identity_settings_fail_without_key_fallback(self):
        os.environ["ANTHROPIC_IDENTITY_TOKEN_FILE"] = "/tmp/missing-token"
        with self.assertRaisesRegex(worker.WorkerError, "ANTHROPIC_FEDERATION_RULE_ID"):
            worker.AnthropicProvider()
        self.sdk.Anthropic.assert_not_called()

    def test_missing_credentials(self):
        os.environ.clear()
        with self.assertRaisesRegex(worker.WorkerError, "ANTHROPIC_API_KEY"):
            worker.AnthropicProvider()

    def test_missing_optional_sdk(self):
        with patch.dict("sys.modules", {"anthropic": None}):
            with self.assertRaisesRegex(worker.WorkerError, "requirements-anthropic.txt"):
                worker.AnthropicProvider()

    def test_constructor_errors_are_sanitized(self):
        self.sdk.Anthropic.side_effect = RuntimeError("secret upstream detail")
        with self.assertRaisesRegex(worker.WorkerError, "Cannot initialize") as caught:
            worker.AnthropicProvider()
        self.assertNotIn("secret", str(caught.exception))

    def test_full_tool_loop_groups_parallel_results(self):
        provider = worker.AnthropicProvider()
        self.client.messages.create.side_effect = [
            response([
                text("Checking CI."),
                tool_use("read1", "list_workflows", {}),
                tool_use("read2", "list_runs", {}),
            ], "tool_use"),
            response([text("Done.")]),
        ]
        github = MagicMock(repo="owner/repo")
        github.execute.side_effect = [{"workflows": []}, {"workflow_runs": []}]
        self.assertEqual(self.run_agent(provider, github), "Done.")
        messages = self.client.messages.create.call_args.kwargs["messages"]
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[1]["content"][1], tool_use("read1", "list_workflows", {}))
        self.assertEqual(messages[2]["role"], "user")
        self.assertEqual(len(messages[2]["content"]), 2)
        self.assertEqual(messages[2]["content"][0], {
            "type": "tool_result", "tool_use_id": "read1",
            "content": json.dumps({"workflows": []}),
        })
        self.assertEqual(github.execute.call_count, 2)

    @patch("worker.api_request")
    def test_confirmation_and_duplicate_protection_apply_to_anthropic(self, api):
        provider = worker.AnthropicProvider()
        self.client.messages.create.side_effect = [
            response([tool_use("cancel1", "cancel_run", {"run_id": 42})], "tool_use"),
            response([tool_use("cancel2", "cancel_run", {"run_id": 42})], "tool_use"),
            response([text("Cancellation was denied.")]),
        ]
        confirm = MagicMock(return_value=False)
        github = worker.GitHubActions("owner/repo", "test-token", confirm=confirm)
        self.run_agent(provider, github)
        confirm.assert_called_once()
        api.assert_not_called()
        transcript = self.client.messages.create.call_args.kwargs["messages"]
        self.assertIn("denied", transcript[2]["content"][0]["content"])
        self.assertIn("Duplicate mutation", transcript[4]["content"][0]["content"])

    @patch("worker.api_request", return_value={})
    def test_approved_anthropic_mutation(self, api):
        provider = worker.AnthropicProvider()
        self.client.messages.create.side_effect = [
            response([tool_use("retry1", "rerun_failed_jobs", {"run_id": 42})], "tool_use"),
            response([text("Retry submitted.")]),
        ]
        github = worker.GitHubActions("owner/repo", "test-token", confirm=lambda _: True)
        self.assertEqual(self.run_agent(provider, github), "Retry submitted.")
        api.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/actions/runs/42/rerun-failed-jobs",
            "test-token", "POST", None,
        )

    def test_invalid_tool_input_is_rejected_by_shared_validator(self):
        provider = worker.AnthropicProvider()
        self.client.messages.create.side_effect = [
            response([tool_use("bad1", "list_workflows", {"repo": "other/repo"})], "tool_use"),
            response([text("Invalid arguments.")]),
        ]
        github = worker.GitHubActions("owner/repo", "test-token")
        self.run_agent(provider, github)
        result = self.client.messages.create.call_args.kwargs["messages"][-1]["content"][0]
        self.assertIn("Unexpected", result["content"])

    def test_malformed_or_truncated_response_never_executes_tools(self):
        provider = worker.AnthropicProvider()
        cases = [
            response([tool_use("cut1", "cancel_run", {"run_id": 42})], "max_tokens"),
            response([tool_use("bad1", "cancel_run", {"run_id": 42})], "end_turn"),
            response([text("No tools")], "tool_use"),
            response([{"type": "tool_use"}], "tool_use"),
            response([None]),
            response([text(123)]),
            response([{"type": "unknown"}]),
        ]
        github = MagicMock(repo="owner/repo")
        for value in cases:
            self.client.messages.create.return_value = value
            with self.subTest(value=value), self.assertRaises(worker.WorkerError):
                self.run_agent(provider, github)
        github.execute.assert_not_called()

    def test_call_limits_and_duplicate_ids(self):
        provider = worker.AnthropicProvider()
        github = MagicMock(repo="owner/repo")
        for calls in (
            [tool_use(str(index), "list_runs", {}) for index in range(9)],
            [tool_use("same", "list_runs", {}), tool_use("same", "list_runs", {})],
        ):
            self.client.messages.create.return_value = response(calls, "tool_use")
            with self.assertRaises(worker.WorkerError):
                self.run_agent(provider, github)
        github.execute.assert_not_called()

    def test_turn_limit(self):
        provider = worker.AnthropicProvider()
        self.client.messages.create.return_value = response([tool_use("read1", "list_runs", {})], "tool_use")
        github = MagicMock(repo="owner/repo")
        github.execute.return_value = {}
        with self.assertRaisesRegex(worker.WorkerError, "turn limit"):
            self.run_agent(provider, github, max_turns=1)

    def test_sdk_request_errors_are_sanitized(self):
        provider = worker.AnthropicProvider()
        self.client.messages.create.side_effect = RuntimeError("secret token or upstream body")
        with self.assertRaisesRegex(worker.WorkerError, "Anthropic request failed") as caught:
            self.run_agent(provider)
        self.assertNotIn("secret", str(caught.exception))

    def test_anthropic_cli_without_openai_key_and_model_selection(self):
        os.environ.update({"GITHUB_TOKEN": "test-token", "ANTHROPIC_MODEL": "custom-claude"})
        self.client.messages.create.return_value = response([text("Ready.")])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(worker.main([
                "--repo", "owner/repo", "--provider", "anthropic", "List workflows",
            ]), 0)
        self.assertEqual(output.getvalue().strip(), "Ready.")
        self.assertEqual(self.client.messages.create.call_args.kwargs["model"], "custom-claude")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(worker.main([
                "--repo", "owner/repo", "--provider", "anthropic",
                "--model", "explicit-claude", "List workflows",
            ]), 0)
        self.assertEqual(self.client.messages.create.call_args.kwargs["model"], "explicit-claude")
        self.assertEqual(self.client.close.call_count, 2)

    def test_anthropic_cli_default_model_and_cleanup_on_failure(self):
        os.environ["GITHUB_TOKEN"] = "test-token"
        self.client.messages.create.side_effect = RuntimeError("secret")
        with contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(worker.main([
                "--repo", "owner/repo", "--provider", "anthropic", "List workflows",
            ]), 1)
        self.assertNotIn("secret", output.getvalue())
        self.assertEqual(self.client.messages.create.call_args.kwargs["model"], "claude-sonnet-4-6")
        self.client.close.assert_called_once()

    def test_openai_default_does_not_initialize_sdk(self):
        os.environ.update({"GITHUB_TOKEN": "test-token", "OPENAI_API_KEY": "test-key"})
        with patch("worker.run_agent", return_value="Ready.") as agent:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(worker.main(["--repo", "owner/repo", "List workflows"]), 0)
        self.assertEqual(agent.call_args.args[3], "gpt-4o-mini")
        self.sdk.Anthropic.assert_not_called()


if __name__ == "__main__":
    unittest.main()
