# nginx — Complete Mental Model

A deep conceptual guide for engineers new to nginx. Covers architecture, request
lifecycle, configuration model, reverse proxying, streaming, and key trade-offs.

---

## 1. What Is nginx?

nginx (pronounced "engine-x") is a **high-performance HTTP server and reverse proxy**.
It was built in 2004 to solve the "C10K problem" — how to handle 10,000 concurrent
connections on a single machine, which Apache at the time could not.

nginx's answer: **event-driven, non-blocking I/O** instead of Apache's one-thread-per-connection model.

### What nginx can do

| Role               | Description                                                  |
| ------------------ | ------------------------------------------------------------ |
| Web server         | Serve static files (HTML, CSS, JS, images) directly          |
| Reverse proxy      | Forward requests to backend app servers (FastAPI, Node, Go…) |
| Load balancer      | Distribute traffic across multiple upstream instances        |
| SSL terminator     | Handle HTTPS, then forward plain HTTP to backends            |
| API gateway (lite) | Path-based routing to different services                     |
| Cache              | Cache backend responses for repeated requests                |

DeerFlow uses nginx as a **reverse proxy + API gateway**: all traffic enters on one
port and is routed to either the Gateway (FastAPI) or the Frontend (Next.js).

---

## 2. Architecture — How nginx Actually Works

### The Master / Worker Model

```
┌──────────────────────────────────────────────────────┐
│  nginx process tree                                   │
│                                                       │
│  master process (PID = nginx.pid)                     │
│    │── reads config                                   │
│    │── binds to ports (privileged)                    │
│    │── spawns workers                                 │
│    │── handles signals (reload, stop, upgrade)        │
│    │                                                  │
│    ├── worker process 1  ──► handles connections      │
│    ├── worker process 2  ──► handles connections      │
│    └── worker process N  ──► handles connections      │
└──────────────────────────────────────────────────────┘
```

- **Master process**: runs as root (or the configured user), never handles HTTP itself
- **Worker processes**: run with reduced privileges, each worker is a **single OS thread**
- The number of workers is typically set to the number of CPU cores (`worker_processes auto;`)

### Event Loop (How One Worker Handles 10,000 Connections)

Each worker runs an **event loop** using the OS's async I/O primitives
(`epoll` on Linux, `kqueue` on BSD/macOS):

```
worker event loop:
  while (true):
    events = epoll_wait(...)   // block until I/O is ready (kernel tells us)
    for each event:
      if new_connection:      → accept() and register socket
      if data_ready:          → read request, parse, route, proxy
      if upstream_responded:  → write response back to client
      if write_ready:         → flush buffered output
```

A worker never **blocks** waiting for a backend. When it sends a request upstream,
it registers the socket with epoll and moves on to other events. When the backend
responds, epoll fires again and the worker picks up where it left off.

This is why nginx can handle thousands of concurrent connections with a handful of
worker threads, while Apache's thread-per-connection model requires thousands of threads.

---

## 3. Configuration Model — Contexts

nginx configuration is **hierarchical**. Directives live inside **contexts** (blocks),
and inner contexts inherit from outer ones.

```
# Global (main) context
worker_processes auto;
pid /tmp/nginx.pid;

events {                     # ← events context
    worker_connections 1024;
}

http {                       # ← http context (all HTTP/HTTPS)
    sendfile on;

    server {                 # ← server context (one virtual host)
        listen 80;
        server_name example.com;

        location / {         # ← location context (one URL pattern)
            proxy_pass http://backend;
        }
    }
}
```

### Inheritance Rules

Directives set in a parent context apply to all children — unless a child overrides them.

```
http {
    proxy_buffering off;      # applies to ALL server and location blocks below

    server {
        location /api/ {
            proxy_buffering on;   # overrides for this location only
        }
    }
}
```

### Key Contexts

| Context    | Scope            | Common Directives                                     |
| ---------- | ---------------- | ----------------------------------------------------- |
| `main`     | global           | `worker_processes`, `pid`, `user`                     |
| `events`   | worker tuning    | `worker_connections`                                  |
| `http`     | all HTTP         | `sendfile`, `keepalive_timeout`, `upstream`, `server` |
| `server`   | one virtual host | `listen`, `server_name`, `location`                   |
| `location` | one URL pattern  | `proxy_pass`, `root`, `try_files`                     |

