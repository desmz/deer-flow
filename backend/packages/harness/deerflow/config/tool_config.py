from pydantic import BaseModel, ConfigDict, Field


# [DL-INSIGHT] Groups are logical capability buckets (web, file:read, bash, etc.).
# get_available_tools(groups=...) filters the tool list by group at assembly time.
class ToolGroupConfig(BaseModel):
    """Config section for a tool group"""

    name: str = Field(..., description="Unique name for the tool group")
    # [DL-NOTE] extra="allow" means group entries can carry future metadata without a schema change.
    model_config = ConfigDict(extra="allow")


class ToolConfig(BaseModel):
    """Config section for a tool"""

    name: str = Field(..., description="Unique name for the tool")
    group: str = Field(..., description="Group name for the tool")
    # [DL-INSIGHT] `use` is a reflection path (module:variable). resolve_variable(cfg.use) loads
    # the LangChain BaseTool at runtime — the same pattern used for models and sandbox providers.
    use: str = Field(
        ...,
        description="Variable name of the tool provider(e.g. deerflow.sandbox.tools:bash_tool)",
    )
    # [DL-INSIGHT] extra="allow" is the open-schema trick: api_key, max_results, timeout, etc.
    # in config.yaml become model_extra on this object. Each community tool reads its own extras
    # via get_app_config().get_tool_config(name).model_extra — no new fields needed here.
    model_config = ConfigDict(extra="allow")
