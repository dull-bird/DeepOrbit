import { execSync } from "node:child_process";
import { existsSync, readFileSync, mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import os from "node:os";

/**
 * DeepOrbit context hook for OpenClaw.
 *
 * agent:bootstrap -> Inject vault context (DeepOrbitPrompt.md + status + profile)
 *   by calling the shared deeporbit_hook.py script.
 * workspace:file-change -> Mark the local search index dirty so the next RAG
 *   query knows to re-index.
 */

const REPO_ROOT = path.join(os.homedir(), "projects", "DeepOrbit");
const HOOK_SCRIPT = path.join(REPO_ROOT, "scripts", "hooks", "deeporbit_hook.py");
const LINKS_FILE = path.join(os.homedir(), ".config", "deeporbit", "links.json");
const AGENTS_MD = path.join(REPO_ROOT, "integrations", "openclaw", "AGENTS.md");

function findVault(cwd: string): string | null {
  // 1. Check env var
  const envVault = process.env.DEEPORBIT_VAULT;
  if (envVault && existsSync(path.join(envVault, "deeporbit.json"))) {
    return envVault;
  }
  // 2. Check cwd and parents
  let dir = cwd;
  for (let i = 0; i < 10; i++) {
    if (existsSync(path.join(dir, "deeporbit.json"))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  // 3. Check links registry for default vault
  try {
    if (existsSync(LINKS_FILE)) {
      const links = JSON.parse(readFileSync(LINKS_FILE, "utf8"));
      const entries = Array.isArray(links) ? links : links.links || [];
      const def = entries.find((l: any) => l.default || l.is_default);
      if (def?.path && existsSync(path.join(def.path, "deeporbit.json"))) {
        return def.path;
      }
      if (entries.length > 0 && entries[0]?.path) {
        const p = entries[0].path;
        if (existsSync(path.join(p, "deeporbit.json"))) return p;
      }
    }
  } catch { /* fail open */ }
  return null;
}

function runHookScript(event: string, cwd: string): string {
  if (!existsSync(HOOK_SCRIPT)) return "";
  try {
    const payload = JSON.stringify({ cwd });
    const result = execSync(
      `python3 "${HOOK_SCRIPT}" --runtime openclaw --event ${event}`,
      { input: payload, timeout: 15000, encoding: "utf8", cwd },
    );
    // The script emits JSON like {"context": "..."} for openclaw runtime
    try {
      const parsed = JSON.parse(result.trim());
      return parsed.context || "";
    } catch {
      return result.trim();
    }
  } catch {
    return ""; // fail open
  }
}

function markDirty(cwd: string): void {
  const vault = findVault(cwd);
  if (!vault) return;
  // Derive cache dir: ~/.cache/deeporbit/<vault-name>/dirty
  const vaultName = path.basename(vault);
  const cacheDir = path.join(os.homedir(), ".cache", "deeporbit", vaultName);
  try {
    mkdirSync(cacheDir, { recursive: true });
    const dirtyPath = path.join(cacheDir, "dirty");
    writeFileSync(dirtyPath, new Date().toISOString());
  } catch { /* fail open */ }
}

// --- Event handlers ---

export function onAgentBootstrap(event: any, ctx: any) {
  const cwd = ctx?.cwd || process.cwd();
  const vault = findVault(cwd);
  if (!vault) return undefined;

  // Build context: AGENTS.md guide + vault-specific runtime status
  let context = "";

  // 1. Load the full AGENTS.md guide (teaches agent how to use DeepOrbit)
  try {
    if (existsSync(AGENTS_MD)) {
      context += readFileSync(AGENTS_MD, "utf8").trim();
    }
  } catch { /* fail open */ }

  // 2. Append vault path so agent knows where to point --vault
  context += `\n\n## Active vault\n\n`;
  context += `Path: \`${vault}\`\n`;
  context += `Always use: \`deeporbit --vault "${vault}" <command>\`\n`;

  // 3. Append runtime status from hook script (profile, index state)
  const status = runHookScript("session-start", cwd);
  if (status) {
    context += `\n## Runtime status\n\n${status}\n`;
  }

  return {
    bootstrapFiles: [
      {
        name: "AGENTS.md",
        content: context,
      },
    ],
  };
}

export function onWorkspaceFileChange(event: any, ctx: any) {
  const cwd = ctx?.cwd || process.cwd();
  markDirty(cwd);
  return undefined;
}
