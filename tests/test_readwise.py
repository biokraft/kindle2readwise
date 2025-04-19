"""Tests for the Readwise API client."""

import json
from datetime import datetime
from unittest.mock import patch

import pytest
import responses

from kindle2readwise.parser import KindleClipping
from kindle2readwise.readwise import ReadwiseAPIClient


@pytest.fixture
def sample_clipping():
    """Fixture providing a sample Kindle clipping."""
    return KindleClipping(
        title="Test Book",
        author="Test Author",
        type="highlight",
        location="123-124",
        date=datetime(2025, 4, 15, 22, 16, 21),
        content="This is a test highlight",
    )


@pytest.fixture
def api_client():
    """Fixture providing a Readwise API client."""
    return ReadwiseAPIClient("test_token")


@responses.activate
def test_validate_token_success(api_client):
    """Test token validation with successful response."""
    responses.add(responses.GET, "https://readwise.io/api/v2/auth/", status=204)

    assert api_client.validate_token() is True


@responses.activate
def test_validate_token_failure(api_client):
    """Test token validation with failure response."""
    responses.add(responses.GET, "https://readwise.io/api/v2/auth/", json={"error": "Invalid token"}, status=401)

    assert api_client.validate_token() is False


@responses.activate
def test_validate_token_exception(api_client):
    """Test token validation with exception."""
    responses.add(responses.GET, "https://readwise.io/api/v2/auth/", body=Exception("Network error"))

    assert api_client.validate_token() is False


@responses.activate
def test_send_highlights_success(api_client, sample_clipping):
    """Test sending highlights with successful response."""
    responses.add(
        responses.POST,
        "https://readwise.io/api/v2/highlights/",
        json={"count": 1, "highlights": [{"id": 123}]},
        status=200,
    )

    result = api_client.send_highlights([sample_clipping])

    assert result["sent"] == 1
    assert result["failed"] == 0

    # Verify the request data
    request = responses.calls[0].request
    request_data = json.loads(request.body)

    assert len(request_data["highlights"]) == 1
    assert request_data["highlights"][0]["text"] == "This is a test highlight"
    assert request_data["highlights"][0]["title"] == "Test Book"
    assert request_data["highlights"][0]["author"] == "Test Author"


@responses.activate
def test_send_highlights_error(api_client, sample_clipping):
    """Test sending highlights with error response."""
    responses.add(responses.POST, "https://readwise.io/api/v2/highlights/", json={"error": "Invalid token"}, status=401)

    result = api_client.send_highlights([sample_clipping])

    assert result["sent"] == 0
    assert result["failed"] == 1


@responses.activate
def test_send_highlights_exception(api_client, sample_clipping):
    """Test sending highlights with exception."""
    responses.add(responses.POST, "https://readwise.io/api/v2/highlights/", body=Exception("Network error"))

    result = api_client.send_highlights([sample_clipping])

    assert result["sent"] == 0
    assert result["failed"] == 1


def test_send_highlights_empty(api_client):
    """Test sending empty highlights list."""
    result = api_client.send_highlights([])

    assert result["sent"] == 0
    assert result["failed"] == 0


@patch("time.sleep", return_value=None)
@responses.activate
def test_send_highlights_batching(mock_sleep, api_client):
    """Test sending highlights in batches."""
    # Create multiple clippings (more than MAX_BATCH_SIZE)
    batch_size = 3  # Use small batch size for testing
    api_client.MAX_BATCH_SIZE = batch_size

    # Expected number of API calls based on batch size
    expected_calls = 2

    clippings = []
    for i in range(batch_size + 2):  # Create batch_size + 2 clippings
        clipping = KindleClipping(
            title=f"Test Book {i}",
            author="Test Author",
            type="highlight",
            location=f"{i}-{i + 1}",
            date=datetime(2025, 4, 15, 22, 16, 21),
            content=f"This is test highlight {i}",
        )
        clippings.append(clipping)

    # Add responses for both batches
    responses.add(
        responses.POST,
        "https://readwise.io/api/v2/highlights/",
        json={"count": batch_size, "highlights": [{"id": i} for i in range(batch_size)]},
        status=200,
    )

    responses.add(
        responses.POST,
        "https://readwise.io/api/v2/highlights/",
        json={"count": 2, "highlights": [{"id": i} for i in range(2)]},
        status=200,
    )

    result = api_client.send_highlights(clippings)

    assert result["sent"] == len(clippings)
    assert result["failed"] == 0
    assert len(responses.calls) == expected_calls

    # Verify that sleep was called between batches
    mock_sleep.assert_called_once_with(api_client.REQUEST_DELAY)
