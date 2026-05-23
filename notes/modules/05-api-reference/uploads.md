# Uploads API

> Source: `backend/app/gateway/routers/uploads.py`
> Prefix: `/api/threads/{thread_id}/uploads`

File upload management for threads. Files are stored in per-thread isolated directories. Supports automatic document conversion (PDF, PPT, Excel, Word → Markdown) when `uploads.auto_convert_documents: true` in `config.yaml`.

## Quick Reference

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `POST` | `/api/threads/{thread_id}/uploads` | Upload files to a thread | `AUTH+OWNER` |
| `GET` | `/api/threads/{thread_id}/uploads/limits` | Get upload limits | `AUTH+OWNER` |
| `GET` | `/api/threads/{thread_id}/uploads/list` | List uploaded files | `AUTH+OWNER` |
| `DELETE` | `/api/threads/{thread_id}/uploads/{filename}` | Delete an uploaded file | `AUTH+OWNER` |

---

## Endpoint Details

### `POST /api/threads/{thread_id}/uploads`

Upload one or more files to a thread's uploads directory. Files are stored at `backend/.deer-flow/users/{user_id}/threads/{thread_id}/user-data/uploads/`. Duplicate filenames within a single request are auto-renamed with `_N` suffixes.

If `uploads.auto_convert_documents: true` is set and the file is a PDF/PPT/Excel/Word document, a converted Markdown version is also created alongside the original.

**Access:** `AUTH+OWNER` (`require_existing=False` — thread need not exist yet)

**Path Params:**

| Param | Description |
|-------|-------------|
| `thread_id` | Thread UUID |

**Query Params:** None

**Request Body** (`multipart/form-data`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `files` | array of files | Yes | One or more files to upload |

**Default Limits** (overridable via `config.yaml`):

| Limit | Default |
|-------|---------|
| Max files per request | 10 |
| Max single file size | 50 MB |
| Max total upload size | 100 MB |

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Upload result (check `success` field) |
| `400` | No files provided, or invalid thread ID |
| `401` | Not authenticated |
| `404` | Thread not found or not owned |
| `413` | File too large, or total upload too large, or too many files |
| `500` | Upload failure |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` if all files uploaded cleanly; `false` if any were skipped |
| `files` | array | List of uploaded file info objects |
| `message` | string | Summary message |
| `skipped_files` | array | Filenames that were skipped due to unsafe paths |

Each file info object:

| Field | Type | Description |
|-------|------|-------------|
| `filename` | string | Saved filename (may differ if deduplicated) |
| `size` | string | File size in bytes (as string) |
| `path` | string | Sandbox-relative physical path |
| `virtual_path` | string | Agent-visible virtual path (e.g., `mnt/user-data/uploads/file.txt`) |
| `artifact_url` | string | URL to retrieve the file via the artifacts API |
| `original_filename` | string | Original filename (only present if renamed during dedup) |
| `markdown_file` | string | Converted Markdown filename (only if auto-conversion ran) |
| `markdown_path` | string | Physical path to Markdown version |
| `markdown_virtual_path` | string | Virtual path to Markdown version |
| `markdown_artifact_url` | string | Artifact URL for the Markdown version |

**Example (200):**
```json
{
  "success": true,
  "files": [
    {
      "filename": "report.pdf",
      "size": "204800",
      "path": ".deer-flow/users/default/threads/abc/user-data/uploads/report.pdf",
      "virtual_path": "mnt/user-data/uploads/report.pdf",
      "artifact_url": "/api/threads/abc/artifacts/mnt/user-data/uploads/report.pdf",
      "markdown_file": "report.md",
      "markdown_path": ".deer-flow/users/default/threads/abc/user-data/uploads/report.md",
      "markdown_virtual_path": "mnt/user-data/uploads/report.md",
      "markdown_artifact_url": "/api/threads/abc/artifacts/mnt/user-data/uploads/report.md"
    }
  ],
  "message": "Successfully uploaded 1 file(s)",
  "skipped_files": []
}
```

---

### `GET /api/threads/{thread_id}/uploads/limits`

Return the upload limits currently in effect for this thread (as configured in `config.yaml`).

**Access:** `AUTH+OWNER`

**Path Params:**

| Param | Description |
|-------|-------------|
| `thread_id` | Thread UUID |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Upload limits returned |
| `401` | Not authenticated |
| `404` | Thread not found or not owned |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `max_files` | integer | Maximum files per upload request |
| `max_file_size` | integer | Maximum size of a single file in bytes |
| `max_total_size` | integer | Maximum combined size of all files in one request in bytes |

**Example (200):**
```json
{
  "max_files": 10,
  "max_file_size": 52428800,
  "max_total_size": 104857600
}
```

---

### `GET /api/threads/{thread_id}/uploads/list`

List all files currently in the thread's uploads directory.

**Access:** `AUTH+OWNER`

**Path Params:**

| Param | Description |
|-------|-------------|
| `thread_id` | Thread UUID |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | File listing returned |
| `400` | Invalid thread ID |
| `401` | Not authenticated |
| `404` | Thread not found or not owned |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `files` | array | List of file info objects |
| `files[].filename` | string | Filename |
| `files[].size` | integer | File size in bytes |
| `files[].path` | string | Sandbox-relative physical path |
| `files[].virtual_path` | string | Agent-visible virtual path |
| `files[].artifact_url` | string | URL to retrieve the file |

**Example (200):**
```json
{
  "files": [
    {
      "filename": "report.pdf",
      "size": 204800,
      "path": ".deer-flow/users/default/threads/abc/user-data/uploads/report.pdf",
      "virtual_path": "mnt/user-data/uploads/report.pdf",
      "artifact_url": "/api/threads/abc/artifacts/mnt/user-data/uploads/report.pdf"
    }
  ]
}
```

---

### `DELETE /api/threads/{thread_id}/uploads/{filename}`

Delete a specific uploaded file from the thread's uploads directory. If the file was auto-converted, the converted Markdown version is also deleted.

**Access:** `AUTH+OWNER` (`require_existing=True`)

**Path Params:**

| Param | Description |
|-------|-------------|
| `thread_id` | Thread UUID |
| `filename` | Filename to delete (must not contain path separators) |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | File deleted |
| `400` | Invalid thread ID or path traversal detected |
| `401` | Not authenticated |
| `404` | File not found |
| `500` | Failed to delete file |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` |
| `deleted` | array | List of deleted filenames (original + converted, if applicable) |
