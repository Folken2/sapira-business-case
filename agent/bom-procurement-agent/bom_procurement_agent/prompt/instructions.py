"""
Instruction builder for bom-procurement-agent.

Composes the system prompt every turn from these layers:
  1. AWAKENING.md (persona scaffold only — present until complete_awakening deletes it)
  2. SOUL.md      (character — read fresh each turn)
  3. Frame        (system posture)
  4. Date
  5. Memory       (AGENT_MEMORY.md + topics)

Skills are exposed via the LazySkillToolset (see agent.py) — queried on
demand rather than injected into the prompt.
"""

import logging

from ..utils.date_utils import format_current_date
from ..state.memory import load_all_memory
from ..config.paths import awakening_file, soul_file

logger = logging.getLogger(__name__)


def _read(path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception as e:
        logger.warning("Failed to read %s: %s", path, e)
        return ""


_FRAME = """\
You are a helpful AI assistant.\n\nUse your tools to take action. When something matters across sessions, save it to memory. Otherwise: act."""


async def get_agent_instruction(ctx) -> str:
    """ADK InstructionProvider — assembled per turn."""
    soul = _read(soul_file())
    memory = ""
    try:
        memory = load_all_memory()
    except Exception as e:
        logger.warning("Failed to load memory: %s", e)

    parts: list[str] = []
    if soul:
        parts.append(soul)
    parts.append(_FRAME)
    parts.append(f"Today: {format_current_date()}")
    if memory:
        parts.append(f"# Memory\n\n{memory}")
    return "\n\n".join(parts)
