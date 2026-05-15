// @ts-check
import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://rentpermitted.com',
  trailingSlash: 'never',
  build: {
    format: 'directory',
  },
  markdown: {
    shikiConfig: {
      theme: 'github-dark',
    },
  },
  vite: {
    ssr: {
      noExternal: ['@fontsource/*'],
    },
  },
});
