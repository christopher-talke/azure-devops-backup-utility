---
layout: home

hero:
  name: "Azure DevOps"
  text: "Backup Utility"
  tagline: Pull and store your entire Azure DevOps organization to disk. Zero pip dependencies. Just Azure CLI and Python.
  actions:
    - theme: brand
      text: Get Started
      link: /guide/
    - theme: alt
      text: View on GitHub
      link: https://github.com/christopher-talke/azure-devops-backup-utility

features:
  - icon: "\U0001F4E6"
    title: Broad Coverage
    details: Repos, PRs, boards, pipelines, artifacts, permissions, dashboards, wikis, test plans, and more.
  - icon: "\U0001F6AB"
    title: Zero Dependencies
    details: Python standard library only. Uses az devops CLI as the sole API transport - no pip install required.
  - icon: "\U0001F504"
    title: CI/CD Ready
    details: Ready-made pipeline definitions for Azure Pipelines and GitHub Actions with multiple storage targets.
  - icon: "\U0001F512"
    title: Security First
    details: Automatic secret redaction, PAT never in argv, restricted directory permissions, path traversal protection.
  - icon: "\U0001F9FE"
    title: Data Integrity
    details: SHA-256 checksums per file, archive verification before deletion, randomised live verification against your ADO instance.
  - icon: "\U0001F4CA"
    title: Dashboard
    details: Azure Function web UI for reviewing backup history, errors, inventory, and verification results.
---

<style>
.section-title {
  text-align: center;
  font-size: 28px;
  font-weight: 700;
  margin: 3rem 0 0.5rem;
}

.section-subtitle {
  text-align: center;
  color: var(--vp-c-text-2);
  margin-bottom: 2rem;
  font-size: 16px;
}

