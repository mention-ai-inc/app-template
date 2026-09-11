import { buildInstructions } from "@/instructions";
import { describe, expect, it } from "vitest";

describe("buildInstructions", () => {
  it("names both tools and explains the summary lifecycle", () => {
    const output = buildInstructions();
    expect(output).toContain("list_notes");
    expect(output).toContain("create_note");
    expect(output).toContain("pending or summarizing");
  });
});
