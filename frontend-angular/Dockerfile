# ==============================================================================
# Brand Guardian AI — Angular Frontend Production Dockerfile (Phase 7)
# ==============================================================================
# Multi-stage build:
#   Stage 1: Compile Angular 21 TypeScript application into optimized static assets
#   Stage 2: Serve compiled bundle via hardened, minimal Nginx reverse proxy
# ==============================================================================

# --- Stage 1: Build Angular Production Distribution ---
FROM node:22-alpine AS build

WORKDIR /app

# Install dependencies utilizing package-lock for reproducible builds
COPY package*.json ./
RUN npm ci

# Copy application source code and compile production distribution
COPY . .
RUN npm run build

# --- Stage 2: Serve via High-Performance Nginx ---
FROM nginx:alpine-slim

# Remove default Nginx welcome site
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled Angular browser bundle from build stage
COPY --from=build /app/dist/frontend-angular/browser /usr/share/nginx/html

# Copy production reverse-proxy Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose standard HTTP port
EXPOSE 80

# Run Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
