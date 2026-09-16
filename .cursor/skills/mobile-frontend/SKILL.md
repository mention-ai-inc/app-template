---
name: mobile-frontend
description: Build or change the Expo and React Native app under apps/mobile. Use for mobile screens, components, navigation, styling, forms, lists, sheets, feedback states, or other mobile UI and UX work. Apply the product design brief and preserve native behavior on iOS and Android.
---

# Mobile frontend

## Workflow

1. Read `docs/product/design.md` and the closest one or two existing screens or components before editing.
2. Follow the agreed design decisions and neighboring code structure. Starter styling is provisional; the `product-design` rule explains how to work before a direction is chosen.
3. Read the applicable project rules for TypeScript, React data access, and comments.
4. Handle loading, empty, error, pending, and disabled states where relevant.
5. Consider iOS and Android behavior, safe areas, keyboards, and touch targets.
6. Run `m run-code-formatting`, then `m run-checks-frontend`. Run `m compile-api` after backend contract changes.

## App conventions

- Routes live in `apps/mobile/app/`; reusable components in `components/`; hooks, contexts, and utilities in `lib/`.
- Use kebab-case filenames. Components use named exports; Expo Router route files use default exports.
- Import app code through `@/`, API hooks through `@packages/acme-api-client`, and generated API types through `components` from `@packages/acme-api`.
- Use TanStack Query wrappers for server state. Do not hand-roll `fetch`, duplicate API types, or add another state-management library.
- Keep providers such as `Toaster`, `KeyboardAvoidingView`, `SafeAreaProvider`, and query providers in the root layout. Do not mount duplicates in screens.

## UI conventions

- Style with NativeWind `className`. Use `style` only for props NativeWind cannot reach, such as `contentContainerStyle`, dynamic inset math, or provider flex styles.
- Use the semantic color tokens from `tailwind.config.js` (`bg-background`, `text-muted-foreground`, `border-border-subtle`, `bg-primary`, spacing tokens like `px-screen`, `p-card`, `gap-stack`, radius tokens like `rounded-surface`). Dark mode is `darkMode: "media"`: every color class needs its explicit `dark:` twin. For imperative color needs (icons, spinners, header options) use `themeColors(useColorScheme() === "dark")` from `lib/theme`.
- Use the shared primitives in `components/ui/` (`Button`, `Field`, `Screen`, `Surface`, `PageHeader`, `EmptyState`, `LoadingState`) via `@/components/ui`. Keep single-use variants near their only consumer.
- The starter uses platform fonts. Apply typography decisions from the product brief through shared components and theme configuration.
- The starter uses `@expo/vector-icons`. Keep icon usage consistent with the product brief and shared components.
- Keep primary touch targets at least 44 points, add pressed and disabled feedback, and label icon-only controls for accessibility.
- Keep text inside `Text`, allow long content to wrap, and avoid fixed dimensions that clip dynamic content.
- Reanimated is available for motion. Follow the product brief and respect reduced-motion preferences.

## Interaction patterns

- Screens generally use `SafeAreaView className="flex-1 bg-background dark:bg-background-dark" edges={["top"]}` (or the `Screen` primitive). Use `useSafeAreaInsets()` for pinned footers and sheets.
- The root keyboard providers already handle avoidance. Do not add screen-level `KeyboardAvoidingView` wrappers.
- Use Expo Router redirects for guards, `router.replace` after auth transitions, and `router.push` or `Link` for forward navigation.
- Use `@gorhom/bottom-sheet` for sheets, with a backdrop, the bottom inset, and scrollable content.
- Surface mutation failures using the app's error-message helpers. Choose inline, toast, or other feedback according to the product brief and interaction.
- Prefer shared platform code. Branch on `Platform.OS` only for genuine platform differences.

## Reference files

Read only the references relevant to the task:

| Concern | Reference |
| --- | --- |
| Providers, startup | `apps/mobile/app/_layout.tsx` |
| Auth, tabs, suspense | `apps/mobile/app/(member)/_layout.tsx` |
| List, mutation | `apps/mobile/app/(member)/notes.tsx` |
| Forms | `apps/mobile/app/sign-in.tsx` |
| Query behavior | `apps/mobile/lib/api.ts` |
| UI primitives | `apps/mobile/components/ui/index.ts` |
| Theme tokens | `apps/mobile/tailwind.config.js`, `apps/mobile/lib/theme.ts` |

Inspect the current app before adding dependencies or replacing shared infrastructure. Use `define-design` for brand and design discovery; keep the resulting product choices in `docs/product/design.md`.
