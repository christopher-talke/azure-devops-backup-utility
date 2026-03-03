# Azure DevOps Backup Utility

A production-grade, non-interactive backup tool for Azure DevOps that uses only Azure CLI (`az devops`) commands and Git CLI to retrieve and persist data. Designed for CI/CD pipelines with zero external Python dependencies.

## Features

- **Full data coverage**: organisations, projects, repos, boards, pipelines, permissions
- **Azure CLI only**: all API access via `az devops` / `az devops invoke` — no direct HTTP clients
- **Git CLI**: repository content cloned via `git clone --mirror`
- **Standard library only**: no pip dependencies beyond Python ≥ 3.9
- **Non-interactive**: designed for CI/CD (Azure Pipelines, GitHub Actions)
- **Resilient**: exponential backoff with jitter, throttle-aware retries, partial progress tracking
- **Redaction**: sensitive fields (secrets, tokens, passwords) automatically masked before persisting
- **Configurable**: CLI flags, environment variables, and optional YAML config file

## Prerequisites

| Requirement | Version |
|---|---|
| Python | ≥ 3.9 |
| Azure CLI | ≥ 2.30 |
| Azure DevOps CLI extension | auto-installed if missing |
| Git | any recent version |

### PAT Permissions

The Personal Access Token must have at least these scopes:

| Scope | Access |
|---|---|
| Project and Team | Read |
| Code | Read |
| Work Items | Read |
| Build | Read |
| Release | Read |
| Graph (Users/Groups) | Read |
| Security (Permissions) | Read |
| Service Connections | Read |
| Variable Groups | Read |
| Agent Pools | Read |

## Quick Start

```bash
# Set required environment variables
export AZURE_DEVOPS_EXT_PAT="your-personal-access-token"
export AZURE_DEVOPS_ORG_URL="https://dev.azure.com/your-org"

# Run the backup
python src/cli.py

# Or with options
python src/cli.py \
  --projects "Project1,Project2" \
  --output-dir ./my-backup \
  --max-items 100 \
  --verbose
```

## CLI Options

| Flag | Default | Description |
|---|---|---|
| `--org-url` | `$AZURE_DEVOPS_ORG_URL` | Azure DevOps organisation URL |
| `--projects` | `all` | Comma-separated project names or `all` |
| `--include` | all components | Comma-separated: `org,projects,git,boards,pipelines,permissions` |
| `--exclude` | none | Components to skip |
| `--since` | — | ISO timestamp for incremental filtering |
| `--max-items` | `0` (unlimited) | Per-entity item limit |
| `--concurrency` | `4` | Number of concurrent workers |
| `--output-dir` | `ado-backup` | Root output directory |
| `--config` | — | Path to YAML configuration file |
| `--fail-fast` | `false` | Abort on first error |
| `--dry-run` | `false` | Preview without writing data |
| `--verbose` | `false` | Enable debug logging |

## Environment Variables

| Variable | Purpose |
|---|---|
| `AZURE_DEVOPS_EXT_PAT` | Personal Access Token (required) |
| `AZURE_DEVOPS_ORG_URL` | Organisation URL (required) |
| `ADO_BACKUP_OUTPUT_DIR` | Override default output directory |
| `ADO_BACKUP_TIMEOUT` | CLI command timeout in seconds |

## YAML Configuration

Create a `config.yaml`:

```yaml
org-url: https://dev.azure.com/myorg
projects: all
include: org,projects,git,boards,pipelines
max-items: 500
concurrency: 4
output-dir: ./backup
verbose: false
```

Then run: `python src/cli.py --config config.yaml`

## Output Structure

