import contextlib
import io
import json
import unittest
from unittest.mock import MagicMock, patch
from urllib import error

import worker


def ai_response(calls=None, content=None):
    message = {"role": "assistant", "content": content}
    if calls is not None:
        message["tool_calls"] = calls
    return {"choices": [{"message": message}]}


def call(name, args, identifier="call_1"):
    return {
        "id": identifier,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


class GitHubActionsTests(unittest.TestCase):
    def setUp(self):
        self.github = worker.GitHubActions("owner/repo", "test-token", confirm=lambda _: True)

    @patch("worker.api_request")
    def test_lists_workflows_and_filters_unneeded_data(self, api):
        api.return_value = {
            "total_count": 1,
            "workflows": [{"id": 12, "name": "CI", "path": ".github/workflows/ci.yml",
                           "irrelevant": "ignored"}],
        }
        result = self.github.execute("list_workflows", {})
        self.assertEqual(result["workflows"][0]["name"], "CI")
        self.assertNotIn("irrelevant", result["workflows"][0])
        api.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/actions/workflows?per_page=100",
            "test-token", "GET", None,
        )

    @patch("worker.api_request", return_value={"total_count": 0, "workflow_runs": []})
    def test_lists_recent_runs_with_optional_workflow(self, api):
        self.github.execute("list_runs", {})
        self.assertIn("/actions/runs?per_page=20", api.call_args.args[0])
        self.github.execute("list_runs", {"workflow_id": "ci.yml"})
        self.assertIn("/actions/workflows/ci.yml/runs?per_page=20", api.call_args.args[0])

    @patch("worker.api_request", return_value={"id": 12, "status": "completed",
                                             "conclusion": "failure"})
    def test_get_run(self, api):
        result = self.github.execute("get_run", {"run_id": 12})
        self.assertEqual(result["conclusion"], "failure")
        self.assertTrue(api.call_args.args[0].endswith("/actions/runs/12"))

    @patch("worker.api_request", side_effect=[{"id": 12}, {}])
    def test_confirmed_dispatch(self, api):
        result = self.github.execute(
            "dispatch_workflow", {"workflow_id": "ci.yml", "ref": "main", "inputs": {"build": "true"}},
        )
        self.assertEqual(result["status"], "submitted")
        self.assertEqual(api.call_count, 2)
        api.assert_called_with(
            "https://api.github.com/repos/owner/repo/actions/workflows/12/dispatches",
            "test-token", "POST", {"ref": "main", "inputs": {"build": "true"}},
        )

    @patch("worker.api_request", side_effect=[{"id": 12}, {}])
    def test_dotted_workflow_filename(self, api):
        self.github.execute("dispatch_workflow", {"workflow_id": "build.release.yml", "ref": "main"})
        self.assertTrue(api.call_args_list[0].args[0].endswith("/workflows/build.release.yml"))
        self.assertTrue(api.call_args.args[0].endswith("/workflows/12/dispatches"))

    @patch("worker.api_request", side_effect=[{"id": 12}, {}, {"id": 12}])
    def test_omitted_and_empty_inputs_are_same_mutation(self, api):
        self.github.execute("dispatch_workflow", {"workflow_id": "ci.yml", "ref": "main"})
        with self.assertRaisesRegex(worker.WorkerError, "Duplicate mutation"):
            self.github.execute(
                "dispatch_workflow", {"workflow_id": "ci.yml", "ref": "main", "inputs": {}},
            )
        self.assertEqual(sum(len(entry.args) == 4 for entry in api.call_args_list), 1)

    @patch("worker.api_request")
    def test_workflow_alias_cannot_repeat_uncertain_dispatch(self, api):
        api.side_effect = [
            {"id": 12}, worker.WorkerError("Connection failed"), {"id": 12},
        ]
        self.github.allow_actions = {"dispatch_workflow"}
        with self.assertRaisesRegex(worker.WorkerError, "Connection failed"):
            self.github.execute("dispatch_workflow", {"workflow_id": "ci.yml", "ref": "main"})
        with self.assertRaisesRegex(worker.WorkerError, "Duplicate mutation"):
            self.github.execute("dispatch_workflow", {"workflow_id": "12", "ref": "main"})
        self.assertEqual(sum(len(entry.args) == 4 for entry in api.call_args_list), 1)

    @patch("worker.api_request")
    def test_dispatch_requires_valid_canonical_workflow_id(self, api):
        for details in ({}, {"id": True}, {"id": -1}, []):
            api.return_value = details
            with self.subTest(details=details), self.assertRaises(worker.WorkerError):
                self.github.execute("dispatch_workflow", {"workflow_id": "ci.yml", "ref": "main"})
        self.assertTrue(all(len(entry.args) == 2 for entry in api.call_args_list))

    @patch("worker.api_request", return_value={})
    def test_run_mutations(self, api):
        for name, suffix in (("rerun_failed_jobs", "/rerun-failed-jobs"), ("cancel_run", "/cancel")):
            with self.subTest(name=name):
                self.github.execute(name, {"run_id": 42})
                self.assertTrue(api.call_args.args[0].endswith("/actions/runs/42" + suffix))
                self.assertEqual(api.call_args.args[2], "POST")

    @patch("worker.api_request")
    def test_denied_mutation_never_calls_api(self, api):
        self.github.confirm = lambda _: False
        self.assertEqual(self.github.execute("cancel_run", {"run_id": 42})["status"], "denied")
        api.assert_not_called()

    @patch("worker.api_request", return_value={})
    def test_explicit_permission_only_authorizes_named_action(self, api):
        github = worker.GitHubActions("owner/repo", "test-token", ["cancel_run"], lambda _: False)
        self.assertEqual(github.execute("cancel_run", {"run_id": 42})["status"], "submitted")
        self.assertEqual(github.execute("rerun_failed_jobs", {"run_id": 42})["status"], "denied")
        self.assertEqual(api.call_count, 1)

    @patch("worker.api_request", side_effect=worker.WorkerError("Connection failed"))
    def test_failed_mutation_cannot_be_replayed(self, api):
        for _ in range(2):
            with self.assertRaises(worker.WorkerError):
                self.github.execute("cancel_run", {"run_id": 42})
        api.assert_called_once()

    @patch("worker.api_request")
    def test_invalid_arguments_rejected_before_api(self, api):
        cases = [
            ("unknown", {}), ("list_workflows", {"repo": "other/repo"}),
            ("get_run", {}), ("get_run", {"run_id": True}),
            ("get_run", {"run_id": -1}), ("get_run", {"run_id": "12"}),
            ("dispatch_workflow", {"workflow_id": "../ci.yml", "ref": "main"}),
            ("dispatch_workflow", {"workflow_id": "ci.yml", "ref": ""}),
            ("dispatch_workflow", {"workflow_id": "ci.yml", "ref": "main\n"}),
            ("dispatch_workflow", {"workflow_id": "ci.yml", "ref": "main", "inputs": {"x": True}}),
            ("list_runs", []),
        ]
        for name, args in cases:
            with self.subTest(name=name, args=args), self.assertRaises(worker.WorkerError):
                self.github.execute(name, args)
        api.assert_not_called()

    def test_repository_validation(self):
        for repo in ("../repo", "owner/repo/extra", "owner/repo?x=y", "https://host/repo",
                     "owner/..", "owner/."):
            with self.subTest(repo=repo), self.assertRaises(worker.WorkerError):
                worker.GitHubActions(repo, "test-token")

    @patch("worker.sys.stdin.isatty", return_value=False)
    @patch("builtins.input")
    def test_noninteractive_confirmation_denies(self, prompt, _):
        self.assertFalse(worker.GitHubActions._confirm("cancel_run"))
        prompt.assert_not_called()

    @patch("worker.sys.stdin.isatty", return_value=True)
    @patch("builtins.input", side_effect=["no", "yes"])
    def test_interactive_confirmation_requires_yes(self, prompt, _):
        self.assertFalse(worker.GitHubActions._confirm("cancel_run"))
        self.assertTrue(worker.GitHubActions._confirm("cancel_run"))


