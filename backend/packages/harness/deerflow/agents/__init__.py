from .factory import create_deerflow_agent
from .features import Next, Prev, RuntimeFeatures
from .lead_agent import make_lead_agent
from .lead_agent.prompt import prime_enabled_skills_cache
from .thread_state import SandboxState, ThreadState

# LangGraph imports deerflow.agents when registering the graph. Prime the
# enabled-skills cache here so the request path can usually read a warm cache
# without forcing synchronous filesystem work during prompt module import.
# [DL-NOTE] prime_enabled_skills_cache is absent from __all__ — imported only for the side effect below.
# [DL-INSIGHT] Python guarantees __init__.py runs before any package name is used, so the background
# skills-loader thread starts before the first request arrives — no cold-cache on request #1.
prime_enabled_skills_cache()

__all__ = [
    "create_deerflow_agent",
    "RuntimeFeatures",
    "Next",
    "Prev",
    "make_lead_agent",
    "SandboxState",
    "ThreadState",
]
