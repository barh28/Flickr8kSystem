"""Response schemas for the files service."""
from typing import List

from pydantic import BaseModel


class FileItem(BaseModel):
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


class FileListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[FileItem]


class WordCount(BaseModel):
    min: int
    max: int


class OptionsResponse(BaseModel):
    datasets: List[str]
    splits: List[str]
    orientations: List[str]
    word_count: WordCount
