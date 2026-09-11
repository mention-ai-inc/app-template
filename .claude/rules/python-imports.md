---
paths:
  - "**/*.py"
---

## Python imports

- Place all imports at module top level. Do not import inside functions, methods, or nested scopes (including tests and helpers) unless there is an exceptional, documented reason such as avoiding a circular import that cannot be resolved otherwise—and prefer refactoring to fix the cycle instead.
- Do not use lazy imports for convenience (e.g. keeping a factory short, type hints on nested callbacks). Hoist those symbols to the top of the file with the rest of the imports.
