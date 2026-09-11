import type { ApiClient } from "@/client";
import { apiFailureResult, caughtResult, textResult } from "@/tools/shared";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp";
import type { components } from "@packages/acme-api";
import { z } from "zod";

export function formatNote(note: components["schemas"]["NoteRead"]): string {
  const lines = [
    `## ${note.title} (note_id: ${note.id})`,
    `Status: ${note.status} · Created: ${note.created_at}`,
  ];
  if (note.summary !== null) {
    lines.push(`Summary: ${note.summary}`);
  }
  return lines.join("\n");
}

export function formatNotes(
  notes: components["schemas"]["NoteRead"][],
): string {
  if (notes.length === 0) {
    return "No notes yet.";
  }
  return notes.map(formatNote).join("\n\n");
}

export function registerNoteTools(server: McpServer, client: ApiClient): void {
  server.registerTool(
    "list_notes",
    {
      description:
        "Lists every note in the organization with its status and, once written, its summary. A note whose status is pending or summarizing has no summary yet.",
    },
    async () => {
      try {
        const { data, error } = await client.GET("/rest/notes/notes", {});
        if (!data) {
          return apiFailureResult("list notes", error);
        }
        return textResult(formatNotes(data.notes));
      } catch (err) {
        return caughtResult(err);
      }
    },
  );

  server.registerTool(
    "create_note",
    {
      description:
        "Records a new note. Acme summarizes it shortly afterwards; call list_notes to see the summary once the status is summarized.",
      inputSchema: {
        title: z.string().min(1).describe("A short title for the note."),
        body: z.string().min(1).describe("The full text of the note."),
      },
    },
    async ({ title, body }) => {
      try {
        const { data, error } = await client.POST("/rest/notes/notes", {
          body: { title, body },
        });
        if (!data) {
          return apiFailureResult("create the note", error);
        }
        return textResult(formatNote(data));
      } catch (err) {
        return caughtResult(err);
      }
    },
  );
}
