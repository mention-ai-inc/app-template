## Iterate on web changes locally, not by deploying

A change confined to `apps/web/**` is checked on a local dev server pointed at an already-deployed feature environment, not by running `m deploy-web` and looking at the deployed site. Vite hot-reloads edits in seconds; a deploy takes minutes, ties up the environment, and tells you nothing the local server would not.

### The loop

1. Start the server from the worktree, pinning the environment explicitly (a stale `FEATURE_ENVIRONMENT` shell export silently overrides the branch-derived value):

   ```
   FEATURE_ENVIRONMENT=<env> m run-web
   ```

   It serves `http://localhost:3000` with `VITE_FEATURE_ENVIRONMENT=<env>`, so the app talks to `https://<env>api.<domain>` and signs in with the development identity-provider instance.
2. Open `http://localhost:3000` in the Chrome browser tools and sign in. The developer's own browser session carries the sign-in, so this works without a headless auth path.
3. Edit, let the page hot-reload, and check the screen visually. Repeat until the change is right.
4. Only then deploy, and only when the user asks for the environment updated or wants to review the final build themselves.

### When this does not apply

- The change also touches a service, the kernel, or Terraform. The local server still runs against the deployed API, so the backend half must deploy first.
- Mobile: use `m run-mobile-device-<platform>` on a device or simulator instead. The principle is the same: never deploy just to look at a UI change.
