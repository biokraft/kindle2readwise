import logging
import time

import requests

from ..parser.models import KindleClipping
from .models import ReadwiseHighlight, ReadwiseHighlightBatch

# Initialize logger for this module
logger = logging.getLogger(__name__)


class ReadwiseAPIClient:
    """Client for interacting with the Readwise API."""

    API_BASE_URL = "https://readwise.io/api/v2"
    HIGHLIGHTS_ENDPOINT = f"{API_BASE_URL}/highlights/"
    AUTH_ENDPOINT = f"{API_BASE_URL}/auth/"

    # HTTP status codes
    HTTP_OK = 200

    # Batch size and rate limiting
    MAX_BATCH_SIZE = 100
    REQUEST_DELAY = 0.25  # 250ms between requests to stay under rate limits

    def __init__(self, api_token: str):
        """Initialize the Readwise API client.

        Args:
            api_token: Readwise API token
        """
        logger.debug("Initializing ReadwiseAPIClient.")
        self.api_token = api_token
        # Define headers before trying to use them for logging
        self.headers = {"Authorization": f"Token {api_token}", "Content-Type": "application/json"}
        # Redact token in logged headers for security
        log_headers = {
            **{"Authorization": "Token [REDACTED]"},
            **{k: v for k, v in self.headers.items() if k != "Authorization"},
        }
        logger.debug("API Headers (token redacted): %s", log_headers)

    def validate_token(self) -> bool:
        """Validate the API token by making a request to the auth endpoint.

        Returns:
            True if the token is valid, False otherwise
        """
        logger.info("Validating Readwise API token...")
        try:
            response = requests.get(self.AUTH_ENDPOINT, headers=self.headers)
            is_valid = response.status_code == self.HTTP_OK
            if is_valid:
                logger.info("Readwise API token is valid (HTTP %d).", response.status_code)
            else:
                logger.warning(
                    "Readwise API token validation failed. Status: %d, Response: %s",
                    response.status_code,
                    response.text[:200],  # Log only the start of the response
                )
            return is_valid
        except requests.RequestException:
            logger.error("Error validating Readwise API token.", exc_info=True)
            return False
        except Exception:
            logger.error("Unexpected error during token validation.", exc_info=True)
            return False

    def send_highlights(self, clippings: list[KindleClipping]) -> dict[str, int]:
        """Send highlights to Readwise.

        Args:
            clippings: List of KindleClipping objects to send

        Returns:
            Dictionary with counts of sent and failed highlights
        """
        if not clippings:
            logger.info("No clippings provided to send.")
            return {"sent": 0, "failed": 0}

        logger.info("Preparing to send %d clippings to Readwise.", len(clippings))

        # Convert clippings to Readwise highlights
        highlights_to_send: list[ReadwiseHighlight] = []
        conversion_skipped = 0
        for clip in clippings:
            highlight = self._convert_clipping_to_highlight(clip)
            if highlight:
                highlights_to_send.append(highlight)
            else:
                conversion_skipped += 1
                logger.debug("Skipped converting clipping (no content or wrong type): %s", clip)

        if conversion_skipped > 0:
            logger.info("Skipped converting %d clippings (e.g., notes without content).", conversion_skipped)

        if not highlights_to_send:
            logger.info("No valid highlights to send after conversion.")
            return {"sent": 0, "failed": 0}

        logger.info(
            "Sending %d converted highlights in batches of up to %d.", len(highlights_to_send), self.MAX_BATCH_SIZE
        )

        # Send highlights in batches
        results = {"sent": 0, "failed": 0}
        total_highlights = len(highlights_to_send)

        for i in range(0, total_highlights, self.MAX_BATCH_SIZE):
            batch = highlights_to_send[i : min(i + self.MAX_BATCH_SIZE, total_highlights)]
            batch_number = (i // self.MAX_BATCH_SIZE) + 1
            total_batches = (total_highlights + self.MAX_BATCH_SIZE - 1) // self.MAX_BATCH_SIZE
            logger.info("Sending batch %d of %d (%d highlights)...", batch_number, total_batches, len(batch))

            batch_result = self._send_batch(batch)

            results["sent"] += batch_result["sent"]
            results["failed"] += batch_result["failed"]

            # Respect rate limits - only sleep if there are more batches
            if i + self.MAX_BATCH_SIZE < total_highlights:
                logger.debug("Sleeping for %.2f seconds before next batch.", self.REQUEST_DELAY)
                time.sleep(self.REQUEST_DELAY)

        logger.info(
            "Finished sending highlights. Total Sent: %d, Total Failed: %d",
            results["sent"],
            results["failed"],
        )
        return results

    def _send_batch(self, highlights: list[ReadwiseHighlight]) -> dict[str, int]:
        """Send a batch of highlights to Readwise.

        Args:
            highlights: List of ReadwiseHighlight objects to send

        Returns:
            Dictionary with counts of sent and failed highlights
        """
        if not highlights:
            logger.warning("_send_batch called with an empty list.")
            return {"sent": 0, "failed": 0}

        batch = ReadwiseHighlightBatch(highlights=highlights)
        batch_dict = batch.to_dict()
        # Avoid logging the full batch content unless DEBUG is enabled and necessary
        logger.debug("Sending batch data: %s", str(batch_dict)[:500] + "...")  # Log truncated data

        try:
            response = requests.post(self.HIGHLIGHTS_ENDPOINT, headers=self.headers, json=batch_dict)

            if response.status_code == self.HTTP_OK:
                logger.debug(
                    "Successfully sent batch of %d highlights (HTTP %d).", len(highlights), response.status_code
                )
                return {"sent": len(highlights), "failed": 0}

            # Log detailed error for non-OK responses
            logger.error(
                "Error sending highlights batch. Status: %d, Response: %s",
                response.status_code,
                response.text[:500],  # Log truncated response
            )
            return {"sent": 0, "failed": len(highlights)}

        except requests.RequestException:
            logger.error("Network error sending highlights batch.", exc_info=True)
            return {"sent": 0, "failed": len(highlights)}
        except Exception:
            logger.error("Unexpected error sending highlights batch.", exc_info=True)
            return {"sent": 0, "failed": len(highlights)}

    def _convert_clipping_to_highlight(self, clipping: KindleClipping) -> ReadwiseHighlight | None:
        """Convert a KindleClipping to a ReadwiseHighlight.

        Args:
            clipping: KindleClipping to convert

        Returns:
            ReadwiseHighlight if parsing is successful, None otherwise
        """
        # Skip creating highlights for empty content or non-highlight/note types
        if not clipping.content:
            logger.debug(
                "Skipping conversion for clipping with no content: Title='%s', Loc='%s'",
                clipping.title,
                clipping.location,
            )
            return None
        if clipping.type not in ["highlight", "note"]:
            logger.debug(
                "Skipping conversion for non-highlight/note clipping: Type='%s', Title='%s'",
                clipping.type,
                clipping.title,
            )
            return None

        logger.debug(
            "Converting clipping to ReadwiseHighlight: Title='%s', Loc='%s'", clipping.title, clipping.location
        )
        return ReadwiseHighlight(
            text=clipping.content,
            title=clipping.title,
            author=clipping.author,
            location=clipping.location,
            highlighted_at=clipping.date.isoformat() if clipping.date else None,
        )
