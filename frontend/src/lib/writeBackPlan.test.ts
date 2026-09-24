import { describe, expect, it } from "vitest";
import { isEmptyWriteBackPlan, planActionLines } from "./writeBackPlan";

describe("writeBackPlan", () => {
  it("builds plan action lines from write-back flags", () => {
    expect(
      planActionLines({
        needs_doc_update: true,
        doc_target: "existing",
        existing_doc_path: "docs/adr/0002-tech-stack.md",
        new_doc_slug: null,
        needs_roadmap_item: true,
      }),
    ).toEqual([
      "Update docs/adr/0002-tech-stack.md",
      "Create Linear roadmap item",
    ]);
  });

  it("detects empty write-back plans", () => {
    expect(
      isEmptyWriteBackPlan({
        needs_doc_update: false,
        doc_target: null,
        existing_doc_path: null,
        new_doc_slug: null,
        needs_roadmap_item: false,
      }),
    ).toBe(true);
  });
});
