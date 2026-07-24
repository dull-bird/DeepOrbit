import {
  ItemView,
  Notice,
  Plugin,
  TAbstractFile,
  TFile,
  WorkspaceLeaf,
} from "obsidian";
import {
  archiveDestination,
  groupByStatus,
  todayLocal,
  WorkItem,
} from "./lifecycle";

export const VIEW_TYPE_STATUS = "deeporbit-status";
const SCAN_ROOTS = [
  "00_Inbox",
  "10_Diary",
  "15_Writings",
  "20_Projects",
  "30_Research",
  "50_Resources",
  "60_Notes",
  "99_System/Archive",
];

export default class DeepOrbitPlugin extends Plugin {
  async onload(): Promise<void> {
    this.registerView(VIEW_TYPE_STATUS, (leaf) => new StatusView(leaf, this));
    this.addRibbonIcon("orbit", "DeepOrbit work status", () => {
      void this.activateView();
    });
    this.addCommand({
      id: "open-work-status",
      name: "Open work status board",
      callback: () => void this.activateView(),
    });
    this.addCommand({
      id: "mark-paused",
      name: "Pause current note",
      callback: () => void this.markCurrent("paused"),
    });
    this.addCommand({
      id: "mark-active",
      name: "Resume current note",
      callback: () => void this.markCurrent("active"),
    });
    this.addCommand({
      id: "mark-done",
      name: "Mark current note done",
      callback: () => void this.markCurrent("done"),
    });
    this.addCommand({
      id: "archive-current",
      name: "Archive current note",
      callback: () => void this.archiveCurrent(),
    });
    this.registerEvent(
      this.app.metadataCache.on("changed", () => this.refreshViews()),
    );
    this.registerEvent(this.app.vault.on("rename", () => this.refreshViews()));
    this.registerEvent(this.app.vault.on("delete", () => this.refreshViews()));
  }

  onunload(): void {
    this.app.workspace.detachLeavesOfType(VIEW_TYPE_STATUS);
  }

  async activateView(): Promise<void> {
    const existing = this.app.workspace.getLeavesOfType(VIEW_TYPE_STATUS)[0];
    if (existing) {
      this.app.workspace.revealLeaf(existing);
      return;
    }
    const leaf = this.app.workspace.getRightLeaf(false);
    if (!leaf) return;
    await leaf.setViewState({ type: VIEW_TYPE_STATUS, active: true });
    this.app.workspace.revealLeaf(leaf);
  }

  scanItems(): WorkItem[] {
    const items: WorkItem[] = [];
    for (const file of this.app.vault.getMarkdownFiles()) {
      if (!SCAN_ROOTS.some((root) => file.path.startsWith(`${root}/`))) continue;
      const fm = this.app.metadataCache.getFileCache(file)?.frontmatter;
      const status = typeof fm?.["status"] === "string" ? (fm["status"] as string) : "";
      if (!status) continue;
      items.push({
        path: file.path,
        title: file.basename,
        status,
        author: typeof fm?.["author"] === "string" ? (fm["author"] as string) : "human",
        updated: typeof fm?.["updated"] === "string" ? (fm["updated"] as string) : "",
      });
    }
    return items;
  }

  async setStatus(file: TFile, status: string): Promise<void> {
    await this.app.fileManager.processFrontMatter(file, (fm) => {
      fm["status"] = status;
      fm["updated"] = todayLocal();
    });
    new Notice(`DeepOrbit: ${file.basename} → ${status}`);
  }

  async markCurrent(status: string): Promise<void> {
    const file = this.app.workspace.getActiveFile();
    if (!file) {
      new Notice("DeepOrbit: no active note");
      return;
    }
    await this.setStatus(file, status);
  }

  async archiveCurrent(): Promise<void> {
    const file = this.app.workspace.getActiveFile();
    if (!file) {
      new Notice("DeepOrbit: no active note");
      return;
    }
    const dest = archiveDestination(file.path, todayLocal());
    if (this.app.vault.getAbstractFileByPath(dest)) {
      new Notice(`DeepOrbit: archive target exists, nothing overwritten: ${dest}`);
      return;
    }
    await this.app.fileManager.processFrontMatter(file, (fm) => {
      fm["status"] = "archived";
      fm["archived"] = todayLocal();
      fm["updated"] = todayLocal();
    });
    const parent = dest.split("/").slice(0, -1).join("/");
    if (!this.app.vault.getAbstractFileByPath(parent)) {
      await this.app.vault.createFolder(parent);
    }
    await this.app.vault.rename(file, dest);
    new Notice(`DeepOrbit: archived → ${dest}`);
  }

  private refreshViews(): void {
    for (const leaf of this.app.workspace.getLeavesOfType(VIEW_TYPE_STATUS)) {
      (leaf.view as StatusView).render();
    }
  }
}

class StatusView extends ItemView {
  private readonly deeporbit: DeepOrbitPlugin;

  constructor(leaf: WorkspaceLeaf, plugin: DeepOrbitPlugin) {
    super(leaf);
    this.deeporbit = plugin;
  }

  getViewType(): string {
    return VIEW_TYPE_STATUS;
  }

  getDisplayText(): string {
    return "DeepOrbit work status";
  }

  getIcon(): string {
    return "orbit";
  }

  async onOpen(): Promise<void> {
    this.render();
  }

  render(): void {
    const container = this.containerEl.children[1] as HTMLElement;
    container.empty();
    container.addClass("deeporbit-status");
    const groups = groupByStatus(this.deeporbit.scanItems());
    if (groups.size === 0) {
      container.createEl("p", { text: "No work items with a status field yet." });
      return;
    }
    for (const [status, items] of groups) {
      const section = container.createEl("details");
      section.createEl("summary", { text: `${status} (${items.length})` });
      if (status === "active") section.open = true;
      for (const item of items) {
        const row = section.createEl("div", { cls: "deeporbit-row" });
        const link = row.createEl("a", { text: item.title, href: "#" });
        link.addEventListener("click", (event) => {
          event.preventDefault();
          const file = this.app.vault.getAbstractFileByPath(item.path);
          if (file instanceof TFile) {
            void this.app.workspace.getLeaf(false).openFile(file);
          }
        });
        row.createEl("span", {
          text: item.author === "ai" ? " · ai" : "",
          cls: "deeporbit-author",
        });
        const actions = row.createEl("span", { cls: "deeporbit-actions" });
        for (const [label, target] of [
          ["⏸", "paused"],
          ["▶", "active"],
          ["✓", "done"],
        ] as const) {
          const button = actions.createEl("button", { text: label });
          button.setAttr("aria-label", `mark ${target}`);
          button.addEventListener("click", () => {
            const file = this.app.vault.getAbstractFileByPath(item.path);
            if (file instanceof TFile) void this.deeporbit.setStatus(file, target);
          });
        }
      }
    }
  }
}
