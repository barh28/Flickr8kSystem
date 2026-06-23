"""Request/response schemas for the tags service."""
from typing import List, Optional

from pydantic import BaseModel, Field


class SetTagsRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    file_ids: List[str] = Field(..., min_length=1)
    status: str = Field(..., pattern="^(passed|failed)$")


class SetTagsResponse(BaseModel):
    tagged: int
    skipped_missing: List[str]


class RemoveTagsRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    file_ids: List[str] = Field(..., min_length=1)


class RemoveTagsResponse(BaseModel):
    removed: int


class TaggedFileItem(BaseModel):
    id: str
    image_url: str
    dataset: str
    split: str
    width: int
    height: int
    orientation: str
    captions: List[str]
    caption_length: int
    agreement: float
    tag_status: Optional[str] = None


class QueryResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[TaggedFileItem]
