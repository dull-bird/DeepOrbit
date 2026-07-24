import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { archiveDestination, bucketFor, groupByStatus, todayLocal } from "./lifecycle.js";

describe("bucketFor", () => {
  it("strips numeric prefixes", () => {
    assert.equal(bucketFor("20_Projects/Big/Big.md"), "Projects");
    assert.equal(bucketFor("00_Inbox/idea.md"), "Inbox");
  });
  it("keeps non-prefixed folders", () => {
    assert.equal(bucketFor("notes/a.md"), "notes");
  });
});

describe("archiveDestination", () => {
  it("routes projects by year", () => {
    assert.equal(
      archiveDestination("20_Projects/Done.md", "2026-07-21"),
      "99_System/Archive/Projects/2026/Done.md",
    );
  });
  it("routes inbox by year and month", () => {
    assert.equal(
      archiveDestination("00_Inbox/idea.md", "2026-07-21"),
      "99_System/Archive/Inbox/2026/07/idea.md",
    );
  });
});

describe("groupByStatus", () => {
  it("orders lifecycle statuses first and keeps others", () => {
    const groups = groupByStatus([
      { path: "b.md", title: "b", status: "done", author: "human", updated: "" },
      { path: "a.md", title: "a", status: "active", author: "ai", updated: "" },
      { path: "c.md", title: "c", status: "draft", author: "human", updated: "" },
    ]);
    assert.deepEqual([...groups.keys()], ["active", "done", "other"]);
    assert.equal(groups.get("other")![0].path, "c.md");
  });
});

describe("todayLocal", () => {
  it("formats YYYY-MM-DD", () => {
    assert.equal(todayLocal(new Date(2026, 6, 4)), "2026-07-04");
  });
});
