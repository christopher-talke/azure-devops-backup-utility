# Demo

::: info Coming Soon
Terminal recordings and example output will be added here. In the meantime, check the [Quick Start](./guide/) to try the tool yourself.
:::

## Example CLI Output

A typical backup run looks like this:

```
$ PYTHONPATH=src python src/cli.py \
    --org-url https://dev.azure.com/myorg \
    --projects MyProject \
    --compress repos \
    --verify \
    --verbose

2026-04-10 02:00:01 INFO  Starting backup of https://dev.azure.com/myorg
2026-04-10 02:00:01 INFO  Output directory: ado-backup/dev.azure.com/myorg/20260410T020001Z
2026-04-10 02:00:02 INFO  Backing up organisation metadata...
2026-04-10 02:00:03 INFO  Found 1 project(s): MyProject
2026-04-10 02:00:03 INFO  [MyProject] Backing up project metadata...
2026-04-10 02:00:04 INFO  [MyProject] Backing up git repositories...
2026-04-10 02:00:04 INFO  [MyProject]   Cloning my-api (mirror)...
2026-04-10 02:00:12 INFO  [MyProject]   Cloning my-frontend (mirror)...
2026-04-10 02:00:18 INFO  [MyProject] Backing up boards and work items...
2026-04-10 02:00:18 INFO  [MyProject]   Fetching work items (WIQL)...
2026-04-10 02:00:20 INFO  [MyProject]   Found 247 work items
2026-04-10 02:00:35 INFO  [MyProject] Backing up pipelines...
2026-04-10 02:00:38 INFO  [MyProject] Backing up pull requests...
2026-04-10 02:00:42 INFO  [MyProject] Backing up artifacts...
2026-04-10 02:00:43 INFO  [MyProject] Backing up dashboards...
2026-04-10 02:00:44 INFO  [MyProject] Backing up wikis...
2026-04-10 02:00:45 INFO  [MyProject] Backing up test plans...
2026-04-10 02:00:46 INFO  Compressing repository clones...
2026-04-10 02:00:48 INFO  Verifying backup (3 samples per category)...
2026-04-10 02:00:52 INFO  Verification: 18 PASS, 0 FAIL, 2 SKIP
2026-04-10 02:00:52 INFO  Backup complete. 312 entities, 0 errors.
```

## Dashboard Preview

The built-in [observability dashboard](./dashboard/) provides a web UI for reviewing backup results:

![Dashboard Preview](./public/images/dashboard-preview.png)

## What to Expect

After a backup run, you'll find a structured directory tree with:

- **Mirror clones** of all Git repositories (full history)
- **JSON exports** of work items, pipelines, PRs, and other entities
- **SHA-256 checksums** for every file in the inventory
- **A manifest** with timing, entity counts, and any errors encountered

See the [Output Structure](./guide/output-structure) page for the full directory layout.
