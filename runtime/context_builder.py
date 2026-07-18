"""Context Builder

Assembles the full context string that gets prepended to a user message
before it's sent to any LLM. This is the core of the identity layer.

Context structure:
  [IDENTITY BLOCK]
  [MEMORY BLOCK]
  [CURRENT MESSAGE]
"""

from typing import Dict, Any
import logging

from memory_engine import MemoryEngine
from identity_loader import IdentityLoader

logger = logging.getLogger(__name__)

# How many memories to pull per request
DEFAULT_TOP_K = 5
# Minimum similarity score to include a memory
DEFAULT_THRESHOLD = 0.3


class ContextBuilder:
    """Assembles identity + memory context for LLM requests."""

    def __init__(self, memory_engine: MemoryEngine, identity_loader: IdentityLoader):
        self.memory = memory_engine
        self.loader = identity_loader

    async def build(
        self,
        message: str,
        identity: Dict[str, Any],
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Build the augmented context string.
        Returns: {context: str, memories_used: int}
        """
        identity_block = self._build_identity_block(identity)
        
        identity_id = identity["identity"]["id"]
        memories = self.memory.retrieve(
            user_id=user_id,
            identity_id=identity_id,
            query=message,
            top_k=DEFAULT_TOP_K,
            threshold=DEFAULT_THRESHOLD
        )
        memory_block = self._build_memory_block(memories)

        # Assemble full context
        parts = [identity_block]
        if memory_block:
            parts.append(memory_block)
        context = "\n\n".join(parts)

        logger.debug(f"Context built: {len(context)} chars, {len(memories)} memories")
        return {
            "context": context,
            "memories_used": len(memories)
        }

    def _build_identity_block(self, identity: Dict[str, Any]) -> str:
        """Convert an identity spec into a system prompt block."""
        info = identity.get("identity", {})
        personality = identity.get("personality", {})
        values = identity.get("values", [])
        relationship = identity.get("relationship_config", {})

        name = info.get("name", "Assistant")
        tone = personality.get("tone", [])
        style = personality.get("communication_style", "")
        avoided = personality.get("avoided_behaviors", [])
        signature = personality.get("signature_phrases", [])

        lines = [
            f"## Identity: {name}",
            "",
        ]

        if info.get("description"):
            lines.append(info["description"])
            lines.append("")

        if tone:
            lines.append(f"**Tone**: {', '.join(tone)}")

        if style:
            lines.append(f"**Style**: {style}")

        if values:
            lines.append("")
            lines.append("**Core Values**:")
            for v in values:
                lines.append(f"- {v}")

        if avoided:
            lines.append("")
            lines.append("**Never do these things**:")
            for a in avoided:
                lines.append(f"- {a}")

        if signature:
            lines.append("")
            lines.append(f"**Signature phrases**: {'; '.join(signature)}")

        if relationship.get("relationship_model"):
            lines.append("")
            lines.append(f"**Relationship**: You are in a {relationship['relationship_model']} relationship with this user.")

        if relationship.get("track_progress"):
            lines.append("Track the user's progress and acknowledge growth over time.")

        return "\n".join(lines)

    def _build_memory_block(self, memories: list) -> str:
        """Convert retrieved memories into a context block."""
        if not memories:
            return ""

        lines = [
            "## What You Remember About This User",
            "",
        ]

        # Group by memory type
        by_type: Dict[str, list] = {}
        for m in memories:
            t = m.get("memory_type", "general")
            by_type.setdefault(t, []).append(m)

        type_labels = {
            "preference": "Preferences",
            "decision": "Decisions Made",
            "milestone": "Milestones",
            "correction": "Corrections/Feedback",
            "general": "Context"
        }

        for mem_type, mems in by_type.items():
            label = type_labels.get(mem_type, mem_type.title())
            lines.append(f"**{label}**:")
            for m in mems:
                lines.append(f"- {m['content']}")
            lines.append("")

        return "\n".join(lines).strip()
