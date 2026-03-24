# Azure DevOps Backup Utility

> **Warning**
> This project has been generated with the assistance of Anthropic's Claude LLM models. Please be aware of this before running it against production systems, and take the time to understand how the project works before using it.

A non-interactive backup tool for Azure DevOps that uses only Azure CLI (`az devops`) commands and Git CLI to retrieve and persist data. Designed for CI/CD pipelines with zero external Python dependencies.

## Features

- **Full data coverage** — organisations, projects, repos, boards, pipelines, permissions
- **Azure CLI only** — all API access via `az devops` / `az devops invoke`; no direct HTTP clients
- **Git CLI** — repository content cloned via `git clone --mirror`
- **Standard library only** — no pip dependencies beyond Python >= 3.9
- **Non-interactive** — designed for CI/CD (Azure Pipelines, GitHub Actions)
- **Resilient** — exponential backoff with jitter, throttle-aware retries, partial progress tracking
- **Redaction** — sensitive fields (secrets, tokens, passwords, `isSecret` variables) automatically masked before persisting across all backup scopes
- **Secure credential handling** — PAT passed to git via environment variables (never in process arguments or on-disk config)
- **Hardened output** — backup directories created with restricted permissions (`0700` on Unix)
- **Input validation** — path traversal protection, config value whitelisting, output directory sanitisation
- **Configurable** — CLI flags, environment variables, and optional YAML config file

## Prerequisites

| Requirement | Version |
|---|---|
| Python | >= 3.9 |
| Azure CLI | >= 2.30 |
| Azure DevOps CLI extension | auto-installed if missing |
| Git | any recent version |

### Authentication

The tool uses Azure CLI authentication.

In Azure DevOps Pipelines, configure the `AZURE_DEVOPS_EXT_PAT` environment variable to `$(System.AccessToken)` so the pipeline's system token is used for all API calls.

A Personal Access Token (PAT) can optionally be provided via `AZURE_DEVOPS_EXT_PAT` or `SYSTEM_ACCESSTOKEN` environment variables. If no PAT is set, the tool relies on whatever authentication the `az` CLI already has configured.

When a PAT is provided, it is used for `git clone --mirror` authentication via git config environment variables. The PAT never appears in process arguments or on-disk git config files.

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
export PYTHONPATH=src
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
| `AZURE_DEVOPS_EXT_PAT` | Personal Access Token (optional; used by az CLI and git clone) |
| `SYSTEM_ACCESSTOKEN` | Azure Pipelines system token (auto-detected as PAT fallback) |
| `AZURE_DEVOPS_ORG_URL` | Organisation URL (required) |
| `ADO_BACKUP_OUTPUT_DIR` | Override default output directory |
| `ADO_BACKUP_TIMEOUT` | CLI command timeout in seconds (default: 120) |

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

Then run:

```bash
python src/cli.py --config config.yaml
```

Unknown YAML keys are logged as warnings and ignored. The `pat` key is accepted but discouraged — use the `AZURE_DEVOPS_EXT_PAT` environment variable instead.

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
          security_namespaces.json
          permissions_acl.json
        git/
          repos.json
          {repo-name}_branches.json
          {repo-name}_policies.json
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
| Users and Groups | `az devops invoke` (Graph API) | AAD/MSA users, security groups |
| Service Connections | `az devops invoke` | Secrets redacted |
| Variable Groups | `az devops invoke` | Secret values redacted (including `isSecret` fields) |
| Agent Pools/Queues | `az devops invoke` | Metadata only |
| Projects | `az devops project list/show` | Full project properties |
| Teams/Areas/Iterations | `az devops invoke` | Full hierarchy |
| Git Repositories | `az repos list` + `git clone --mirror` | All branches/tags; metadata redacted |
| Work Items | `az boards query` + `az boards work-item show` | Full fields and relations; redacted |
| Queries and Tags | `az devops invoke` | Board queries and tags; redacted |
| Pipelines (YAML) | `az pipelines list` | Definitions metadata; redacted |
| Pipeline Runs | `az devops invoke` | Index with configurable limits; redacted |
| Permissions/ACLs | `az devops invoke` | Security namespaces and ACLs; redacted |

### Known Limitations

