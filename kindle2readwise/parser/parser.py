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
    # Updated regex patterns to handle various location formats
    METADATA_RE = re.compile(
        r"- Your (\w+)(?: on page (\d+(?:-\d+)?)?)?(?: \| )?(?:[Ll]ocation )?(\d+-\d+|\d+)?(?: \| )?Added on (.+)$"
    )
    ALT_METADATA_RE = re.compile(r"- Your (\w+)(?: at [Ll]ocation (\d+-\d+|\d+))?(?: \| )?Added on (.+)$")
    PAGE_ONLY_RE = re.compile(r"- Your (\w+)(?: on)? page (\d+(?:-\d+)?)?(?: \| )?Added on (.+)$")

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
        bookmark_count = 0

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
                # Skip bookmarks as they don't serve a purpose for this project
                if clipping.type.lower() == "bookmark":
                    bookmark_count += 1
                    logger.debug("Skipping bookmark in section %d.", i + 1)
                    continue

                clippings.append(clipping)
            else:
                error_count += 1
                # Error details are logged within _parse_clipping

        total_parsed = len(clippings)
        logger.info(
            "Parsing complete. Processed: %d, Skipped Empty: %d, Bookmarks: %d, Errors: %d, Parsed OK: %d",
            processed_count,
            skipped_count,
            bookmark_count,
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
            clipping_type, page, location, date = self._parse_metadata(metadata_line, section_index)

            # Parse content (everything after metadata line)
            content = "\n".join(lines[2:]).strip()
            if not content and clipping_type.lower() != "bookmark":
                logger.warning("Section %d ('%s') has metadata but no content.", section_index, title)
                # Decide if this should be an error or just a warning - currently warning

            clipping_obj = KindleClipping(
                title=title, author=author, type=clipping_type, page=page, location=location, date=date, content=content
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

    def _parse_metadata(self, metadata_line: str, section_index: int) -> tuple[str, str | None, str | None, datetime]:
        """Parse the metadata line to extract clipping type, page, location, and date.

        Args:
            metadata_line: The metadata line of the clipping
            section_index: The 1-based index of the section in the file (for logging)

        Returns:
            Tuple of (clipping_type, page, location, date)
        """
        logger.debug("Parsing metadata for section %d: '%s'", section_index, metadata_line)

        # Initialize variables
        page = None
        location = None

        # 1. Try standard format: "- Your Highlight on page X | Location Y-Z | Added on..."
        match = self.METADATA_RE.match(metadata_line)
        if match:
            clipping_type = match.group(1).lower()  # 'Highlight', 'Note', etc.
            page = match.group(2)  # Page number (might be None)
            location_value = match.group(3)  # Location value (might be None)
            date_str = match.group(4)

            # Set location if available
            if location_value:
                location = location_value

            logger.debug(f"Matched primary regex. Type: {clipping_type}, Page: {page}, Location: {location}")

        # 2. Try alternate format: "- Your Highlight at location X-Y | Added on..."
        else:
            alt_match = self.ALT_METADATA_RE.match(metadata_line)
            if alt_match:
                clipping_type = alt_match.group(1).lower()
                location = alt_match.group(2) if alt_match.group(2) else None
                date_str = alt_match.group(3)
                logger.debug(f"Matched alternate regex. Type: {clipping_type}, Location: {location}")

            # 3. Try page-only format: "- Your Highlight on page X-Y | Added on..."
            else:
                page_match = self.PAGE_ONLY_RE.match(metadata_line)
                if page_match:
                    clipping_type = page_match.group(1).lower()
                    page = page_match.group(2) if page_match.group(2) else None
                    date_str = page_match.group(3)
                    logger.debug(f"Matched page-only regex. Type: {clipping_type}, Page: {page}")

                # 4. Special case for formats like "- Your Highlight on page 92 | location 1406-1407 | Added on..."
                elif " | location " in metadata_line and " | Added on " in metadata_line:
                    # Extract the type, page, location and date directly
                    logger.debug("Using direct extraction for special case metadata")
                    try:
                        clipping_type, page, location, date_str = self._extract_metadata_directly(metadata_line)
                    except Exception as e:
                        logger.warning(f"Error in direct extraction: {e}")
                        return "unknown", None, None, datetime.now()

                # If none of the regex patterns match
                else:
                    logger.warning(
                        "Could not parse metadata line format in section %d: '%s'. Using defaults.",
                        section_index,
                        metadata_line,
                    )
                    # Default fallback
                    return "unknown", None, None, datetime.now()

        logger.debug(
            "Extracted metadata parts for section %d: Type='%s', Page='%s', Loc='%s', DateStr='%s'",
            section_index,
            clipping_type,
            page,
            location,
            date_str,
        )

        try:
            # Try to parse the date
            # Common format: "Tuesday, April 15, 2025 11:18:50 PM"
            date = datetime.strptime(date_str, "%A, %B %d, %Y %I:%M:%S %p")
            logger.debug("Parsed date for section %d: %s", section_index, date)
        except ValueError:
            try:
                # Try alternate format (e.g. "Saturday, 26 March 2016 14:59:39")
                date = datetime.strptime(date_str, "%A, %d %B %Y %H:%M:%S")
                logger.debug("Parsed date for section %d using alternate format: %s", section_index, date)
            except ValueError as e:
                logger.warning(
                    "Could not parse date string '%s' in section %d using standard formats. "
                    "Error: %s. Using current time as fallback.",
                    date_str,
                    section_index,
                    e,
                )
                # Fallback if date format is different
                date = datetime.now()

        return clipping_type, page, location, date

    def _extract_metadata_directly(self, metadata_line: str) -> tuple[str, str | None, str | None, str]:
        """Extract metadata directly using regex searches.

        Args:
            metadata_line: The metadata line to parse

        Returns:
            Tuple of (clipping_type, page, location, date_str)
        """
        type_match = re.search(r"- Your (\w+)", metadata_line)
        clipping_type = type_match.group(1).lower() if type_match else "unknown"

        page_match = re.search(r"page (\d+(?:-\d+)?)", metadata_line)
        page = page_match.group(1) if page_match else None

        loc_match = re.search(r"location (\d+-\d+|\d+)", metadata_line)
        location = loc_match.group(1) if loc_match else None

        date_match = re.search(r"Added on (.+)$", metadata_line)
        date_str = date_match.group(1) if date_match else datetime.now().strftime("%A, %d %B %Y %H:%M:%S")

        logger.debug(
            f"Direct extraction results: Type={clipping_type}, Page={page}, Location={location}, Date={date_str}"
        )

        return clipping_type, page, location, date_str
