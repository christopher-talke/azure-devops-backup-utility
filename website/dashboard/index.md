# Observability Dashboard

A lightweight Azure Function that reads backup metadata from Azure Blob Storage and presents it in a simple web UI.

Administrators can quickly review backup health, errors, inventory, and verification results without downloading or decompressing archives.

The dashboard is **read-only and informational only** - it reads `_indexes/` metadata files. To retrieve raw backup data, access the storage container directly.

## What You Can See

- **Backup history** - list of all runs with entity counts and error counts
- **Errors** - per-run error table (category, name, message, timestamp)
- **Inventory** - searchable list of backed-up entities with SHA-256 checksums
- **Verification results** - pass/fail/skip status for sampled items (when `--verify` was used)

## Preview

![ADO Backup Dashboard](../public/images/dashboard-preview.png)

## Next Steps

- [Setup & Deployment](./setup) - install and configure the dashboard
- [API Reference](./api) - available HTTP endpoints
