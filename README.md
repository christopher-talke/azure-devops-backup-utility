# Azure DevOps Backup Utility

A non-interactive backup tool for Azure DevOps that uses only Azure CLI (`az devops`) commands and Git CLI to retrieve and persist data. 

Designed for CI/CD pipelines with zero external Python dependencies.

## Warning

🤖 This project has been generated with the assistance of Anthropics Claude LLM Models, please be aware of this before running this against production systems, and please take the time to understand how this project works before blindly running it.

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

### Authentication

The tool uses Azure CLI authentication. 

In Azure DevOps Pipelines, configure the `AZURE_DEVOPS_EXT_PAT` environment variable to `$(System.AccessToken)` so the pipeline's system token is used for all API calls.

A Personal Access Token (PAT) can optionally be provided via `AZURE_DEVOPS_EXT_PAT` or `SYSTEM_ACCESSTOKEN` environment variables. If no PAT is set, the tool relies on whatever authentication the `az` CLI already has configured.

When a PAT is provided, it is also used for `git clone --mirror` authentication. Without a PAT, git clones rely on existing credential helpers.

#### PAT Scopes (if using a PAT)

| Scope | Access |
|---|---|
| Project and Team | Read |
| Code | Read |
| Work Items | Read |
| Build | Read |
| Graph (Users/Groups) | Read |
| Security (Permissions) | Read |
| Service Connections | Read |
| Variable Groups | Read |
| Agent Pools | Read |

## Quick Start

```bash
# Set required environment variables
export AZURE_DEVOPS_ORG_URL="https://dev.azure.com/your-org"

# Optional: provide a PAT (otherwise relies on az CLI auth)
export AZURE_DEVOPS_EXT_PAT="your-personal-access-token"

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
| `--compress` | — | Compress output: `repos`, `project`, or `all` |
| `--output-dir` | `ado-backup` | Root output directory |
| `--config` | — | Path to YAML configuration file |
| `--fail-fast` | `false` | Abort on first error |
| `--dry-run` | `false` | Preview without writing data |
| `--verbose` | `false` | Enable debug logging |

## Environment Variables

| Variable | Purpose |
|---|---|
| `AZURE_DEVOPS_EXT_PAT` | Personal Access Token (optional – used by az CLI and git clone) |
| `SYSTEM_ACCESSTOKEN` | Azure Pipelines system token (auto-detected as PAT fallback) |
| `AZURE_DEVOPS_ORG_URL` | Organisation URL (required) |
| `ADO_BACKUP_OUTPUT_DIR` | Override default output directory |
| `ADO_BACKUP_TIMEOUT` | CLI command timeout in seconds |

## YAML Configuration

Create a `config.yaml` (see [`examples/config.yaml`](examples/config.yaml)):

```yaml
org-url: https://dev.azure.com/myorg
projects: all
include: org,projects,git,boards,pipelines
max-items: 500
compress: repos
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
- Large organisations: consider backing up subsets of projects with `--projects`

## Storage Footprint

- JSON exports are typically small (KB–MB per entity)
- Git mirror clones can be large depending on repository size
- Use `--exclude git` to skip repository cloning if storage is limited
- Use `--compress repos` to tar.gz each mirror clone, `--compress project` for per-project archives, or `--compress all` for a single archive
- Recommended: set artifact retention policies in your CI system

## CI/CD Examples

Ready-to-use pipeline definitions are in the [`examples/`](examples/) folder:

| File | Platform | Upload target |
|---|---|---|
| [`azure-pipelines.yml`](examples/azure-pipelines.yml) | Azure DevOps | Build artifacts |
| [`azure-pipelines-blob-storage.yml`](examples/azure-pipelines-blob-storage.yml) | Azure DevOps | Azure Blob Storage |
| [`github-actions-backup.yml`](examples/github-actions-backup.yml) | GitHub Actions | Workflow artifacts |
| [`github-actions-blob-storage.yml`](examples/github-actions-blob-storage.yml) | GitHub Actions | Azure Blob Storage |
| [`github-actions-s3.yml`](examples/github-actions-s3.yml) | GitHub Actions | AWS S3 |
| [`config.yaml`](examples/config.yaml) | — | Example YAML config |

Copy the relevant file into your project and adjust variables/secrets as described in the file comments.

## Running Tests

```bash
cd /path/to/repo
python -m pytest tests/ -v
```

## Project Structure

```
examples/
  azure-pipelines.yml                # ADO pipeline (artifact upload)
  azure-pipelines-blob-storage.yml   # ADO pipeline → Azure Blob Storage
  github-actions-backup.yml          # GitHub Actions (artifact upload)
  github-actions-blob-storage.yml    # GitHub Actions → Azure Blob Storage
  github-actions-s3.yml              # GitHub Actions → AWS S3
  config.yaml                        # Example YAML configuration
src/
  __init__.py          # Package init
  __main__.py          # Entry point
  cli.py               # argparse CLI
  config.py            # Configuration merge (env, CLI, YAML)
  compress.py          # Backup compression (repos, project, all)
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
  test_compress.py
  test_backoff.py
  test_writers.py
  test_paginator.py
  test_azcli.py
```

## License

MIT - See [LICENSE](LICENSE).