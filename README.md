# Workflows

A robust, scalable worker service for processing background jobs and asynchronous tasks with reliability, error handling, and retry mechanisms.

## Overview

The worker service is designed to handle background jobs and asynchronous tasks with:
- **Reliable Job Processing**: Ensures jobs are processed reliably with error handling
- **Retry Mechanisms**: Automatic retries with configurable attempts
- **Scalable Architecture**: Designed to scale horizontally
- **Comprehensive Logging**: Detailed logs for monitoring and debugging

## Table of Contents

- [Getting Started](#getting-started)
- [Usage](#usage)
- [Features](#features)
- [Configuration](#configuration)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Getting Started

### Prerequisites

- Git
- Node.js 18+ or Python 3.8+
- npm or pip (depending on your language choice)

### Installation

```bash
# Clone the repository
git clone https://github.com/tannerpresscorp/worker.git
cd worker

# Install dependencies
npm install
# or
pip install -r requirements.txt
```

### Quick Start

```bash
# Set up environment variables
cp .env.example .env

# Start the worker
npm start
# or
python -m worker
```

## Usage

### Basic Job Processing

```javascript
// JavaScript example
const Worker = require('./worker');

const worker = new Worker();

// Register a job handler
worker.register('send-email', async (job) => {
  console.log('Processing email job:', job.data);
  // Your job logic here
  return { success: true };
});

// Start processing
worker.start();
```

```python
# Python example
from worker import Worker

worker = Worker()

@worker.job('send-email')
async def send_email(job_data):
    print(f'Processing email job: {job_data}')
    # Your job logic here
    return {'success': True}

if __name__ == '__main__':
    worker.start()
```

### Enqueueing Jobs

```javascript
const queue = worker.getQueue();

await queue.add('send-email', {
  to: 'user@example.com',
  subject: 'Welcome',
  body: 'Welcome to our service'
}, {
  attempts: 3,
  backoff: {
    type: 'exponential',
    delay: 2000
  }
});
```

## Features

- ✅ **Reliable Job Processing**: Guarantees job execution with error handling
- ✅ **Automatic Retries**: Configurable retry attempts with exponential backoff
- ✅ **Job Persistence**: Jobs are persisted for reliability
- ✅ **Dead Letter Queue**: Failed jobs are moved to DLQ after max retries
- ✅ **Concurrent Processing**: Configure worker concurrency levels
- ✅ **Job Monitoring**: Real-time job status tracking
- ✅ **Priority Queues**: Process high-priority jobs first
- ✅ **Scheduled Jobs**: Support for delayed and recurring jobs
- ✅ **Comprehensive Logging**: Structured logging for all operations
- ✅ **Health Checks**: Built-in health check endpoints

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `WORKER_NAME` | Identifier for this worker instance | `worker-1` | No |
| `WORKER_CONCURRENCY` | Number of concurrent jobs to process | `4` | No |
| `LOG_LEVEL` | Logging level (debug, info, warn, error) | `info` | No |
| `MAX_RETRIES` | Maximum retry attempts for failed jobs | `3` | No |
| `RETRY_DELAY` | Initial retry delay in ms | `2000` | No |
| `QUEUE_PREFIX` | Redis key prefix for queues | `queue:` | No |

### Configuration File

Create a `config.yml` in the project root:

```yaml
worker:
  name: worker-1
  concurrency: 4
  timeout: 30000
  
queues:
  - name: default
    priority: normal
  - name: priority
    priority: high
  
retry:
  max_attempts: 3
  backoff_type: exponential
  initial_delay: 2000
  
logging:
  level: info
  format: json
  
health:
  port: 3000
  path: /health
```

### Local Development

Create a `.env` file for local development:

```env
WORKER_NAME=local-worker
WORKER_CONCURRENCY=2
LOG_LEVEL=debug
MAX_RETRIES=1
```

## Development

### Project Structure

```
worker/
├── src/
│   ├── worker.js       # Main worker class
│   ├── queue.js        # Queue management
│   ├── job.js          # Job definition
│   └── handlers/       # Job handlers
├── tests/
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
├── docs/               # Documentation
├── config/             # Configuration files
├── .env.example        # Example environment file
├── README.md           # This file
└── package.json        # Project dependencies
```

### Running Tests

```bash
# Run all tests
npm test
# or
pytest

# Run tests with coverage
npm run test:coverage
# or
pytest --cov

# Run specific test file
npm test -- --testPathPattern=queue
# or
pytest tests/test_queue.py

# Run tests in watch mode
npm run test:watch
```

### Building

```bash
# Build for production
npm run build
# or
python setup.py build

# Create distribution package
npm run dist

# Lint code
npm run lint

# Format code
npm run format
```

### Development Commands

```bash
# Start in development mode with hot reload
npm run dev

# Run linter
npm run lint

# Fix linter issues
npm run lint:fix

# Format code with Prettier
npm run format

# Type check (if using TypeScript)
npm run type-check
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Quick Start for Contributors

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Write tests for new functionality
5. Run tests and linter: `npm test && npm run lint`
6. Commit with a clear message: `git commit -m 'feat: add new feature'`
7. Push and create a Pull Request

### Reporting Issues

Use the [Bug Report](https://github.com/tannerpresscorp/worker/issues/new?template=bug_report.md) or [Feature Request](https://github.com/tannerpresscorp/worker/issues/new?template=feature_request.md) templates when creating issues.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or suggestions:
- [Open an Issue](https://github.com/tannerpresscorp/worker/issues)
- [Start a Discussion](https://github.com/tannerpresscorp/worker/discussions)
- Email: support@tannerpresscorp.com
