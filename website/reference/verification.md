# Integrity & Verification

## File Integrity

- Each file recorded in `inventory.json` includes a `sha256` checksum computed at write time
- The `manifest.json` records timing, entity counts, error counts, and any limits applied
- Archives are verified (member listing read back) before the uncompressed source is removed
- Errors are tracked in `errors.jsonl` with timestamps and PAT scrubbing

## Live Verification

When `--verify` is passed, the tool samples `--verify-samples` items (default 3) per category per project after backup completes and compares them against the live ADO instance.

### Verification Checks

| Category | Check |
|----------|-------|
| git | HEAD SHA of default branch matches live |
| boards | `System.Rev` matches live work item |
| pipelines | `revision` field matches live build definition |
| pull_requests | `status` field matches live PR |
| wikis | Pages file is non-empty |
| artifacts | Package count matches live feed |
| dashboards | Dashboard ID exists in live instance |
| testplans | Test plan ID exists in live instance |

### Behaviour

- Items modified after the backup started are automatically skipped (`_SKIP`)
- Results are written to `_indexes/verification_report.json`
- Exit code is `2` on any verification failure (as opposed to `0` for success or `1` for backup errors)

### Usage

```bash
# Verify with default 3 samples per category
python src/cli.py --verify

# Verify with more samples for higher confidence
python src/cli.py --verify --verify-samples 10
```

The verification report includes per-item results with status (`PASS`, `FAIL`, or `SKIP`), making it straightforward to identify any discrepancies between the backup and the live instance.
