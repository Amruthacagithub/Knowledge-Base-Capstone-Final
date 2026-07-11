import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { splitByExcerpts } from "./highlightContent";
import { previewExcerpt, buildFocusNeedles } from "./citationExcerpt";

const leavePolicy = readFileSync(
  new URL("../../../documents/hr/leave_policy.md", import.meta.url),
  "utf8"
);

describe("panel preview highlights", () => {
  it("highlights focused passages in full chunk", () => {
    const segs = splitByExcerpts(leavePolicy, buildFocusNeedles(leavePolicy));
    expect(segs.some((s) => s.type === "highlight")).toBe(true);
    const highlighted = segs
      .filter((s) => s.type === "highlight")
      .map((s) => s.text)
      .join(" ");
    expect(highlighted.toLowerCase()).toMatch(/cash|pto/);
  });

  it("highlights cash-out line in compact preview", () => {
    const preview = previewExcerpt(leavePolicy);
    const segs = splitByExcerpts(preview, buildFocusNeedles(leavePolicy));
    expect(segs.some((s) => s.type === "highlight")).toBe(true);
    const highlighted = segs
      .filter((s) => s.type === "highlight")
      .map((s) => s.text)
      .join(" ");
    expect(highlighted.toLowerCase()).toMatch(/cash/);
  });
});
