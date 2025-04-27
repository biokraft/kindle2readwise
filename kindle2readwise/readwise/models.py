from pydantic import BaseModel, Field, field_validator


class ReadwiseHighlight(BaseModel):
    """Represents a highlight to be sent to the Readwise API."""

    text: str = Field(description="The text content of the highlight")
    title: str = Field(description="The title of the book")
    author: str | None = Field(default="Unknown", description="The author of the book")
    source_type: str = Field(default="kindle", description="The source type of the highlight")
    category: str = Field(default="books", description="The category of the highlight")
    location: int | None = Field(default=None, description="The location of the highlight within the book (as integer)")
    location_type: str | None = Field(default="page", description="The type of location (e.g., 'location', 'page')")
    highlighted_at: str | None = Field(default=None, description="ISO timestamp when the highlight was created")

    @field_validator("title")
    @classmethod
    def format_title(cls, value):
        """Replace underscores with spaces in the title for better readability in Readwise."""
        return value.replace("_", " ") if value else value


class ReadwiseHighlightBatch(BaseModel):
    """Represents a batch of highlights to be sent to the Readwise API."""

    highlights: list[ReadwiseHighlight] = Field(description="A list of highlights to send to Readwise")

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
