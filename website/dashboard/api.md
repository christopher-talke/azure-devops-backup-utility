# Dashboard API Reference

The dashboard exposes a set of read-only HTTP endpoints for querying backup metadata.

## Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/backups` | List all backup runs |
| GET | `/api/backups/{id}/manifest` | Full manifest for a backup run |
| GET | `/api/backups/{id}/errors` | Errors as JSON array |
| GET | `/api/backups/{id}/inventory` | Inventory entries |
| GET | `/api/backups/{id}/verification` | Verification report |

The `{id}` parameter is the backup prefix path, URL-encoded (e.g., `dev.azure.com%2Fmyorg%2F20260410T020000Z`).

## Query Parameters

### `GET /api/backups`

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Maximum number of runs to return |
| `offset` | integer | Number of runs to skip (for pagination) |

### `GET /api/backups/{id}/errors`

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Maximum number of errors to return |

### `GET /api/backups/{id}/inventory`

| Parameter | Type | Description |
|-----------|------|-------------|
| `category` | string | Filter inventory entries by category |

### `GET /api/backups/{id}/verification`

Returns `404` if no verification report exists for the given backup run (i.e., `--verify` was not used).

## Response Format

All endpoints return JSON. The backup list endpoint returns an array of backup run summaries with entity counts and error counts. Detail endpoints return the raw content of the corresponding `_indexes/` file.

## Static Frontend

The dashboard also serves a static web UI at the root URL (`/`). The frontend is plain HTML, CSS, and JavaScript - no build step required. The source files are in `dashboard/frontend/`.
