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
    # Metadata regex patterns to handle various location formats
    METADATA_RE = re.compile(
        r"- Your (\w+)(?: on page (\d+(?:-\d+)?)?)?(?: \| )?(?:[Ll]ocation )?(\d+-\d+|\d+)?(?: \| )?Added on (.+)$"
    )
    ALT_METADATA_RE = re.compile(r"- Your (\w+)(?: at [Ll]ocation (\d+-\d+|\d+))?(?: \| )?Added on (.+)$")
    PAGE_ONLY_RE = re.compile(r"- Your (\w+)(?: on)? page (\d+(?:-\d+)?)?(?: \| )?Added on (.+)$")
    TYPE_RE = re.compile(r"- Your (\w+)")
    PAGE_RE = re.compile(r"page (\d+(?:-\d+)?)")
    LOCATION_RE = re.compile(r"location (\d+-\d+|\d+)")
    DATE_RE = re.compile(r"Added on (.+)$")

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

        content = self._read_clippings_file()
        raw_clippings = self._split_content(content)
        return self._process_clippings(raw_clippings)

    def _read_clippings_file(self) -> str:
        """Read content from the clippings file.

        Returns:
            String content of the file

        Raises:
            OSError: If file can't be read
        """
        try:
            with open(self.clippings_file, encoding="utf-8-sig") as f:
                content = f.read()
            logger.debug("Successfully read %d bytes from %s", len(content), self.clippings_file)
            return content
        except Exception as e:
            logger.error("Failed to read clippings file %s", self.clippings_file, exc_info=True)
            raise OSError(f"Could not read clippings file: {self.clippings_file}") from e

    def _split_content(self, content: str) -> list[str]:
        """Split content by separator.

        Args:
            content: Full content of clippings file

        Returns:
            List of raw clipping strings
        """
        raw_clippings = content.split(self.SEPARATOR)
        logger.debug("Split content into %d raw sections.", len(raw_clippings))
        return raw_clippings

    def _process_clippings(self, raw_clippings: list[str]) -> list[KindleClipping]:
        """Process all raw clippings.

        Args:
            raw_clippings: List of raw clipping strings

        Returns:
            List of parsed KindleClipping objects
        """
        clippings = []
        processed_count = 0
        skipped_count = 0
        error_count = 0
        bookmark_count = 0

        for i, raw_clipping in enumerate(raw_clippings):
            processed_count += 1
            section_index = i + 1

            trimmed_clipping = raw_clipping.strip()
            if not trimmed_clipping:
                skipped_count += 1
                logger.debug("Skipping empty section %d.", section_index)
                continue

            logger.debug("Parsing raw clipping section %d.", section_index)
            clipping = self._parse_clipping(trimmed_clipping, section_index)

            if clipping:
                if clipping.type.lower() == "bookmark":
                    bookmark_count += 1
                    logger.debug("Skipping bookmark in section %d.", section_index)
                    continue
                clippings.append(clipping)
            else:
                error_count += 1

        self._log_parsing_summary(processed_count, skipped_count, bookmark_count, error_count, len(clippings))
        return clippings

    def _log_parsing_summary(self, processed: int, skipped: int, bookmarks: int, errors: int, parsed: int) -> None:
        """Log a summary of parsing statistics.

        Args:
            processed: Number of sections processed
            skipped: Number of empty sections skipped
            bookmarks: Number of bookmarks skipped
            errors: Number of parsing errors
            parsed: Number of successfully parsed clippings
        """
        logger.info(
            "Parsing complete. Processed: %d, Skipped Empty: %d, Bookmarks: %d, Errors: %d, Parsed OK: %d",
            processed,
            skipped,
            bookmarks,
            errors,
            parsed,
        )

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
        first_line_preview = self._get_preview_text(lines[0], self.TITLE_PREVIEW_LENGTH)
        logger.debug("Attempting to parse section %d, starting with: '%s'", section_index, first_line_preview)

        try:
            if not self._validate_clipping_lines(lines, section_index, first_line_preview):
                return None

            # Parse title and author
            title_line = self._clean_title_line(lines[0])
            title, author = self._parse_title_author(title_line, section_index)

            # Parse metadata
            metadata_line = lines[1].strip()
            clipping_type, page, location, date = self._parse_metadata(metadata_line, section_index)

            # Parse content (everything after metadata line)
            content = self._extract_content(lines)
            if not content and clipping_type.lower() != "bookmark":
                logger.warning("Section %d ('%s') has metadata but no content.", section_index, title)

            clipping_obj = KindleClipping(
                title=title, author=author, type=clipping_type, page=page, location=location, date=date, content=content
            )
            logger.debug("Successfully parsed section %d: %s", section_index, clipping_obj)
            return clipping_obj
        except Exception:
            logger.error(
                "Error parsing section %d. Raw content snippet: '%s'",
                section_index,
                self._get_preview_text(raw_clipping, self.CONTENT_PREVIEW_LENGTH),
                exc_info=True,
            )
            return None

    def _get_preview_text(self, text: str, max_length: int) -> str:
        """Get a preview of text, truncated if too long.

        Args:
            text: Text to preview
            max_length: Maximum length of preview

        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text

    def _validate_clipping_lines(self, lines: list[str], section_index: int, preview: str) -> bool:
        """Validate that a clipping has enough lines to be parsed.

        Args:
            lines: Lines of the clipping
            section_index: Section index for logging
            preview: Preview of content for logging

        Returns:
            True if valid, False otherwise
        """
        if len(lines) < self.MIN_LINES_PER_CLIPPING:
            logger.warning(
                "Skipping section %d: Too few lines (%d < %d). Content: '%s'",
                section_index,
                len(lines),
                self.MIN_LINES_PER_CLIPPING,
                preview,
            )
            return False
        return True

    def _clean_title_line(self, title_line: str) -> str:
        """Clean the title line, removing BOM if present.

        Args:
            title_line: Raw title line

        Returns:
            Cleaned title line
        """
        title_line = title_line.strip()
        if title_line.startswith("\ufeff"):
            logger.debug("Removing BOM from title line.")
            title_line = title_line[1:]
        return title_line

    def _extract_content(self, lines: list[str]) -> str:
        """Extract the content from clipping lines.

        Args:
            lines: Lines of the clipping

        Returns:
            Extracted content
        """
        return "\n".join(lines[2:]).strip()

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

        # Try each regex pattern in sequence
        metadata_result = self._try_metadata_patterns(metadata_line)
        if metadata_result:
            clipping_type, page, location, date_str = metadata_result
        else:
            # Default fallback
            logger.warning(
                "Could not parse metadata line format in section %d: '%s'. Using defaults.",
                section_index,
                metadata_line,
            )
            return "unknown", None, None, datetime.now()

        logger.debug(
            "Extracted metadata parts for section %d: Type='%s', Page='%s', Loc='%s', DateStr='%s'",
            section_index,
            clipping_type,
            page,
            location,
            date_str,
        )

        date = self._parse_date(date_str, section_index)
        return clipping_type, page, location, date

    def _try_metadata_patterns(self, metadata_line: str) -> tuple[str, str | None, str | None, str] | None:
        """Try different regex patterns to parse metadata.

        Args:
            metadata_line: Metadata line to parse

        Returns:
            Tuple of (clipping_type, page, location, date_str) if parsed, None otherwise
        """
        # 1. Try standard format: "- Your Highlight on page X | Location Y-Z | Added on..."
        match = self.METADATA_RE.match(metadata_line)
        if match:
            clipping_type = match.group(1).lower()
            page = match.group(2)
            location = match.group(3) if match.group(3) else None
            date_str = match.group(4)
            logger.debug(f"Matched primary regex. Type: {clipping_type}, Page: {page}, Location: {location}")
            return clipping_type, page, location, date_str

        # 2. Try alternate format: "- Your Highlight at location X-Y | Added on..."
        alt_match = self.ALT_METADATA_RE.match(metadata_line)
        if alt_match:
            clipping_type = alt_match.group(1).lower()
            location = alt_match.group(2) if alt_match.group(2) else None
            date_str = alt_match.group(3)
            logger.debug(f"Matched alternate regex. Type: {clipping_type}, Location: {location}")
            return clipping_type, None, location, date_str

        # 3. Try page-only format: "- Your Highlight on page X-Y | Added on..."
        page_match = self.PAGE_ONLY_RE.match(metadata_line)
        if page_match:
            clipping_type = page_match.group(1).lower()
            page = page_match.group(2) if page_match.group(2) else None
            date_str = page_match.group(3)
            logger.debug(f"Matched page-only regex. Type: {clipping_type}, Page: {page}")
            return clipping_type, page, None, date_str

        # 4. Special case for formats like "- Your Highlight on page 92 | location 1406-1407 | Added on..."
        if " | location " in metadata_line and " | Added on " in metadata_line:
            # Extract the type, page, location and date directly
            logger.debug("Using direct extraction for special case metadata")
            try:
                return self._extract_metadata_directly(metadata_line)
            except Exception as e:
                logger.warning(f"Error in direct extraction: {e}")
                return None

        return None

    def _parse_date(self, date_str: str, section_index: int) -> datetime:
        """Parse date string into datetime object.

        Args:
            date_str: Date string to parse
            section_index: Section index for logging

        Returns:
            Parsed datetime or current time as fallback
        """
        try:
            # Try to parse the date
            # Common format: "Tuesday, April 15, 2025 11:18:50 PM"
            date = datetime.strptime(date_str, "%A, %B %d, %Y %I:%M:%S %p")
            logger.debug("Parsed date for section %d: %s", section_index, date)
            return date
        except ValueError:
            try:
                # Try alternate format (e.g. "Saturday, 26 March 2016 14:59:39")
                date = datetime.strptime(date_str, "%A, %d %B %Y %H:%M:%S")
                logger.debug("Parsed date for section %d using alternate format: %s", section_index, date)
                return date
            except ValueError as e:
                logger.warning(
                    "Could not parse date string '%s' in section %d using standard formats. "
                    "Error: %s. Using current time as fallback.",
                    date_str,
                    section_index,
                    e,
                )
                # Fallback if date format is different
                return datetime.now()

    def _extract_metadata_directly(self, metadata_line: str) -> tuple[str, str | None, str | None, str]:
        """Extract metadata directly using regex searches.

        Args:
            metadata_line: The metadata line to parse

        Returns:
            Tuple of (clipping_type, page, location, date_str)
        """
        type_match = self.TYPE_RE.search(metadata_line)
        clipping_type = type_match.group(1).lower() if type_match else "unknown"

        page_match = self.PAGE_RE.search(metadata_line)
        page = page_match.group(1) if page_match else None

        loc_match = self.LOCATION_RE.search(metadata_line)
        location = loc_match.group(1) if loc_match else None

        date_match = self.DATE_RE.search(metadata_line)
        date_str = date_match.group(1) if date_match else datetime.now().strftime("%A, %d %B %Y %H:%M:%S")

        logger.debug(
            f"Direct extraction results: Type={clipping_type}, Page={page}, Location={location}, Date={date_str}"
        )

        return clipping_type, page, location, date_str
