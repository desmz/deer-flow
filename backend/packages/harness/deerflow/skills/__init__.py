from __future__ import annotations

from .installer import SkillAlreadyExistsError, SkillSecurityScanError
from .storage import LocalSkillStorage, SkillStorage, get_or_new_skill_storage
from .types import Skill
from .validation import ALLOWED_FRONTMATTER_PROPERTIES, _validate_skill_frontmatter

# [DL-NOTE] Narrow public surface: only Skill (type), storage types, error types, and two validation symbols.
# Internal harness code (agent.py, executor.py, etc.) imports directly from submodules — this API
# is primarily for the App layer (app/gateway/routers/skills.py) and external consumers.
# [DL-WARN] _validate_skill_frontmatter is exported despite its leading underscore — it is semi-public,
# needed by the skills router. The underscore signals "not stable API" rather than truly private.
__all__ = [
    "Skill",
    "ALLOWED_FRONTMATTER_PROPERTIES",
    "_validate_skill_frontmatter",
    "SkillAlreadyExistsError",
    "SkillSecurityScanError",
    "SkillStorage",
    "LocalSkillStorage",
    "get_or_new_skill_storage",
]
