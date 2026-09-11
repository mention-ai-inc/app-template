import type { ApiClient } from "@/client";
import { formatNote, formatNotes, registerNoteTools } from "@/tools/notes";
import type { ToolResult } from "@/tools/shared";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp";
import type { components } from "@packages/acme-api";
import { describe, expect, it, vi } from "vitest";
import type { ZodTypeAny } from "zod";

type Registration = {
  config: { description: string; inputSchema?: Record<string, ZodTypeAny> };
  handler: (args: Record<string, string>) => Promise<ToolResult>;
};

function registerAgainst(
  client: Partial<ApiClient>,
): Map<string, Registration> {
  const registrations = new Map<string, Registration>();
  const server = {
    registerTool: (
      name: string,
      config: Registration["config"],
      handler: Registration["handler"],
    ) => {
      registrations.set(name, { config, handler });
    },
  } as unknown as McpServer;
  registerNoteTools(server, client as ApiClient);
  return registrations;
}

const NOTE: components["schemas"]["NoteRead"] = {
  id: "note-1",
  title: "Standup",
  status: "summarized",
  summary: "Login fix shipped.",
  created_at: "2026-01-01T00:00:00Z",
};

describe("formatNotes", () => {
  it("says so when there are no notes", () => {
    expect(formatNotes([])).toBe("No notes yet.");
  });

  it("omits the summary line while none exists", () => {
    const pending = { ...NOTE, status: "pending" as const, summary: null };
    expect(formatNote(pending)).not.toContain("Summary:");
    expect(formatNote(NOTE)).toContain("Summary: Login fix shipped.");
  });
});

describe("note tools", () => {
  it("registers list_notes without inputs and create_note with title and body", () => {
    const registrations = registerAgainst({});
    expect(registrations.get("list_notes")?.config.inputSchema).toBeUndefined();
    expect(
      Object.keys(registrations.get("create_note")!.config.inputSchema!),
    ).toEqual(["title", "body"]);
  });

  it("posts the note and returns it formatted", async () => {
    const POST = vi.fn(async () => ({ data: NOTE, error: undefined }));
    const { handler } = registerAgainst({
      POST: POST as unknown as ApiClient["POST"],
    }).get("create_note")!;
    const result = await handler({ title: "Standup", body: "Shipped." });
    expect(POST).toHaveBeenCalledWith("/rest/notes/notes", {
      body: { title: "Standup", body: "Shipped." },
    });
    expect(result.content[0]!.text).toContain("note_id: note-1");
  });

  it("surfaces the API error detail", async () => {
    const GET = vi.fn(async () => ({
      data: undefined,
      error: { detail: "Forbidden." },
    }));
    const { handler } = registerAgainst({
      GET: GET as unknown as ApiClient["GET"],
    }).get("list_notes")!;
    const result = await handler({});
    expect(result.isError).toBe(true);
    expect(result.content[0]!.text).toBe(
      "Error: Failed to list notes: Forbidden.",
    );
  });
});
