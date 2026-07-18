from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid
from datetime import datetime


class RelationshipType(Enum):
    PEER = "peer"             # Equal standing
    MENTOR = "mentor"         # Guides another
    STUDENT = "student"       # Learns from another
    COLLABORATOR = "collaborator"
    DELEGATE = "delegate"     # Acts on behalf of another
    PRINCIPAL = "principal"   # Another acts on behalf of this
    ADVERSARY = "adversary"
    OBSERVER = "observer"


class TrustLevel(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    ABSOLUTE = 4


@dataclass
class RelationshipEdge:
    """
    A directed edge in the Identity Graph.
    Represents how identity A relates to identity B.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""         # The identity holding this relationship
    target_id: str = ""         # The identity being related to
    relationship_type: RelationshipType = RelationshipType.PEER
    trust_level: TrustLevel = TrustLevel.MEDIUM
    bidirectional: bool = False  # If True, both identities share this relationship
    strength: float = 1.0        # 0.0 to 1.0, decays over time without interaction
    context: str = ""            # Shared context or origin of this relationship
    permissions: List[str] = field(default_factory=list)  # What target can access
    established_at: datetime = field(default_factory=datetime.utcnow)
    last_interaction: Optional[datetime] = None
    interaction_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def record_interaction(self) -> None:
        """Mark an interaction between these identities."""
        self.last_interaction = datetime.utcnow()
        self.interaction_count += 1

    def decay(self, factor: float = 0.95) -> None:
        """Reduce relationship strength over time without interaction."""
        self.strength = max(0.0, self.strength * factor)

    def reinforce(self, amount: float = 0.05) -> None:
        """Strengthen this relationship after positive interaction."""
        self.strength = min(1.0, self.strength + amount)


class IdentityGraph:
    """
    The Identity Graph models how a set of identities relate to each other.
    This is the social/relational fabric of the IdentityOS.

    Relationships are directed by default (A knows B does not mean B knows A).
    Bidirectional edges are stored as two directed edges for flexibility.
    """

    def __init__(self):
        # source_id -> list of edges originating from that identity
        self._edges: Dict[str, List[RelationshipEdge]] = {}

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType = RelationshipType.PEER,
        trust_level: TrustLevel = TrustLevel.MEDIUM,
        bidirectional: bool = False,
        **kwargs
    ) -> RelationshipEdge:
        """Create a new relationship edge between two identities."""
        edge = RelationshipEdge(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            trust_level=trust_level,
            bidirectional=bidirectional,
            **kwargs
        )
        if source_id not in self._edges:
            self._edges[source_id] = []
        self._edges[source_id].append(edge)

        if bidirectional:
            reverse = RelationshipEdge(
                source_id=target_id,
                target_id=source_id,
                relationship_type=relationship_type,
                trust_level=trust_level,
                bidirectional=True,
            )
            if target_id not in self._edges:
                self._edges[target_id] = []
            self._edges[target_id].append(reverse)

        return edge

    def get_relationships(self, source_id: str) -> List[RelationshipEdge]:
        """Get all outgoing relationships from an identity."""
        return self._edges.get(source_id, [])

    def get_relationship(
        self, source_id: str, target_id: str
    ) -> Optional[RelationshipEdge]:
        """Get a specific edge between two identities."""
        for edge in self._edges.get(source_id, []):
            if edge.target_id == target_id:
                return edge
        return None

    def get_trusted(
        self, source_id: str, min_trust: TrustLevel = TrustLevel.MEDIUM
    ) -> List[RelationshipEdge]:
        """Return all relationships meeting a minimum trust threshold."""
        return [
            e for e in self._edges.get(source_id, [])
            if e.trust_level.value >= min_trust.value
        ]

    def remove_relationship(self, source_id: str, target_id: str) -> bool:
        """Remove a directed relationship."""
        edges = self._edges.get(source_id, [])
        original = len(edges)
        self._edges[source_id] = [e for e in edges if e.target_id != target_id]
        return len(self._edges[source_id]) < original

    def record_interaction(self, source_id: str, target_id: str) -> None:
        edge = self.get_relationship(source_id, target_id)
        if edge:
            edge.record_interaction()
            edge.reinforce()

    def all_identities(self) -> List[str]:
        """Return all identity IDs present in the graph."""
        ids = set(self._edges.keys())
        for edges in self._edges.values():
            for e in edges:
                ids.add(e.target_id)
        return list(ids)

    def to_adjacency_summary(self) -> Dict[str, List[str]]:
        """Compact adjacency map for inspection."""
        return {
            src: [e.target_id for e in edges]
            for src, edges in self._edges.items()
        }
