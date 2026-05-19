# nginx Cheatsheet — General Reference

Quick-reference card for nginx configuration. For conceptual depth, see [[nginx-concepts]].

---

## Config File Structure

```nginx
# Global (main) context
worker_processes auto;
pid /tmp/nginx.pid;

events {
    worker_connections 1024;
}

http {
    # HTTP-wide settings

    upstream mybackend {        # optional: named upstream group
        server 127.0.0.1:8001;
        server 127.0.0.1:8002;
    }

    server {
        listen 80;
        server_name example.com;

        location /path {
            # request handling
        }
    }
}
```

---

## Location Matching — Priority Order

```
1. Exact:           location = /foo          → highest priority, stops search
2. Preferential:    location ^~ /images/     → wins over regex if matched
3. Case-sensitive:  location ~ \.php$        → regex, config order
4. Case-insensitive:location ~* \.jpg$       → regex, config order
5. Prefix:          location /api/           → longest prefix wins
6. Catch-all:       location /               → always matches, lowest priority
```

```nginx
# Examples
location = /health    { return 200 "ok"; }         # exact
location ^~ /static/  { root /var/www; }           # preferential prefix
location ~ \.php$     { fastcgi_pass php:9000; }   # case-sensitive regex
location ~* \.(jpg|png)$ { expires 30d; }          # case-insensitive regex
location /api/        { proxy_pass http://api; }   # prefix
location /            { try_files $uri $uri/ =404; } # catch-all
```

---

## proxy_pass — Reverse Proxy

```nginx
# Forward to backend, keeping the path as-is
location /api/ {
    proxy_pass http://backend:8001;
    # /api/foo → http://backend:8001/api/foo
}

# Strip the location prefix (trailing slash on proxy_pass)
location /api/ {
    proxy_pass http://backend:8001/;
    # /api/foo → http://backend:8001/foo
}

# Use a variable (enables runtime DNS resolution)
set $upstream backend:8001;
proxy_pass http://$upstream;
```

---

## Essential Proxy Headers

```nginx
proxy_http_version 1.1;                                         # enable keep-alive
proxy_set_header Host              $http_host;                  # original Host
proxy_set_header X-Real-IP         $remote_addr;                # client IP
proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for; # proxy chain
proxy_set_header X-Forwarded-Proto $scheme;                     # http or https
proxy_set_header Connection        '';                          # clear for keep-alive
```

---

## WebSocket Proxy

```nginx
location /ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade    $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_cache_bypass          $http_upgrade;
}
```

---

## SSE / Streaming Proxy

```nginx
location /stream/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_buffering           off;
    proxy_cache               off;
    proxy_set_header Connection        '';
    proxy_set_header X-Accel-Buffering no;
    chunked_transfer_encoding on;
    proxy_read_timeout        600s;
}
```

---

## Timeouts

```nginx
proxy_connect_timeout 60s;   # time to establish TCP to upstream
proxy_send_timeout    60s;   # time between writes to upstream
proxy_read_timeout    60s;   # time between reads from upstream (most important)
keepalive_timeout     65s;   # how long to keep client connection alive
```

---

## Buffering

```nginx
# Response buffering (default: on)
proxy_buffering off;          # disable for streaming
proxy_buffer_size 4k;         # size of first buffer (headers)
proxy_buffers 8 8k;           # number and size of response buffers

# Request buffering
proxy_request_buffering off;  # stream request body directly to backend
client_max_body_size 100M;    # max allowed request body size (0 = unlimited)
```

---

## URL Rewriting

```nginx
# rewrite <regex> <replacement> [flag]
rewrite ^/old/(.*)$ /new/$1 break;   # rewrite and stop (use new URI)
rewrite ^/old/(.*)$ /new/$1 last;    # rewrite and re-match locations
rewrite ^/(.*)$     /index.html last; # SPA catch-all

# Flags:
# break  — stop rewriting, use this URI as-is
# last   — stop rewriting, restart location matching
# redirect  — 302 redirect
# permanent — 301 redirect
```

---

## Static Files

