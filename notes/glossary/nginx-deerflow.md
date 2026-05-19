# DeerFlow nginx Configuration

Study notes for `docker/nginx/nginx.conf`. For nginx fundamentals see
[[nginx-concepts]]; for a directive quick-reference see [[nginx-cheatsheet]].

---

## Purpose

nginx sits at the front of the entire DeerFlow Docker Compose stack. Every
browser request enters on port `2026` and nginx decides — by URL path — whether
to forward it to the **Gateway** (FastAPI, port 8001), the **Provisioner**
(sandbox manager, port 8002), or the **Frontend** (Next.js, port 3000).

It is a pure reverse proxy: no SSL termination (not configured here), no static
file serving, no caching. Its only jobs are **routing** and **header manipulation**.

```
Browser
  │
  ▼
nginx :2026
  ├─ /api/langgraph/*  ──► rewrite ──► gateway :8001  (SSE streaming)
  ├─ /api/models        ──────────────► gateway :8001
  ├─ /api/memory        ──────────────► gateway :8001
  ├─ /api/mcp           ──────────────► gateway :8001
  ├─ /api/skills        ──────────────► gateway :8001
  ├─ /api/agents        ──────────────► gateway :8001
  ├─ /api/threads/*/uploads ──────────► gateway :8001  (100 MB uploads)
  ├─ /api/threads/*     ──────────────► gateway :8001
  ├─ /docs, /redoc, /openapi.json ────► gateway :8001
  ├─ /health            ──────────────► gateway :8001
  ├─ /api/sandboxes     ──────────────► provisioner :8002  (optional)
  ├─ /api/*             ──────────────► gateway :8001  (catch-all)
  └─ /*                 ──────────────► frontend :3000
```

---

## Key Files

- `docker/nginx/nginx.conf` — the only nginx file in the project

---

## Important Concepts

### 1. Non-Root Operation

By default, standard Docker images (like the official nginx image) spin up the master process as root. If an attacker exploits a remote code execution (RCE) vulnerability in nginx, they instantly gain root access inside that container, which makes it drastically easier to break out of the container and compromise the host machine.

Two details reveal that nginx runs as a non-root user inside Docker:

- `pid /tmp/nginx.pid` — root-owned directories like `/run/` are not writable;
  `/tmp` always is
- `proxy_request_buffering off` on the upload endpoint — nginx normally buffers
  request bodies to disk (in `/var/cache/nginx/` or similar); those paths may
  not be writable by a non-root user

This is a hardening choice: running as non-root limits the blast radius if the
nginx process were compromised.

### 2. Runtime DNS Resolution (The Variable Trick)

nginx resolves upstream hostnames at **startup** by default. In Docker Compose,
container IPs change on restart. If a container restarts and gets a new IP, nginx
would keep proxying to the old dead address.

The fix:

```nginx
resolver 127.0.0.11 valid=10s ipv6=off;
set $gateway_upstream gateway:8001;
proxy_pass http://$gateway_upstream;
```

When `proxy_pass` receives a variable (not a literal hostname), it resolves via
the configured `resolver` on **every request**. `127.0.0.11` is Docker's embedded
DNS server, always available inside containers. `valid=10s` caps the DNS cache so
stale IPs age out within 10 seconds.

The Provisioner goes further — its variable is scoped **inside** the location block:

```nginx
location /api/sandboxes {
    set $provisioner_upstream provisioner:8002;
    ...
}
```

This means nginx will not even attempt DNS resolution for `provisioner` unless a
request hits `/api/sandboxes`. nginx can start and serve traffic normally even if
the provisioner container has never been started.

### 3. SSE / Streaming Configuration

DeerFlow's core value is AI-generated content streamed to the browser in real time.
The `/api/langgraph/` location carries all of that traffic as Server-Sent Events.

Three layers of configuration ensure streaming works end-to-end:

