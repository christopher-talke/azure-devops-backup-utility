# Azure DevOps Backup Utility

<table><tr><td>
<strong>&#9888;&#65039; Warning</strong><br><br>
This project has been generated with the assistance of Anthropic's Claude LLM models.<br>
Please be aware of this before running it against production systems, and take the time to understand how the project works before using it.
</td></tr></table>

A non-interactive backup tool for Azure DevOps that uses only Azure CLI (`az devops`) commands and Git CLI to retrieve and persist data. 

Designed for CI/CD pipelines with zero external Python dependencies.

## Features

- **Broad data coverage** - organisations, projects, repos, pull requests, boards, pipelines, artifacts, dashboards, and permissions
- **Azure CLI only** - all API access via `az devops` / `az devops invoke`; no direct HTTP clients
- **Git CLI** - repository content cloned via `git clone --mirror`
- **Standard library only** - no pip dependencies beyond Python >= 3.9
- **Non-interactive** - designed for CI/CD (Azure Pipelines, GitHub Actions)
- **Automatic pagination** - continuation token handling built into `az devops invoke` so large result sets are never silently truncated
- **Incremental filtering** - `--since` flag filters work items and pipeline runs by date
- **Resilient** - exponential backoff with jitter, throttle-aware retries, partial progress tracking
- **Redaction** - best effort to scrub sensitive fields (secrets, tokens, passwords, `isSecret` variables) automatically masked before persisting across all backup scopes
- **Secure credential handling** - PAT passed to git via environment variables (never in process arguments or on-disk config)
- **Hardened output** - backup directories created with restricted permissions (`0700` on Unix)
- **Integrity verification** - SHA-256 checksums recorded per file in the inventory; archives verified before source deletion
- **Input validation** - path traversal protection, config value whitelisting, output directory sanitisation
- **Configurable** - CLI flags, environment variables, and optional YAML config file
- **Compression** - per-repo, per-project, or full backup compression with archive verification

## Feature Support

The tables below show what Azure DevOps data is backed up, grouped by category.

### Repositories

| Feature | Status | Notes |
|---|---|---|
| Mirror clone (full history) | Supported | `git clone --mirror` via Git CLI |
| Branch refs | Supported | Exported as structured JSON via `git/refs` with `filter=heads/` |
| Tag refs | Supported | Exported as structured JSON via `git/refs` with `filter=tags/` |
| Branch policies | Supported | Per-repository filtering via `policy/configurations?repositoryId=` |
| Repository metadata | Supported | Default branch, size, and other properties from `az repos list` |
| Repository permissions | Partial | Project-level ACLs captured; per-repo security namespace tokens not yet targeted |

### Pull Requests

| Feature | Status | Notes |
|---|---|---|
| PR metadata (all statuses) | Supported | Title, description, author, timestamps, target branch, reviewers, votes |
| PR comment threads | Supported | All threads including resolved/active state and comment authors |
| PR work item links | Supported | Linked work items per PR |
| PR labels | Not yet | Labels endpoint not yet wired |
| PR iteration history | Not yet | Iteration/commit history endpoint not yet wired |

### Pipelines

| Feature | Status | Notes |
|---|---|---|
| Pipeline definitions (YAML) | Supported | Via `az pipelines list` |
| Pipeline variables | Supported | Via variable groups export; secrets redacted |
| Variable groups | Supported | Via `distributedtask/variablegroups`; `isSecret` values redacted |
| Pipeline environments | Supported | Via `distributedtask/environments` |
| Secure files | Supported | Metadata only (names, IDs); file contents are never exported |
| Task groups (classic) | Supported | Via `distributedtask/taskgroups` |
| Release definitions (classic) | Supported | Via `release/definitions`; may require the release management area to be registered |
| Service connections | Supported | Names, types, endpoint URLs; credentials redacted via `authorization.parameters` path |
| Agent pools and queues | Supported | Metadata only |
| Pipeline run history | Supported | Build index with configurable `--max-items` and `--since` filtering |
| Pipeline run logs | Not yet | Log content download is not yet implemented |

### Boards and Work Items

