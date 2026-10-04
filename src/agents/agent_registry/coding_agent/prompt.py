"""System prompt for the DeepAgent coding agent."""

from pathlib import Path

from agents.agent_utils import substitute_shared_prompts

_DIR = Path(__file__).parent
CodingAgentDescription = (_DIR / "coding_agent_description.txt").read_text().strip()


def CodingAgentPrompt() -> str:
    """Render the coding prompt with the shared workspace layout."""
    return substitute_shared_prompts((_DIR / "coding_agent_prompt.txt").read_text())
