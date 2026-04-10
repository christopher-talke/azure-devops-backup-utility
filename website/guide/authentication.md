# Authentication

The tool uses Azure CLI authentication. There are two ways to provide credentials:

1. **Pipeline Identity (recommended)** - use the built-in Build Service account in Azure DevOps Pipelines.
2. **Personal Access Token (PAT)** - for local use, non-ADO CI systems, or when pipeline identity permissions cannot be configured.

When a token is provided via `AZURE_DEVOPS_EXT_PAT` or `SYSTEM_ACCESSTOKEN`, it is also used for `git clone --mirror` authentication via git config environment variables. The token never appears in process arguments or on-disk git config files.

## Pipeline Identity (Recommended)

When running as an Azure DevOps Pipeline, the pipeline already has an identity: the **Build Service** account. Using `$(System.AccessToken)` feeds this token through the `AZURE_DEVOPS_EXT_PAT` environment variable. No PAT creation or manual rotation is needed.

### Why Pipeline Identity is Preferred

- Tokens are automatically rotated every pipeline run (24-hour lifetime)
- Token scope is limited to the pipeline's execution context
- No shared secrets to create, store, or rotate
- Eliminates risk of PAT leakage or expiry-related backup failures
- Audit trail ties every API call to a specific pipeline run

### Setup Steps

1. **Enable OAuth token access.** In your pipeline YAML, the system token is available by default. In classic pipelines, check *Allow scripts to access the OAuth token* on the Agent Job options.

2. **Expand job authorisation scope (cross-project backups).** By default, the build service identity can only access the project that contains the pipeline. To back up other projects:
   - Go to **Organisation Settings > Pipelines > Settings**
   - Set *Limit job authorization scope to current project for non-release pipelines* to **Off**
   - Set *Limit job authorization scope to referenced Azure DevOps repositories* to **Off** (required for cloning repos in other projects)

   ::: tip Targeted Alternative
   If you only back up specific projects, keep these limits **On** and instead grant the build service identity access per-project (step 3).
   :::

3. **Grant the Build Service identity Reader access.** For each project being backed up, go to **Project Settings > Permissions** and add the build service account to the **Readers** group. There are two identities to consider:
   - `{Project Name} Build Service ({Org Name})` - project-scoped identity
   - `Project Collection Build Service ({Org Name})` - collection-scoped identity

4. **Grant feed access for Artifacts.** If backing up Artifacts, go to **Artifacts > Feed Settings > Permissions** and add the Build Service identity as a **Reader** for each feed.

5. **Wire the token in YAML:**
   ```yaml
   env:
     AZURE_DEVOPS_EXT_PAT: $(System.AccessToken)
     AZURE_DEVOPS_ORG_URL: $(System.CollectionUri)
   ```

### Permissions Required by Component

| Component | ADO Permission | Where to Set |
|-----------|---------------|--------------|
| `projects` | View project-level information | Project Settings > Permissions (Readers group) |
| `git` | Read (repositories) | Project Settings > Repositories > Security |
| `boards` | View work items | Project Settings > Permissions (Readers group) |
| `pipelines` | View builds, View build definitions | Project Settings > Pipelines > Security |
| `pull_requests` | Read (repositories) | Project Settings > Repositories > Security |
| `artifacts` | Read (feed) | Artifacts > Feed Settings > Permissions |
| `permissions` | View identity information | Organisation Settings > Permissions |
| `dashboards` | Read (dashboards) | Project Settings > Permissions (Readers group) |
| `wikis` | Read (wiki) | Project Settings > Permissions (Readers group) |
| `testplans` | View test runs | Project Settings > Permissions (Readers group) |
| `org` | View instance-level information | Organisation Settings > Permissions |

::: tip
The Readers group in most projects already grants the majority of these permissions. You typically only need to explicitly grant feed access (Artifacts) and verify repository-level read permissions.
:::

## PAT Authentication

If you cannot use pipeline identity, create a Personal Access Token with the following scopes:

| Scope | Access |
|---|---|
| Project and Team | Read |
| Code | Read |
| Work Items | Read |
| Build | Read |
| Release | Read |
| Packaging | Read |
| Graph (Users/Groups) | Read |
| Security (Permissions) | Read |
| Service Connections | Read |
| Variable Groups | Read |
| Agent Pools | Read |
| Dashboard | Read |
| Notifications | Read |

Set the PAT as an environment variable:

```bash
export AZURE_DEVOPS_EXT_PAT="your-personal-access-token"
```

::: danger Never store a PAT in a config file
The tool will warn if it detects a PAT in a YAML configuration file. Always use environment variables for credentials.
:::
