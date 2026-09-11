import type { ApiClient } from "@/client";
import { registerNoteTools } from "@/tools/notes";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp";

export function registerTools(server: McpServer, client: ApiClient): void {
  registerNoteTools(server, client);
}
