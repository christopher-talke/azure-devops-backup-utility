# Contributing

This document covers development setup, project structure, testing, and contribution guidelines.

## Getting Started

### Requirements

| Requirement | Version |
|---|---|
| Python | >= 3.9 |
| Azure CLI | >= 2.30 (for integration testing) |
| Git | Any recent version |

There are **no external Python dependencies**. The project uses only the Python standard library.

### Setup

```bash
# Clone the repository
git clone https://github.com/christopher-talke/azure-devops-backup-utility.git
cd azure-devops-backup-utility

# No virtual environment or pip install required - stdlib only
# Set the Python path for running the tool directly
export PYTHONPATH=src
```

## Project Structure

```
src/
  cli.py               # argparse CLI
  config.py            # Configuration merge (env, CLI, YAML) with validation
  compress.py          # Backup compression with archive verification
  azcli.py             # az CLI wrapper with retry, pagination, and secure git clone
  backoff.py           # Exponential backoff with jitter
  paginator.py         # Continuation token pagination
  paths.py             # Output directory path builder with traversal protection
  redact.py            # Sensitive field and isSecret-aware redaction
  writers.py           # Atomic JSON/binary writers with secure permissions and checksums
  inventory.py         # Manifest and inventory tracking with PAT scrubbing
  orchestrator.py      # Full backup orchestration
  scopes/
    org.py             # Org-level exports
    projects.py        # Project enumeration and metadata
    git.py             # Repository backup
    pull_requests.py   # Pull request data
    boards.py          # Work items and boards
    pipelines.py       # Pipeline definitions and runs
    artifacts.py       # Artifact feeds
    dashboards.py      # Dashboards and widgets
    permissions.py     # Security namespaces and ACLs
    wikis.py           # Wiki pages
    testplans.py       # Test plans and suites
tests/                 # pytest unit tests
examples/              # CI/CD pipeline examples
```

## Architecture

### Configuration Flow

Configuration is resolved in priority order: CLI arguments > environment variables > YAML config file > built-in defaults. The `BackupConfig` dataclass in `src/config.py` holds the merged result.

### Orchestration

`src/orchestrator.py` drives the backup:

1. Creates a timestamped output directory via `BackupPaths`
2. Initialises the `Inventory` tracker
3. Ensures the Azure DevOps CLI extension is installed
4. Configures `az devops` defaults for the organisation
5. Runs org-level backup (if included)
6. Enumerates projects (filtered by `--projects` if specified)
7. For each project, calls each active scope module in order
8. Writes inventory, manifest, and error files
9. Runs compression if configured

Each scope call is wrapped in `_safe_call` which catches exceptions unless `--fail-fast` is set.

### Scope Modules

Each file under `src/scopes/` exports a single `backup_*()` function that:

1. Accepts the `BackupPaths` instance, project name, config, and inventory
2. Calls the Azure DevOps API via `azcli.az()` or `azcli.invoke()`
3. Passes data through `redact.redact()` before writing
4. Writes output via `writers.write_json()` or `writers.write_binary()`
5. Records entities in the inventory with SHA-256 checksums

### API Layer

`src/azcli.py` wraps all Azure CLI interactions:

- **`az()`** - runs native `az` subcommands (e.g., `az repos list`)
- **`invoke()`** - runs `az devops invoke` for REST endpoints, with automatic pagination
- **`git_clone()`** - secure mirror clone with PAT via environment variables

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_redact.py -v

# Run with coverage (requires pytest-cov)
python -m pytest tests/ --cov=src --cov-report=term-missing
```

All tests use the `unittest` module with `pytest` as the test runner. No real `az` binary is required - tests mock `subprocess.run` or higher-level `azcli.*` functions.

## Adding a New Backup Scope

1. Create `src/scopes/{name}.py` with a `backup_{name}(paths, project, cfg, inventory)` function
2. Add `"{name}"` to `ALL_COMPONENTS` in `src/config.py`
3. Add path helpers to `src/paths.py`
4. Call the new scope from `src/orchestrator.py` inside the project loop
5. Add tests in `tests/test_{name}.py`
6. Update the [Backup Components](./reference/components) documentation

### Scope Implementation Checklist

- [ ] API data passes through `redact.redact()` before writing
- [ ] Output written via `writers.write_json()` or `writers.write_binary()`
- [ ] Entities recorded in inventory via `inventory.add()`
- [ ] Errors caught and recorded via `inventory.add_error()` (unless `fail_fast`)
- [ ] `max_items` respected where applicable
- [ ] `since` filtering applied where applicable
- [ ] `dry_run` mode skips writes

## Code Conventions

- **No external dependencies** - everything must use the Python standard library
- **Redaction first** - always redact API responses before writing to disk
- **Atomic writes** - use `writers.write_json()` / `writers.write_binary()` which write to a temp file then rename
- **Inventory everything** - all written files must be tracked in the inventory with checksums
- **Scrub errors** - PAT values must be removed from any error messages before persisting

## Licence

MIT - See [LICENSE](https://github.com/christopher-talke/azure-devops-backup-utility/blob/main/LICENSE).