| Setting                                 | Effect                                                                                      |
| --------------------------------------- | ------------------------------------------------------------------------------------------- |
| `proxy_buffering off` (server-wide)     | nginx does not buffer response body                                                         |
| `proxy_cache off` (server-wide)         | nginx does not cache streaming responses                                                    |
| `proxy_set_header X-Accel-Buffering no` | Signal to any intermediate proxy to also disable buffering                                  |
| `proxy_set_header Connection ''`        | Clears `Connection: close` → enables HTTP/1.1 keep-alive on the upstream TCP connection     |
| `chunked_transfer_encoding on`          | Allows the gateway to send response body in chunks without declaring Content-Length upfront |
| `proxy_read_timeout 600s`               | Keeps the upstream connection alive for up to 10 minutes — long AI tasks need this          |

`proxy_buffering off` is set at the **server block** level (not just inside the
langgraph location). This is an intentional default: if a future streaming endpoint
is added anywhere under this server, it works correctly out of the box without
needing to remember to add buffering settings.

### 4. URL Rewriting for LangGraph Compatibility

LangGraph Studio (the graph debugging UI) sends requests to `/api/langgraph/*`.
DeerFlow's Gateway exposes its API at `/api/*`. The rewrite bridges them:

```nginx
rewrite ^/api/langgraph/(.*) /api/$1 break;
```

- `(.*)` captures everything after `/api/langgraph/`
- `/api/$1` pastes it after `/api/`
- `break` prevents nginx from re-evaluating location blocks with the new URI

Example: `/api/langgraph/threads/abc/runs/stream` → `/api/threads/abc/runs/stream`

This lets DeerFlow serve both LangGraph Studio clients (via the rewrite) and
direct API clients without duplicating Gateway routes.

### 5. Location Matching and Order

nginx location matching is **not** first-match for prefix locations. It uses a
priority system (exact > preferential prefix > regex > longest prefix). But
within regex locations, **order matters** — the first matching regex wins.

DeerFlow exploits this for the `/api/threads` variants:

```nginx
location ~ ^/api/threads/[^/]+/uploads { ... }   # ← must come first
location ~ ^/api/threads               { ... }   # ← catch-all for /api/threads/*
```

The uploads regex (`/api/threads/<id>/uploads`) is more specific. Because it
appears first in the config, it wins over the broader threads regex for upload
requests. If the order were reversed, upload requests would be handled by the
general threads location (missing the 100M size limit and request buffering settings).

### 6. CORS Design Decision

The config includes this comment:

> "configure the Gateway allowlist with GATEWAY_CORS_ORIGINS so CORS and CSRF
> origin checks stay aligned instead of approving every origin at the proxy layer"

This is a deliberate architectural choice: **nginx does not add CORS headers**.
CORS is handled entirely by the FastAPI Gateway.

Why this matters: nginx `add_header` directives and FastAPI CORS middleware both
influence what `Access-Control-*` headers the browser sees. If both are active,
you get duplicate headers and potentially inconsistent allow-lists. By keeping
CORS in one place (the Gateway), the team avoids that split-brain problem.

### 7. WebSocket Support (Frontend Location)

The catch-all `location /` forwards everything to the Next.js frontend. It
includes WebSocket upgrade headers:

```nginx
proxy_set_header Upgrade    $http_upgrade;
proxy_set_header Connection 'upgrade';
proxy_cache_bypass          $http_upgrade;
```

This supports Next.js Hot Module Replacement (HMR) in development, which
uses a WebSocket connection. Note the contrast with the `/api/langgraph/`
location where `Connection ''` (empty) is used to enable keep-alive without
WebSocket upgrade. SSE does not need `Upgrade` — it runs over plain HTTP/1.1.

---

## Execution Flow

### Request: `GET /api/langgraph/threads/abc123/runs/stream`

