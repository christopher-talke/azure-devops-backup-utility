# Introduction

The Azure DevOps Backup Utility (`ado-backup`) is a non-interactive CLI tool that backs up Azure DevOps organisations to disk. It uses only the Azure CLI (`az devops`) and Git CLI to retrieve and persist data - no direct HTTP clients, no external Python dependencies.

::: warning Pull-and-store only
This tool creates offline copies of your Azure DevOps data. There is no automated restore functionality - Azure DevOps does not provide programmatic APIs for restoring data. Recovery from backups is a manual process.
:::

::: warning AI-generated project
This project was generated with the assistance of Anthropic's Claude LLM models. Please take the time to understand how it works before running it against production systems.
:::

## Key Features

- **Broad data coverage** - organisations, projects, repos, pull requests, boards, pipelines, artifacts, dashboards, permissions, wikis, and test plans
- **Azure CLI only** - all API access via `az devops` / `az devops invoke`
- **Standard library only** - no pip dependencies beyond Python >= 3.9
- **Non-interactive** - designed for CI/CD (Azure Pipelines, GitHub Actions)
- **Automatic pagination** - continuation token handling so large result sets are never silently truncated
- **Incremental filtering** - `--since` flag filters work items and pipeline runs by date
- **Resilient** - exponential backoff with jitter, throttle-aware retries, partial progress tracking
- **Secure** - automatic secret redaction, PAT never in argv, restricted directory permissions
- **Integrity** - SHA-256 checksums per file, archive verification, live verification against ADO
- **Compression** - per-repo, per-project, or full backup compression
- **Dashboard** - Azure Function web UI for reviewing backup history

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

## What's Next

- [Installation & Prerequisites](./installation) - set up your environment
- [Authentication](./authentication) - configure pipeline identity or PAT access
- [Configuration](./configuration) - learn all CLI flags, env vars, and YAML options
- [Output Structure](./output-structure) - understand the backup directory layout
- [CI/CD Examples](./ci-cd) - ready-made pipeline definitions
