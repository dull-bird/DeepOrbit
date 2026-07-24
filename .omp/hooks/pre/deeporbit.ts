import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { HookAPI } from "@oh-my-pi/pi-coding-agent/extensibility/hooks";

const pluginRoot = dirname(dirname(dirname(fileURLToPath(import.meta.url))));

function loadPrompt(cwd: string): string {
  const vault = process.env.DEEPORBIT_VAULT;
  const candidates = [
    vault && join(vault, "DeepOrbitPrompt.md"),
    join(cwd, "DeepOrbitPrompt.md"),
    join(pluginRoot, "DeepOrbitPrompt.md"),
  ].filter((path): path is string => Boolean(path));

  for (const path of candidates) {
    if (existsSync(path)) return readFileSync(path, "utf8").trim();
  }
  return "";
}

export default function deeporbitHook(pi: HookAPI): void {
  pi.on("before_agent_start", (_event, ctx) => {
    const prompt = loadPrompt(ctx.cwd);
    if (!prompt) return;

    return {
      message: {
        customType: "deeporbit-context",
        content: prompt,
        display: false,
        details: { source: "DeepOrbitPrompt.md" },
        attribution: "DeepOrbit",
      },
    };
  });
}