.coverage-wrapper {
  max-width: 960px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

.quickstart-wrapper {
  max-width: 700px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

.faq-wrapper {
  max-width: 760px;
  margin: 0 auto;
  padding: 0 1.5rem 2rem;
}

.faq-wrapper h3 {
  font-size: 17px;
  font-weight: 600;
  margin: 2rem 0 0.5rem;
  color: var(--vp-c-text-1);
}

.faq-wrapper p {
  color: var(--vp-c-text-2);
  font-size: 15px;
  line-height: 1.7;
  margin: 0;
}

.warranty-wrapper {
  max-width: 760px;
  margin: 0 auto;
  padding: 1.5rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg-soft);
}

.warranty-wrapper p {
  color: var(--vp-c-text-2);
  font-size: 14px;
  line-height: 1.7;
  margin: 0.75rem 0 0;
}

.warranty-wrapper ul {
  color: var(--vp-c-text-2);
  font-size: 14px;
  line-height: 1.7;
  padding-left: 1.5rem;
  margin: 0.5rem 0;
}

.cta-section {
  text-align: center;
  padding: 3rem 1.5rem;
  margin-top: 2rem;
}

.cta-section h2 {
  font-size: 24px;
  margin-bottom: 0.5rem;
}

.cta-section p {
  color: var(--vp-c-text-2);
  margin-bottom: 1.5rem;
}

.cta-button {
  display: inline-block;
  padding: 10px 24px;
  background: var(--vp-c-brand-1);
  text-decoration: none !important;
  color: white !important;
  border-radius: 20px;
  font-weight: 600;
  font-size: 14px;
  transition: opacity 0.2s;
}

.cta-button.alt {
  background: var(--vp-c-brand-soft);
}

.cta-button:hover {
  opacity: 0.75;
}

table th:nth-child(1) {
  width: 250px;
  max-width: 300px;
}
</style>

<h2 class="section-title">Backup Coverage</h2>
<p class="section-subtitle">Everything backed up from your Azure DevOps organization</p>

<div class="coverage-wrapper">

### Repositories

| Feature | Status | Notes |
|---|---|---|
| Mirror clone (full history) | <span class="pill-supported">Supported</span> | `git clone --mirror` via Git CLI |
| Branch refs | <span class="pill-supported">Supported</span> | Structured JSON via `git/refs` |
| Tag refs | <span class="pill-supported">Supported</span> | Structured JSON via `git/refs` |
| Branch policies | <span class="pill-supported">Supported</span> | Per-repository via `policy/configurations` |
| Repository metadata | <span class="pill-supported">Supported</span> | Default branch, size, properties |
| Repository permissions | <span class="pill-supported">Supported</span> | Per-repo ACLs via `security/accesscontrollists` |

### Pull Requests

| Feature | Status | Notes |
|---|---|---|
| PR metadata (all statuses) | <span class="pill-supported">Supported</span> | Title, author, timestamps, reviewers, votes |
| PR comment threads | <span class="pill-supported">Supported</span> | All threads including resolved/active state |
| PR work item links | <span class="pill-supported">Supported</span> | Linked work items per PR |
| PR labels | <span class="pill-supported">Supported</span> | Via `git/pullRequestLabels` |
| PR iteration history | <span class="pill-supported">Supported</span> | Via `git/pullRequestIterations` |

### Boards & Work Items

| Feature | Status | Notes |
|---|---|---|
| Work items (all fields) | <span class="pill-supported">Supported</span> | WIQL query + `az boards work-item show --expand all` |
| Work item relations | <span class="pill-supported">Supported</span> | Included via `--expand all` |
| Work item history | <span class="pill-supported">Supported</span> | Full revision history per work item |
| Work item attachments | <span class="pill-supported">Supported</span> | Binary files downloaded per work item |
| Saved queries | <span class="pill-supported">Supported</span> | Via `wit/queries` with depth 2 |
| Board column/swimlane config | <span class="pill-supported">Supported</span> | Board definitions, columns, and rows |
| Team settings & iterations | <span class="pill-supported">Supported</span> | Via `work/teamsettings` and `work/iterations` |
| Iteration & area paths | <span class="pill-supported">Supported</span> | Full hierarchy with depth 10 |

### Pipelines

| Feature | Status | Notes |
|---|---|---|
| Pipeline definitions (YAML) | <span class="pill-supported">Supported</span> | Via `az pipelines list` |
| Variable groups | <span class="pill-supported">Supported</span> | `isSecret` values redacted |
| Environments & secure files | <span class="pill-supported">Supported</span> | Secure file contents not exported |
| Task groups (classic) | <span class="pill-supported">Supported</span> | Via `distributedtask/taskgroups` |
| Release definitions (classic) | <span class="pill-supported">Supported</span> | Via `release/definitions` |
| Service connections | <span class="pill-supported">Supported</span> | Credentials redacted |
| Agent pools and queues | <span class="pill-supported">Supported</span> | Metadata only |
| Pipeline run history | <span class="pill-supported">Supported</span> | Configurable `--max-items` and `--since` filtering |
| Pipeline run logs | <span class="pill-supported">Supported</span> | Log files per build run |

### Artifacts

| Feature | Status | Notes |
|---|---|---|
| Feed configurations | <span class="pill-supported">Supported</span> | Via `packaging/feeds` |
| Package metadata | <span class="pill-supported">Supported</span> | Per-feed listing; binary content not downloaded |
| Feed permissions | <span class="pill-supported">Supported</span> | Via `packaging/feedpermissions` |
| Retention policies | <span class="pill-supported">Supported</span> | Via `packaging/retentionpolicies` |

### Access & Identity

| Feature | Status | Notes |
|---|---|---|
| Users | <span class="pill-supported">Supported</span> | AAD/MSA users via `graph/users` |
| Groups & memberships | <span class="pill-supported">Supported</span> | Security groups and group memberships |
| Security namespaces | <span class="pill-supported">Supported</span> | Fetched once org-wide and cached |
| Project-level ACLs | <span class="pill-supported">Supported</span> | Via `security/accesscontrollists` per project |
| Service principal/PAT metadata | <span class="pill-supported">Supported</span> | Token values redacted |

### Dashboards, Wikis & Test Plans

| Feature | Status | Notes |
|---|---|---|
| Dashboards & widgets | <span class="pill-supported">Supported</span> | Dashboard list plus per-dashboard widget config |
| Notification subscriptions | <span class="pill-supported">Supported</span> | Via `notification/subscriptions` |
| Wiki page content | <span class="pill-supported">Supported</span> | Full page tree via `wiki/pages?recursionLevel=full` |
| Test plans | <span class="pill-supported">Supported</span> | Via `test/plans` |
| Test suites | <span class="pill-supported">Supported</span> | Per-plan suites via `test/suites` |

</div>

<h2 class="section-title">Quick Start</h2>
<p class="section-subtitle">Get your first backup running in minutes</p>

<div class="quickstart-wrapper">

```bash
# Set your org URL
export AZURE_DEVOPS_ORG_URL="https://dev.azure.com/your-org"

# Optional: provide a PAT (otherwise uses az CLI auth)
export AZURE_DEVOPS_EXT_PAT="your-personal-access-token"

# Run the backup
PYTHONPATH=src python src/cli.py

# Or with options
python src/cli.py \
  --projects "Project1,Project2" \
  --output-dir ./my-backup \
  --compress repos \
  --verify \
  --verbose
```

</div>

<h2 class="section-title">Dashboard</h2>
<p class="section-subtitle">Get a quick overview of your backup status via the provided optional dashboard</p>

<div class="dashboard-screenshot">
  <img src="./public/images/dashboard-preview.png" alt="ADO Backup Dashboard showing backup history, errors, and verification results">
</div>

<h2 class="section-title">FAQ</h2>

<div class="faq-wrapper">

<h3>Why does this tool exist?</h3>
<p>
Microsoft does not guarantee recovery of deleted or lost data in Azure DevOps.
</p>
<p>
Whilst Azure DevOps has service-level disaster recovery; granular data recovery for specific work items, deleted repositories, pipeline histories, or individual attachments is not available to end customers. Microsoft's position is that data protection is a shared responsibility: they protect the infrastructure, but it is your responsibility as a customer to maintain your own copies of your data.
</p>

<h3>What about Microsoft's built-in backup?</h3>
<p>
Azure DevOps replicates data across regions for high availability, but this is not the same as a backup. Accidental deletions, corruption, or loss of granular data (a closed work item, a purged pipeline run, a removed wiki page) cannot be recovered by Microsoft once gone. There is no "restore from backup" feature exposed to customers for individual resources. You can try your luck with Microsoft support, but there are no guarantees and it is not a reliable recovery strategy. This tool exists to give you control over your data and ensure you have your own copies that you can manage independently of Microsoft.
</p>

<h3>Is this a full backup and restore solution (aka disaster recovery tool)?</h3>
<p>
  <strong style="color: #e67e22;">Absolutely not.</strong>
    This is a <strong>pull-and-store</strong> solution only; it just creates structured offline copies of your Azure DevOps data. There is no automated restore functionality. Recovery from these backups requires manual intervention, as Azure DevOps does not provide programmatic APIs for importing or restoring most data types. This tool ensures you have the data; what you do with it in a recovery scenario is up to you.
</p>

<h3>What data does it back up?</h3>
<p>
See the <a href="/azure-devops-backup-utility/reference/components">Backup Components</a> reference for the complete list.
</p>

<h3>Was AI used to develop this project?</h3>
<p>
Yes. This project was generated with the assistance of Anthropic's Claude LLM models.
</p>
<p>
In saying that, just like any open source tooling, please do your due diligence. Please take the time to understand how it works before running it against production systems. You can review the source code on GitHub, and I encourage you to do so. I also welcome contributions, feedback, and improvements from the community to make this tool better for everyone.
</p>

</div>

<h2 class="section-title">Guarantees &amp; Warranty</h2>

<div class="warranty-wrapper">
  <p>This tool is provided <strong>as-is</strong> under the <a href="https://github.com/christopher-talke/azure-devops-backup-utility/blob/main/LICENSE">MIT License</a>. By using it, you accept the following:</p>

  <ul>
    <li>The authors and contributors provide <strong>no warranty</strong>, express or implied, regarding fitness for purpose, data completeness, or reliability.</li>
    <li>The authors are <strong>not liable</strong> for data loss, service disruption, missed backups, incorrect data, or any other damages arising from use of this tool.</li>
    <li>This is an open source project. You are responsible for <strong>testing, operating, and maintaining</strong> it in your own environment - including keeping dependencies up to date and verifying that backups complete successfully.</li>
    <li>Backup completeness depends on the permissions granted to the authenticated identity. If a scope fails silently due to insufficient permissions, that data will not be backed up.</li>
    <li>Always validate that your backups are complete and current before relying on them for recovery.</li>
    <li>You are not relying on this tool for disaster recovery; or your primary comprehensive backup solution for Azure DevOps.</li>
  </ul>
</div>

<div class="cta-section">
  <h2>Want to use this tool?</h2>
  <p>Get started with the installation guide and explore the full documentation OR read the code on GitHub.</p>
  <a class="cta-button" href="/azure-devops-backup-utility/guide/">Read the Docs</a>
  <a class="cta-button alt" style="margin-left: 1rem;" href="https://github.com/christopher-talke/azure-devops-backup-utility">View on GitHub</a>
</div>
