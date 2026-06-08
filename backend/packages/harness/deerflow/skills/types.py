from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

# [DL-NOTE] Discovery-by-convention: the parser walks directories looking for this filename to locate skills.
SKILL_MD_FILE = "SKILL.md"


# [DL-INSIGHT] StrEnum chosen so SkillCategory.PUBLIC == "public" — the string value doubles as a filesystem path segment
# (e.g., f"skills/{category}" works without any conversion).
class SkillCategory(StrEnum):
    """Source category for a skill.

    - ``PUBLIC``: built-in skill bundled with the platform, read-only.
    - ``CUSTOM``: user-authored skill that can be edited or deleted.
    """

    PUBLIC = "public"
    CUSTOM = "custom"


@dataclass
class Skill:
    """Represents a skill with its metadata and file path"""

    name: str
    description: str
    license: str | None
    skill_dir: Path
    skill_file: Path
    relative_path: Path  # Relative path from category root to skill directory
    category: SkillCategory  # 'public' or 'custom'
    # [DL-NOTE] Three-way semantics enforced by tool_policy.py: None=unrestricted, []=deny all, [...]=allowlist.
    # The YAML front-matter key is `allowed-tools`; absent key → None via parser.py.
    allowed_tools: list[str] | None = None
    # [DL-NOTE] Opt-in activation: skills are disabled by default; enabled state persisted in extensions_config.json.
    enabled: bool = False  # Whether this skill is enabled

    @property
    def skill_path(self) -> str:
        """Returns the relative path from the category root (skills/{category}) to this skill's directory"""
        path = self.relative_path.as_posix()
        # [DL-NOTE] "." → "" collapse handles skills sitting directly at the category root (no subdirectory).
        return "" if path == "." else path

    def get_container_path(self, container_base_path: str = "/mnt/skills") -> str:
        """
        Get the full path to this skill in the container.

        Args:
            container_base_path: Base path where skills are mounted in the container

        Returns:
            Full container path to the skill directory
        """
        # [DL-INSIGHT] Dual-path design: host paths (skill_dir/skill_file) carry the real filesystem location;
        # container paths here carry the virtual mount point the agent sees (/mnt/skills/...).
        # Mirrors the sandbox virtual path translation pattern — same abstraction, different domain.
        category_base = f"{container_base_path}/{self.category}"
        skill_path = self.skill_path
        if skill_path:
            return f"{category_base}/{skill_path}"
        return category_base

    def get_container_file_path(self, container_base_path: str = "/mnt/skills") -> str:
        """
        Get the full path to this skill's main file (SKILL.md) in the container.

        Args:
            container_base_path: Base path where skills are mounted in the container

        Returns:
            Full container path to the skill's SKILL.md file
        """
        return f"{self.get_container_path(container_base_path)}/SKILL.md"

    def __repr__(self) -> str:
        return f"Skill(name={self.name!r}, description={self.description!r}, category={self.category!r})"
