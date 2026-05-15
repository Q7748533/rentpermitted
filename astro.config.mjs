// @ts-check
import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://rentpermitted.com',
  // Enable content collections for city pages
  markdown: {
    shikiConfig: {
      theme: 'github-dark',
    },
  },
});
