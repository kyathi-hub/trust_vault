# TrustVault Frontend — multi-stage build
# Stage 1: build the React app
# Stage 2: serve with nginx (minimal image)

FROM node:20-alpine AS builder

WORKDIR /app

# Accept build args for Vite env vars (injected at build time, not runtime)
ARG VITE_API_URL=/api/v1
ARG VITE_KEYCLOAK_URL=/auth
ARG VITE_KEYCLOAK_REALM=trustvault
ARG VITE_KEYCLOAK_CLIENT_ID=trustvault-frontend

ENV VITE_API_URL=$VITE_API_URL
ENV VITE_KEYCLOAK_URL=$VITE_KEYCLOAK_URL
ENV VITE_KEYCLOAK_REALM=$VITE_KEYCLOAK_REALM
ENV VITE_KEYCLOAK_CLIENT_ID=$VITE_KEYCLOAK_CLIENT_ID

COPY package.json package-lock.json* ./
RUN npm ci --frozen-lockfile

COPY . .
RUN npm run build

# Stage 2: serve static files
FROM nginx:1.27-alpine AS production

# Non-root nginx
RUN addgroup -g 101 nginx-app && adduser -u 101 -G nginx-app -s /bin/sh -D nginx-app || true

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

RUN chown -R nginx-app:nginx-app /usr/share/nginx/html \
    && chown -R nginx-app:nginx-app /var/cache/nginx \
    && chown -R nginx-app:nginx-app /var/log/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx-app:nginx-app /var/run/nginx.pid

USER nginx-app

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
