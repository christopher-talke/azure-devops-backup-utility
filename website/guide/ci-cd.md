# CI/CD Examples

Ready-to-use pipeline definitions are included in the [`examples/`](https://github.com/christopher-talke/azure-devops-backup-utility/tree/main/examples) folder.

## Available Templates

| File | Platform | Upload Target |
|---|---|---|
| [`azure-pipelines.yml`](https://github.com/christopher-talke/azure-devops-backup-utility/blob/main/examples/azure-pipelines.yml) | Azure DevOps | Build artifacts |
| [`azure-pipelines-blob-storage.yml`](https://github.com/christopher-talke/azure-devops-backup-utility/blob/main/examples/azure-pipelines-blob-storage.yml) | Azure DevOps | Azure Blob Storage |
| [`github-actions-backup.yml`](https://github.com/christopher-talke/azure-devops-backup-utility/blob/main/examples/github-actions-backup.yml) | GitHub Actions | Workflow artifacts |
| [`github-actions-blob-storage.yml`](https://github.com/christopher-talke/azure-devops-backup-utility/blob/main/examples/github-actions-blob-storage.yml) | GitHub Actions | Azure Blob Storage |
| [`github-actions-s3.yml`](https://github.com/christopher-talke/azure-devops-backup-utility/blob/main/examples/github-actions-s3.yml) | GitHub Actions | AWS S3 |
| [`config.yaml`](https://github.com/christopher-talke/azure-devops-backup-utility/blob/main/examples/config.yaml) | n/a | Example YAML config |

Copy the relevant file into your project and adjust variables/secrets as described in the file comments.

## Security Considerations

- **GitHub Actions** examples pin actions to commit SHAs for supply chain security
- **Azure Pipelines** examples use schedule-only triggers (no push triggers) to prevent compromised commits from triggering backup runs
- All examples store credentials as pipeline secrets or environment variables - never in source code

## Azure Pipelines Example

A minimal Azure Pipelines setup using the system token:

```yaml
schedules:
  - cron: '0 2 * * *'
    displayName: Nightly backup
    branches:
      include: [main]
    always: true

pool:
  vmImage: ubuntu-latest

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.11'

  - script: |
      export PYTHONPATH=src
      python src/cli.py \
        --compress all \
        --verify \
        --verbose
    env:
      AZURE_DEVOPS_EXT_PAT: $(System.AccessToken)
      AZURE_DEVOPS_ORG_URL: $(System.CollectionUri)
    displayName: Run backup

  - publish: ado-backup
    artifact: ado-backup
```

## GitHub Actions Example

A minimal GitHub Actions setup:

```yaml
on:
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - run: |
          export PYTHONPATH=src
          python src/cli.py \
            --compress all \
            --verify \
            --verbose
        env:
          AZURE_DEVOPS_EXT_PAT: ${{ secrets.ADO_PAT }}
          AZURE_DEVOPS_ORG_URL: ${{ secrets.ADO_ORG_URL }}

      - uses: actions/upload-artifact@v4
        with:
          name: ado-backup
          path: ado-backup/
          retention-days: 30
```

## Storage Recommendations

- Set artifact retention policies in your CI system
- For long-term storage, upload to Azure Blob Storage or AWS S3
- Use `--compress all` to reduce storage footprint
- Consider `--exclude git` if repository clones are too large for your storage budget
