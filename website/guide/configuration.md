# Configuration

Configuration is resolved in the following priority order (highest wins):

1. **CLI arguments**
2. **Environment variables**
3. **YAML config file**
4. **Built-in defaults**

## CLI Options

| Flag | Default | Description |
|---|---|---|
| `--org-url` | `$AZURE_DEVOPS_ORG_URL` | Azure DevOps organisation URL |
| `--projects` | `all` | Comma-separated project names or `all` |
| `--include` | all components | Comma-separated: `org,projects,git,boards,pipelines,permissions,pull_requests,artifacts,dashboards,wikis,testplans` |
| `--exclude` | none | Components to skip |
| `--since` | none | ISO timestamp for incremental filtering (applies to work items and pipeline runs) |
| `--max-items` | `0` (unlimited) | Per-entity item limit |
| `--compress` | none | Compress output: `repos`, `project`, or `all` |
| `--output-dir` | `ado-backup` | Root output directory |
| `--config` | none | Path to YAML configuration file |
| `--fail-fast` | `false` | Abort on first error |
| `--dry-run` | `false` | Preview without writing data |
| `--verbose` | `false` | Enable debug logging |
| `--verify` | `false` | After backup, verify a random sample of items against the live ADO instance |
| `--verify-samples` | `3` | Number of items to sample per category during verification |

## Environment Variables

| Variable | Purpose |
|---|---|
| `AZURE_DEVOPS_EXT_PAT` | Personal Access Token (optional; used by az CLI and git clone) |
| `SYSTEM_ACCESSTOKEN` | Azure Pipelines system token (auto-detected as PAT fallback) |
| `AZURE_DEVOPS_ORG_URL` | Organisation URL (required) |
| `ADO_BACKUP_OUTPUT_DIR` | Override default output directory |
| `ADO_BACKUP_TIMEOUT` | CLI command timeout in seconds (default: 120) |

## YAML Configuration

Create a `config.yaml` (see the [example config](https://github.com/christopher-talke/azure-devops-backup-utility/blob/main/examples/config.yaml)):

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

## Components

Valid component values for `--include` and `--exclude`:

| Component | Description |
|---|---|
| `org` | Organisation-level data (users, groups, service connections, variable groups) |
| `projects` | Project metadata, teams, areas, iterations |
| `git` | Repository mirror clones, branches, tags, policies, permissions |
| `boards` | Work items, queries, tags, board config, team settings |
| `pipelines` | Pipeline definitions, runs, environments, releases, logs |
| `pull_requests` | PR metadata, threads, work item links, labels |
| `permissions` | Security namespaces, project ACLs |
| `artifacts` | Artifact feeds, packages, permissions, retention |
| `dashboards` | Dashboards, widgets, notification subscriptions |
| `wikis` | Wiki list and page content |
| `testplans` | Test plans and suites |

All components are active by default. Use `--include a,b` to back up only specific components, or `--exclude c,d` to skip certain ones.

## Incremental Filtering

When `--since` is provided with an ISO timestamp:

- **Work items**: the WIQL query filters by `[System.ChangedDate] >= '{since}'`
- **Pipeline runs**: the build index query uses the `minTime` parameter

Other entity types are always fetched in full regardless of the `--since` value.

## Compression Modes

| Mode | Behaviour |
|---|---|
| `repos` | Tar.gz each mirror clone individually |
| `project` | Tar.gz each project directory |
| `all` | Single tar.gz for the entire backup |

Archives are verified (member listing read back) before the uncompressed source is removed.
