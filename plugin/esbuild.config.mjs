import esbuild from "esbuild";
import process from "process";
import builtins from "builtin-modules";

const production = process.argv[2] === "production";
const testBuild = process.argv[2] === "test";

const shared = {
  bundle: true,
  external: ["obsidian", "electron", ...builtins],
  format: "cjs",
  target: "es2020",
  logLevel: "info",
  sourcemap: production ? false : "inline",
  treeShaking: true,
};

if (testBuild) {
  await esbuild.build({
    ...shared,
    format: "esm",
    platform: "node",
    entryPoints: ["src/lifecycle.test.ts"],
    outfile: "dist-test/lifecycle.test.mjs",
  });
} else {
  const ctx = await esbuild.context({
    ...shared,
    entryPoints: ["src/main.ts"],
    outfile: "main.js",
  });
  if (production) {
    await ctx.rebuild();
    await ctx.dispose();
  } else {
    await ctx.watch();
  }
}
