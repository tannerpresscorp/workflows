# Workflows

This repository is currently a small collection of project-level files plus one GitHub Actions workflow. It does not yet contain a worker service.

## Status

- The repository was previously described as a background-job worker. That service's source code is **not** in this repository yet.
- Contents today:
  - `.github/workflows/anthropic-wif-test.yml`: a test that runs on every push and exchanges a GitHub OIDC token for an Anthropic access token (workload identity federation).
  - `.env.example`: sample environment variables for a future worker.
  - `CONTRIBUTING.md`, `SECURITY.md`, and issue templates in `.github/ISSUE_TEMPLATE/`.

## Environment variables

`.env.example` lists the variables a worker is expected to read. They are not used by any code in this repository yet.

| Variable | Example value | Purpose |
|----------|---------------|---------|
| `WORKER_NAME` | `local-worker` | Identifier for a worker instance |
| `WORKER_CONCURRENCY` | `2` | Number of concurrent jobs |
| `LOG_LEVEL` | `debug` | Logging level |
| `MAX_RETRIES` | `1` | Maximum retry attempts |
| `RETRY_DELAY` | `2000` | Initial retry delay in milliseconds |
| `QUEUE_PREFIX` | `queue:` | Key prefix for queues |
| `HEALTH_CHECK_PORT` | `3000` | Port for the health check |
| `HEALTH_CHECK_PATH` | `/health` | Path for the health check |

Copy the file to `.env` for local use. Do not commit `.env`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Report bugs or request features with the templates in `.github/ISSUE_TEMPLATE/`.

## Security

See [SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).