```
ado-backup/
  {host}/{org-name}/{YYYYMMDDTHHMMSSZ}/
    org/
      users.json
      groups.json
      memberships.json
      service_connections.json
      variable_groups.json
      agent_pools.json
      queues.json
      permissions_acl.json
    projects/
      {project-name}/
        metadata/
          project.json
          teams.json
          areas.json
          iterations.json
          permissions_acl.json
        git/
          repos.json
          {repo-name}/          # mirror clone
        boards/
          work_items/
            index.json
            {id}.json
          queries.json
          tags.json
        pipelines/
          pipelines.json
          classic_build_definitions.json
          classic_release_definitions.json
          runs_index.json
    _indexes/
      inventory.json
      manifest.json
      errors.jsonl
```

## Data Coverage

| Category | Method | Notes |
|---|---|---|
| Users & Groups | `az devops invoke` (Graph API) | AAD/MSA users, security groups |
| Service Connections | `az devops invoke` | Secrets redacted |
| Variable Groups | `az devops invoke` | Secret values redacted |
| Agent Pools/Queues | `az devops invoke` | Metadata only |
| Projects | `az devops project list/show` | Full project properties |
| Teams/Areas/Iterations | `az devops invoke` | Full hierarchy |
| Git Repositories | `az repos list` + `git clone --mirror` | All branches/tags |
| Work Items | `az boards query` + `az boards work-item show` | Full fields, relations |
| Queries & Tags | `az devops invoke` | Board queries and tags |
| Pipelines (YAML) | `az pipelines list` | Definitions metadata |
| Classic Build Defs | `az devops invoke` | Tasks and variables (redacted) |
| Classic Release Defs | `az devops invoke` | Tasks and variables (redacted) |
| Pipeline Runs | `az devops invoke` | Index with configurable limits |
| Permissions/ACLs | `az devops invoke` | Security namespaces and ACLs |

### Known Limitations

- Wiki content export is not yet implemented
- Artifacts feed metadata export is not yet implemented
- Test plans/suites export is not yet implemented
- Work item attachments (binary download) is not yet implemented
- Incremental (`--since`) filtering depends on API support per entity

## Security & Redaction

- The PAT is **never** logged or persisted
- Fields named `password`, `secret`, `token`, `privateKey`, `certificate`, `apiKey`, `accessToken`, `connectionString`, `secureFileId` are automatically replaced with `***REDACTED***`
- The path `authorization.parameters` is always redacted
- Service connections and variable groups are redacted before writing

## Performance & Throttling

- All API calls use exponential backoff with jitter (default: 5 retries)
- HTTP 429 and 5xx errors trigger automatic retry with increasing delay
- Use `--max-items` to cap per-entity exports for CI-friendly runs
- Use `--concurrency` to control parallelism (future enhancement)
- Large organisations: consider backing up subsets of projects with `--projects`

## Storage Footprint

- JSON exports are typically small (KB–MB per entity)
- Git mirror clones can be large depending on repository size
- Use `--exclude git` to skip repository cloning if storage is limited
- Recommended: set artifact retention policies in your CI system

## Running Tests

```bash
cd /path/to/repo
python -m pytest tests/ -v
```

## Project Structure

```
src/
  __init__.py          # Package init
  __main__.py          # Entry point
  cli.py               # argparse CLI
  config.py            # Configuration merge (env, CLI, YAML)
  azcli.py             # az CLI wrapper with retry
  backoff.py           # Exponential backoff with jitter
  paginator.py         # Continuation token pagination
  paths.py             # Output directory path builder
  redact.py            # Sensitive field redaction
  writers.py           # Atomic JSON/binary writers
  inventory.py         # Manifest and inventory tracking
  orchestrator.py      # Full backup orchestration
  scopes/
    __init__.py
    org.py             # Org-level exports
    projects.py        # Project enumeration
    git.py             # Repository backup
    boards.py          # Work items, queries, tags
    pipelines.py       # Pipeline definitions and runs
    permissions.py     # ACL and security export
tests/
  test_redact.py
  test_paths.py
  test_config.py
  test_backoff.py
  test_writers.py
  test_paginator.py
  test_azcli.py
```

## License

MIT — see [LICENSE](LICENSE).