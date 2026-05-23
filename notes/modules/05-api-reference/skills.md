# Skills API

> Source: `backend/app/gateway/routers/skills.py`
> Prefix: `/api`

Manage agent skills — enable/disable public skills, install custom skills from `.skill` archives, and read/write/rollback custom skill content. Skills are SOUL.md-style markdown files that inject task templates into the agent's system prompt.

## Quick Reference

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `GET` | `/api/skills` | List all skills (public + custom) | `PUBLIC` |
| `POST` | `/api/skills/install` | Install a skill from a `.skill` archive | `PUBLIC` |
| `GET` | `/api/skills/custom` | List custom skills only | `PUBLIC` |
| `GET` | `/api/skills/custom/{skill_name}` | Get custom skill with raw SKILL.md content | `PUBLIC` |
| `PUT` | `/api/skills/custom/{skill_name}` | Edit custom skill SKILL.md | `PUBLIC` |
| `DELETE` | `/api/skills/custom/{skill_name}` | Delete a custom skill | `PUBLIC` |
| `GET` | `/api/skills/custom/{skill_name}/history` | Get edit history for a custom skill | `PUBLIC` |
| `POST` | `/api/skills/custom/{skill_name}/rollback` | Rollback a custom skill to a previous version | `PUBLIC` |
| `GET` | `/api/skills/{skill_name}` | Get a skill by name | `PUBLIC` |
| `PUT` | `/api/skills/{skill_name}` | Enable or disable a skill | `PUBLIC` |

---

## Shared Response Schemas

### `SkillResponse`

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Skill name |
| `description` | string | What the skill does |
| `license` | string \| null | License identifier |
| `category` | string | `"public"` or `"custom"` |
| `enabled` | boolean | Whether skill is currently enabled |

---

## Endpoint Details

### `GET /api/skills`

List all available skills from both the `skills/public/` and `skills/custom/` directories.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Skill list returned |
| `500` | Failed to load skills |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `skills` | array | List of `SkillResponse` objects (all, including disabled) |

**Example (200):**
```json
{
  "skills": [
    {
      "name": "code-review",
      "description": "Review code for bugs and best practices",
      "license": "MIT",
      "category": "public",
      "enabled": true
    },
    {
      "name": "my-custom-skill",
      "description": "Custom skill for data analysis",
      "license": null,
      "category": "custom",
      "enabled": false
    }
  ]
}
```

---

### `POST /api/skills/install`

