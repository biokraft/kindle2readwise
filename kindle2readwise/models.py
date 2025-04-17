"""Core data models for kindle2readwise application."""

from pydantic import BaseModel, Field


class ExportStats(BaseModel):
    """Statistics for an export session."""

    total_processed: int = Field(default=0, description="Total number of clippings processed")
    new_sent: int = Field(default=0, description="Number of new clippings sent to Readwise")
    duplicates_skipped: int = Field(default=0, description="Number of duplicate clippings skipped")
    failed_to_send: int = Field(default=0, description="Number of clippings that failed to send to Readwise")
