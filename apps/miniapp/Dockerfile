# syntax=docker/dockerfile:1

# The build context is the repository root, not this directory: the install needs the workspace
# lockfile, and tsconfig.json resolves @shared/* to ../../packages/api-types/src. Those imports
# are type-only and nothing from that package reaches the bundle, but `next build` type-checks,
# so the files must be on disk.
#
#   docker build -f apps/miniapp/Dockerfile -t smart-accounting-miniapp .

# ---------------------------------------------------------------- build stage

FROM node:20.18.0-alpine AS builder

# Corepack prompts before downloading a pnpm it does not have, and a prompt in a
# non-interactive build is a hang, not a question.
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    NEXT_TELEMETRY_DISABLED=1

# Baked into .next/routes-manifest.json by `next build` (see next.config.mjs). `sa-api` is the
# API's alias on the shared edge network. Caddy routes /api/v1/* before a request reaches Next,
# so this matters only for a path the Caddy matcher misses — and then it answers instead of 502.
ENV API_PROXY_TARGET=http://sa-api:8000

# The corepack bundled with Node 20.18 verifies pnpm against npm registry signing keys that npm
# has since rotated, and fails with "Cannot find matching keyid". A newer corepack carries the
# current keys. Pinned, so a future corepack release cannot change the build under us.
RUN npm install -g corepack@0.36.0 \
 && corepack enable

WORKDIR /app

# Manifests before source, so a code change does not invalidate the install layer.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY apps/miniapp/package.json apps/miniapp/package.json
COPY packages/api-types/package.json packages/api-types/package.json
RUN --mount=type=cache,id=pnpm-store,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

COPY apps/miniapp apps/miniapp
COPY packages/api-types packages/api-types
RUN pnpm turbo run build --filter=@smart-accounting/miniapp

# --------------------------------------------------------------- runtime stage

FROM node:20.18.0-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0 \
    NEXT_TELEMETRY_DISABLED=1

# A process that only reads its own bundle has no reason to be root.
RUN addgroup -S -g 1001 nodejs \
 && adduser -S -u 1001 -G nodejs nextjs

# `output: "standalone"` emits traced node_modules at the bundle root and the app under its
# workspace path, so server.js lands at /app/apps/miniapp/server.js with its dependencies beside
# it. Static assets are not traced and are copied separately. The app has no public/ directory.
COPY --from=builder --chown=nextjs:nodejs /app/apps/miniapp/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/miniapp/.next/static ./apps/miniapp/.next/static

USER nextjs

EXPOSE 3000

# Lets compose wait for the server to answer rather than merely exist.
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:3000/ || exit 1

CMD ["node", "apps/miniapp/server.js"]
