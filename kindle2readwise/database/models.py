"""Data models for kindle2readwise using Pydantic."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Highlight(BaseModel):
    """Model representing a Kindle highlight."""

    id: int | None = None
    highlight_hash: str | None = None
    title: str
    author: str
    text: str
    location: str | None = None
    date_highlighted: datetime | None = None
    date_exported: datetime | None = None
    readwise_id: str | None = None
    status: str | None = None

    model_config = ConfigDict(json_schema_extra={"json_encoders": {datetime: lambda dt: dt.isoformat()}})


class ExportSession(BaseModel):
    """Model representing an export session."""

    id: int | None = None
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: datetime | None = None
    highlights_total: int = 0
    highlights_new: int = 0
    highlights_dupe: int = 0
    source_file: str
    status: str = "in_progress"

    model_config = ConfigDict(json_schema_extra={"json_encoders": {datetime: lambda dt: dt.isoformat()}})


class ExportStats(BaseModel):
    """Statistics for an export operation."""

    total: int = 0
    new: int = 0
    dupe: int = 0


class HighlightFilters(BaseModel):
    """Model for highlight filtering options."""

    title: str | None = None
    author: str | None = None
    text_search: str | None = None
    limit: int = 100
    offset: int = 0
    sort_by: str = "date_exported"
    sort_dir: str = "desc"
