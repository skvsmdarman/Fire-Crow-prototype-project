FROM nginx:1.27-alpine

RUN apk add --no-cache curl

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80 443

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/health/live || exit 1
