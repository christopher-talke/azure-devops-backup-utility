# Performance & Storage

## Pagination

All `az devops invoke` API calls automatically handle continuation tokens. If a response includes a `continuationToken`, subsequent pages are fetched and merged into a single result set (up to 100 pages by default). This prevents silent data truncation for large organisations with many users, repositories, work items, or other entities.

## Throttling and Retries

- All API calls use exponential backoff with jitter (default: 5 retries)
- HTTP 429 and 5xx errors trigger automatic retry with increasing delay
- Use `--max-items` to cap per-entity exports for CI-friendly runs
- Large organisations: consider backing up subsets of projects with `--projects`

## Incremental Filtering

When `--since` is provided with an ISO timestamp:

- **Work items**: the WIQL query filters by `[System.ChangedDate] >= '{since}'`
- **Pipeline runs**: the build index query uses the `minTime` parameter

Other entity types are always fetched in full regardless of the `--since` value.

## Storage Footprint

- JSON exports are typically small (KB to MB per entity)
- Git mirror clones can be large depending on repository size
- Use `--exclude git` to skip repository cloning if storage is limited
- Use `--compress repos` to tar.gz each mirror clone, `--compress project` for per-project archives, or `--compress all` for a single archive
- Recommended: set artifact retention policies in your CI system

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success - backup completed without errors |
| `1` | Backup errors - some entities could not be backed up (or `--fail-fast` triggered) |
| `2` | Verification failures - `--verify` found discrepancies |