| Feature | Status | Notes |
|---|---|---|
| Work items (all fields) | Supported | Fetched via WIQL query then `az boards work-item show --expand all` in batches of 200 |
| Work item relations | Supported | Included via `--expand all` |
| Work item history | Partial | Revision data included via expand; full update history not yet wired |
| Work item attachments | Not yet | Path helper exists but binary download is not yet implemented |
| Saved queries | Supported | Via `wit/queries` with depth 2 |
| Work item tags | Supported | Via `wit/tags` |
| Board column/swimlane config | Supported | Board definitions, columns, and rows (swimlanes) per board |
| Team settings | Supported | Via `work/teamsettings` |
| Team iterations | Supported | Via `work/iterations` |
| Iteration paths | Supported | Full hierarchy via `wit/classificationNodes` with depth 10 |
| Area paths | Supported | Full hierarchy via `wit/classificationNodes` with depth 10 |

### Artifacts

| Feature | Status | Notes |
|---|---|---|
| Feed configurations | Supported | Via `packaging/feeds` |
| Package metadata | Supported | Per-feed package listing; binary content is not downloaded |
| Feed permissions | Not yet | Feed-level permissions endpoint not yet wired |
| Retention policies | Not yet | Feed retention settings not yet wired |

### Access and Identity

| Feature | Status | Notes |
|---|---|---|
| Users | Supported | AAD/MSA users via `graph/users` |
| Groups | Supported | Security groups via `graph/groups` |
| Group memberships | Supported | Via `graph/memberships` (API v7.1-preview.1) |
| Security namespaces | Supported | Fetched once (org-wide) and cached to avoid redundant calls |
| Project-level ACLs | Supported | Via `security/accesscontrollists` per project |
| Service principal/PAT metadata | Not yet | `tokens/pats` and `graph/serviceprincipals` endpoints not yet wired |

### Project and Organisation Settings

| Feature | Status | Notes |
|---|---|---|
| Project properties and visibility | Supported | Via `az devops project show` |
| Teams | Supported | Via `core/teams` |
| Dashboards and widgets | Supported | Dashboard list plus per-dashboard widget configurations |
| Notification subscriptions | Supported | Via `notification/subscriptions` |

### Not Yet Implemented / To Be Completed

| Feature | Notes |
|---|---|
| Wiki content export | Not yet implemented |
| Test plans and suites | Not yet implemented |
| Work item attachment download | Path helper exists; binary download not yet wired |
| Pipeline run log download | Log content download not yet implemented |
| PR labels and iteration history | Endpoints not yet wired |
| Feed permissions and retention | Endpoints not yet wired |
| Service principal/PAT metadata | Endpoints not yet wired |

## Prerequisites

| Requirement | Version |
|---|---|
| Python | >= 3.9 |
| Azure CLI | >= 2.30 |
| Azure DevOps CLI extension | Auto-installed if missing |
| Git | Any recent version |

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
| Release | Read |
| Packaging | Read |
| Graph (Users/Groups) | Read |
| Security (Permissions) | Read |
| Service Connections | Read |
| Variable Groups | Read |
| Agent Pools | Read |
| Dashboard | Read |
| Notifications | Read |

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
| `--include` | all components | Comma-separated: `org,projects,git,boards,pipelines,permissions,pull_requests,artifacts,dashboards` |
| `--exclude` | none | Components to skip |
| `--since` | none | ISO timestamp for incremental filtering (applies to work items and pipeline runs) |
| `--max-items` | `0` (unlimited) | Per-entity item limit |
| `--compress` | none | Compress output: `repos`, `project`, or `all` |
| `--output-dir` | `ado-backup` | Root output directory |
| `--config` | none | Path to YAML configuration file |
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
include: org,projects,git,boards,pipelines,pull_requests,artifacts,dashboards
max-items: 500
compress: repos
output-dir: ./backup
verbose: false
```

Then run:

```bash
python src/cli.py --config config.yaml
```

Unknown YAML keys are logged as warnings and ignored. The `pat` key is accepted but discouraged - use the `AZURE_DEVOPS_EXT_PAT` environment variable instead.

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
      security_namespaces.json
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
          {repo-name}_branches.json
          {repo-name}_tags.json
          {repo-name}_policies.json
          {repo-name}/                  # mirror clone
        pull_requests/
          {repo-name}/
            pull_requests.json
            {pr-id}/
              threads.json
              work_items.json
        boards/
          work_items/
            index.json
            {id}.json
          queries.json
          tags.json
          board_config.json
          board_{name}_columns.json
          board_{name}_rows.json
          team_settings.json
          team_iterations.json
        pipelines/
          pipelines.json
          runs_index.json
          environments.json
          secure_files.json
          task_groups.json
          release_definitions.json
        artifacts/
          feeds.json
          feed_{name}_packages.json
        dashboards/
          dashboards.json
          dashboard_{name}_widgets.json
          notification_subscriptions.json
    _indexes/
      inventory.json          # all exported entities with SHA-256 checksums
      manifest.json           # backup metadata (timing, counts, limits)
      errors.jsonl            # any errors encountered (PATs scrubbed)
```

