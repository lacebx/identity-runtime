from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .identity import Identity
    from .memory import MemoryStore
    from .knowledge import KnowledgeBase
    from .skills import SkillRegistry
    from .goals import GoalEngine
    from .relationships import IdentityGraph


@dataclass
class ComposedContext:
    """
    The assembled context block ready to be injected into an LLM prompt.
    Each section is optional and can be toggled per use case.
    """
    identity_block: str = ""
    memory_block: str = ""
    knowledge_block: str = ""
    skills_block: str = ""
    goals_block: str = ""
    relationships_block: str = ""
    custom_blocks: Dict[str, str] = field(default_factory=dict)

    def render(self, separator: str = "\n\n") -> str:
        """
        Render the full context as a single string.
        Sections are included only if non-empty.
        """
        sections = []
        if self.identity_block:
            sections.append(self.identity_block)
        if self.memory_block:
            sections.append(self.memory_block)
        if self.knowledge_block:
            sections.append(self.knowledge_block)
        if self.skills_block:
            sections.append(self.skills_block)
        if self.goals_block:
            sections.append(self.goals_block)
        if self.relationships_block:
            sections.append(self.relationships_block)
        for block in self.custom_blocks.values():
            if block:
                sections.append(block)
        return separator.join(sections)

    def token_estimate(self, chars_per_token: float = 4.0) -> int:
        """Rough estimate of token usage for budget tracking."""
        return int(len(self.render()) / chars_per_token)


class ContextComposer:
    """
    Assembles runtime context from all identity modules.

    The ContextComposer is the bridge between the bounded modules
    (Identity, Memory, Knowledge, Skills, Goals, Relationships)
    and the LLM adapter layer. It does not call any LLM itself —
    it produces a ComposedContext that adapters inject into prompts.

    Design principle: composability over rigidity.
    Each section is independently controlled and weighted.
    """

    def __init__(
        self,
        max_tokens: int = 4000,
        include_identity: bool = True,
        include_memory: bool = True,
        include_knowledge: bool = True,
        include_skills: bool = True,
        include_goals: bool = True,
        include_relationships: bool = False,
    ):
        self.max_tokens = max_tokens
        self.include_identity = include_identity
        self.include_memory = include_memory
        self.include_knowledge = include_knowledge
        self.include_skills = include_skills
        self.include_goals = include_goals
        self.include_relationships = include_relationships

    def compose(
        self,
        identity: "Identity",
        memory_store: Optional["MemoryStore"] = None,
        knowledge_base: Optional["KnowledgeBase"] = None,
        skill_registry: Optional["SkillRegistry"] = None,
        goal_engine: Optional["GoalEngine"] = None,
        identity_graph: Optional["IdentityGraph"] = None,
        query: Optional[str] = None,
        top_k_memories: int = 5,
    ) -> ComposedContext:
        """
        Compose a full runtime context for the given identity.

        Args:
            identity: The active identity.
            memory_store: Optional memory store to pull relevant memories from.
            knowledge_base: Optional knowledge base for loaded packs.
            skill_registry: Optional skill registry for available skills.
            goal_engine: Optional goal engine for active goals.
            identity_graph: Optional graph for relationship context.
            query: The current user input (used for memory relevance).
            top_k_memories: How many memory items to include.

        Returns:
            ComposedContext ready to be rendered into a prompt.
        """
        ctx = ComposedContext()

        # --- Identity Block ---
        if self.include_identity:
            ctx.identity_block = self._render_identity(identity)

        # --- Memory Block ---
        if self.include_memory and memory_store:
            ctx.memory_block = self._render_memory(
                memory_store, identity.id, query, top_k_memories
            )

        # --- Knowledge Block ---
        if self.include_knowledge and knowledge_base:
            ctx.knowledge_block = self._render_knowledge(knowledge_base)

        # --- Skills Block ---
        if self.include_skills and skill_registry:
            ctx.skills_block = skill_registry.to_prompt_manifest()

        # --- Goals Block ---
        if self.include_goals and goal_engine:
            ctx.goals_block = goal_engine.to_prompt_summary()

        # --- Relationships Block ---
        if self.include_relationships and identity_graph:
            ctx.relationships_block = self._render_relationships(
                identity_graph, identity.id
            )

        return ctx

    def _render_identity(self, identity: "Identity") -> str:
        lines = [
            f"## Identity: {identity.name}",
            f"Role: {identity.role}",
        ]
        if identity.persona:
            lines.append(f"Persona: {identity.persona}")
        if identity.core_values:
            lines.append(f"Core Values: {', '.join(identity.core_values)}")
        if identity.communication_style:
            lines.append(f"Style: {identity.communication_style}")
        if identity.system_prompt:
            lines.append(f"\n{identity.system_prompt}")
        return "\n".join(lines)

    def _render_memory(
        self,
        store: "MemoryStore",
        identity_id: str,
        query: Optional[str],
        top_k: int
    ) -> str:
        from .memory import MemoryTier
        if query:
            items = store.search(query, identity_id=identity_id, limit=top_k)
        else:
            items = store.recent(identity_id=identity_id, limit=top_k)
        if not items:
            return ""
        lines = ["## Relevant Memory"]
        for item in items:
            tier_label = item.tier.value.upper()
            lines.append(f"  [{tier_label}] {item.content}")
        return "\n".join(lines)

    def _render_knowledge(self, kb: "KnowledgeBase") -> str:
        packs = kb.loaded_packs()
        if not packs:
            return ""
        lines = ["## Active Knowledge"]
        for pack in packs:
            lines.append(f"  - [{pack.tier.value}] {pack.name}: {pack.description}")
        return "\n".join(lines)

    def _render_relationships(
        self, graph: "IdentityGraph", identity_id: str
    ) -> str:
        edges = graph.get_relationships(identity_id)
        if not edges:
            return ""
        lines = ["## Relationships"]
        for e in edges:
            lines.append(
                f"  -> {e.target_id} [{e.relationship_type.value}] "
                f"trust={e.trust_level.name} strength={e.strength:.2f}"
            )
        return "\n".join(lines)
