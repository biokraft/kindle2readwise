import logging
import re
from datetime import datetime
from pathlib import Path

from .models import KindleClipping

# Initialize logger for this module
logger = logging.getLogger(__name__)


class KindleClippingsParser:
    """Parser for Kindle 'My Clippings.txt' files."""

    SEPARATOR = "=========="
    MIN_LINES_PER_CLIPPING = 3

    # Preview length limits for log messages
    TITLE_PREVIEW_LENGTH = 80
    CONTENT_PREVIEW_LENGTH = 200

    # Regular expressions for parsing
    TITLE_AUTHOR_RE = re.compile(r"^(.+?)(?:\s+\(([^)]+)\))?$")
    METADATA_RE = re.compile(r"- Your (\w+) (?:on (?:page (\d+) \| )?)?Location (\d+-\d+|(\d+)) \| Added on (.+)$")

    def __init__(self, clippings_file: str):
        """Initialize the parser with the path to a clippings file.

        Args:
            clippings_file: Path to the 'My Clippings.txt' file
        """
        self.clippings_file = Path(clippings_file)
        logger.debug("Initializing KindleClippingsParser with file: %s", self.clippings_file)
        if not self.clippings_file.exists():
            logger.error("Clippings file not found: %s", clippings_file)
            raise FileNotFoundError(f"Clippings file not found: {clippings_file}")

    def parse(self) -> list[KindleClipping]:
        """Parse the clippings file and return a list of structured clippings.

        Returns:
            List of KindleClipping objects
        """
        logger.info("Starting to parse clippings file: %s", self.clippings_file)
        try:
            with open(self.clippings_file, encoding="utf-8-sig") as f:
                content = f.read()
            logger.debug("Successfully read %d bytes from %s", len(content), self.clippings_file)
        except Exception as e:
            logger.error("Failed to read clippings file %s", self.clippings_file, exc_info=True)
            raise OSError(f"Could not read clippings file: {self.clippings_file}") from e

        # Split by separator
        raw_clippings = content.split(self.SEPARATOR)
        logger.debug("Split content into %d raw sections.", len(raw_clippings))

        # Parse each clipping
        clippings = []
        processed_count = 0
        skipped_count = 0
        error_count = 0

        for i, raw_clipping in enumerate(raw_clippings):
            processed_count += 1
            trimmed_clipping = raw_clipping.strip()
            if not trimmed_clipping:
                skipped_count += 1
                logger.debug("Skipping empty section %d.", i + 1)
                continue

            logger.debug("Parsing raw clipping section %d.", i + 1)
            clipping = self._parse_clipping(trimmed_clipping, section_index=i + 1)
            if clipping:
                clippings.append(clipping)
            else:
                error_count += 1
                # Error details are logged within _parse_clipping

        total_parsed = len(clippings)
        logger.info(
            "Parsing complete. Processed: %d, Skipped Empty: %d, Errors: %d, Parsed OK: %d",
            processed_count,
            skipped_count,
            error_count,
            total_parsed,
        )
        return clippings

    def _parse_clipping(self, raw_clipping: str, section_index: int) -> KindleClipping | None:
        """Parse a single clipping entry.

        Args:
            raw_clipping: Text of a single clipping
            section_index: The 1-based index of the section in the file (for logging)

        Returns:
            KindleClipping if parsing is successful, None otherwise
        """
        lines = raw_clipping.split("\n")
        # Log the first line for context, truncate if too long
        first_line_preview = (
            lines[0][: self.TITLE_PREVIEW_LENGTH] + "..." if len(lines[0]) > self.TITLE_PREVIEW_LENGTH else lines[0]
        )
        logger.debug("Attempting to parse section %d, starting with: '%s'", section_index, first_line_preview)

        try:
            # Need at least MIN_LINES_PER_CLIPPING lines for a valid clipping
            if len(lines) < self.MIN_LINES_PER_CLIPPING:
                logger.warning(
                    "Skipping section %d: Too few lines (%d < %d). Content: '%s'",
                    section_index,
                    len(lines),
                    self.MIN_LINES_PER_CLIPPING,
                    first_line_preview,
                )
                return None

            # Parse title and author
            title_line = lines[0].strip()
            # Remove BOM if present
            if title_line.startswith("\ufeff"):
                logger.debug("Removing BOM from title line in section %d.", section_index)
                title_line = title_line[1:]
            title, author = self._parse_title_author(title_line, section_index)

            # Parse metadata
            metadata_line = lines[1].strip()
            clipping_type, location, date = self._parse_metadata(metadata_line, section_index)

            # Parse content (everything after metadata line)
            content = "\n".join(lines[2:]).strip()
            if not content:
                logger.warning("Section %d ('%s') has metadata but no content.", section_index, title)
                # Decide if this should be an error or just a warning - currently warning

            clipping_obj = KindleClipping(
                title=title, author=author, type=clipping_type, location=location, date=date, content=content
            )
            logger.debug("Successfully parsed section %d: %s", section_index, clipping_obj)
            return clipping_obj
        except Exception:
            logger.error(
                "Error parsing section %d. Raw content snippet: '%s'",
                section_index,
                raw_clipping[: self.CONTENT_PREVIEW_LENGTH] + "..."
                if len(raw_clipping) > self.CONTENT_PREVIEW_LENGTH
                else raw_clipping,
                exc_info=True,
            )
            return None

    def _parse_title_author(self, title_line: str, section_index: int) -> tuple[str, str | None]:
        """Parse the title and author from the first line of a clipping.

        Args:
            title_line: First line of the clipping
            section_index: The 1-based index of the section in the file (for logging)

        Returns:
            Tuple of (title, author)
        """
        match = self.TITLE_AUTHOR_RE.match(title_line)
        if match:
            title, author = match.groups()
            parsed_title = title.strip()
            parsed_author = author.strip() if author else None
            logger.debug(
                "Parsed title/author for section %d: Title='%s', Author='%s'",
                section_index,
                parsed_title,
                parsed_author,
            )
            return parsed_title, parsed_author

        logger.warning(
            "Could not parse author from title line in section %d: '%s'. Using full line as title.",
            section_index,
            title_line,
        )
        return title_line, None

    def _parse_metadata(self, metadata_line: str, section_index: int) -> tuple[str, str, datetime]:
        """Parse the metadata line to extract clipping type, location, and date.

        Args:
            metadata_line: The metadata line of the clipping
            section_index: The 1-based index of the section in the file (for logging)

        Returns:
            Tuple of (clipping_type, location, date)
        """
        logger.debug("Parsing metadata for section %d: '%s'", section_index, metadata_line)
        match = self.METADATA_RE.match(metadata_line)
        if not match:
            logger.warning(
                "Could not parse metadata line format in section %d: '%s'. Using defaults.",
                section_index,
                metadata_line,
            )
            # Fallback for non-standard formats - consider if defaults are acceptable
            return "unknown", "unknown", datetime.now()  # Using now() might be misleading

        clipping_type = match.group(1).lower()  # 'Highlight', 'Note', etc.
        # Handle cases where location might be a range or single number
        location = match.group(3) if match.group(3) else match.group(4)
        location = location if location else "unknown"  # Ensure location is not None
        date_str = match.group(5)
        logger.debug(
            "Extracted metadata parts for section %d: Type='%s', Loc='%s', DateStr='%s'",
            section_index,
            clipping_type,
            location,
            date_str,
        )

        try:
            # Try to parse the date
            # Example format: "Tuesday, April 15, 2025 11:18:50 PM"
            date = datetime.strptime(date_str, "%A, %B %d, %Y %I:%M:%S %p")
            logger.debug("Parsed date for section %d: %s", section_index, date)
        except ValueError as e:
            logger.warning(
                "Could not parse date string '%s' in section %d using standard format. "
                "Error: %s. Using current time as fallback.",
                date_str,
                section_index,
                e,
            )
            # Fallback if date format is different - consider if now() is appropriate
            date = datetime.now()

        return clipping_type, location, date
