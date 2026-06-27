"""Return type models for CNS store queries."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConnectorValidation:
    connector_id: str
    found: bool
    is_active: bool
    domain: str
    kind: str
    repo: str
    path: str


@dataclass
class NeighborhoodNode:
    id: str
    label: str
    kind: str
    repo: str
    path: str
    relation_kind: str
    direction: str  # "outbound" | "inbound"
    weight: float


@dataclass
class NeighborhoodResult:
    entity_id: str
    found: bool
    label: str
    kind: str
    neighbors: list[NeighborhoodNode] = field(default_factory=list)


@dataclass
class AuthorityLink:
    entity_id: str
    label: str
    kind: str
    relation_kind: str


@dataclass
class AuthorityChain:
    connector_id: str
    found: bool
    chain: list[AuthorityLink] = field(default_factory=list)


@dataclass
class EntityContext:
    entity_id: str
    found: bool
    label: str
    kind: str
    repo: str
    path: str
    cluster: str
    importance_tier: str
    connected_ids: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class MissionEvent:
    entity_id: str
    label: str
    kind: str
    relation_kind: str


@dataclass
class MissionHistory:
    entity_id: str
    events: list[MissionEvent] = field(default_factory=list)


@dataclass
class DomainInfo:
    entity_id: str
    found: bool
    label: str
    domain_id: Optional[str]
    domain_label: Optional[str]
    repo: str
    cluster: str