class AgentTests(unittest.TestCase):
    @patch("worker.api_request")
    def test_full_tool_loop(self, api):
        api.side_effect = [
            ai_response([call("list_runs", {})]),
            {"total_count": 1, "workflow_runs": [{"id": 42, "conclusion": "failure"}]},
            ai_response([call("rerun_failed_jobs", {"run_id": 42}, "call_2")]),
            {},
            ai_response(content="Retry submitted for run 42."),
        ]
        github = worker.GitHubActions("owner/repo", "test-token", confirm=lambda _: True)
        answer = worker.run_agent("Retry my failed CI", github, "test-key", "test-model")
        self.assertEqual(answer, "Retry submitted for run 42.")
        messages = api.call_args.args[3]["messages"]
        outputs = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
        self.assertEqual(outputs[1]["status"], "submitted")
        self.assertNotIn("test-token", json.dumps(messages))
        self.assertNotIn("test-key", json.dumps(messages))

    @patch("worker.api_request")
    def test_bad_tool_arguments_are_returned_to_model(self, api):
        bad_call = call("cancel_run", {})
        bad_call["function"]["arguments"] = "{invalid"
        api.side_effect = [ai_response([bad_call]), ai_response(content="Unable to cancel.")]
        github = MagicMock(repo="owner/repo")
        worker.run_agent("Cancel", github, "test-key", "test-model")
        github.execute.assert_not_called()
        self.assertIn("valid JSON", api.call_args.args[3]["messages"][-1]["content"])

    @patch("worker.api_request")
    def test_malformed_ai_response_has_controlled_error(self, api):
        for result in ({}, {"choices": []}, ai_response(content=None),
                       ai_response([{"id": "bad"}]), ai_response([None])):
            api.return_value = result
            with self.subTest(result=result), self.assertRaises(worker.WorkerError):
                worker.run_agent("List", MagicMock(repo="owner/repo"), "test-key", "test-model")

    @patch("worker.api_request")
    def test_duplicate_call_ids_are_rejected(self, api):
        api.return_value = ai_response([call("list_workflows", {}), call("list_runs", {})])
        github = MagicMock(repo="owner/repo")
        with self.assertRaises(worker.WorkerError):
            worker.run_agent("List", github, "test-key", "test-model")
        github.execute.assert_not_called()

    @patch("worker.api_request")
    def test_turn_limit(self, api):
        api.return_value = ai_response([call("list_workflows", {})])
        github = MagicMock(repo="owner/repo")
        github.execute.return_value = {}
        with self.assertRaisesRegex(worker.WorkerError, "turn limit"):
            worker.run_agent("List", github, "test-key", "test-model", max_turns=1)