- Wiki content export is not yet implemented
- Artifacts feed metadata export is not yet implemented
- Test plans/suites export is not yet implemented
- Work item attachments (binary download) are not yet implemented
- Incremental (`--since`) filtering depends on API support per entity

## Security and Redaction

All backup scopes (org, git, boards, pipelines, permissions) pass API data through the redaction engine before writing to disk.

### Credential Handling

- The PAT is **never** logged, persisted to disk, or passed in process arguments
- Git clone authentication uses `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY` / `GIT_CONFIG_VALUE` environment variables with Base64-encoded Basic auth — the PAT never appears in `argv` or on-disk git config
- Error messages written to `errors.jsonl` are scrubbed of PAT values before persisting

### Field Redaction

Fields matching the following names (case-insensitive) are replaced with `***REDACTED***`:

`password`, `secret`, `token`, `privatekey`, `private_key`, `certificate`, `apikey`, `api_key`, `accesstoken`, `access_token`, `connectionstring`, `connection_string`, `securefileid`, `client_secret`, `clientsecret`, `sas_token`, `sastoken`, `encrypted_value`, `encryptedvalue`, `credentials`, `subscription_key`, `subscriptionkey`

### Path Redaction

The following dot-separated JSON paths are always redacted:

- `authorization.parameters`
- `configuration.value`
- `data.accesstoken`

### Contextual Redaction

Objects containing `"isSecret": true` (or `issecret`, `is_secret`) have their `value` field redacted automatically. This catches Azure DevOps variable group secrets where the key name is generic.

### Output Hardening

- Backup directories are created with `0700` permissions on Unix systems
- File names derived from API data are sanitised to prevent path traversal (`..` is stripped)
- The `output_dir` config value is validated to reject `..` path components
- Compression operations verify that source paths are within the backup tree before deletion

## Performance and Throttling

- All API calls use exponential backoff with jitter (default: 5 retries)
- HTTP 429 and 5xx errors trigger automatic retry with increasing delay
- Use `--max-items` to cap per-entity exports for CI-friendly runs
- Large organisations: consider backing up subsets of projects with `--projects`

## Storage Footprint

- JSON exports are typically small (KB-MB per entity)
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

GitHub Actions examples pin actions to commit SHAs for supply chain security. Azure Pipelines examples use schedule-only triggers (no push triggers) to prevent compromised commits from triggering backup runs.

## Running Tests

```bash
cd /path/to/repo
python -m pytest tests/ -v
```

All log output is directed to stderr, keeping stdout clean for programmatic consumption.

## Project Structure

```
examples/
  azure-pipelines.yml                # ADO pipeline (artifact upload, schedule-only)
  azure-pipelines-blob-storage.yml   # ADO pipeline -> Azure Blob Storage
  github-actions-backup.yml          # GitHub Actions (artifact upload)
  github-actions-blob-storage.yml    # GitHub Actions -> Azure Blob Storage
  github-actions-s3.yml              # GitHub Actions -> AWS S3 (with SSE)
  config.yaml                        # Example YAML configuration
src/
  __init__.py          # Package init
  __main__.py          # Entry point
  cli.py               # argparse CLI
  config.py            # Configuration merge (env, CLI, YAML) with validation
  compress.py          # Backup compression with bounds checking
  azcli.py             # az CLI wrapper with retry and secure git clone
  backoff.py           # Exponential backoff with jitter
  paginator.py         # Continuation token pagination
  paths.py             # Output directory path builder with traversal protection
  redact.py            # Sensitive field and isSecret-aware redaction
  writers.py           # Atomic JSON/binary writers with secure permissions
  inventory.py         # Manifest and inventory tracking with PAT scrubbing
  orchestrator.py      # Full backup orchestration
  scopes/
    __init__.py
    org.py             # Org-level exports (redacted)
    projects.py        # Project enumeration
    git.py             # Repository backup (redacted)
    boards.py          # Work items, queries, tags (redacted)
    pipelines.py       # Pipeline definitions and runs (redacted)
    permissions.py     # ACL and security export (redacted)
tests/
  test_azcli.py
  test_backoff.py
  test_compress.py
  test_config.py
  test_paginator.py
  test_paths.py
  test_redact.py
  test_writers.py
```

## License

MIT — See [LICENSE](LICENSE).
