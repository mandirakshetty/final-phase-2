from dataclasses import dataclass

@dataclass
class KnowledgeEntry:
    issue: str
    root_cause: str
    solution: str
    affected_components: list
    tags: list
    confidence: float = 1.0