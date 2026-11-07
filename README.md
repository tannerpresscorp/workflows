# Workflows

This repository contains GitHub Actions workflows. Its current workflow tests
exchanging a GitHub Actions OpenID Connect (OIDC) token for an Anthropic access
token through Anthropic's workload identity federation endpoint.

It is a workflow configuration repository, not a background-job worker library
or service. There is no application package to install or run locally.

## Workflow

| Workflow | File | Trigger |
| --- | --- | --- |
| `anthropic-wif-test` | [`.github/workflows/anthropic-wif-test.yml`](.github/workflows/anthropic-wif-test.yml) | Every push |

The workflow runs on a GitHub-hosted Ubuntu runner and:

1. Requests a GitHub OIDC token with the audience `https://api.anthropic.com`.
2. Exchanges that token at Anthropic's OAuth token endpoint using the JWT
   bearer grant and the federation, organization, service account, and workspace
   identifiers configured in the workflow file.
3. Prints the response as JSON, replacing response values for fields whose
   names end in `token` with `<redacted>`.

The workflow grants `id-token: write` so GitHub Actions can issue the OIDC
token, and `contents: read`. It does not configure any other GitHub
permissions.

## Running the workflow

The workflow is triggered automatically when a commit is pushed to this
repository. To view a run, open the repository's **Actions** tab and select
`anthropic-wif-test`.

For the exchange to succeed, the Anthropic federation configuration must
recognize the GitHub Actions identity for this repository and the identifiers
in the workflow must refer to the intended Anthropic resources. The current
workflow has those identifiers inline; update them there if the federation
configuration changes. Do not put access tokens or other secrets in the
workflow file.

## Repository contents

- `.github/workflows/anthropic-wif-test.yml` — the GitHub Actions workflow.
- `.github/ISSUE_TEMPLATE/` — templates for bug reports and feature requests.
- `.env.example` — example worker-related settings; it is not consumed by the
  current workflow.
- `CONTRIBUTING.md` — contribution guidance.

There are no package manifests or automated test commands in the repository.
Changes to the workflow can be reviewed and tested by running it through
GitHub Actions.

## Contributing and support

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidance. Use the
[bug report](.github/ISSUE_TEMPLATE/bug_report.md) or
[feature request](.github/ISSUE_TEMPLATE/feature_request.md) template when
filing an issue.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
