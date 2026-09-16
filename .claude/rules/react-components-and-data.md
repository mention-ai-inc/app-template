---
paths:
  - "**/*.tsx"
---

## React / UI conventions

- Components follow the principle of locality. Components that are only to be used by a single page live in a `components/` directory that is a sibling of the `index.tsx` for that page. Components that are meant to be re-used live in the `components/` directory at the top level of the project.

## Data fetching / mutations

- Never write your own queries and mutations in components or pages. Server queries and mutations live in `@packages/acme-api-client`. App-local composition hooks may live in the app's `hooks/` directory. If you cannot find a query or mutation that you think should exist based on the backend API and the functionality you are trying to implement, raise this as an issue before proceeding.

## Error feedback

- Surface failures using the app's error-message helpers. Follow the product design brief for placement and presentation of feedback.
