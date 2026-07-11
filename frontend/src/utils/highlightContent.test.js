import { describe, it, expect } from "vitest";
import { findExcerptRange, splitByExcerpts } from "./highlightContent";

describe("highlightContent", () => {
  it("finds exact excerpt", () => {
    const content = "The PTO policy allows fifteen days per year.";
    const r = findExcerptRange(content, "fifteen days per year");
    expect(r).not.toBeNull();
    expect(content.slice(r.start, r.end)).toBe("fifteen days per year");
  });

  it("splits multiple highlights", () => {
    const content = "AAAA BBBB CCCC DDDD";
    const segs = splitByExcerpts(content, ["BBBB", "DDDD"]);
    expect(segs.filter((s) => s.type === "highlight")).toHaveLength(2);
  });

  it("matches across extra whitespace", () => {
    const content = "The PTO policy allows\n\nfifteen days per year.";
    const r = findExcerptRange(content, "PTO policy allows fifteen days per year");
    expect(r).not.toBeNull();
    expect(content.slice(r.start, r.end)).toMatch(/fifteen/);
  });

  it("falls back to a shortened prefix for long excerpts", () => {
    const shared = "A".repeat(120);
    const content = `Before ${shared} after`;
    const r = findExcerptRange(content, `${shared}${"B".repeat(800)}`);
    expect(r).not.toBeNull();
    expect(content.slice(r.start, r.end)).toContain(shared);
  });

  it("merges overlapping highlight ranges", () => {
    const content = "alpha beta gamma delta";
    const segs = splitByExcerpts(content, ["beta gamma", "gamma delta"]);
    const highlights = segs.filter((segment) => segment.type === "highlight");
    expect(highlights).toHaveLength(1);
    expect(highlights[0].text).toBe("beta gamma delta");
  });
});
