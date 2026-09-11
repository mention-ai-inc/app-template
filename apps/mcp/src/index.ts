import { createApiClient } from "@/client.js";
import { buildInstructions } from "@/instructions.js";
import { registerTools } from "@/tools/index.js";
import { clerkMiddleware } from "@clerk/express";
import {
  authServerMetadataHandlerClerk,
  mcpAuthClerk,
  protectedResourceHandler,
} from "@clerk/mcp-tools/express";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import cors from "cors";
import express from "express";

const apiUrl = process.env.API_URL ?? "https://api.acme.mentionai.app";

const MCP_SCOPES = ["openid", "profile", "email", "user:org:read"];

function deriveClerkAuthServerUrl(publishableKey: string): string {
  const encoded = publishableKey.replace(/^pk_(test|live)_/, "");
  const host = Buffer.from(encoded, "base64")
    .toString("utf8")
    .replace(/\$$/, "");
  return `https://${host}`;
}

const app = express();
app.set("trust proxy", true);
app.use(express.json());
app.use(cors({ exposedHeaders: ["WWW-Authenticate"] }));
app.use(clerkMiddleware());

const protectedResource = protectedResourceHandler({
  authServerUrl: deriveClerkAuthServerUrl(process.env.CLERK_PUBLISHABLE_KEY!),
  properties: { scopes_supported: MCP_SCOPES },
});
app.get("/.well-known/oauth-protected-resource/mcp", protectedResource);
app.get("/.well-known/oauth-protected-resource", protectedResource);
app.get(
  "/.well-known/oauth-authorization-server",
  authServerMetadataHandlerClerk,
);

app.all("/mcp", mcpAuthClerk, async (req, res) => {
  try {
    const token = req.headers.authorization!.replace("Bearer ", "");
    const client = createApiClient(token, apiUrl);

    const server = new McpServer(
      { name: "acme", version: "0.1.0" },
      { instructions: buildInstructions() },
    );

    registerTools(server, client);

    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,
    });

    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);

    res.on("finish", () => {
      server.close().catch(() => {});
    });
  } catch (error) {
    if (!res.headersSent) {
      const message =
        error instanceof Error ? error.message : "Internal server error";
      res.status(500).json({ error: message });
    }
  }
});

app.get("/health", (_, res) => {
  res.json({ ok: true });
});

const port = Number(process.env.PORT ?? 8080);
app.listen(port, () => {
  console.log(`MCP server listening on port ${port}`);
});
