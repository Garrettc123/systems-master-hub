# Railway deployment: serve the static GAR-25 dashboard via nginx
FROM nginx:1.25-alpine

# Copy dashboard HTML as the root index
COPY dashboard/gar25-autonomous-dashboard.html /usr/share/nginx/html/index.html

# Copy any other static assets if present
COPY dashboard/ /usr/share/nginx/html/

# Nginx listens on 80; Railway will map $PORT -> 80 via its proxy
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
