import re
from datetime import datetime
from pathlib import Path

from .models import KindleClipping


class KindleClippingsParser:
    """Parser for Kindle 'My Clippings.txt' files."""

    SEPARATOR = "=========="
    MIN_LINES_PER_CLIPPING = 3

    # Regular expressions for parsing
    TITLE_AUTHOR_RE = re.compile(r"^(.+?)(?:\s+\(([^)]+)\))?$")
    METADATA_RE = re.compile(r"- Your (\w+) (?:on (?:page (\d+) \| )?)?Location (\d+-\d+|(\d+)) \| Added on (.+)$")

    def __init__(self, clippings_file: str):
        """Initialize the parser with the path to a clippings file.

        Args:
            clippings_file: Path to the 'My Clippings.txt' file
        """
        self.clippings_file = Path(clippings_file)
        if not self.clippings_file.exists():
            raise FileNotFoundError(f"Clippings file not found: {clippings_file}")

    def parse(self) -> list[KindleClipping]:
        """Parse the clippings file and return a list of structured clippings.

        Returns:
            List of KindleClipping objects
        """
        with open(self.clippings_file, encoding="utf-8-sig") as f:
            content = f.read()

        # Split by separator
        raw_clippings = content.split(self.SEPARATOR)

        # Parse each clipping
        clippings = []
        for raw_clipping in raw_clippings:
            if not raw_clipping.strip():
                continue

            clipping = self._parse_clipping(raw_clipping.strip())
            if clipping:
                clippings.append(clipping)

        return clippings

    def _parse_clipping(self, raw_clipping: str) -> KindleClipping | None:
        """Parse a single clipping entry.

        Args:
            raw_clipping: Text of a single clipping

        Returns:
            KindleClipping if parsing is successful, None otherwise
        """
        try:
            lines = raw_clipping.split("\n")

            # Need at least MIN_LINES_PER_CLIPPING lines for a valid clipping
            if len(lines) < self.MIN_LINES_PER_CLIPPING:
                return None

            # Parse title and author
            title_line = lines[0].strip()
            # Remove BOM if present
            if title_line.startswith("\ufeff"):
                title_line = title_line[1:]
            title, author = self._parse_title_author(title_line)

            # Parse metadata
            metadata_line = lines[1].strip()
            clipping_type, location, date = self._parse_metadata(metadata_line)

            # Parse content (everything after metadata line)
            content = "\n".join(lines[2:]).strip()

            return KindleClipping(
                title=title, author=author, type=clipping_type, location=location, date=date, content=content
            )
        except Exception as e:
            # Log the error in a real implementation
            print(f"Error parsing clipping: {e}")
            return None

    def _parse_title_author(self, title_line: str) -> tuple[str, str | None]:
        """Parse the title and author from the first line of a clipping.

        Args:
            title_line: First line of the clipping

        Returns:
            Tuple of (title, author)
        """
        match = self.TITLE_AUTHOR_RE.match(title_line)
        if match:
            title, author = match.groups()
            return title.strip(), author.strip() if author else None
        return title_line, None

    def _parse_metadata(self, metadata_line: str) -> tuple[str, str, datetime]:
        """Parse the metadata line to extract clipping type, location, and date.

        Args:
            metadata_line: The metadata line of the clipping

        Returns:
            Tuple of (clipping_type, location, date)
        """
        match = self.METADATA_RE.match(metadata_line)
        if not match:
            # Fallback for non-standard formats
            return "unknown", "unknown", datetime.now()

        clipping_type = match.group(1).lower()  # 'Highlight', 'Note', etc.
        location = match.group(3) or "unknown"
        date_str = match.group(5)

        try:
            # Try to parse the date
            # Example format: "Tuesday, April 15, 2025 11:18:50 PM"
            date = datetime.strptime(date_str, "%A, %B %d, %Y %I:%M:%S %p")
        except ValueError:
            # Fallback if date format is different
            date = datetime.now()

        return clipping_type, location, date
