# ADO Backup Dashboard

A lightweight Azure Function that reads backup metadata from Azure Blob Storage and presents it in a simple web UI. 

Administrators can quickly review backup health, errors, inventory, and verification results without downloading or decompressing archives.

The dashboard is **read-only and informational only** - it reads `_indexes/` metadata files. To retrieve raw backup data, access the storage container directly.

## Prerequisites

- Python 3.9+
- [Azure Functions Core Tools v4](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local)
- An Azure Storage Account with a blob container containing backups uploaded by `azure-pipelines-blob-storage.yml`

## Setup

1. Copy `local.settings.json.example` to `local.settings.json` and fill in your storage connection string:

   ```json
   {
     "IsEncrypted": false,
     "Values": {
       "AzureWebJobsStorage": "UseDevelopmentStorage=true", // Requires local emulator
       "FUNCTIONS_WORKER_RUNTIME": "python",
       "AZURE_STORAGE_CONNECTION_STRING": "<your-connection-string>", // Not required when developing with emulator
       "AZURE_STORAGE_CONTAINER": "ado-backups"
     }
   }
   ```

2. Install dependencies:

   ```bash
   cd dashboard
   pip install -r requirements.txt
   ```

3. Start the function locally:

   ```bash
   func start
   ```

4. Open `http://localhost:7071` in your browser.

## Configuration

| Setting | Description | Required |
|---------|-------------|----------|
| `AZURE_STORAGE_CONNECTION_STRING` | Storage account connection string | Yes (or use account URL) |
| `AZURE_STORAGE_ACCOUNT_URL` | Storage account URL for managed identity auth | Alternative to connection string |
| `AZURE_STORAGE_CONTAINER` | Blob container name | No (default: `ado-backups`) |

When `AZURE_STORAGE_ACCOUNT_URL` is set instead of a connection string, the function uses `DefaultAzureCredential` (managed identity, az CLI login, etc.).

## Pipeline Compatibility

The dashboard reads `_indexes/` metadata that is uploaded as raw blobs alongside the compressed backup archive. 

The updated `examples/azure-pipelines-blob-storage.yml` handles this automatically - it uploads `_indexes/` files first, then the `.tar.gz` archive.

Expected blob storage layout:

```
ado-backups/
  dev.azure.com/{org}/{timestamp}/
    _indexes/
      manifest.json
      inventory.json
      errors.jsonl
      verification_report.json
    backup.tar.gz
```

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/backups` | List all backup runs (supports `?limit=` and `?offset=`) |
| GET | `/api/backups/{id}/manifest` | Full manifest for a backup run |
| GET | `/api/backups/{id}/errors` | Errors as JSON array (supports `?limit=`) |
| GET | `/api/backups/{id}/inventory` | Inventory entries (supports `?category=` filter) |
| GET | `/api/backups/{id}/verification` | Verification report (404 if absent) |

The `{id}` parameter is the backup prefix path, URL-encoded (e.g., `dev.azure.com%2Fmyorg%2F20260410T020000Z`).

## Deployment to Azure

1. Create a Function App (Python 3.9+, Consumption or App Service plan).

2. Deploy:

   ```bash
   cd dashboard
   func azure functionapp publish <your-function-app-name>
   ```

3. Configure application settings in the Azure portal:
   - Set `AZURE_STORAGE_CONNECTION_STRING` or `AZURE_STORAGE_ACCOUNT_URL`.
   - Set `AZURE_STORAGE_CONTAINER` if not using the default `ado-backups`.

4. **For managed identity (recommended):**
   - Enable system-assigned managed identity on the Function App.
   - Grant the identity **Storage Blob Data Reader** on the storage account.
   - Set `AZURE_STORAGE_ACCOUNT_URL` to `https://<account>.blob.core.windows.net`.
   - Remove any connection string setting.

## Authentication

The dashboard itself does not implement authentication, the minimum recommendation is to enable **Azure AD Easy Auth** on the Function App:

1. In the Azure portal, go to the Function App -> Authentication.
2. Add an identity provider (Microsoft Entra ID).
3. Configure your allowed tenant and user/group restrictions as needed.

This ensures only authorised users within your organisation can access the dashboard.