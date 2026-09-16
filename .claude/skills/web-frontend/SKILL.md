---
name: web-frontend
description: Build or change the Vite and React web app under apps/web. Use for web pages, routes, components, styling, forms, dialogs, sheets, onboarding flows, or other web UI and UX work. Apply the product design brief and the app's routing and data-access conventions.
---

# Web frontend

## Workflow

1. Read `docs/product/design.md` and the closest one or two existing pages, routes, or components before editing.
2. Follow the agreed design decisions and neighboring code structure. Starter styling is provisional; the `product-design` rule explains how to work before a direction is chosen.
3. Read the applicable project rules for TypeScript, React data access, and comments.
4. Handle loading, empty, error, pending, and disabled states where relevant.
5. Prefer existing shadcn primitives in `src/components/ui/` over hand-rolled equivalents.
6. Run `m run-code-formatting`, then `m run-checks-frontend`. Run `m compile-api` after backend contract changes.

## App conventions

- Routes live in `apps/web/src/routes/` and stay thin (wiring, guards, loaders, pending/error components). Page UI lives in `apps/web/src/pages/`.
- Reusable components live in `apps/web/src/components/`. Page-only components live in a sibling `components/` directory next to that page (locality). Feature-shared pieces may live under a feature folder such as `pages/notes/components/`.
- App-local composition hooks live in `apps/web/src/hooks/` or a page-local `hooks/` directory. Server queries and mutations live in `@packages/acme-api-client` — do not invent API CRUD hooks under `apps/web`.
- Use kebab-case filenames. Page and shared components use named exports.
- Import app code through `@/`, API hooks through `@packages/acme-api-client`, and generated API types through `components` from `@packages/acme-api`.
- Do not hand-roll `fetch`, duplicate OpenAPI types, or add another client-side state-management library for server data.
- Keep providers (`Clerk`, `ApiProvider`, `QueryClientProvider`, `ThemeProvider`, `Toaster`) in `main.tsx` / root layout. Do not mount duplicates in pages.
- Do not hand-edit `routeTree.gen.ts`.

## UI conventions

- The starter uses shadcn/ui primitives from `src/components/ui/`, configured in `components.json`. Reuse and adapt them to the product design brief.
- Style with Tailwind utility classes and theme tokens from `src/main.css`. Use `cn()` from `@/lib/utils` when merging classes.
- Keep theme selection in `ThemeProvider` and colors in the light/dark CSS variables. The starter follows the system theme; the product brief can choose different behavior.
- The starter uses lucide-react icons. Keep icon usage consistent with the product brief and shared components.
- Controlled Dialog and Sheet patterns use `open` / `onOpenChange`.
- Forms use local `useState` and a native `<form onSubmit>` with shadcn inputs. Do not introduce react-hook-form or zod form schemas unless the product explicitly requires a new convention.
- Format mutation failures with `getErrorMessage(error, "Fallback…")`. Choose inline, toast, or other feedback according to the product brief and interaction.

## Interaction patterns

- Authenticated shells use layout route groups. Follow the existing organization guard on the root route.
- Prefer route `loader` + `pendingComponent` / `errorComponent` and Suspense query hooks where neighboring routes already do.
- Use shared page states in `src/components/page-states/` for full-page loading, error, and not-found UI.

## Reference files

Read only the references relevant to the task:

| Concern | Reference |
| --- | --- |
| Providers, bootstrap | `apps/web/src/main.tsx`, `apps/web/src/routes/__root.tsx` |
| List, mutation, form | `apps/web/src/pages/notes/index.tsx` |
| Loading and errors | `apps/web/src/components/page-states/loading.tsx`, `error.tsx` |
| Query hook | `packages/acme-api-client/src/hooks/use-notes.ts` |

Inspect the current app before adding dependencies or replacing shared infrastructure. Use `define-design` for brand and design discovery; keep the resulting product choices in `docs/product/design.md`.
