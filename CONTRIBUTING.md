# Contributing to worker

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the worker project.

## Code of Conduct

Be respectful, inclusive, and professional in all interactions. We're committed to providing a welcoming environment for everyone.

## Getting Started

### Prerequisites

- Git
- Node.js 18+ or Python 3.8+
- npm or pip

### Setup Development Environment

```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/worker.git
cd worker

# 3. Add upstream remote
git remote add upstream https://github.com/tannerpresscorp/worker.git

# 4. Install dependencies
npm install
# or
pip install -r requirements.txt -r requirements-dev.txt

# 5. Create a feature branch
git checkout -b feature/your-feature-name
```

## Development Workflow

### Making Changes

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/description-of-feature
   ```

2. **Make your changes** with clear, focused commits

3. **Write tests** for new functionality

4. **Run tests locally**:
   ```bash
   npm test
   npm run lint
   npm run format
   ```

5. **Commit with clear messages** (see Commit Guidelines below)

### Commit Guidelines

Use clear, descriptive commit messages following the Conventional Commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring without feature changes
- `perf`: Performance improvements
- `test`: Test additions or changes
- `chore`: Build, dependency, or tooling changes

**Examples:**
```
feat(queue): add priority queue support
fix(worker): resolve race condition in job processing
docs(readme): update installation instructions
test(handlers): add integration tests for email handler
```

**Reference Issues:**
```
feat(queue): implement priority queues

Adds support for priority-based job processing.
Closes #123
```

## Pull Request Process

### Before Submitting

1. **Sync with upstream**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Ensure all tests pass**:
   ```bash
   npm test
   npm run lint
   ```

3. **Update documentation** if needed

4. **Add tests** for new functionality (aim for >80% coverage)

### Creating a Pull Request

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create PR on GitHub** with a descriptive title and body:
   ```
   Title: Brief description of changes
   
   ## Description
   Detailed explanation of what changed and why.
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update
   
   ## Testing
   Describe how you tested these changes.
   
   ## Checklist
   - [ ] Tests pass locally
   - [ ] Code follows style guidelines
   - [ ] Documentation updated
   - [ ] No new warnings generated
   ```

3. **Respond to feedback** and update your PR as needed

### Merging

- At least one maintainer review is required
- All tests must pass
- Code style checks must pass
- Branch must be up to date with main

## Reporting Issues

### Bug Reports

Use the [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.md):

- **Clear title**: Describe the problem in a few words
- **Steps to reproduce**: Exact steps to reproduce the issue
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Environment**: OS, Node/Python version, browser (if relevant)
- **Screenshots/Logs**: If applicable

### Feature Requests

Use the [Feature Request Template](.github/ISSUE_TEMPLATE/feature_request.md):

- **Clear description**: What feature should be added
- **Motivation**: Why is this feature needed
- **Proposed solution**: How it should work (if you have ideas)
- **Alternative approaches**: Other solutions considered
- **Additional context**: Anything else relevant

## Code Style Guidelines

### JavaScript/Node.js

- Use ESLint configuration (run `npm run lint`)
- Use Prettier for formatting (run `npm run format`)
- Prefer async/await over callbacks
- Use meaningful variable names
- Add JSDoc comments for public functions

```javascript
/**
 * Process a job from the queue
 * @param {Object} job - The job to process
 * @param {string} job.id - Job ID
 * @returns {Promise<Object>} Processing result
 */
async function processJob(job) {
  // Implementation
}
```

### Python

- Follow PEP 8 style guide
- Use Black for formatting
- Use type hints
- Add docstrings using Google style

```python
def process_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Process a job from the queue.
    
    Args:
        job: The job to process with 'id' and 'data' keys.
        
    Returns:
        Processing result with status and output.
    """
    # Implementation
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/              # Unit tests (no external dependencies)
│   ├── test_job.js
│   ├── test_queue.js
│   └── test_worker.js
├── integration/       # Integration tests (with external services)
│   └── test_e2e.js
└── fixtures/          # Test data and mocks
    └── mock_jobs.js
```

### Writing Tests

```javascript
// Unit test example
describe('Worker', () => {
  let worker;
  
  beforeEach(() => {
    worker = new Worker();
  });
  
  afterEach(() => {
    worker.stop();
  });
  
  it('should process a job successfully', async () => {
    worker.register('test', async (job) => {
      return { success: true };
    });
    
    const result = await worker.process({ type: 'test', data: {} });
    expect(result.success).toBe(true);
  });
});
```

### Test Coverage

Aim for >80% code coverage:

```bash
npm run test:coverage
pytest --cov=worker tests/
```

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Issues**: Check existing issues before creating new ones
- **Slack/Chat**: Contact maintainers for real-time discussion
- **Email**: support@tannerpresscorp.com

## Maintainer Notes

If you become a maintainer, see [MAINTAINERS.md](MAINTAINERS.md) for additional responsibilities.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
