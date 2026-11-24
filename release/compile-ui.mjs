// Run from the isolated editor tool directory prepared by build_ui.py.
import { readFile, writeFile } from "node:fs/promises";
import { resolve, join } from "node:path";
import postcss from "postcss";
import { build } from "esbuild";
import config from "./postcss.config.js";

const [desktopStyles, output] = process.argv.slice(2);
const editorStyles = resolve("src/styles.css");
const css = await readFile(editorStyles, "utf8") + "\n" + await readFile(desktopStyles, "utf8");
process.env.NODE_ENV = "production";
const plugins = await Promise.all(Object.entries(config.plugins).map(async ([name, options]) =>
  (await import(name)).default(options)
));
const compiled = await postcss(plugins).process(css, { from: editorStyles });
await writeFile(join(output, "desktop.css"), compiled.css);
await build({ entryPoints: ["src/desktop-theme.ts"], bundle: true, minify: true,
  format: "iife", outfile: join(output, "desktop-theme.js") });
