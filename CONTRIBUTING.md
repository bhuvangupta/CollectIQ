# Contributing to CollectIQ

Thank you for your interest in contributing to CollectIQ! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](../../issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce the bug
   - Expected vs actual behavior
   - Environment details (OS, Python/Node version, etc.)
   - Screenshots if applicable

### Suggesting Features

1. Check existing issues for similar suggestions
2. Create a new issue with:
   - Clear description of the feature
   - Use case and motivation
   - Proposed implementation (optional)

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Run tests and linting
5. Commit with clear messages
6. Push to your fork
7. Open a Pull Request

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/collectiq.git
cd collectiq

# Install dependencies
./scripts/install.sh

# Setup database
./scripts/setup_db.sh

# Start development servers
./scripts/start.sh
```

### Running Tests

```bash
# Backend tests
./scripts/test.sh backend

# Frontend tests
./scripts/test.sh frontend

# All tests with coverage
./scripts/test.sh cov
```

### Code Style

#### Python (Backend)
- Follow PEP 8
- Use type hints
- Format with Black
- Lint with Ruff

```bash
./scripts/lint.sh fix
```

#### TypeScript (Frontend)
- Use TypeScript strict mode
- Follow ESLint configuration
- Format with Prettier

```bash
cd frontend && npm run lint
```

## Project Structure

```
collectiq/
├── backend/          # FastAPI backend
├── frontend/         # React frontend
├── ai_engine/        # AI/ML services
├── telephony/        # Telephony service
└── scripts/          # Utility scripts
```

## Commit Messages

Use clear, descriptive commit messages:

- `feat: add payment recording feature`
- `fix: resolve case assignment bug`
- `docs: update API documentation`
- `refactor: simplify authentication flow`
- `test: add unit tests for cases endpoint`

## Pull Request Guidelines

1. **One feature per PR** - Keep PRs focused and manageable
2. **Update documentation** - If your change affects the API or usage
3. **Add tests** - For new features and bug fixes
4. **Pass CI checks** - Ensure all tests and linting pass
5. **Describe changes** - Provide clear PR description

## Getting Help

- Open an issue for questions
- Tag maintainers for urgent items
- Check existing documentation

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