---

## 4. Location Matching — The Most Important Concept

When a request arrives, nginx must pick which `location` block handles it.
This is NOT first-match — nginx uses a **priority system**.

### Priority Order (highest to lowest)

```
1. Exact match:         location = /foo { }      (stops searching immediately)
2. Prefix match (^~):  location ^~ /images/ { } (stops regex search if matched)
3. Regex match:        location ~ \.php$ { }     (case-sensitive regex)
                       location ~* \.jpg$ { }    (case-insensitive regex)
4. Prefix match:       location /api/ { }        (longest prefix wins)
5. Catch-all:          location / { }            (always matches)
```

### How nginx Selects a Location

1. Exact Match.
2. Check all **prefix** locations, remember the longest match.
3. If longest prefix was `^~`, use it and stop.
4. Try all **regex** locations in config order; use first match.
5. If no regex matched, use the longest prefix from Step 1.

```nginx
# Given these locations:
location = /health    { ... }   # exact
location /api/        { ... }   # prefix (length 5)
location ~ ^/api/threads { ... } # regex

# Request: GET /api/threads/123
# Step 1: longest prefix = /api/   (length 5 — no ^~ so continue)
# Step 3: regex ^/api/threads matches → USE THIS ONE

# Request: GET /health
# Step 1: exact match = /health → USE THIS ONE (stops immediately)
```

More info: `notes/glossary/nginx-location-matching-detailed-explaination.md`

### DeerFlow's Pattern

DeerFlow uses regex (`~`) for the `/api/threads/[^/]+/uploads` and `/api/threads`
locations because path parameters make exact/prefix matching impossible.
More specific regex is placed first so it wins over the broader one.

---

## 5. Reverse Proxy — The Core Use Case

A **reverse proxy** sits between clients and backend servers. Clients talk to nginx;
nginx forwards to backends. From the client's perspective, only nginx exists.

```
Browser ──► nginx :2026 ──► gateway :8001  (FastAPI)
                       └──► frontend :3000 (Next.js)
```

### Why Use a Reverse Proxy?

- **Single origin**: frontend and API share the same domain → no CORS issues
- **SSL termination**: nginx handles TLS; backends get plain HTTP
- **Load balancing**: nginx distributes across multiple backend instances
- **Path-based routing**: different URL prefixes go to different services
- **Header manipulation**: add/remove/rewrite headers before forwarding
- **Buffering**: absorb slow clients so backends are freed quickly

### The proxy_pass Directive

```nginx
location /api/ {
    proxy_pass http://backend:8001;
    # nginx strips the matched prefix: /api/foo → http://backend:8001/api/foo
    # (with trailing slash on proxy_pass, it would strip /api/ off the path)
}
```

Trailing slash in `proxy_pass` matters:

```nginx
location /api/ {
    proxy_pass http://backend/;   # /api/foo → http://backend/foo  (strips /api/)
    proxy_pass http://backend;    # /api/foo → http://backend/api/foo (keeps path)
}
```

---

## 6. Variables and Lazy DNS Resolution

nginx resolves upstream hostnames **at startup** by default. In Docker Compose,
container IPs change when a container restarts. If nginx resolved the IP at startup
and the container restarted with a new IP, nginx would proxy to a dead address.

### The Variable Trick

```nginx
set $upstream backend:8001;
proxy_pass http://$upstream;
```

When `proxy_pass` uses a **variable**, nginx resolves the hostname at **request time**
(using the `resolver` directive), not at startup. This means:

- nginx can start before backend containers are up
- Restarted containers with new IPs are automatically picked up

```nginx
resolver 127.0.0.11 valid=10s ipv6=off;  # Docker's internal DNS
set $gateway_upstream gateway:8001;
proxy_pass http://$gateway_upstream;
```

`valid=10s` — nginx caches the DNS result for 10 seconds, then re-resolves.
This is the correct pattern for Docker Compose deployments.

---

## 7. Headers — Forwarding Client Identity

When nginx proxies a request, the backend sees nginx's IP as the client, not the
real browser's IP. Standard headers are used to pass the original client info.

### Headers nginx Sets for the Backend

