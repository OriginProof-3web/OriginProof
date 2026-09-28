FROM node:22.18.0-alpine

WORKDIR /app
RUN corepack enable

ARG ORIGINPROOF_API_ORIGIN=http://api:8000
ENV ORIGINPROOF_API_ORIGIN=$ORIGINPROOF_API_ORIGIN

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --frozen-lockfile

COPY apps/web apps/web
COPY packages/schemas/generated/types packages/schemas/generated/types
RUN pnpm --filter originproof-demo-web build

WORKDIR /app/apps/web
ENV NODE_ENV=production
EXPOSE 3000
CMD ["pnpm", "start"]
