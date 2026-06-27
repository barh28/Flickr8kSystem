"""Request/response schemas for the tags service."""
from typing import List, Optional

from pydantic import BaseModel, Field


class SetTagsRequest(BaseModel):
    file_ids: List[str] = Field(..., min_length=1)
    status: str = Field(..., pattern="^(passed|failed)$")


class SetTagsResponse(BaseModel):
    tagged: int
    skipped_missing: List[str]


class RemoveTagsRequest(BaseModel):
    file_ids: List[str] = Field(..., min_length=1)


class RemoveTagsResponse(BaseModel):
    removed: int


class ExportSelectedRequest(BaseModel):
    file_ids: List[str] = Field(..., min_length=1)


class LabelRequest(BaseModel):
    file_ids: List[str] = Field(..., min_length=1)
    label: str = Field(..., min_length=1, max_length=50)


class AddLabelResponse(BaseModel):
    labeled: int
    skipped_missing: List[str]
    label: str


class RemoveLabelResponse(BaseModel):
    removed: int
    label: str


class LabelsResponse(BaseModel):
    file_id: str
    labels: List[str]


class LabelOption(BaseModel):
    label: str
    count: int


class LabelOptionsResponse(BaseModel):
    labels: List[LabelOption]


class TagsStatsResponse(BaseModel):
    passed: int
    failed: int
    tagged_total: int
    labels: List[LabelOption]


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
    labels: List[str] = []


class QueryResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[TaggedFileItem]