## Security and Redaction

All backup scopes pass API data through the redaction engine before writing to disk.

### Credential Handling

- The PAT is **never** logged, persisted to disk, or passed in process arguments
- Git clone authentication uses `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY` / `GIT_CONFIG_VALUE` environment variables with Base64-encoded Basic auth - the PAT never appears in `argv` or on-disk git config
- Error messages written to `errors.jsonl` are scrubbed of PAT values before persisting (both at the orchestrator level and within each scope module)

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
- Compression operations verify the archive is readable before deleting the source directory

## Integrity and Verification

- Each file recorded in `inventory.json` includes a `sha256` checksum computed at write time
- The `manifest.json` records timing, entity counts, error counts, and any limits applied
- Archives are verified (member listing read back) before the uncompressed source is removed
- Errors are tracked in `errors.jsonl` with timestamps and PAT scrubbing

## Pagination

All `az devops invoke` API calls automatically handle continuation tokens. If a response includes a `continuationToken`, subsequent pages are fetched and merged into a single result set (up to 100 pages by default). This prevents silent data truncation for large organisations with many users, repositories, work items, or other entities.

## Incremental Filtering

When `--since` is provided with an ISO timestamp:

- **Work items**: the WIQL query filters by `[System.ChangedDate] >= '{since}'`
- **Pipeline runs**: the build index query uses the `minTime` parameter

Other entity types are always fetched in full regardless of the `--since` value.

## Performance and Throttling

- All API calls use exponential backoff with jitter (default: 5 retries)
- HTTP 429 and 5xx errors trigger automatic retry with increasing delay
- Use `--max-items` to cap per-entity exports for CI-friendly runs
- Large organisations: consider backing up subsets of projects with `--projects`

## Storage Footprint

- JSON exports are typically small (KB to MB per entity)
- Git mirror clones can be large depending on repository size
- Use `--exclude git` to skip repository cloning if storage is limited
- Use `--compress repos` to tar.gz each mirror clone, `--compress project` for per-project archives, or `--compress all` for a single archive
- Recommended: set artefact retention policies in your CI system

## CI/CD Examples

Ready-to-use pipeline definitions are in the [`examples/`](examples/) folder:

| File | Platform | Upload Target |
|---|---|---|
| [`azure-pipelines.yml`](examples/azure-pipelines.yml) | Azure DevOps | Build artefacts |
| [`azure-pipelines-blob-storage.yml`](examples/azure-pipelines-blob-storage.yml) | Azure DevOps | Azure Blob Storage |
| [`github-actions-backup.yml`](examples/github-actions-backup.yml) | GitHub Actions | Workflow artefacts |
| [`github-actions-blob-storage.yml`](examples/github-actions-blob-storage.yml) | GitHub Actions | Azure Blob Storage |
| [`github-actions-s3.yml`](examples/github-actions-s3.yml) | GitHub Actions | AWS S3 |
| [`config.yaml`](examples/config.yaml) | n/a | Example YAML config |

Copy the relevant file into your project and adjust variables/secrets as described in the file comments.

GitHub Actions examples pin actions to commit SHAs for supply chain security. Azure Pipelines examples use schedule-only triggers (no push triggers) to prevent compromised commits from triggering backup runs.

## Contributing

See [DEVELOPMENT.md](DEVELOPMENT.md) for development setup, project structure, testing, and contribution guidelines.

## Licence

MIT - See [LICENCE](LICENSE).