```nginx
location /static/ {
    root /var/www;           # serves /var/www/static/...
    # OR
    alias /var/www/files/;   # serves /var/www/files/... (strips /static/)

    expires 30d;
    add_header Cache-Control "public";
    try_files $uri =404;
}
```

---

## try_files

```nginx
# Try paths in order; use last as fallback (uri or status code)
try_files $uri $uri/ /index.html;   # SPA routing
try_files $uri =404;                # serve file or 404
try_files $uri @fallback;           # named location fallback

location @fallback {
    proxy_pass http://backend;
}
```

---

## Upstream Block (Load Balancing)

```nginx
upstream myapp {
    server backend1:8001;
    server backend2:8001;
    server backend3:8001 backup;   # only used when others are down

    # Load balancing methods (default: round-robin)
    least_conn;        # fewest active connections
    ip_hash;           # sticky sessions by client IP

    keepalive 32;      # keep 32 idle connections to upstreams
}

location / {
    proxy_pass http://myapp;
}
```

---

## DNS Resolver (Required for Variable proxy_pass)

```nginx
resolver 8.8.8.8 valid=30s;         # public DNS, cache 30s
resolver 127.0.0.11 valid=10s ipv6=off;  # Docker internal DNS
```

---

## HTTPS / SSL

```nginx
server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate     /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;

    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 10m;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    return 301 https://$host$request_uri;
}
```

---

## Response Headers

```nginx
add_header X-Frame-Options      "SAMEORIGIN";
add_header X-Content-Type-Options "nosniff";
add_header X-XSS-Protection     "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

# CORS (simple, not recommended — let app handle it)
add_header Access-Control-Allow-Origin  "$http_origin";
add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
add_header Access-Control-Allow-Headers "Authorization, Content-Type";
```

---

## Logging

```nginx
access_log /var/log/nginx/access.log;
error_log  /var/log/nginx/error.log warn;

# Custom log format
log_format main '$remote_addr - $remote_user [$time_local] '
                '"$request" $status $body_bytes_sent '
                '"$http_referer" "$http_user_agent"';
access_log /var/log/nginx/access.log main;

# Log to stdout/stderr (useful in Docker)
access_log /dev/stdout;
error_log  /dev/stderr;
```

---

## Gzip Compression

```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml;
gzip_min_length 1000;
gzip_comp_level 6;
gzip_vary on;
```

---

## Rate Limiting

```nginx
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    server {
        location /api/ {
            limit_req zone=api burst=20 nodelay;
        }
    }
}
```

---

## Common Variables

| Variable                     | Value                                            |
| ---------------------------- | ------------------------------------------------ |
| `$host`                      | Host header (without port)                       |
| `$http_host`                 | Host header (with port if present)               |
| `$remote_addr`               | Client IP                                        |
| `$scheme`                    | `http` or `https`                                |
| `$request_uri`               | Full URI including query string                  |
| `$uri`                       | URI without query string (may be rewritten)      |
| `$args`                      | Query string                                     |
| `$http_upgrade`              | Value of the Upgrade header                      |
| `$proxy_add_x_forwarded_for` | Existing XFF header + `, $remote_addr`           |
| `$upstream_addr`             | Address of the upstream that handled the request |

---

## Signals / CLI Commands

```bash
nginx -t                    # test config syntax
nginx -s reload             # reload config without downtime
nginx -s stop               # fast shutdown
nginx -s quit               # graceful shutdown
nginx -c /path/nginx.conf   # use specific config file
```

---

## Common Gotchas

| Gotcha                       | Explanation                                             |
| ---------------------------- | ------------------------------------------------------- |
| `proxy_pass` trailing slash  | With slash: strips matched prefix. Without: keeps it.   |
| Default upstream is HTTP/1.0 | Always add `proxy_http_version 1.1`                     |
| Location is not first-match  | Regex vs prefix priority system — read the docs         |
| SSE broken by default        | `proxy_buffering off` required                          |
| 502 on container restart     | Use variable-based `proxy_pass` + `resolver` for Docker |
| `$host` vs `$http_host`      | `$host` strips port; `$http_host` preserves it          |
| `add_header` inheritance     | Inner block `add_header` clears parent's headers        |
