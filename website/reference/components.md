# Backup Components

The tables below show what Azure DevOps data is backed up, grouped by category. All components are active by default - use `--include` or `--exclude` to control which are run.

## Repositories

| Feature | Status | Notes |
|---|---|---|
| Mirror clone (full history) | Supported | `git clone --mirror` via Git CLI |
| Branch refs | Supported | Exported as structured JSON via `git/refs` with `filter=heads/` |
| Tag refs | Supported | Exported as structured JSON via `git/refs` with `filter=tags/` |
| Branch policies | Supported | Per-repository filtering via `policy/configurations?repositoryId=` |
| Repository metadata | Supported | Default branch, size, and other properties from `az repos list` |
| Repository permissions | Supported | Per-repo ACLs via `security/accesscontrollists` with `repoV2/{projectId}/{repoId}` token |

## Pull Requests

| Feature | Status | Notes |
|---|---|---|
| PR metadata (all statuses) | Supported | Title, description, author, timestamps, target branch, reviewers, votes |
| PR comment threads | Supported | All threads including resolved/active state and comment authors |
| PR work item links | Supported | Linked work items per PR |
| PR labels | Supported | Via `git/pullRequestLabels` |
| PR iteration history | Supported | Via `git/pullRequestIterations` |

## Pipelines

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
| Pipeline run logs | Supported | Log files downloaded via `az rest` per build run |

## Boards and Work Items

| Feature | Status | Notes |
|---|---|---|
| Work items (all fields) | Supported | Fetched via WIQL query then `az boards work-item show --expand all` in batches of 200 |
| Work item relations | Supported | Included via `--expand all` |
| Work item history | Supported | Full revision history via `wit/revisions` per work item |
| Work item attachments | Supported | Binary files downloaded via `az rest` per work item |
| Saved queries | Supported | Via `wit/queries` with depth 2 |
| Work item tags | Supported | Via `wit/tags` |
| Board column/swimlane config | Supported | Board definitions, columns, and rows (swimlanes) per board |
| Team settings | Supported | Via `work/teamsettings` |
| Team iterations | Supported | Via `work/iterations` |
| Iteration paths | Supported | Full hierarchy via `wit/classificationNodes` with depth 10 |
| Area paths | Supported | Full hierarchy via `wit/classificationNodes` with depth 10 |

## Artifacts

| Feature | Status | Notes |
|---|---|---|
| Feed configurations | Supported | Via `packaging/feeds` |
| Package metadata | Supported | Per-feed package listing; binary content is not downloaded |
| Feed permissions | Supported | Via `packaging/feedpermissions` per feed |
| Retention policies | Supported | Via `packaging/retentionpolicies` per feed |

## Access and Identity

| Feature | Status | Notes |
|---|---|---|
| Users | Supported | AAD/MSA users via `graph/users` |
| Groups | Supported | Security groups via `graph/groups` |
| Group memberships | Supported | Via `graph/memberships` (API v7.1-preview.1) |
| Security namespaces | Supported | Fetched once (org-wide) and cached to avoid redundant calls |
| Project-level ACLs | Supported | Via `security/accesscontrollists` per project |
| Service principal/PAT metadata | Supported | Via `graph/serviceprincipals` and `tokens/pats`; token values redacted |

## Project and Organisation Settings

| Feature | Status | Notes |
|---|---|---|
| Project properties and visibility | Supported | Via `az devops project show` |
| Teams | Supported | Via `core/teams` |
| Dashboards and widgets | Supported | Dashboard list plus per-dashboard widget configurations |
| Notification subscriptions | Supported | Via `notification/subscriptions` |

## Wikis

| Feature | Status | Notes |
|---|---|---|
| Wiki list | Supported | Via `wiki/wikis` |
| Wiki page content | Supported | Full page tree with content via `wiki/pages?recursionLevel=full` |

## Test Plans

| Feature | Status | Notes |
|---|---|---|
| Test plans | Supported | Via `test/plans` |
| Test suites | Supported | Per-plan suites via `test/suites` |
