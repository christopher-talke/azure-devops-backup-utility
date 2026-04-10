# Security & Redaction

All backup scopes pass API data through the redaction engine before writing to disk. The tool is designed to prevent accidental credential leakage at every layer.

## Credential Handling

- The PAT is **never** logged, persisted to disk, or passed in process arguments
- Git clone authentication uses `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY` / `GIT_CONFIG_VALUE` environment variables with Base64-encoded Basic auth - the PAT never appears in `argv` or on-disk git config
- Error messages written to `errors.jsonl` are scrubbed of PAT values before persisting (both at the orchestrator level and within each scope module)

## Field Redaction

Fields matching the following names (case-insensitive) are replaced with `***REDACTED***`:

`password`, `secret`, `token`, `privatekey`, `private_key`, `certificate`, `apikey`, `api_key`, `accesstoken`, `access_token`, `connectionstring`, `connection_string`, `securefileid`, `client_secret`, `clientsecret`, `sas_token`, `sastoken`, `encrypted_value`, `encryptedvalue`, `credentials`, `subscription_key`, `subscriptionkey`

## Path Redaction

The following dot-separated JSON paths are always redacted:

- `authorization.parameters`
- `configuration.value`
- `data.accesstoken`

## Contextual Redaction

Objects containing `"isSecret": true` (or `issecret`, `is_secret`) have their `value` field redacted automatically. This catches Azure DevOps variable group secrets where the key name is generic.

## Output Hardening

- Backup directories are created with `0700` permissions on Unix systems
- File names derived from API data are sanitised to prevent path traversal (`..` is stripped)
- The `output_dir` config value is validated to reject `..` path components
- Compression operations verify the archive is readable before deleting the source directory
