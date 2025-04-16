import time

import requests

from ..parser.models import KindleClipping
from .models import ReadwiseHighlight, ReadwiseHighlightBatch


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
        self.api_token = api_token
        self.headers = {"Authorization": f"Token {api_token}", "Content-Type": "application/json"}

    def validate_token(self) -> bool:
        """Validate the API token by making a request to the auth endpoint.

        Returns:
            True if the token is valid, False otherwise
        """
        try:
            response = requests.get(self.AUTH_ENDPOINT, headers=self.headers)
            return response.status_code == self.HTTP_OK
        except Exception:
            return False

    def send_highlights(self, clippings: list[KindleClipping]) -> dict[str, int]:
        """Send highlights to Readwise.

        Args:
            clippings: List of KindleClipping objects to send

        Returns:
            Dictionary with counts of sent and failed highlights
        """
        if not clippings:
            return {"sent": 0, "failed": 0}

        # Convert clippings to Readwise highlights
        highlights = [self._convert_clipping_to_highlight(clip) for clip in clippings]

        # Send highlights in batches
        results = {"sent": 0, "failed": 0}

        for i in range(0, len(highlights), self.MAX_BATCH_SIZE):
            batch = highlights[i : i + self.MAX_BATCH_SIZE]
            batch_result = self._send_batch(batch)

            results["sent"] += batch_result["sent"]
            results["failed"] += batch_result["failed"]

            # Respect rate limits
            if i + self.MAX_BATCH_SIZE < len(highlights):
                time.sleep(self.REQUEST_DELAY)

        return results

    def _send_batch(self, highlights: list[ReadwiseHighlight]) -> dict[str, int]:
        """Send a batch of highlights to Readwise.

        Args:
            highlights: List of ReadwiseHighlight objects to send

        Returns:
            Dictionary with counts of sent and failed highlights
        """
        batch = ReadwiseHighlightBatch(highlights=highlights)
        batch_dict = batch.to_dict()

        try:
            response = requests.post(self.HIGHLIGHTS_ENDPOINT, headers=self.headers, json=batch_dict)

            if response.status_code == self.HTTP_OK:
                return {"sent": len(highlights), "failed": 0}
            # In a real implementation, log the detailed error
            print(f"Error sending highlights: {response.status_code} - {response.text}")
            return {"sent": 0, "failed": len(highlights)}

        except Exception as e:
            # In a real implementation, log the detailed error
            print(f"Exception sending highlights: {e}")
            return {"sent": 0, "failed": len(highlights)}

    def _convert_clipping_to_highlight(self, clipping: KindleClipping) -> ReadwiseHighlight:
        """Convert a KindleClipping to a ReadwiseHighlight.

        Args:
            clipping: KindleClipping to convert

        Returns:
            ReadwiseHighlight
        """
        # Skip creating highlights for empty content or non-highlight types
        if not clipping.content or clipping.type not in ["highlight", "note"]:
            return None

        return ReadwiseHighlight(
            text=clipping.content,
            title=clipping.title,
            author=clipping.author,
            location=clipping.location,
            highlighted_at=clipping.date.isoformat() if clipping.date else None,
        )
