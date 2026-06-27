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


class Bucket(BaseModel):
    label: str
    count: int


class LengthStats(BaseModel):
    min: int
    max: int
    avg: float
    buckets: List[Bucket]


class AgreementStats(BaseModel):
    avg: float
    buckets: List[Bucket]


class StatsResponse(BaseModel):
    total: int
    by_split: List[Bucket]
    by_orientation: List[Bucket]
    caption_length: LengthStats
    agreement: AgreementStats
