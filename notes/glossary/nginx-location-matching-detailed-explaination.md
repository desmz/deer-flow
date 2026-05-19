Think of nginx `location` matching like a tournament with strict rules.

When a request comes in, nginx does **not** simply use the first matching block it sees.
Instead, it follows a multi-step selection algorithm.

---

# The Big Idea

For a request like:

```http
GET /api/threads/123
```

nginx asks:

1. Is there an **exact** match?
2. What is the **best prefix** match?
3. Should I check regex rules?
4. Which final winner should handle the request?

---

# 1. Exact Match (`=`) — Highest Priority

```nginx
location = /health {
    return 200 "OK";
}
```

This only matches:

```text
/health
```

NOT:

```text
/health/
/healthcheck
```

If nginx finds an exact match, it **stops immediately**.

---

## Example

Request:

```http
GET /health
```

nginx sees:

```nginx
location = /health
```

Result:

✅ Use this block immediately.

No regex checks. No prefix checks. Done.

---

# 2. Prefix Match (`/something/`)

```nginx
location /api/ {
    proxy_pass http://backend;
}
```

A prefix match means:

> “Does the URL start with this string?”

---

## Example

```http
GET /api/users
```

Matches:

```nginx
location /api/
```

because:

```text
/api/users
^^^^^^
```

starts with `/api/`.

---

# Longest Prefix Wins

Suppose:

```nginx
location / {
    ...
}

location /api/ {
    ...
}

location /api/admin/ {
    ...
}
```

Request:

```http
GET /api/admin/users
```

All three technically match:

- `/`
- `/api/`
- `/api/admin/`

nginx chooses the **longest** prefix:

✅ `/api/admin/`

because it is the most specific.

---

# 3. Prefix with `^~`

```nginx
location ^~ /images/ {
    ...
}
```

This means:

> “If this prefix matches, STOP and do NOT test regex locations.”

Normally, regex can override prefix matches.

But `^~` protects the prefix from being overridden.

---

## Without `^~`

```nginx
location /images/ {
    ...
}

location ~ \.jpg$ {
    ...
}
```

Request:

```http
GET /images/cat.jpg
```

Step-by-step:

- Prefix `/images/` matches
- nginx still checks regex
- `\.jpg$` matches
- regex wins

Final result:

✅ regex location used

---

## With `^~`

```nginx
location ^~ /images/ {
    ...
}

location ~ \.jpg$ {
    ...
}
```

Request:

```http
GET /images/cat.jpg
```

Now:

- `/images/` matches
- because it is `^~`, nginx STOPS
- regex never checked

Final result:

✅ `/images/` block used

---

# 4. Regex Match (`~` and `~*`)

Regex locations are powerful pattern matches.

---

## Case-Sensitive Regex (`~`)

```nginx
location ~ \.php$ {
    ...
}
```

Matches:

```text
index.php
```

Does NOT match:

```text
INDEX.PHP
```

because it is case-sensitive.

---

## Case-Insensitive Regex (`~*`)

```nginx
location ~* \.(jpg|png)$ {
    ...
}
```

Matches:

```text
cat.jpg
CAT.JPG
logo.PnG
```

because `~*` ignores case.

---

# Important Regex Rule

Regex locations are checked:

- AFTER prefix matching
- IN CONFIG ORDER
- FIRST MATCH WINS

---

## Example

```nginx
location ~ \.php$ {
    return 1;
}

location ~ ^/api/ {
    return 2;
}
```

Request:

```http
GET /api/test.php
```

Both regexes match.

Which wins?

✅ The FIRST one in the config.

So nginx uses:

```nginx
location ~ \.php$
```

Order matters for regex locations.

---

# Full Selection Algorithm

Here is the real nginx process.

---

## Step 1 — Exact Match

Check:

```nginx
location = ...
```

If found:

✅ use immediately

---

## Step 2 — Find Best Prefix

Check all prefix locations:

```nginx
location /foo/
location /api/
location /
```

Remember the **longest** match.

---

## Step 3 — If Best Prefix Uses `^~`

If the chosen prefix is:

```nginx
location ^~ /foo/
```

✅ use it immediately

❌ skip regex checks

---

## Step 4 — Test Regex Locations

Check regex locations **top to bottom**.

First regex that matches wins.

---

## Step 5 — Fallback to Prefix

If no regex matched:

✅ use the best prefix from Step 2.

---

# Walkthrough Example

```nginx
location = /health {
    return 1;
}

location /api/ {
    return 2;
}

location ~ ^/api/threads {
    return 3;
}

location / {
    return 4;
}
```

---

## Request 1

```http
GET /health
```

- Exact match exists
- stop immediately

Result:

✅ `return 1`

---

## Request 2

```http
GET /api/users
```

Step 1:

- no exact match

Step 2:

- longest prefix = `/api/`

Step 3:

- not `^~`

Step 4:

- regex `^/api/threads` does NOT match

Step 5:

- use `/api/`

Result:

✅ `return 2`

---

## Request 3

```http
GET /api/threads/123
```

Step 1:

- no exact

Step 2:

- longest prefix = `/api/`

Step 3:

- not `^~`

Step 4:

- regex `^/api/threads` matches

Result:

✅ `return 3`

---

# Why This Design Exists

nginx is optimized for:

- fast routing
- static file serving
- flexible URL handling

The priority system allows:

- fast exact routes
- efficient directory-style matching
- advanced regex overrides

without ambiguity.

---

# Easy Mental Model

Remember this order:

```text
EXACT
→ PREFIX (^~ can lock it)
→ REGEX
→ LONGEST PREFIX
```

Or shorter:

```text
Exact > ^~ Prefix > Regex > Normal Prefix > /
```