| Header              | Value                        | Purpose                                              |
| ------------------- | ---------------------------- | ---------------------------------------------------- |
| `Host`              | `$http_host`                 | Original Host header (includes port if non-standard) |
| `X-Real-IP`         | `$remote_addr`               | Client's IP address                                  |
| `X-Forwarded-For`   | `$proxy_add_x_forwarded_for` | Comma-separated chain of proxy IPs                   |
| `X-Forwarded-Proto` | `$scheme`                    | Original protocol (http or https)                    |

```nginx
proxy_set_header Host $http_host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

`$proxy_add_x_forwarded_for` = existing `X-Forwarded-For` header from client + `, $remote_addr`.
This preserves the full proxy chain for backends that need to audit request routing.

---

## 8. HTTP Version and Keep-Alive

### Why proxy_http_version 1.1?

nginx defaults to HTTP/1.0 for upstream connections. HTTP/1.0 closes the TCP
connection after each request — expensive for backends that receive many requests.

```nginx
proxy_http_version 1.1;
proxy_set_header Connection '';   # clears the "Connection: close" HTTP/1.0 default
```

With HTTP/1.1 + empty Connection header, nginx reuses upstream TCP connections
(keep-alive), reducing connection overhead to backends.

For WebSocket upgrades, Connection must be set differently:

```nginx
proxy_set_header Upgrade $http_upgrade;      # passes the Upgrade header
proxy_set_header Connection 'upgrade';       # tells upstream to upgrade
```

---

## 9. Buffering and Streaming (SSE)

### Default Buffering Behavior

By default, nginx **buffers** proxy responses: it collects the full backend response
in memory (or temp files) before sending it to the client.

Benefits: frees the backend quickly; handles slow clients without holding a backend connection.
Problem: breaks **streaming** — clients don't receive data until nginx flushes the full buffer.

### Server-Sent Events (SSE) Requirements

SSE is a protocol where the server sends a stream of `data: ...\n\n` events over
a persistent HTTP connection. The client receives events in real time.

For SSE to work through nginx:

```nginx
proxy_buffering off;          # don't buffer the response body
proxy_cache off;              # don't cache streaming responses
proxy_set_header X-Accel-Buffering no;  # tells upstream proxy not to buffer either
chunked_transfer_encoding on; # allows response to be sent in chunks
proxy_set_header Connection ''; # keep-alive (HTTP/1.1), not close
```

DeerFlow's LangGraph API (`/api/langgraph/`) is an SSE endpoint — AI responses
are streamed token by token. All of the above settings are applied there.

### proxy_request_buffering off

For large **uploads**, nginx by default buffers the request body before forwarding
to the backend. This uses disk for large files and adds latency.

```nginx
proxy_request_buffering off;    # stream request body directly to backend
client_max_body_size 100M;      # allow up to 100MB uploads
```

---

## 10. Timeouts

nginx has three proxy timeout settings:

| Directive               | What it Times                                | Default |
| ----------------------- | -------------------------------------------- | ------- |
| `proxy_connect_timeout` | Time to establish TCP connection to upstream | 60s     |
| `proxy_send_timeout`    | Time between successive writes to upstream   | 60s     |
| `proxy_read_timeout`    | Time between successive reads from upstream  | 60s     |

`proxy_read_timeout` is the one that bites AI applications. If the AI backend takes
2 minutes to generate a response and nginx's read timeout is 60s, nginx kills the
connection. DeerFlow sets all three to 600s (10 minutes) for its streaming endpoints.

---

## 11. URL Rewriting

### rewrite directive

```nginx
rewrite ^/api/langgraph/(.*) /api/$1 break;
```

- `^/api/langgraph/(.*)` — regex, captures everything after `/api/langgraph/`
- `/api/$1` — replacement, `$1` is the captured group
- `break` — stop rewriting and use the new URI (don't fall through to other rewrites)
- `last` — stop rewriting but restart location matching (like a redirect internally)

DeerFlow uses `rewrite` to translate LangGraph Studio's URL format to the gateway's
internal API format, without changing what the client sees.

---

## 12. The sendfile / tcp_nopush / tcp_nodelay Trio

These are low-level TCP optimizations for serving static files:

| Directive        | What it Does                                                                                                                                    |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `sendfile on`    | Uses the OS `sendfile()` syscall to transfer file data directly from disk to socket buffer, bypassing user space — much faster for static files |
| `tcp_nopush on`  | Batches TCP packets to fill frames before sending — reduces packet count. Only effective with `sendfile on`                                     |
| `tcp_nodelay on` | Disables Nagle's algorithm — sends packets immediately. Used for keep-alive connections so responses aren't delayed                             |

In practice: `sendfile + tcp_nopush` for throughput on large static files;
`tcp_nodelay` for low latency on keep-alive connections.

---

## 13. DNS Resolver

```nginx
resolver 127.0.0.11 valid=10s ipv6=off;
```

- `127.0.0.11` — Docker's embedded DNS server (always available inside containers)
- `valid=10s` — override the TTL; re-resolve every 10 seconds regardless of DNS TTL
- `ipv6=off` — don't query AAAA records; avoids issues in Docker networks that don't
  have IPv6 configured

Without `resolver`, the variable-based `proxy_pass` trick doesn't work. Nginx's internal architecture requires you to explicitly tell it which DNS server to query for these dynamic, runtime lookups.

---

## 14. Common Mental Model Mistakes

### Mistake 1: Thinking location is first-match

nginx always scans all prefix locations and picks the **longest** one, then tries
regex in order. Only exact match (`=`) stops scanning immediately.

### Mistake 2: Trailing slash in proxy_pass

```nginx
location /api/ {
    proxy_pass http://backend;    # /api/foo → http://backend/api/foo
    proxy_pass http://backend/;   # /api/foo → http://backend/foo
}
```

These behave differently. With a trailing slash, the matched prefix is stripped.

### Mistake 3: HTTP/1.0 upstream connections

Always add `proxy_http_version 1.1` for upstream connections — otherwise every
request opens a new TCP connection.

### Mistake 4: CORS at nginx vs. application layer

nginx can add CORS headers (`add_header Access-Control-Allow-Origin *;`) but this
duplicates logic and creates a mismatch with the application's own CORS policy.
Better to let the application handle CORS and keep nginx unaware of it
(as DeerFlow's config explicitly notes in the comment about GATEWAY_CORS_ORIGINS).

### Mistake 5: Buffering with SSE/streaming

If clients receive AI-streamed responses in one big dump at the end, buffering is on.
Set `proxy_buffering off` for all streaming endpoints.

---

## 15. Request Lifecycle Through nginx (DeerFlow Context)

```
Browser sends: GET /api/langgraph/threads/abc/runs/stream

