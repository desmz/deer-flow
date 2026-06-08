from pydantic import BaseModel, Field


class SkillEvolutionConfig(BaseModel):
    """Configuration for agent-managed skill evolution."""

    # [DL-INSIGHT] Default False is a security posture: skill evolution lets the agent write executable
    # scripts to skills/custom/, which is a powerful and potentially dangerous capability. Opt-in only.
    enabled: bool = Field(
        default=False,
        description="Whether the agent can create and modify skills under skills/custom.",
    )
    # [DL-NOTE] None falls back to the default chat model in security_scanner.py — scan quality varies
    # with whatever model the operator has configured as their primary LLM.
    moderation_model_name: str | None = Field(
        default=None,
        description="Optional model name for skill security moderation. Defaults to the primary chat model.",
    )
