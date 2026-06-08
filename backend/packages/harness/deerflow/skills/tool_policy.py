import logging
from typing import Protocol

from deerflow.skills.types import Skill

logger = logging.getLogger(__name__)


# [DL-NOTE] Structural Protocol — only name: str is required. Works with LangChain tools,
# custom tool objects, or test stubs without any shared base class.
class NamedTool(Protocol):
    name: str


def allowed_tool_names_for_skills(skills: list[Skill]) -> set[str] | None:
    """Return the union of explicit skill allowed-tools declarations.

    None means legacy allow-all behavior. It is returned only when no loaded
    skill declares allowed-tools. Once any skill declares the field, legacy
    skills without the field contribute no tools instead of disabling the
    explicit restrictions from other skills.
    """
    if not skills:
        return None

    allowed: set[str] = set()
    has_explicit_declaration = False
    for skill in skills:
        # [DL-INSIGHT] "Opt-in poisoning": once any skill in the session declares allowed_tools,
        # legacy skills (allowed_tools=None) contribute nothing to the union.
        # This ensures one strict skill cannot be neutralized by a co-loaded legacy skill.
        if skill.allowed_tools is None:
            continue
        has_explicit_declaration = True
        if not skill.allowed_tools:
            logger.info("Skill %s declared empty allowed-tools", skill.name)
        allowed.update(skill.allowed_tools)

    # [DL-NOTE] Only return None when no skill in the session declared the field at all —
    # signals callers to preserve the legacy allow-all behavior unchanged.
    if not has_explicit_declaration:
        return None
    return allowed


# [DL-NOTE] Python 3.12 generic syntax: ToolT: NamedTool without a separate TypeVar declaration.
# Preserves the concrete list element type so the caller doesn't need to cast after filtering.
def filter_tools_by_skill_allowed_tools[ToolT: NamedTool](tools: list[ToolT], skills: list[Skill]) -> list[ToolT]:
    allowed = allowed_tool_names_for_skills(skills)
    if allowed is None:
        return tools

    return [tool for tool in tools if tool.name in allowed]
