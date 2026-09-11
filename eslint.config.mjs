import path from "node:path";
import { fileURLToPath } from "node:url";
import tsParser from "@typescript-eslint/parser";
import reactHooks from "eslint-plugin-react-hooks";
import tailwindCanonicalClasses from "eslint-plugin-tailwind-canonical-classes";
import unusedImports from "eslint-plugin-unused-imports";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default [
  {
    ignores: [
      "apps/web/dist/**",
      "apps/mcp/dist/**",
      "apps/web/src/components/ui/*.tsx",
      "apps/web/src/routeTree.gen.ts",
      "apps/mobile/.expo/**",
      "apps/mobile/expo-env.d.ts",
      "packages/acme-api/src/*.d.ts",
      "services/*/.venv/**/*.js",
      "library/.venv/**/*.js",
      ".venv/**/*.js",
    ],
  },
  {
    files: ["**/*.{js,jsx,ts,tsx}"],
    plugins: {
      "unused-imports": unusedImports,
    },
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    rules: {
      "unused-imports/no-unused-imports": "error",
    },
  },
  {
    files: ["apps/**/*.{js,jsx,ts,tsx}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: [".*", "../*"],
              message: "Use @/ imports instead of relative imports (./ or ../)",
            },
          ],
        },
      ],
    },
  },
  {
    files: ["**/vite.config.ts", "**/tailwind.config.ts"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
      },
    },
  },
  {
    files: ["apps/web/**/*.{js,jsx,ts,tsx}", "apps/mobile/**/*.{js,jsx,ts,tsx}"],
    plugins: {
      "react-hooks": reactHooks,
    },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
    },
  },
  {
    files: ["apps/web/**/*.{js,jsx,ts,tsx}"],
    plugins: {
      "tailwind-canonical-classes": tailwindCanonicalClasses,
    },
    rules: {
      "tailwind-canonical-classes/tailwind-canonical-classes": [
        "error",
        { cssPath: path.join(__dirname, "apps/web/src/main.css") },
      ],
    },
  },
];
