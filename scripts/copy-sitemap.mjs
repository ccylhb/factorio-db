// Copies the generated leaf sitemap to a stable name (sitemap.xml) so Google
// treats it as a fresh submission and fetches it.
import { copyFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const src = join(process.cwd(), "dist", "sitemap-0.xml");
const dst = join(process.cwd(), "dist", "sitemap.xml");

if (existsSync(src)) {
  copyFileSync(src, dst);
  console.log("copied sitemap-0.xml -> sitemap.xml");
} else {
  console.warn("sitemap-0.xml not found, skipping copy");
}
