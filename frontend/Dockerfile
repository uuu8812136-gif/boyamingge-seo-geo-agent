FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

FROM node:20-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_URL=
ARG NEXT_PUBLIC_SITE_URL=http://localhost
ARG NEXT_PUBLIC_ROOT_DOMAIN=boyamingge.com
ARG NEXT_PUBLIC_ADMIN_URL=https://admin.boyamingge.com
ARG NEXT_PUBLIC_CITY_DOMAIN_MODE=path
ARG NEXT_PUBLIC_ENABLE_CITY_PATH_REDIRECT=false
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_ROOT_DOMAIN=$NEXT_PUBLIC_ROOT_DOMAIN
ENV NEXT_PUBLIC_ADMIN_URL=$NEXT_PUBLIC_ADMIN_URL
ENV NEXT_PUBLIC_CITY_DOMAIN_MODE=$NEXT_PUBLIC_CITY_DOMAIN_MODE
ENV NEXT_PUBLIC_ENABLE_CITY_PATH_REDIRECT=$NEXT_PUBLIC_ENABLE_CITY_PATH_REDIRECT
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# Next.js standalone 产物，使用 node 用户运行
COPY --from=builder --chown=node:node /app/public ./public
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static

USER node
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -qO- http://127.0.0.1:3000/ >/dev/null 2>&1 || exit 1

CMD ["node", "server.js"]
