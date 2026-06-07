from .tools import get_available_tools

# [DL-NOTE] skill_manage_tool is in __all__ but not eagerly imported; resolved via __getattr__ below.
__all__ = ["get_available_tools", "skill_manage_tool"]


# [DL-INSIGHT] PEP 562 lazy module attribute: defers skill_manage_tool import to avoid pulling
# the skills subsystem (security_scanner, storage, prompt cache) at package load time.
def __getattr__(name: str):
    if name == "skill_manage_tool":
        from .skill_manage_tool import skill_manage_tool

        return skill_manage_tool
    raise AttributeError(name)
