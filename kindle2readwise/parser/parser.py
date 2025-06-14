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

    # Note attachment constants
    NOTE_CONTENT_PREVIEW_LENGTH = 50
    MAX_LOCATION_DISTANCE = 10

    # Duplicate detection constants
    CONTENT_OVERLAP_THRESHOLD = 0.7
    CONTENT_PREVIEW_LENGTH = 50

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

        # Merge duplicate highlights before attaching notes
        merged_clippings = self._merge_duplicate_highlights(clippings)

        # Apply note detection after merging duplicates
        clippings_with_notes = self._attach_notes_to_highlights(merged_clippings)

        self._log_parsing_summary(
            processed_count, skipped_count, bookmark_count, error_count, len(clippings_with_notes)
        )
        return clippings_with_notes

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

    def _merge_duplicate_highlights(self, clippings: list[KindleClipping]) -> list[KindleClipping]:
        """Merge duplicate highlights from the same book and page, keeping the most recent/longest version.

        This addresses the issue where users resize highlights, creating multiple versions of the same highlight.
        We want to keep only the final version and ensure notes are properly attached.

        Args:
            clippings: List of KindleClipping objects

        Returns:
            List of KindleClipping objects with duplicates merged
        """
        if not clippings:
            return clippings

        result = []
        processed_indices = set()

        for i, current_clipping in enumerate(clippings):
            if i in processed_indices:
                continue

            # Only process highlights for merging
            if current_clipping.type.lower() != "highlight":
                result.append(current_clipping)
                continue

            # Find all duplicates of this highlight in the remaining clippings
            duplicates = [current_clipping]
            duplicate_indices = {i}

            for j in range(i + 1, len(clippings)):
                if j in processed_indices:
                    continue

                other_clipping = clippings[j]
                if other_clipping.type.lower() == "highlight" and self._are_highlights_duplicates(
                    current_clipping, other_clipping
                ):
                    duplicates.append(other_clipping)
                    duplicate_indices.add(j)

            # Mark all duplicates as processed
            processed_indices.update(duplicate_indices)

            # If we found duplicates, merge them
            if len(duplicates) > 1:
                merged_highlight = self._merge_highlights(duplicates)
                result.append(merged_highlight)
                logger.debug(
                    "Merged %d duplicate highlights for '%s' (page %s): kept version with %d chars",
                    len(duplicates),
                    merged_highlight.title,
                    merged_highlight.page,
                    len(merged_highlight.content),
                )
            else:
                # No duplicates found, keep the original
                result.append(current_clipping)

        logger.info(
            "Duplicate merging complete. Original clippings: %d, After merging: %d", len(clippings), len(result)
        )
        return result

    def _are_highlights_duplicates(self, highlight1: KindleClipping, highlight2: KindleClipping) -> bool:
        """Check if two highlights are duplicates (same book, same page, overlapping content).

        Args:
            highlight1: First highlight
            highlight2: Second highlight

        Returns:
            True if the highlights are considered duplicates
        """
        # Must be from the same book
        if highlight1.title != highlight2.title:
            return False

        # Must be from the same page (if both have page info)
        if highlight1.page and highlight2.page:
            # Handle page ranges like "283-283" vs "283"
            page1 = highlight1.page.split("-")[0]
            page2 = highlight2.page.split("-")[0]
            if page1 != page2:
                return False
        elif highlight1.page != highlight2.page:  # One has page, other doesn't
            return False

        # Check if content overlaps (one is a substring of the other or they share significant text)
        content1 = highlight1.content.strip().lower()
        content2 = highlight2.content.strip().lower()

        # If one content is contained in the other, they're duplicates
        if content1 in content2 or content2 in content1:
            return True

        # Check for significant overlap (at least 70% of the shorter text)
        shorter_len = min(len(content1), len(content2))
        if shorter_len == 0:
            return False

        # Simple overlap check: count common words
        words1 = set(content1.split())
        words2 = set(content2.split())
        common_words = words1.intersection(words2)

        # If at least 70% of words from the shorter text are in common, consider them duplicates
        overlap_ratio = len(common_words) / min(len(words1), len(words2)) if min(len(words1), len(words2)) > 0 else 0
        return overlap_ratio >= self.CONTENT_OVERLAP_THRESHOLD

    def _merge_highlights(self, highlights: list[KindleClipping]) -> KindleClipping:
        """Merge multiple duplicate highlights into one, keeping the most recent/longest version.

        Args:
            highlights: List of duplicate highlights to merge

        Returns:
            Single merged highlight
        """
        if not highlights:
            raise ValueError("Cannot merge empty list of highlights")

        if len(highlights) == 1:
            return highlights[0]

        # Sort by date (most recent first), then by content length (longest first)
        sorted_highlights = sorted(highlights, key=lambda h: (h.date, len(h.content)), reverse=True)

        # Use the most recent/longest highlight as the base
        best_highlight = sorted_highlights[0]

        logger.debug(
            "Merging highlights: selected version from %s with %d chars: '%s'",
            best_highlight.date,
            len(best_highlight.content),
            best_highlight.content[: self.CONTENT_PREVIEW_LENGTH] + "..."
            if len(best_highlight.content) > self.CONTENT_PREVIEW_LENGTH
            else best_highlight.content,
        )

        return best_highlight

    def _attach_notes_to_highlights(self, clippings: list[KindleClipping]) -> list[KindleClipping]:
        """Attach notes to highlights by combining notes with related highlights from the same book/location.

        Args:
            clippings: List of KindleClipping objects

        Returns:
            List of parsed KindleClipping objects with notes attached to highlights
        """
        result = []

        for current_clipping in clippings:
            if current_clipping.type.lower() == "note":
                # This is a note - look for a recent highlight to attach it to
                attached = False

                # Look backwards through recent results to find a matching highlight
                for i in range(len(result) - 1, -1, -1):
                    if result[i].type.lower() == "highlight" and self._is_note_related_to_highlight(
                        result[i], current_clipping
                    ):
                        # Found a matching highlight - attach the note
                        logger.debug(
                            "Attaching note to highlight: %s (page %s) -> note content: %s",
                            result[i].title,
                            result[i].page,
                            current_clipping.content[: self.NOTE_CONTENT_PREVIEW_LENGTH] + "..."
                            if len(current_clipping.content) > self.NOTE_CONTENT_PREVIEW_LENGTH
                            else current_clipping.content,
                        )

                        # Create a new highlight with the note attached
                        highlight_with_note = KindleClipping(
                            title=result[i].title,
                            author=result[i].author,
                            type=result[i].type,
                            page=result[i].page,
                            location=result[i].location,
                            date=result[i].date,
                            content=result[i].content,
                            note=current_clipping.content,
                        )
                        result[i] = highlight_with_note  # Replace the highlight with the version that has the note
                        attached = True
                        break

                if not attached:
                    # No matching highlight found - keep as standalone note
                    result.append(current_clipping)

            else:
                # This is a highlight or other type - add it to results
                result.append(current_clipping)

        logger.info("Note detection complete. Original clippings: %d, Final clippings: %d", len(clippings), len(result))
        return result

    def _is_note_related_to_highlight(self, highlight: KindleClipping, note: KindleClipping) -> bool:
        """Check if a note is related to a highlight (same book and similar location).

        Args:
            highlight: The highlight clipping
            note: The potential note clipping

        Returns:
            True if the note should be attached to the highlight
        """
        # Must be a note type
        if note.type.lower() != "note":
            return False

        # Must be from the same book
        if highlight.title != note.title:
            return False

        # Must be from the same page (if both have page info)
        if highlight.page and note.page:
            # Handle page ranges like "207-207" vs "207"
            highlight_page = highlight.page.split("-")[0]
            note_page = note.page.split("-")[0]
            if highlight_page != note_page:
                return False

        # If no page info, check location proximity
        elif highlight.location and note.location:
            try:
                # Extract numeric location values
                highlight_loc = int(highlight.location.split("-")[0])
                note_loc = int(note.location.split("-")[0])
                # Allow notes within a reasonable range
                if abs(highlight_loc - note_loc) > self.MAX_LOCATION_DISTANCE:
                    return False
            except (ValueError, IndexError):
                # If we can't parse locations, be conservative and don't attach
                return False

        logger.debug(
            "Note is related to highlight: %s (page %s, loc %s) -> note (page %s, loc %s)",
            highlight.title,
            highlight.page,
            highlight.location,
            note.page,
            note.location,
        )
        return True
