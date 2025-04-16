from dataclasses import dataclass


@dataclass
class ReadwiseHighlight:
    """Represents a highlight to be sent to the Readwise API."""

    text: str
    title: str
    author: str | None = None
    source_type: str = "kindle"
    category: str = "books"
    location: str | None = None
    location_type: str | None = "location"
    highlighted_at: str | None = None


@dataclass
class ReadwiseHighlightBatch:
    """Represents a batch of highlights to be sent to the Readwise API."""

    highlights: list[ReadwiseHighlight]

    def to_dict(self) -> dict:
        """Convert the batch to the format expected by the Readwise API."""
        return {
            "highlights": [
                {
                    "text": h.text,
                    "title": h.title,
                    "author": h.author,
                    "source_type": h.source_type,
                    "category": h.category,
                    "location": h.location,
                    "location_type": h.location_type,
                    "highlighted_at": h.highlighted_at,
                }
                for h in self.highlights
            ]
        }
