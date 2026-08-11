import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../data/daily.json");
const dest = resolve(here, "../src/data/daily.json");

mkdirSync(dirname(dest), { recursive: true });
copyFileSync(src, dest);
console.log(`sync-data: ${src} -> ${dest}`);
