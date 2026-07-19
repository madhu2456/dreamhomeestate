FROM node:20-alpine

WORKDIR /app

RUN apk add --no-cache libc6-compat

# Install pnpm
RUN corepack enable && corepack prepare pnpm@9.4.0 --activate

COPY apps/web/package.json apps/web/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

COPY apps/web .

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["pnpm", "dev"]
