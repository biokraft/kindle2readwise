from dataclasses import dataclass
from datetime import datetime


@dataclass
class KindleClipping:
    """Represents a single Kindle clipping (highlight, note, or bookmark)."""

    title: str
    author: str | None
    type: str  # "highlight", "note", or "bookmark"
    location: str
    date: datetime
    content: str

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
