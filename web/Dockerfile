# KORA Web Dashboard Production Dockerfile
# =========================================

# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Build arguments for environment
ARG VITE_API_URL=http://localhost:4000

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN VITE_API_URL=$VITE_API_URL npm run build

# Production stage with nginx
FROM nginx:alpine AS production

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Add health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
