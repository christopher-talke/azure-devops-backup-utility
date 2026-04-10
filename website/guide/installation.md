# Installation & Prerequisites

## Requirements

| Requirement | Version |
|---|---|
| Python | >= 3.9 |
| Azure CLI | >= 2.30 |
| Azure DevOps CLI extension | Auto-installed if missing |
| Git | Any recent version |

There are **no external Python dependencies**. The tool uses only the Python standard library.

## Installation

### Option 1: Run directly (no install)

```bash
git clone https://github.com/christopher-talke/azure-devops-backup-utility.git
cd azure-devops-backup-utility

export PYTHONPATH=src
python src/cli.py --help
```

### Option 2: Install as a package

```bash
git clone https://github.com/christopher-talke/azure-devops-backup-utility.git
cd azure-devops-backup-utility

pip install -e .
ado-backup --help
```

## Azure CLI Setup

The tool requires the Azure CLI with the DevOps extension. If the extension is not installed, the tool will attempt to install it automatically.

To install manually:

```bash
az extension add --name azure-devops
```

Verify your setup:

```bash
az --version        # Should be >= 2.30
az devops --help    # Should show DevOps commands
git --version       # Any recent version
python --version    # Should be >= 3.9
```

## Next Steps

Once your environment is ready, [configure authentication](./authentication) to connect to your Azure DevOps organisation.
