import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";

import VersionHistoryPanel from "./VersionHistoryPanel";


describe("VersionHistoryPanel", () => {
  test("renders current history, claim changes, and reviewable conflicts", () => {
    const html = renderToStaticMarkup(
      <VersionHistoryPanel
        canReview
        onReviewConflict={() => {}}
        temporal={{
          available: true,
          loading: false,
          versions: [
            { id: "v1", version_number: 1, effective_from: "2025-01-01T00:00:00Z", authority_level: 50, is_current: false },
            { id: "v2", version_number: 2, effective_from: "2026-01-01T00:00:00Z", authority_level: 80, is_current: true },
          ],
          diff: {
            added: [{ id: "new", text: "PTO is 20 days." }],
            removed: [{ id: "old", text: "PTO is 15 days." }],
            conflicts: [{
              id: "conflict-1",
              status: "candidate",
              conflict_type: "value_change",
              rationale: "Values differ across versions.",
            }],
          },
        }}
      />
    );

    expect(html).toContain("Version 2");
    expect(html).toContain("Current");
    expect(html).toContain("PTO is 20 days.");
    expect(html).toContain("PTO is 15 days.");
    expect(html).toContain("Confirm");
    expect(html).toContain("Dismiss");
  });
});