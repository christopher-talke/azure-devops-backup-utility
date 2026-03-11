# Disaster Recovery Guide

This guide explains how to recover your Azure DevOps organisation from a backup produced by this utility.

> **Note:** This tool was generated with LLM assistance. Review all steps carefully before executing against production systems.

## Overview

Not all Azure DevOps data is equally recoverable. The table below summarises what the backup captures and how well it can be restored:

| Component | Backup Coverage | Restore Automation | Notes |
|---|---|---|---|
| Git repositories | Full mirror (all branches/tags/history) | ✅ Scriptable | Mirror push to new remote |
| Work items | Full JSON (fields + relations) | ⚠️ Partial | IDs change on import; history trail lost |
| Board queries | JSON metadata | ⚠️ Partial | Can be re-created via REST API |
| Pipeline definitions | JSON metadata only | ⚠️ Partial | YAML lives in git repos (fully backed up) |
| Pipeline run history | Index only | ❌ Reference | Archived; cannot be re-run |
| Service connections | JSON (secrets redacted) | ❌ Manual | Must re-enter credentials |
| Variable groups | JSON (secret values redacted) | ⚠️ Partial | Non-secret values restorable |
| Agent pools | JSON metadata | ❌ Manual | Agents must re-register |
| Users & groups | JSON | ❌ Manual | Must re-invite users; new subject IDs |
| Permissions/ACLs | JSON | ❌ Reference | Use as guide for manual reconstruction |
| Wiki content | Not backed up | ❌ N/A | Known limitation |
| Test plans/suites | Not backed up | ❌ N/A | Known limitation |
| Work item attachments | Not backed up | ❌ N/A | Known limitation |

## Prerequisites

Before starting recovery, ensure you have:

- **Azure CLI** ≥ 2.30 with the DevOps extension (`az extension add --name azure-devops`)
- **Git** (any recent version)
- A destination Azure DevOps organisation (either restored or newly created)
- A PAT with **write** scopes for the destination org:
  - Code (Read & Write)
  - Work Items (Read & Write)
  - Build (Read & Write)
  - Project and Team (Read, Write & Manage)

```bash
export AZURE_DEVOPS_EXT_PAT="<destination-pat>"
export TARGET_ORG_URL="https://dev.azure.com/<target-org>"
```

## Recovery Order

Restore components in this order to satisfy dependencies:

1. Organisation setup (users, groups)
2. Projects (create project shells)
3. Git repositories (push mirror clones)
4. Pipelines (re-create from git YAML)
5. Boards (work items, queries)
6. Service connections & variable groups (manual credential re-entry)

## Locating Your Backup

The backup root follows this layout:

```
ado-backup/
  {host}/
    {org-name}/
      {YYYYMMDDTHHMMSSZ}/       ← use the most recent timestamp
        _indexes/
          manifest.json         ← backup metadata and summary
          inventory.json        ← all entities that were backed up
          errors.jsonl          ← any entities that failed during backup
        org/
        projects/
```

Identify the backup you want to restore from:

```bash
BACKUP_ROOT="./ado-backup"
# List available backup snapshots
ls "$BACKUP_ROOT"/dev.azure.com/<org-name>/
```

Set a shell variable pointing to the snapshot you want:

```bash
BACKUP_SNAPSHOT="$BACKUP_ROOT/dev.azure.com/<org-name>/20240101T120000Z"
```

Check the backup manifest before proceeding:

```bash
cat "$BACKUP_SNAPSHOT/_indexes/manifest.json"
cat "$BACKUP_SNAPSHOT/_indexes/inventory.json" | python -m json.tool | head -60
```

---

## Step 1 – Create Projects

For each project in the backup, create it in the target organisation:

```bash
# List backed-up projects
ls "$BACKUP_SNAPSHOT/projects/"

# Create each project (adjust process template to match your org settings)
az devops project create \
  --name "<project-name>" \
  --org "$TARGET_ORG_URL" \
  --process "Agile" \
  --visibility private
```

Read the original project properties from the backup:

```bash
cat "$BACKUP_SNAPSHOT/projects/<project-name>/metadata/project.json"
```

Re-create teams, areas, and iterations using the backed-up hierarchy as a reference:

```bash
cat "$BACKUP_SNAPSHOT/projects/<project-name>/metadata/teams.json"
cat "$BACKUP_SNAPSHOT/projects/<project-name>/metadata/areas.json"
cat "$BACKUP_SNAPSHOT/projects/<project-name>/metadata/iterations.json"
```

