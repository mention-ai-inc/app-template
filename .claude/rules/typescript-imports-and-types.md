---
paths:
  - "**/*.ts"
  - "**/*.tsx"
---

## TypeScript conventions

- Use `[]` array syntax instead of `Array<>`.
- Always use `@` syntax for imports from within the project, as opposed to relative imports starting with `./` or `../`.
- API types should always be used via the `components` import from `@packages/acme-api`. Do not create type aliases as a shorthand.
