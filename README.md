# worker

A small AI worker that turns natural-language requests into GitHub Actions API
operations for one repository. Uses OpenAI tool calling and Python's standard
library; no third-party packages are required.

## Run

Requires Python 3.10+ and network access to `api.openai.com` and `api.github.com`.
Set `OPENAI_API_KEY` and `GITHUB_TOKEN` in your environment using your secret
manager or CI secret settings. Do not put credentials in source files, task
text, or command-line arguments.

The GitHub token needs access to the target repository with **Actions: read**
for inspection or **Actions: write** for mutations. For classic personal access
tokens, GitHub requires the `repo` scope for these Actions endpoints; prefer a
fine-grained token restricted to the target repository. Use short-lived tokens
where possible.

From the repository root:

```sh
python worker.py --repo owner/repo "List recent workflow runs and summarize failures"
python worker.py --repo owner/repo "Run ci.yml on main"
python worker.py --repo owner/repo "Retry failed jobs in run 123456"
python worker.py --repo owner/repo "Cancel run 123456"
```

The default model is `gpt-4o-mini`. Override it with `--model` or `OPENAI_MODEL`
using an OpenAI model that supports Chat Completions tool calling.

## Supported operations and safety

- List up to 100 workflows and the 20 latest runs, optionally by workflow.
- Inspect a run's current status and conclusion.
- Dispatch a `workflow_dispatch` workflow with an explicit branch/tag and optional
  string-valued inputs. Supply required input names and values in your request.
- Retry failed jobs or cancel a run.

Read operations run automatically. Each mutation displays its exact operation,
repository, and arguments and requires typing `yes`. Without an interactive
terminal, mutations are denied unless explicitly authorized by action type:

```sh
python worker.py --repo owner/repo --allow-action rerun_failed_jobs \
  "Retry failed jobs in run 123456"
```

`--allow-action` can be repeated; it only bypasses confirmation for the named
actions. **It authorizes any calls of that type during this invocation**, not
just a particular run. Use it only with trusted tasks and appropriately scoped
tokens. Workflow dispatch can execute repository code, deployments, and workflows
with access to secrets; review the workflow and ref before approving.

The AI cannot select another repository or execute arbitrary shell commands.
Identical mutation attempts are blocked within an invocation, and API calls are
not automatically retried. After a timeout or interruption, check GitHub before
retrying: the operation may already have succeeded. The agent is bounded to ten
AI turns and eight tool calls per turn. A submitted operation does not imply
successful workflow completion.

Task text and selected workflow/run metadata are sent to OpenAI. API credentials
are used only in request headers, never included in model messages. Do not
include secrets in tasks or workflow inputs. Repository metadata is untrusted;
confirmation and token permissions remain the security boundary, not the model.
This starter has no polling daemon, pagination beyond the limits above, or
multi-turn user conversation; if it asks for clarification, rerun with a more
specific request.

## Test

```sh
python -m unittest discover -s tests -v
```

Tests use mocked APIs and need neither credentials nor network access.