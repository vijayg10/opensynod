import { defaultTheme } from '@vuepress/theme-default'
import { defineUserConfig } from 'vuepress'
import { viteBundler } from '@vuepress/bundler-vite'

export default defineUserConfig({
  lang: 'en-US',

  title: 'OpenSynod',
  description: 'Where LLMs Debate. Consensus Redefined.',

  theme: defaultTheme({
    logo: '/images/opensynod_hlogo.png',

    navbar: [
      { text: 'Home', link: '/' },
      {
        text: 'Get to Know',
        children: [
          { text: 'What is OpenSynod?', link: '/get-to-know/what-is-opensynod' },
          { text: 'How It Works', link: '/get-to-know/how-it-works' },
          { text: 'Features', link: '/get-to-know/features' },
        ],
      },
      {
        text: 'Gallery',
        children: [
          { text: 'Screenshots', link: '/gallery/screenshots' },
          { text: 'Demo Videos', link: '/gallery/demo-videos' },
        ],
      },
      {
        text: 'Documentation',
        children: [
          { text: 'Installation Guide', link: '/guide/installation' },
          { text: 'Configuration', link: '/guide/configuration' },
          { text: 'Under the Hood', link: '/technical/architecture' },
        ],
      },
    ],

    sidebar: {
      '/get-to-know/': [
        {
          text: 'Get to Know',
          children: [
            '/get-to-know/what-is-opensynod',
            '/get-to-know/how-it-works',
            '/get-to-know/features',
          ],
        },
      ],
      '/guide/': [
        {
          text: 'Getting Started',
          children: [
            '/guide/installation',
            '/guide/configuration',
          ],
        },
      ],
      '/gallery/': [
        {
          text: 'Gallery',
          children: [
            '/gallery/screenshots',
            '/gallery/demo-videos',
          ],
        },
      ],
      '/technical/': [
        {
          text: 'Under the Hood',
          children: [
            '/technical/architecture',
            '/technical/tech-stack',
            '/technical/agents',
            '/technical/judges',
            '/technical/llm-providers',
          ],
        },
      ],
    },

    colorMode: 'light',
    colorModeSwitch: false,
    editLink: false,
    lastUpdated: false,
  }),

  bundler: viteBundler(),

  plugins: [],
})
