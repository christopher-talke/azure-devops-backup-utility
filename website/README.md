# ADO Backup - Website

This directory contains the documentation and marketing website for the Azure DevOps Backup Utility, built with [VitePress](https://vitepress.dev/).

## Local Development

```bash
cd website
npm install
npm run dev
```

This starts a dev server at `http://localhost:5173/azure-devops-backup-utility/`.

## Build

```bash
npm run build
```

Static output is generated in `.vitepress/dist/`.

## Preview Production Build

```bash
npm run preview
```

## Deployment

The site deploys automatically to GitHub Pages via the `.github/workflows/deploy-website.yml` workflow:

- **Trigger**: Push to `main` when files in `website/` change, or manual `workflow_dispatch`
- **Requirement**: In your GitHub repo, go to **Settings > Pages** and set the source to **GitHub Actions**

## Editing Content

All documentation pages are plain Markdown files in the `website/` directory:

| Directory | Content |
|-----------|---------|
| `guide/` | Getting started, installation, authentication, configuration, output structure, CI/CD |
| `reference/` | Backup components, security, verification, performance |
| `dashboard/` | Dashboard overview, setup, API reference |
| `index.md` | Landing page |
| `contributing.md` | Development guide |
| `demo.md` | Demo / example output |

Edit any `.md` file and commit - the site rebuilds automatically.

## Images

Place images in `public/images/`. Reference them in markdown as:

```markdown
![Alt text](/azure-devops-backup-utility/images/filename.png)
```

The `/azure-devops-backup-utility/` prefix is required because the site is deployed as a GitHub Pages project site.

## Configuration

Site navigation, sidebar, and metadata are configured in `.vitepress/config.ts`. Brand colours and custom styles are in `.vitepress/theme/style.css`.
