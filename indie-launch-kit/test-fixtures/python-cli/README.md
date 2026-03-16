# TaskFlow CLI

> A fast, opinionated task runner for developers who live in the terminal.

TaskFlow CLI lets you define, organize, and execute project tasks using simple TOML config files. Think of it as a modern alternative to Makefiles that understands your development workflow.

## Features

- **TOML-based task definitions** with dependency graphs
- **Parallel execution** of independent tasks
- **Watch mode** that re-runs tasks on file changes
- **Environment management** with `.env` file support and variable interpolation
- **Shell completion** for Bash, Zsh, and Fish
- **Dry-run mode** to preview commands before execution
- **Cross-platform** support for Linux, macOS, and Windows

## Installation

Install from PyPI:

```bash
pip install taskflow-cli
```

Or with pipx for isolated installation:

```bash
pipx install taskflow-cli
```

### From Source

```bash
git clone https://github.com/mnavarro/taskflow-cli.git
cd taskflow-cli
pip install -e ".[dev]"
```

## Usage

### Initialize a Project

```bash
taskflow init
```

This creates a `taskflow.toml` file in your project root with some example tasks.

### Define Tasks

Edit `taskflow.toml`:

```toml
[tasks.lint]
cmd = "ruff check src/"
description = "Run linter on source files"

[tasks.test]
cmd = "pytest tests/ -v"
description = "Run the test suite"
depends_on = ["lint"]

[tasks.build]
cmd = "python -m build"
description = "Build distribution packages"
depends_on = ["test"]
env = { PYTHONDONTWRITEBYTECODE = "1" }
```

### Run Tasks

```bash
# Run a single task
taskflow run test

# Run multiple tasks
taskflow run lint test

# Run with watch mode
taskflow run test --watch

# Dry run (show commands without executing)
taskflow run build --dry-run

# Run tasks in parallel where possible
taskflow run lint test --parallel
```

### List Available Tasks

```bash
$ taskflow list

  Task     Description                    Depends On
  ----     -----------                    ----------
  lint     Run linter on source files     -
  test     Run the test suite             lint
  build    Build distribution packages    test
```

### Environment Variables

```bash
# Run a task with extra env vars
taskflow run deploy --env STAGE=production --env REGION=us-east-1

# Use a specific .env file
taskflow run deploy --env-file .env.production
```

### Shell Completion

```bash
# Bash
taskflow completions bash >> ~/.bashrc

# Zsh
taskflow completions zsh >> ~/.zshrc

# Fish
taskflow completions fish > ~/.config/fish/completions/taskflow.fish
```

## Configuration

TaskFlow reads configuration from `taskflow.toml` in the current directory or any parent directory.

### Global Settings

```toml
[settings]
shell = "/bin/bash"          # Default shell for commands
dotenv = true                # Auto-load .env file
parallel_limit = 4           # Max parallel tasks
log_level = "info"           # Logging verbosity: debug, info, warn, error
```

### Task Options

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `cmd` | `string` | Yes | The command to execute |
| `description` | `string` | No | Human-readable description |
| `depends_on` | `list[str]` | No | Tasks that must run first |
| `env` | `table` | No | Environment variables for this task |
| `workdir` | `string` | No | Working directory for the command |
| `silent` | `bool` | No | Suppress command output |
| `ignore_errors` | `bool` | No | Continue even if the command fails |

## Contributing

We welcome contributions of all kinds. Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Clone and set up dev environment
git clone https://github.com/mnavarro/taskflow-cli.git
cd taskflow-cli
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/
```

All commits should follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

## License

MIT License. See [LICENSE](LICENSE) for details.

Maintained by [Maria Navarro](https://github.com/mnavarro).
