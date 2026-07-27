from uuid import UUID

from pydantic import BaseModel


class SearchResult(BaseModel):
    id: UUID
    type: str
    title: str
    subtitle: str
    href: str