---

## Step 2 – Restore Git Repositories

This is the most complete and automatable restore. Mirror clones contain the full commit history, all branches, and all tags.

### Using the provided script

```bash
# Restore all repositories for a project
bash examples/restore-repos.sh \
  --backup-dir "$BACKUP_SNAPSHOT/projects/<project-name>/git" \
  --target-org "$TARGET_ORG_URL" \
  --project "<project-name>"
```

### Manual restore (single repository)

```bash
# 1. Create the repository in the target project
az repos create \
  --name "<repo-name>" \
  --project "<project-name>" \
  --org "$TARGET_ORG_URL"

# 2. Obtain the new remote URL
NEW_REMOTE=$(az repos show \
  --repository "<repo-name>" \
  --project "<project-name>" \
  --org "$TARGET_ORG_URL" \
  --query remoteUrl \
  --output tsv)

# 3. Push the mirror clone to the new remote
cd "$BACKUP_SNAPSHOT/projects/<project-name>/git/<repo-name>"
git remote set-url origin "https://:$AZURE_DEVOPS_EXT_PAT@${NEW_REMOTE#https://}"
git push --mirror
```

> **Tip:** If using compressed backups (`--compress repos`), extract the `.tar.gz` archive first:
> ```bash
> tar -xzf <repo-name>.tar.gz
> ```

### Verifying the restore

```bash
# Count refs in the restored repository
git --git-dir "$BACKUP_SNAPSHOT/projects/<project-name>/git/<repo-name>" for-each-ref | wc -l

# Compare against the newly pushed remote
git ls-remote "$NEW_REMOTE" | wc -l
```

---

## Step 3 – Re-create Pipelines

Pipeline YAML definitions live inside Git repositories (which are fully restored in Step 2). You only need to re-register the pipeline definition in Azure DevOps.

```bash
# List backed-up pipeline definitions
cat "$BACKUP_SNAPSHOT/projects/<project-name>/pipelines/pipelines.json" | \
  python -c "import json,sys; [print(p['name'], '->', p.get('configuration',{}).get('path','')) for p in json.load(sys.stdin)]"

# Re-create a YAML pipeline
az pipelines create \
  --name "<pipeline-name>" \
  --repository "<repo-name>" \
  --repository-type tfsgit \
  --branch main \
  --yml-path "<path/to/pipeline.yaml>" \
  --project "<project-name>" \
  --org "$TARGET_ORG_URL"
```

> **Note:** Pipeline run history (`runs_index.json`) is backed up for reference only. Historical runs cannot be replayed.

---

## Step 4 – Restore Work Items

Work items can be re-created individually. Note that:

- **Work item IDs will be different** in the restored organisation
- **History/audit trail** is not preserved (only the current state)
- **Attachments** are not included in the backup
- **Relations** between work items need to be restored using the new IDs

```bash
# Inspect backed-up work items
ls "$BACKUP_SNAPSHOT/projects/<project-name>/boards/work_items/"
cat "$BACKUP_SNAPSHOT/projects/<project-name>/boards/work_items/index.json"

# Example: restore a single work item
ITEM=$(cat "$BACKUP_SNAPSHOT/projects/<project-name>/boards/work_items/<id>.json")
TITLE=$(echo "$ITEM" | python -c "import json,sys; d=json.load(sys.stdin); print(d['fields']['System.Title'])")
TYPE=$(echo "$ITEM" | python -c "import json,sys; d=json.load(sys.stdin); print(d['fields']['System.WorkItemType'])")

az boards work-item create \
  --title "$TITLE" \
  --type "$TYPE" \
  --project "<project-name>" \
  --org "$TARGET_ORG_URL"
```

