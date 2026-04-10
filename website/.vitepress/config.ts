import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Azure DevOps Backup Utility',
  description: 'Back up your Azure DevOps organization to disk using only Azure CLI. Zero dependencies.',
  base: '/azure-devops-backup-utility/',
  lastUpdated: true,
  cleanUrls: true,
  srcExclude: ['README-WEBSITE.md'],

  head: [
    ['meta', { property: 'og:title', content: 'Azure DevOps Backup Utility' }],
    ['meta', { property: 'og:description', content: 'Back up your entire Azure DevOps organization to disk. Zero dependencies. Just Azure CLI.' }],
    ['meta', { property: 'og:type', content: 'website' }],
  ],

  themeConfig: {
    nav: [
      { text: 'Guide', link: '/guide/' },
      { text: 'Reference', link: '/reference/components' },
      { text: 'Dashboard', link: '/dashboard/' },
      { text: 'Demo', link: '/demo' },
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Getting Started',
          items: [
            { text: 'Introduction', link: '/guide/' },
            { text: 'Installation', link: '/guide/installation' },
            { text: 'Authentication', link: '/guide/authentication' },
            { text: 'Configuration', link: '/guide/configuration' },
            { text: 'Output Structure', link: '/guide/output-structure' },
            { text: 'CI/CD Examples', link: '/guide/ci-cd' },
          ],
        },
      ],
      '/reference/': [
        {
          text: 'Reference',
          items: [
            { text: 'Backup Components', link: '/reference/components' },
            { text: 'Security & Redaction', link: '/reference/security' },
            { text: 'Integrity & Verification', link: '/reference/verification' },
            { text: 'Performance & Storage', link: '/reference/performance' },
          ],
        },
      ],
      '/dashboard/': [
        {
          text: 'Dashboard',
          items: [
            { text: 'Overview', link: '/dashboard/' },
            { text: 'Setup & Deployment', link: '/dashboard/setup' },
            { text: 'API Reference', link: '/dashboard/api' },
          ],
        },
      ],
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/christopher-talke/azure-devops-backup-utility' },
    ],

    editLink: {
      pattern: 'https://github.com/christopher-talke/azure-devops-backup-utility/edit/main/website/:path',
      text: 'Edit this page on GitHub',
    },

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright Christopher Talke',
    },

    search: {
      provider: 'local',
    },
  },
})
