# Dashboard Setup & Deployment

## Prerequisites

- Python 3.9+
- [Azure Functions Core Tools v4](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local)
- An Azure Storage Account with a blob container containing backups uploaded by the [Azure Pipelines blob storage example](../guide/ci-cd)

## Local Development

1. Copy `local.settings.json.example` to `local.settings.json` and fill in your storage connection string:

   ```json
   {
     "IsEncrypted": false,
     "Values": {
       "AzureWebJobsStorage": "UseDevelopmentStorage=true",
       "FUNCTIONS_WORKER_RUNTIME": "python",
       "AZURE_STORAGE_CONNECTION_STRING": "<your-connection-string>",
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

## Deploy to Azure

1. Create a Function App (Python 3.9+, Consumption or App Service plan).

2. Deploy:

   ```bash
   cd dashboard
   func azure functionapp publish <your-function-app-name>
   ```

3. Configure application settings in the Azure portal:
   - Set `AZURE_STORAGE_CONNECTION_STRING` or `AZURE_STORAGE_ACCOUNT_URL`
   - Set `AZURE_STORAGE_CONTAINER` if not using the default `ado-backups`

4. **For managed identity (recommended):**
   - Enable system-assigned managed identity on the Function App
   - Grant the identity **Storage Blob Data Reader** on the storage account
   - Set `AZURE_STORAGE_ACCOUNT_URL` to `https://<account>.blob.core.windows.net`
   - Remove any connection string setting

## Authentication

The dashboard itself does not implement authentication. The minimum recommendation is to enable **Azure AD Easy Auth** on the Function App:

1. In the Azure portal, go to the Function App > Authentication
2. Add an identity provider (Microsoft Entra ID)
3. Configure your allowed tenant and user/group restrictions as needed

This ensures only authorised users within your organisation can access the dashboard.

## Pipeline Compatibility

The dashboard reads `_indexes/` metadata that is uploaded as raw blobs alongside the compressed backup archive.

The `azure-pipelines-blob-storage.yml` example handles this automatically - it uploads `_indexes/` files first, then the `.tar.gz` archive.

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
