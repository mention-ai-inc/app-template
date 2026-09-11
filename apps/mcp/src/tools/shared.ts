export type ToolResult = {
  content: { type: "text"; text: string }[];
  isError?: boolean;
};

export function textResult(text: string): ToolResult {
  return { content: [{ type: "text", text }] };
}

export function errorResult(text: string): ToolResult {
  return {
    content: [{ type: "text", text: `Error: ${text}` }],
    isError: true,
  };
}

export function caughtResult(err: unknown): ToolResult {
  return errorResult(err instanceof Error ? err.message : String(err));
}

export function missingFieldsResult(
  action: string,
  fields: string[],
): ToolResult {
  return errorResult(
    `Action "${action}" requires the following input field${fields.length === 1 ? "" : "s"}: ${fields.join(", ")}.`,
  );
}

export function apiFailureResult(what: string, error?: unknown): ToolResult {
  const detail = extractErrorDetail(error);
  if (detail) {
    return errorResult(`Failed to ${what}: ${detail}`);
  }
  return errorResult(`Failed to ${what} via the API.`);
}

function extractErrorDetail(error: unknown): string | null {
  if (typeof error !== "object" || error === null) {
    return null;
  }
  const detail = (error as Record<string, unknown>).detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (detail !== undefined) {
    return JSON.stringify(detail);
  }
  return null;
}