Install a skill from a `.skill` file (ZIP archive) located in a thread's user-data directory. The `.skill` file must have been uploaded to the thread first via the uploads API. Refreshes the agent's system prompt cache after installation.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body** (`application/json`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `thread_id` | string | Yes | The thread ID where the `.skill` file is located |
| `path` | string | Yes | Virtual path to the `.skill` file (e.g., `mnt/user-data/outputs/my-skill.skill`) |

**Example Request:**
```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "path": "mnt/user-data/outputs/my-skill.skill"
}
```

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Skill installed |
| `400` | Invalid archive or skill content |
| `404` | `.skill` file not found at the specified path |
| `409` | Skill already exists |
| `500` | Failed to install skill |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` if installed |
| `skill_name` | string | Name of the installed skill |
| `message` | string | Installation result message |

**Example (200):**
```json
{
  "success": true,
  "skill_name": "my-custom-skill",
  "message": "Skill 'my-custom-skill' installed successfully"
}
```

---

### `GET /api/skills/custom`

List only custom skills (from `skills/custom/`).

**Access:** `PUBLIC`

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Custom skill list |
| `500` | Failed to load skills |

**Response Schema (200):** Same as `GET /api/skills`.

---

### `GET /api/skills/custom/{skill_name}`

Get a custom skill including its raw `SKILL.md` content.

**Access:** `PUBLIC`

**Path Params:**

| Param | Description |
|-------|-------------|
| `skill_name` | Custom skill name |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Skill with content returned |
| `404` | Custom skill not found |
| `500` | Failed to read skill |

**Response Schema (200):** `SkillResponse` plus:

| Field | Type | Description |
|-------|------|-------------|
| `content` | string | Raw SKILL.md content |

**Example (200):**
```json
{
  "name": "my-custom-skill",
  "description": "Custom data analysis skill",
  "license": null,
  "category": "custom",
  "enabled": true,
  "content": "---\nname: my-custom-skill\ndescription: Custom data analysis skill\n---\n\n# Instructions\n..."
}
```

---

### `PUT /api/skills/custom/{skill_name}`

Edit the `SKILL.md` content of a custom skill. Runs a security scan before saving; blocks content flagged as malicious. Appends an entry to the skill's edit history and refreshes the agent's system prompt cache.

**Access:** `PUBLIC`

**Path Params:**

| Param | Description |
|-------|-------------|
| `skill_name` | Custom skill name to edit |

**Query Params:** None

**Request Body** (`application/json`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | New full SKILL.md content (replaces existing) |

**Example Request:**
```json
{
  "content": "---\nname: my-custom-skill\ndescription: Updated description\n---\n\n# New instructions\n..."
}
```

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Updated skill returned |
| `400` | Security scan blocked the content, or invalid SKILL.md format |
| `404` | Custom skill not found |
| `500` | Failed to update skill |

**Response Schema (200):** Same as `GET /api/skills/custom/{skill_name}`.

---

### `DELETE /api/skills/custom/{skill_name}`

Delete a custom skill. Records a deletion entry in the skill's history before removing the file. Refreshes the agent's system prompt cache.

**Access:** `PUBLIC`

**Path Params:**

| Param | Description |
|-------|-------------|
| `skill_name` | Custom skill name to delete |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Skill deleted |
| `404` | Custom skill not found |
| `400` | Validation error |
| `500` | Failed to delete skill |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Always `true` |

---

### `GET /api/skills/custom/{skill_name}/history`

Get the full edit history for a custom skill (including entries from deleted skills if history file exists).

**Access:** `PUBLIC`

**Path Params:**

| Param | Description |
|-------|-------------|
| `skill_name` | Custom skill name |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | History returned |
| `404` | Skill and history file not found |
| `500` | Failed to read history |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `history` | array | List of history entries (each is a dict with `action`, `author`, `thread_id`, `file_path`, `prev_content`, `new_content`, `scanner`, `ts`) |

**Example (200):**
```json
{
  "history": [
    {
      "action": "human_edit",
      "author": "human",
      "thread_id": null,
      "file_path": "SKILL.md",
      "prev_content": "---\nname: old-skill\n---",
      "new_content": "---\nname: old-skill\ndescription: Added description\n---",
      "scanner": {"decision": "allow", "reason": null},
      "ts": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

### `POST /api/skills/custom/{skill_name}/rollback`

Rollback a custom skill to a previous version from its history. Runs a security scan on the target content and records the rollback in history.

**Access:** `PUBLIC`

**Path Params:**

| Param | Description |
|-------|-------------|
| `skill_name` | Custom skill name to rollback |

**Query Params:** None

**Request Body** (`application/json`):

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `history_index` | integer | No | Default: `-1` (latest change) | Index into the history array to restore from |

**Example Request:**
```json
{
  "history_index": -1
}
```

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Skill rolled back; updated skill returned |
| `400` | No history, index out of range, selected entry has no previous content, or security scan blocked |
| `404` | Skill or history not found |
| `500` | Failed to rollback skill |

**Response Schema (200):** Same as `GET /api/skills/custom/{skill_name}`.

---

### `GET /api/skills/{skill_name}`

Get information about any skill (public or custom) by name.

**Access:** `PUBLIC`

**Path Params:**

| Param | Description |
|-------|-------------|
| `skill_name` | Skill name to look up |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Skill info returned |
| `404` | Skill not found |
| `500` | Failed to load skill |

**Response Schema (200):** `SkillResponse` (without raw content).

---

### `PUT /api/skills/{skill_name}`

Enable or disable a skill by updating `extensions_config.json`. Refreshes the agent's system prompt cache.

**Access:** `PUBLIC`

**Path Params:**

| Param | Description |
|-------|-------------|
| `skill_name` | Skill name to update |

**Query Params:** None

**Request Body** (`application/json`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | boolean | Yes | `true` to enable, `false` to disable |

**Example Request:**
```json
{
  "enabled": true
}
```

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Updated skill returned |
| `404` | Skill not found |
| `500` | Failed to update skill |

**Response Schema (200):** `SkillResponse` with updated `enabled` field.
