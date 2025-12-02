# Multi-stage build for React frontend
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY frontend/react_dashboard/package*.json ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Copy source code
COPY frontend/react_dashboard/ ./

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine AS production

# Copy custom nginx configuration
COPY deployment/docker/frontend/nginx.conf /etc/nginx/nginx.conf

# Copy built application from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Use existing nginx user or create if doesn't exist
RUN addgroup -g 1001 -S appgroup 2>/dev/null || true && \
    adduser -S -D -H -u 1001 -h /var/cache/nginx -s /sbin/nologin -G appgroup appuser

# Set permissions
RUN chown -R appuser:appgroup /var/cache/nginx && \
    chown -R appuser:appgroup /usr/share/nginx/html && \
    chown -R appuser:appgroup /var/log/nginx && \
    chown -R appuser:appgroup /etc/nginx/conf.d

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]