# Development Guide

This document covers development setup, project structure, testing, and contribution guidelines for the Azure DevOps Backup Utility.

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
  __init__.py          # Package init
  __main__.py          # Entry point
  cli.py               # argparse CLI
  config.py            # Configuration merge (env, CLI, YAML) with validation
  compress.py          # Backup compression with archive verification
  azcli.py             # az CLI wrapper with retry, pagination, and secure git clone
  backoff.py           # Exponential backoff with jitter
  paginator.py         # Continuation token pagination (legacy; pagination now built into azcli.invoke)
  paths.py             # Output directory path builder with traversal protection
  redact.py            # Sensitive field and isSecret-aware redaction
  writers.py           # Atomic JSON/binary writers with secure permissions and checksums
  inventory.py         # Manifest and inventory tracking with PAT scrubbing and SHA-256 hashing
  orchestrator.py      # Full backup orchestration
  scopes/
    __init__.py
    org.py             # Org-level exports (users, groups, memberships, service connections, variable groups)
    projects.py        # Project enumeration and metadata (teams, areas, iterations, ACLs)
    git.py             # Repository backup (clone, branches, tags, policies)
    pull_requests.py   # Pull request metadata, threads, and work item links
    boards.py          # Work items, queries, tags, board config, team settings
    pipelines.py       # Pipeline definitions, runs, environments, secure files, task groups, releases
    artifacts.py       # Azure Artifacts feed configs and package metadata
    dashboards.py      # Dashboards, widgets, and notification subscriptions
    permissions.py     # Security namespaces (cached) and project-level ACLs
tests/
  test_azcli.py        # PAT masking, JSON parsing, error handling, throttle detection
  test_backoff.py      # Retry behaviour, exhaustion, non-retryable exceptions
  test_compress.py     # Archive creation, verification, all compression modes
  test_config.py       # Defaults, validation, env var loading, CLI overrides
  test_paginator.py    # Single page, multi-page, max_pages limits
  test_paths.py        # safe_name, URL parsing, all path builders
  test_redact.py       # Key/path/contextual redaction, case-insensitivity, data preservation
  test_writers.py      # JSON/binary writes, JSONL append, pretty printing
examples/
  azure-pipelines.yml                # ADO pipeline (artifact upload, schedule-only)
  azure-pipelines-blob-storage.yml   # ADO pipeline to Azure Blob Storage
  github-actions-backup.yml          # GitHub Actions (artifact upload)
  github-actions-blob-storage.yml    # GitHub Actions to Azure Blob Storage
  github-actions-s3.yml              # GitHub Actions to AWS S3 (with SSE)
  config.yaml                        # Example YAML configuration
```

## Architecture

### Configuration Flow

Configuration is resolved in the following priority order (highest wins):

1. CLI arguments
2. Environment variables
3. YAML config file
4. Built-in defaults

The `BackupConfig` dataclass in `src/config.py` holds the merged result. Validation rejects invalid component names, unsafe output directory paths, and unrecognised compress modes.

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

Each scope call is wrapped in `_safe_call` which catches exceptions unless `--fail-fast` is set, allowing partial backups to complete even if individual scopes fail.

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
- **`invoke()`** - runs `az devops invoke` for REST endpoints, with automatic pagination via continuation tokens
- **`git_clone()`** - secure mirror clone with PAT via environment variables

All API calls go through exponential backoff retry (see `src/backoff.py`) and detect HTTP 429/5xx for throttle-aware retries.

### Security Design

- **Redaction** (`src/redact.py`): Three strategies (key-name, path-based, contextual `isSecret`) applied to deep copies of API data before writing
- **Credential handling**: PAT never logged, written to disk, or passed in process arguments; git clone uses `GIT_CONFIG_*` env vars
- **Output hardening**: Directories created with `0700` permissions; file names sanitised against path traversal
- **Error scrubbing**: PAT values removed from error messages before persisting to `errors.jsonl`

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_redact.py -v

# Run with coverage (requires pytest-cov)
python -m pytest tests/ --cov=src --cov-report=term-missing
```

All tests use the `unittest` module. No external test dependencies are required beyond `pytest` as the test runner.

All log output is directed to stderr, keeping stdout clean for programmatic consumption.

## Adding a New Backup Scope

To add a new scope (e.g., `wikis`):

1. Create `src/scopes/wikis.py` with a `backup_wikis(paths, project, cfg, inventory)` function
2. Add `"wikis"` to `ALL_COMPONENTS` in `src/config.py`
3. Add path helpers to `src/paths.py` (e.g., `wikis_dir()`)
4. Call the new scope from `src/orchestrator.py` inside the project loop
5. Add tests in `tests/test_wikis.py`
6. Update the feature support tables in `README.md`

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

MIT - See [LICENCE](LICENSE).
