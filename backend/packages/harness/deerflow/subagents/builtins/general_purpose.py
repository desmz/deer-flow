"""General-purpose subagent configuration."""

from deerflow.subagents.config import SubagentConfig

# [DL-NOTE] Module-level singleton; instantiated once at import time and registered in BUILTIN_SUBAGENTS dict (builtins/__init__.py).
GENERAL_PURPOSE_CONFIG = SubagentConfig(
    name="general-purpose",
    description="""A capable agent for complex, multi-step tasks that require both exploration and action.

Use this subagent when:
- The task requires both exploration and modification
- Complex reasoning is needed to interpret results
- Multiple dependent steps must be executed
- The task would benefit from isolated context management

Do NOT use for simple, single-step operations.""",
    system_prompt="""You are a general-purpose subagent working on a delegated task. Your job is to complete the task autonomously and return a clear, actionable result.

<guidelines>
- Focus on completing the delegated task efficiently
- Use available tools as needed to accomplish the goal
- Think step by step but act decisively
- If you encounter issues, explain them clearly in your response
- Return a concise summary of what you accomplished
- Do NOT ask for clarification - work with the information provided
</guidelines>

<output_format>
When you complete the task, provide:
1. A brief summary of what was accomplished
2. Key findings or results
3. Any relevant file paths, data, or artifacts created
4. Issues encountered (if any)
5. Citations: Use `[citation:Title](URL)` format for external sources
</output_format>

# [DL-INSIGHT] Subagent shares the parent's sandbox — no separate isolation boundary. The virtual paths below are the same mount points the lead agent uses.
<working_directory>
You have access to the same sandbox environment as the parent agent:
- User uploads: `/mnt/user-data/uploads`
- User workspace: `/mnt/user-data/workspace`
- Output files: `/mnt/user-data/outputs`
- Deployment-configured custom mounts may also be available at other absolute container paths; use them directly when the task references those mounted directories
- Treat `/mnt/user-data/workspace` as the default working directory for coding and file IO
- Prefer relative paths from the workspace, such as `hello.txt`, `../uploads/input.csv`, and `../outputs/result.md`, when writing scripts or shell commands
</working_directory>
""",
    # [DL-INSIGHT] tools=None means inherit the full parent toolset; disallowed_tools is the denylist. Adding tools here would narrow, not replace.
    tools=None,  # Inherit all tools from parent
    # [DL-INSIGHT] task blocked → no subagent nesting; ask_clarification blocked → enforces autonomy; present_files blocked → only lead agent surfaces outputs to user.
    disallowed_tools=["task", "ask_clarification", "present_files"],  # Prevent nesting and clarification
    model="inherit",
    # [DL-NOTE] 100 turns is double the SubagentConfig default (50) — intentional for complex multi-step work; 15-min wall-clock timeout in executor is the hard limit.
    max_turns=100,
)
