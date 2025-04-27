from datetime import datetime

from pydantic import BaseModel, Field


class KindleClipping(BaseModel):
    """Represents a single Kindle clipping (highlight, note, or bookmark)."""

    title: str = Field(description="The title of the book")
    author: str | None = Field(default=None, description="The author of the book")
    type: str = Field(description="Type of clipping: 'highlight', 'note', or 'bookmark'")
    page: str | None = Field(default=None, description="Page number of the clipping")
    location: str | None = Field(default=None, description="Location information from the Kindle")
    date: datetime = Field(description="Date when the clipping was created")
    content: str = Field(description="Content of the clipping")

    def get_identifier(self) -> str:
        """Generate a unique identifier for the clipping based on title, author, and content."""
        identifier_parts = [self.title, self.author or "", self.content]
        return "_".join(identifier_parts).strip().lower().replace(" ", "_")

    def to_readwise_format(self) -> dict:
        """Convert the clipping to the format expected by Readwise API."""
        # Prioritize page over location for Readwise
        location_value = self.page if self.page else self.location
        location_type = "page" if self.page else "location"

        return {
            "text": self.content,
            "title": self.title,
            "author": self.author or "Unknown",
            "source_type": "kindle",
            "category": "books",
            "location": location_value,
            "location_type": location_type,
            "highlighted_at": self.date.isoformat() if self.date else None,
        }