1. TCP connection arrives at nginx worker
2. Worker reads and parses the HTTP request line + headers
3. nginx matches server block: listen 2026
4. nginx evaluates location blocks:
   - /api/langgraph/ → PREFIX match (length 15)
   - No regex for this path
   - Longest prefix wins → location /api/langgraph/
5. Rewrite fires: /api/langgraph/threads/abc/runs/stream
                → /api/threads/abc/runs/stream
6. DNS resolver looks up "gateway" → 172.x.x.x:8001
7. nginx opens (or reuses) TCP connection to gateway:8001
8. nginx sends rewritten request with forwarded headers
9. Gateway starts streaming SSE events
10. nginx reads each chunk (buffering=off) and immediately
    forwards to the browser
11. Connection stays open until gateway sends end of stream
    or proxy_read_timeout fires (600s)
```

---

## Summary

| Concept             | Key Takeaway                                                                         |
| ------------------- | ------------------------------------------------------------------------------------ |
| Architecture        | Event-driven master/worker; one worker handles thousands of connections concurrently |
| Config model        | Hierarchical contexts; inner blocks inherit from outer                               |
| Location matching   | Priority-based (not first-match): exact > regex > longest prefix                     |
| Reverse proxy       | Single nginx entry point; routes to multiple backends by path                        |
| Variable proxy_pass | Enables runtime DNS resolution — essential for Docker Compose                        |
| Buffering off       | Required for SSE/streaming; set `proxy_buffering off` + `X-Accel-Buffering no`       |
| Timeouts            | Set `proxy_read_timeout` high (600s+) for long AI-generation requests                |
| HTTP/1.1            | Always use for upstream — enables keep-alive connection reuse                        |