```
1. TCP connection arrives at nginx worker on :2026
2. nginx matches server block (listen 2026)
3. Location selection:
   - Prefix scan: /api/langgraph/ matches (length 16)
   - No earlier ^~ prefix or exact match
   - No regex matches (no ~ location for /api/langgraph/)
   - Winner: location /api/langgraph/ (longest prefix)
4. Rewrite fires:
   /api/langgraph/threads/abc123/runs/stream
   → /api/threads/abc123/runs/stream
5. DNS: resolver looks up "gateway" via 127.0.0.11 → 172.18.0.5
6. nginx opens (or reuses) HTTP/1.1 connection to 172.18.0.5:8001
7. Sends:  GET /api/threads/abc123/runs/stream HTTP/1.1
           Host: localhost:2026
           X-Real-IP: 192.168.1.10
           X-Forwarded-For: 192.168.1.10
           X-Forwarded-Proto: http
           Connection: (empty)
           X-Accel-Buffering: no
8. Gateway starts sending SSE events:
   data: {"type":"token","content":"Hello"}\n\n
   data: {"type":"token","content":" world"}\n\n
   ...
9. nginx reads each chunk immediately (proxy_buffering off)
   and writes it to the client socket
10. Connection stays open until gateway sends `data: [DONE]`
    or the 600s timeout fires
```

### Request: `POST /api/threads/abc123/uploads` (100MB file)

```
1. Location selection:
   - Prefix scan: /api/threads (length 11), /api/ (length 5)
   - Regex scan: ^/api/threads/[^/]+/uploads → MATCH (first regex in config order)
   - Winner: uploads regex location
2. proxy_request_buffering off → nginx streams request body directly to gateway
3. client_max_body_size 100M → nginx accepts the large body without rejecting it
4. Gateway receives the file stream and handles storage
```

---

## My Insights

**nginx as the "same-origin trick"**: By running both frontend and API behind one
nginx endpoint on the same port, the browser sees a single origin. There are no
CORS preflight requests for XHR/fetch calls from the React frontend to `/api/*`.
This is a major simplification — no CORS configuration needed for the happy path.

**Intentional over-engineering on timeouts**: Setting `proxy_connect_timeout 600s`
is unusual (the TCP handshake itself should complete in milliseconds). The 600s
connect timeout is almost certainly overkill. It suggests a defensive posture:
"just make sure nothing can timeout" rather than tuning each value individually.
For a research/demo project this is fine; in production you'd want more precise
values and alerts.

**No upstream block**: DeerFlow doesn't use nginx's `upstream {}` blocks, which
are the idiomatic way to define backend groups (with load balancing, health checks,
keepalive pools). Instead it uses bare `set $var host:port` + `proxy_pass http://$var`.
This works perfectly for single-instance Docker Compose. Scaling to multiple backend
replicas would require switching to `upstream {}` blocks.

**Missing gzip**: nginx is not configured to gzip responses. For the streaming SSE
case this is correct (you can't gzip a streaming response effectively), but static
assets and API responses that return large JSON payloads would benefit from
compression. Not a bug — a gap.

---

## Questions

- [DL-QUESTION] Why port 2026 specifically? Is this a convention, or does it
  reference a project year/version? (Note: the recent commit message mentions
  "listen 2026" — may be a year-stamped convention.)
- [DL-QUESTION] The `/api/` catch-all comment says "e.g. /api/v1/auth/\*" — is
  there an auth system planned? No `/api/v1/` routes appear in the Gateway today.
- [DL-QUESTION] `proxy_request_buffering off` comment says "Disable response
  buffering to avoid permission errors" — this is actually about _request_ buffering,
  not response. Is the comment misleading or is there a response buffering issue too?

---

## Links to Related Modules

- [[nginx-concepts]] — conceptual foundation for understanding this config
- [[nginx-cheatsheet]] — directive quick-reference
- Gateway (FastAPI) — the primary upstream; handles all `/api/*` routes
- Frontend (Next.js) — receives all non-API traffic
- Provisioner — optional upstream for `/api/sandboxes`; sandbox management service