For bulk import, consider exporting work items to CSV and using the [Azure DevOps CSV import](https://learn.microsoft.com/en-us/azure/devops/boards/queries/import-work-items-from-csv) feature, which preserves more fields.

---

## Step 5 – Re-create Variable Groups

Non-secret variable values are stored in the backup and can be restored. Secret variable values were redacted (`***REDACTED***`) and must be re-entered manually.

```bash
# Inspect variable groups
cat "$BACKUP_SNAPSHOT/org/variable_groups.json" | python -m json.tool

# Re-create a variable group (adjust values from the JSON)
az pipelines variable-group create \
  --name "<group-name>" \
  --variables key1=value1 key2=value2 \
  --project "<project-name>" \
  --org "$TARGET_ORG_URL"
```

After creation, open the variable group in the Azure DevOps UI and manually enter any secret values that appear as `***REDACTED***` in the backup.

---

## Step 6 – Re-create Service Connections

Service connection credentials were redacted before backup. Use the backup JSON as a guide for which connections existed and their configuration type.

```bash
# List backed-up service connections
cat "$BACKUP_SNAPSHOT/org/service_connections.json" | \
  python -c "import json,sys; [print(s['name'], ':', s.get('type','')) for s in json.load(sys.stdin)]"
```

Re-create each service connection via the Azure DevOps UI or CLI, re-entering the appropriate credentials.

---

## Step 7 – Restore Users and Groups

User accounts are tied to Azure Active Directory / Microsoft accounts; they cannot be migrated directly. Use the backup as a reference to re-invite users to the new organisation.

```bash
# List backed-up users
cat "$BACKUP_SNAPSHOT/org/users.json" | \
  python -c "import json,sys; [print(u.get('mailAddress',''), u.get('displayName','')) for u in json.load(sys.stdin)]"

# Add each user to the target org
az devops user add \
  --email-id "<user@example.com>" \
  --license-type stakeholder \
  --org "$TARGET_ORG_URL"
```

Re-create groups and memberships using the backed-up data as a reference:

```bash
cat "$BACKUP_SNAPSHOT/org/groups.json"
cat "$BACKUP_SNAPSHOT/org/memberships.json"
```

---

## Step 8 – Review Permissions

Permissions/ACLs are backed up as reference data. Use them to guide manual permission reconstruction in the target organisation.

```bash
# Review org-level ACLs
cat "$BACKUP_SNAPSHOT/org/permissions_acl.json" | python -m json.tool

# Review project-level ACLs
cat "$BACKUP_SNAPSHOT/projects/<project-name>/metadata/permissions_acl.json" | python -m json.tool
```

---

## Verifying the Recovery

After completing all steps, verify the restoration:

```bash
# Compare repository count
echo "=== Source backup repos ==="
cat "$BACKUP_SNAPSHOT/projects/<project-name>/git/repos.json" | \
  python -c "import json,sys; repos=json.load(sys.stdin); print(f'{len(repos)} repos')"

echo "=== Target org repos ==="
az repos list \
  --project "<project-name>" \
  --org "$TARGET_ORG_URL" \
  --query "length(@)"

# Compare work item count
echo "=== Source backup work items ==="
cat "$BACKUP_SNAPSHOT/projects/<project-name>/boards/work_items/index.json" | \
  python -c "import json,sys; d=json.load(sys.stdin); print(d.get('count',0), 'items')"

echo "=== Target org work items ==="
az boards query \
  --wiql "SELECT [System.Id] FROM WorkItems" \
  --project "<project-name>" \
  --org "$TARGET_ORG_URL" \
  --query "length(workItems)"
```

---

## What Cannot Be Recovered

The following data is **not** included in the backup and cannot be restored:

| Data | Reason |
|---|---|
| Wiki content | Not yet implemented in backup utility |
| Test plans & suites | Not yet implemented in backup utility |
| Work item attachments | Not yet implemented in backup utility |
| Artifact feed packages | Not yet implemented in backup utility |
| Pipeline run logs/artifacts | Not yet implemented in backup utility |
| Secret variable values | Redacted for security; must be re-entered |
| Service connection credentials | Redacted for security; must be re-entered |
| User identity mappings | Tied to AAD/MSA identities; IDs change when re-invited |

---

## Troubleshooting

**`git push --mirror` fails with authentication errors**

Ensure your PAT is exported and the remote URL includes the token:
```bash
git remote set-url origin "https://:${AZURE_DEVOPS_EXT_PAT}@dev.azure.com/<org>/<project>/_git/<repo>"
```

**`az` commands fail with "Project does not exist"**

Create the project first (Step 1) before restoring its contents.

**Work item create fails with field validation errors**

Some fields are read-only (e.g., `System.CreatedDate`, `System.Id`). Only set writable fields when using `az boards work-item create`. Use the CSV import method for richer field support.

**Backup snapshot has errors**

Review `errors.jsonl` to see which entities failed during backup. These will need special attention during recovery:
```bash
cat "$BACKUP_SNAPSHOT/_indexes/errors.jsonl"
```
