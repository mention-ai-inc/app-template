FROM node:22-alpine AS builder
WORKDIR /app

# Pin pnpm to match the repo lockfile expectations (pnpm 11 changes lockfile config semantics).
RUN corepack enable && corepack prepare pnpm@10.26.2 --activate

COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./
COPY apps/mcp/ apps/mcp/
COPY packages/ packages/
RUN pnpm install --frozen-lockfile --filter @acme/mcp...
RUN pnpm --filter @acme/mcp build

FROM node:22-alpine
WORKDIR /app
COPY --from=builder /app/apps/mcp/dist/index.js .

ARG FEATURE_ENVIRONMENT=
ENV FEATURE_ENVIRONMENT=${FEATURE_ENVIRONMENT}

CMD ["node", "index.js"]
