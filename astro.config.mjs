import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import { readFileSync } from "node:fs";

const site = JSON.parse(readFileSync("./site.config.json", "utf-8"));

export default defineConfig({
  site: site.siteUrl,
  output: "static",
  compressHTML: true,
  integrations: [sitemap()],
});
