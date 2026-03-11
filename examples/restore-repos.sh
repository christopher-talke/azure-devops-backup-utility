#!/usr/bin/env bash
# restore-repos.sh – Restore all Git repositories from a mirror-clone backup
#
# Usage:
#   bash examples/restore-repos.sh \
#     --backup-dir  <path-to-git-backup-dir>   \
#     --target-org  https://dev.azure.com/myorg \
#     --project     MyProject
#
# Requirements:
#   - Azure CLI with the azure-devops extension
#   - Git
#   - AZURE_DEVOPS_EXT_PAT environment variable set (write access to target org)
#
# The script:
#   1. Reads the repos.json index from the backup directory
#   2. Creates each repository in the target project if it does not exist
#   3. Pushes the local mirror clone to the new remote via `git push --mirror`

set -euo pipefail

# ── Argument parsing ────────────────────────────────────────────────────────────
BACKUP_DIR=""
TARGET_ORG=""
PROJECT=""

usage() {
  echo "Usage: $0 --backup-dir <dir> --target-org <url> --project <name>"
  echo ""
  echo "Options:"
  echo "  --backup-dir   Path to the git backup directory (contains repos.json and repo folders)"
  echo "  --target-org   Target Azure DevOps organisation URL"
  echo "  --project      Target project name"
  echo ""
  echo "Environment variables:"
  echo "  AZURE_DEVOPS_EXT_PAT   PAT with Code (Read & Write) scope for the target org"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backup-dir)  BACKUP_DIR="$2";  shift 2 ;;
    --target-org)  TARGET_ORG="$2";  shift 2 ;;
    --project)     PROJECT="$2";     shift 2 ;;
    --help|-h)     usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

[[ -z "$BACKUP_DIR" || -z "$TARGET_ORG" || -z "$PROJECT" ]] && usage

# ── Preflight checks ────────────────────────────────────────────────────────────
if [[ -z "${AZURE_DEVOPS_EXT_PAT:-}" ]]; then
  echo "ERROR: AZURE_DEVOPS_EXT_PAT environment variable is not set."
  echo "       Export a PAT with Code (Read & Write) scope for the target organisation."
  exit 1
fi

if ! command -v az &>/dev/null; then
  echo "ERROR: Azure CLI ('az') is not installed or not in PATH."
  exit 1
fi

if ! command -v git &>/dev/null; then
  echo "ERROR: Git is not installed or not in PATH."
  exit 1
fi

REPOS_INDEX="$BACKUP_DIR/repos.json"
if [[ ! -f "$REPOS_INDEX" ]]; then
  echo "ERROR: repos.json not found at '$REPOS_INDEX'"
  echo "       Ensure --backup-dir points to the 'git' subdirectory of a project backup."
  exit 1
fi

# ── Main restore loop ────────────────────────────────────────────────────────────
echo "Restoring Git repositories"
echo "  Backup directory : $BACKUP_DIR"
echo "  Target org       : $TARGET_ORG"
echo "  Target project   : $PROJECT"
echo ""

SUCCEEDED=0
FAILED=0
SKIPPED=0

# Read repo names from the JSON index using python (stdlib only, no jq required)
REPO_NAMES=$(python3 - "$REPOS_INDEX" <<'EOF'
import json, sys
try:
    with open(sys.argv[1]) as f:
        repos = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"ERROR: Failed to parse repos.json: {e}", file=sys.stderr)
    sys.exit(1)
for r in repos:
    name = r.get("name", "")
    if name:
        print(name)
EOF
) || { echo "ERROR: Could not read repository list from $REPOS_INDEX"; exit 1; }

if [[ -z "$REPO_NAMES" ]]; then
  echo "No repositories found in $REPOS_INDEX"
  exit 0
fi

while IFS= read -r REPO_NAME; do
  REPO_DIR="$BACKUP_DIR/$REPO_NAME"

  if [[ ! -d "$REPO_DIR" ]]; then
    # Check for a compressed backup (.tar.gz)
    REPO_ARCHIVE="$BACKUP_DIR/${REPO_NAME}.tar.gz"
    if [[ -f "$REPO_ARCHIVE" ]]; then
      echo "[$REPO_NAME] Extracting compressed mirror clone …"
      tar -xzf "$REPO_ARCHIVE" -C "$BACKUP_DIR"
    fi
  fi

  if [[ ! -d "$REPO_DIR" ]]; then
    echo "[$REPO_NAME] SKIP – mirror clone directory not found (backup may be incomplete)"
    (( SKIPPED++ ))
    continue
  fi

  echo "[$REPO_NAME] Creating repository in target project …"

  # Create the repo; ignore error if it already exists
  if ! az repos create \
        --name "$REPO_NAME" \
        --project "$PROJECT" \
        --org "$TARGET_ORG" \
        --output none 2>/dev/null; then
    echo "[$REPO_NAME] Repository already exists or create failed – attempting push anyway"
  fi

  # Retrieve the new remote URL
  NEW_REMOTE=$(az repos show \
    --repository "$REPO_NAME" \
    --project "$PROJECT" \
    --org "$TARGET_ORG" \
    --query remoteUrl \
    --output tsv 2>/dev/null || true)

  if [[ -z "$NEW_REMOTE" ]]; then
    echo "[$REPO_NAME] FAIL – could not determine remote URL"
    (( FAILED++ ))
    continue
  fi

  # Embed PAT into the URL (strips the scheme prefix, re-adds with credentials)
  REMOTE_HOST="${NEW_REMOTE#https://}"
  AUTH_REMOTE="https://:${AZURE_DEVOPS_EXT_PAT}@${REMOTE_HOST}"

  echo "[$REPO_NAME] Pushing mirror clone …"
  if git -C "$REPO_DIR" push --mirror "$AUTH_REMOTE" 2>&1 | \
     python3 -c "import sys; [sys.stdout.write(line.replace(sys.argv[1], '***REDACTED***')) for line in sys.stdin]" "$AZURE_DEVOPS_EXT_PAT"; then
    echo "[$REPO_NAME] OK"
    (( SUCCEEDED++ ))
  else
    echo "[$REPO_NAME] FAIL – git push --mirror returned non-zero exit code"
    (( FAILED++ ))
  fi

done <<< "$REPO_NAMES"

# ── Summary ──────────────────────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────"
echo "Git restore complete"
echo "  Succeeded : $SUCCEEDED"
echo "  Failed    : $FAILED"
echo "  Skipped   : $SKIPPED"
echo "────────────────────────────────────────"

[[ $FAILED -gt 0 ]] && exit 1 || exit 0
