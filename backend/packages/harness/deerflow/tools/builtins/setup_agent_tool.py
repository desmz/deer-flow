import logging

import yaml
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command

from deerflow.config.agents_config import validate_agent_name
from deerflow.config.paths import get_paths
from deerflow.runtime.user_context import resolve_runtime_user_id
from deerflow.tools.types import Runtime

logger = logging.getLogger(__name__)


# [DL-INSIGHT] Bootstrap-only tool: added to the tool list exclusively when is_bootstrap=True in
# RunnableConfig.configurable (see make_lead_agent). Normal agent runs never see this tool.
@tool(parse_docstring=True)
def setup_agent(
    soul: str,
    description: str,
    runtime: Runtime,
    skills: list[str] | None = None,
) -> Command:
    """Setup the custom DeerFlow agent.

    Args:
        soul: Full SOUL.md content defining the agent's personality and behavior.
        description: One-line description of what the agent does.
        skills: Optional list of skill names this agent should use. None means use all enabled skills, empty list means no skills.
    """

    # [DL-NOTE] agent_name injected via RunnableConfig.configurable["agent_name"]; None means default agent.
    agent_name: str | None = runtime.context.get("agent_name") if runtime.context else None
    agent_dir = None
    is_new_dir = False

    try:
        agent_name = validate_agent_name(agent_name)
        paths = get_paths()
        if agent_name:
            # Custom agents are persisted under the current user's bucket so
            # different users do not see each other's agents.
            # [DL-INSIGHT] resolve_runtime_user_id checks runtime.context["user_id"] first — the
            # only user_id channel that survives thread-pool and timer boundaries.
            user_id = resolve_runtime_user_id(runtime)
            agent_dir = paths.user_agent_dir(user_id, agent_name)
        else:
            # Default agent (no agent_name): SOUL.md lives at the global base dir.
            agent_dir = paths.base_dir
        is_new_dir = not agent_dir.exists()
        agent_dir.mkdir(parents=True, exist_ok=True)

        if agent_name:
            # If agent_name is provided, we are creating a custom agent in the agents/ directory
            config_data: dict = {"name": agent_name}
            if description:
                config_data["description"] = description
            if skills is not None:
                config_data["skills"] = skills

            config_file = agent_dir / "config.yaml"
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        soul_file = agent_dir / "SOUL.md"
        soul_file.write_text(soul, encoding="utf-8")

        logger.info(f"[agent_creator] Created agent '{agent_name}' at {agent_dir}")
        # [DL-QUESTION] `created_agent_name` is written to LangGraph state but no Python or
        # frontend consumer reads it. It may be a vestigial debugging field or a future hook.
        return Command(
            update={
                "created_agent_name": agent_name,
                "messages": [ToolMessage(content=f"Agent '{agent_name}' created successfully!", tool_call_id=runtime.tool_call_id)],
            }
        )

    except Exception as e:
        import shutil

        if agent_name and is_new_dir and agent_dir is not None and agent_dir.exists():
            # [DL-NOTE] Atomic cleanup: only removes the dir if this call created it, preventing
            # partial agent directories on failure (is_new_dir guards against deleting pre-existing agents).
            shutil.rmtree(agent_dir)
        logger.error(f"[agent_creator] Failed to create agent '{agent_name}': {e}", exc_info=True)
        return Command(update={"messages": [ToolMessage(content=f"Error: {e}", tool_call_id=runtime.tool_call_id)]})
