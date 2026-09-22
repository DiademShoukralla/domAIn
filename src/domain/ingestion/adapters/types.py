from dataclasses import dataclass


@dataclass(frozen=True)
class FetchedDocument:
    document_id: str
    content: str
