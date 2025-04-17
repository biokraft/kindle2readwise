from datetime import datetime

from pydantic import BaseModel, Field


class KindleClipping(BaseModel):
    """Represents a single Kindle clipping (highlight, note, or bookmark)."""

    title: str = Field(description="The title of the book")
    author: str | None = Field(default=None, description="The author of the book")
    type: str = Field(description="Type of clipping: 'highlight', 'note', or 'bookmark'")
    location: str = Field(description="Location information from the Kindle")
    date: datetime = Field(description="Date when the clipping was created")
    content: str = Field(description="Content of the clipping")

    def get_identifier(self) -> str:
        """Generate a unique identifier for the clipping based on title, author, and content."""
        identifier_parts = [self.title, self.author or "", self.content]
        return "_".join(identifier_parts).strip().lower().replace(" ", "_")

    def to_readwise_format(self) -> dict:
        """Convert the clipping to the format expected by Readwise API."""
        return {
            "text": self.content,
            "title": self.title,
            "author": self.author,
            "source_type": "kindle",
            "category": "books",
            "location": self.location,
            "location_type": "location",
            "highlighted_at": self.date.isoformat() if self.date else None,
        }
