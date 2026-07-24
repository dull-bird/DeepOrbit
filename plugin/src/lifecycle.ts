/**
 * Pure lifecycle logic shared by the Obsidian plugin and mirrored from the
 * Python core (src/deeporbit/work.py). No Obsidian imports — unit-testable.
 */

export const STATUSES = ["active", "paused", "done", "archived"] as const;
export type Status = (typeof STATUSES)[number];

export interface WorkItem {
  path: string;
  title: string;
  status: string;
  author: string;
  updated: string;
}

/** "20_Projects/x.md" → "Projects"; "00_Inbox/x.md" → "Inbox". */
export function bucketFor(relPath: string): string {
  const top = relPath.split("/")[0] ?? "";
  const match = top.match(/^\d+_(.+)$/);
  return match ? match[1] : top || "Misc";
}

/**
 * Archive destination mirroring the Python core:
 * inbox → 99_System/Archive/Inbox/YYYY/MM/<name>
 * other → 99_System/Archive/<Bucket>/<YYYY>/<name>
 * `today` is YYYY-MM-DD.
 */
export function archiveDestination(relPath: string, today: string): string {
  const name = relPath.split("/").pop() ?? relPath;
  const [year, month] = [today.slice(0, 4), today.slice(5, 7)];
  if (bucketFor(relPath) === "Inbox") {
    return `99_System/Archive/Inbox/${year}/${month}/${name}`;
  }
  return `99_System/Archive/${bucketFor(relPath)}/${year}/${name}`;
}

/** Group scanned items by status, lifecycle order first, others appended. */
export function groupByStatus(items: WorkItem[]): Map<string, WorkItem[]> {
  const groups = new Map<string, WorkItem[]>();
  for (const status of STATUSES) groups.set(status, []);
  for (const item of items) {
    const key = groups.has(item.status as Status) ? item.status : "other";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(item);
  }
  for (const [key, list] of groups) if (list.length === 0) groups.delete(key);
  return groups;
}

export function todayLocal(now: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}
