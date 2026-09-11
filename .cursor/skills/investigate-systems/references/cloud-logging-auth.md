# Cloud Logging MCP authentication

Claude Code does not expand environment variables inside `oauth` fields. Use a Web application OAuth client in the operations project; do not reuse Cursor's Desktop client.

Register both loopback redirects, matching `oauth.callbackPort`:

- `http://localhost:8787/callback`
- `http://127.0.0.1:8787/callback`

Add the feature server with Claude Code:

```bash
claude mcp remove cloud-logging-feature -s project 2>/dev/null || true
claude mcp add --transport http \
  --client-id "YOUR_WEB_CLIENT_ID.apps.googleusercontent.com" \
  --client-secret \
  --callback-port 8787 \
  -H "x-goog-user-project: <feature-project>" \
  -s project \
  cloud-logging-feature https://logging.googleapis.com/mcp
```

Repeat for production with `cloud-logging-production` and the production project. Then run `claude mcp login <server>` and restart Claude Code.

The target project requires `roles/mcp.toolUser` plus logging read access. `--client-secret` prompts securely or reads `MCP_CLIENT_SECRET`; do not commit the secret.
