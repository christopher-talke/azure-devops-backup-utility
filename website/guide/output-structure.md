# Output Structure

Backups are written to a timestamped directory under the output root. The structure is organised by host, organisation, and timestamp.

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
      service_principals.json
      pat_tokens.json
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
          {repo-name}_permissions.json
          {repo-name}/                  # mirror clone
        pull_requests/
          {repo-name}/
            pull_requests.json
            {pr-id}/
              threads.json
              work_items.json
              labels.json
              iterations.json
        boards/
          work_items/
            index.json
            {id}.json
            {id}_revisions.json
            {id}/
              attachments/              # binary files
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
          logs/
            {build-id}/
              {log-id}.txt
        artifacts/
          feeds.json
          feed_{name}_packages.json
          feed_{name}_permissions.json
          feed_{name}_retention.json
        dashboards/
          dashboards.json
          dashboard_{name}_widgets.json
          notification_subscriptions.json
        wikis/
          wikis.json
          wiki_{name}_pages.json
        test_plans/
          plans.json
          plan_{name}_suites.json
    _indexes/
      inventory.json          # all exported entities with SHA-256 checksums
      manifest.json           # backup metadata (timing, counts, limits)
      errors.jsonl            # any errors encountered (PATs scrubbed)
```

## Index Files

The `_indexes/` directory contains metadata about the backup run:

### `manifest.json`

Records backup start/end timestamps, entity counts per category, error counts, and any limits that were applied (`max_items`, `since`, components).

### `inventory.json`

Lists every exported file with its SHA-256 checksum, computed at write time. This can be used to verify backup integrity independently.

### `errors.jsonl`

One JSON record per error encountered during the backup. Each record includes a timestamp, category, entity name, and error message. PAT values are scrubbed from error messages before persisting.

### `verification_report.json`

Written only when `--verify` is used. Contains pass/fail/skip results for each sampled item. See [Integrity & Verification](../reference/verification) for details.