class HttpAndCliTests(unittest.TestCase):
    @patch("worker.request.build_opener")
    def test_authenticated_json_request_and_empty_response(self, build):
        response = build.return_value.open.return_value.__enter__.return_value
        response.read.return_value = b""
        result = worker.api_request("https://api.github.com/test", "test-token", "POST", {"ref": "main"})
        self.assertEqual(result, {})
        req = build.return_value.open.call_args.args[0]
        self.assertEqual(req.get_header("Authorization"), "Bearer " + "test-token")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(json.loads(req.data), {"ref": "main"})
        self.assertEqual(build.return_value.open.call_args.kwargs["timeout"], 30)
        self.assertIsInstance(build.call_args.args[0], worker.NoRedirect)

    def test_redirects_are_not_followed(self):
        self.assertIsNone(worker.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other"))

    @patch("worker.request.build_opener")
    def test_http_errors_do_not_disclose_response(self, build):
        build.return_value.open.side_effect = error.HTTPError(
            "https://api.github.com/test", 403, "sensitive upstream content", {}, None,
        )
        with self.assertRaisesRegex(worker.WorkerError, "HTTP 403") as caught:
            worker.api_request("https://api.github.com/test", "test-token")
        self.assertNotIn("sensitive", str(caught.exception))

    @patch("worker.request.build_opener")
    def test_invalid_json(self, build):
        build.return_value.open.return_value.__enter__.return_value.read.return_value = b"not JSON"
        with self.assertRaisesRegex(worker.WorkerError, "invalid JSON"):
            worker.api_request("https://api.github.com/test", "test-token")

    @patch("worker.request.build_opener")
    def test_timeout_warns_about_possible_mutation(self, build):
        build.return_value.open.side_effect = TimeoutError
        with self.assertRaisesRegex(worker.WorkerError, "may have succeeded"):
            worker.api_request("https://api.github.com/test", "test-token", "POST")

    @patch.dict("worker.os.environ", {}, clear=True)
    def test_missing_credentials_exit_nonzero(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            self.assertEqual(worker.main(["--repo", "owner/repo", "List workflows"]), 1)
        self.assertIn("GITHUB_TOKEN", output.getvalue())

    @patch.dict("worker.os.environ", {"GITHUB_TOKEN": "test-token", "OPENAI_API_KEY": "test-key"})
    @patch("worker.run_agent", return_value="Found CI.")
    def test_cli_success(self, agent):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(worker.main(["--repo", "owner/repo", "List workflows"]), 0)
        self.assertEqual(output.getvalue().strip(), "Found CI.")
        self.assertEqual(agent.call_args.args[1].repo, "owner/repo")


if __name__ == "__main__":
    unittest.main()
