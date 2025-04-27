"""Tests for the Kindle clippings parser."""

import datetime
from pathlib import Path

import pytest

from kindle2readwise.parser import KindleClippingsParser


@pytest.fixture
def sample_clippings_path():
    """Fixture providing path to sample clippings file."""
    return Path(__file__).parent / "fixtures" / "clippings_sample.txt"


def test_parser_init():
    """Test initialization of parser with non-existent file."""
    with pytest.raises(FileNotFoundError):
        KindleClippingsParser("non_existent_file.txt")


def test_parser_parse(sample_clippings_path):
    """Test parsing clippings file."""
    parser = KindleClippingsParser(sample_clippings_path)
    clippings = parser.parse()

    # Expected number of clippings in the sample file (excluding bookmarks)
    expected_clipping_count = 6

    # Check the correct number of clippings were parsed
    assert len(clippings) == expected_clipping_count

    # Validate first clipping
    assert clippings[0].title == "The_Power_of_Now"
    assert clippings[0].author == "Eckhart Tolle"
    assert clippings[0].type == "highlight"
    assert clippings[0].page == "8"
    assert clippings[0].location == "64-64"
    assert isinstance(clippings[0].date, datetime.datetime)
    assert clippings[0].content == "would change for the better. Values would shift in the flotsam"

    # Validate second clipping (a note)
    assert clippings[1].title == "The_Power_of_Now"
    assert clippings[1].author == "Eckhart Tolle"
    assert clippings[1].type == "note"
    assert clippings[1].page == "31"
    assert clippings[1].location == "307"
    assert isinstance(clippings[1].date, datetime.datetime)
    assert clippings[1].content == "Watch the thinker or be present in the moment"

    # Validate third clipping (Harry Potter, no author)
    assert clippings[2].title == "Harry_Potter_und_die_Kammer_des_Schreckens"
    assert clippings[2].author is None  # Author is None when it can't be parsed
    assert clippings[2].type == "highlight"
    assert clippings[2].page == "207-207"
    assert clippings[2].location is None  # No location provided
    assert isinstance(clippings[2].date, datetime.datetime)
    assert clippings[2].content == "Harry drehte sich auf die Seite"

    # Validate fourth clipping (The Selfish Gene)
    assert clippings[3].title == "The Selfish Gene: 30th Anniversary Edition"
    assert clippings[3].author == "Richard Dawkins"
    assert clippings[3].type == "highlight"
    assert clippings[3].page == "92"
    assert clippings[3].location == "1406-1407"
    assert isinstance(clippings[3].date, datetime.datetime)
    assert (
        clippings[3].content
        == "Perhaps consciousness arises when the brain's simulation of the world becomes so complete "
        "that it must include a model of itself.(4)"
    )

    # Validate fifth clipping (Fahrenheit 451)
    assert clippings[4].title == "Fahrenheit 451"
    assert clippings[4].author == "Ray Bradbury"
    assert clippings[4].type == "highlight"
    assert clippings[4].page is None  # No page provided
    assert clippings[4].location == "784-785"
    assert isinstance(clippings[4].date, datetime.datetime)
    assert clippings[4].content == "Who knows who might be the target of the well-read man?"

    # Validate sixth clipping (second Harry Potter highlight)
    assert clippings[5].title == "Harry_Potter_und_die_Kammer_des_Schreckens"
    assert clippings[5].author is None
    assert clippings[5].type == "highlight"
    assert clippings[5].page == "207-207"
    assert clippings[5].location is None
    assert isinstance(clippings[5].date, datetime.datetime)
    assert clippings[5].content == "Hast du jemals von einem anständigen gehört, der zu Schlangen sprechen konnte"


def test_clipping_to_readwise_format(sample_clippings_path):
    """Test conversion of clipping to Readwise format."""
    parser = KindleClippingsParser(sample_clippings_path)
    clippings = parser.parse()

    # Test highlight with page and location
    readwise_format = clippings[0].to_readwise_format()
    assert readwise_format["text"] == "would change for the better. Values would shift in the flotsam"
    assert readwise_format["title"] == "The_Power_of_Now"
    assert readwise_format["author"] == "Eckhart Tolle"
    assert readwise_format["source_type"] == "kindle"
    assert readwise_format["category"] == "books"
    assert readwise_format["location"] == "8"  # Should use page, not location
    assert readwise_format["location_type"] == "page"
    assert readwise_format["highlighted_at"] is not None

    # Test note with page and location
    note_format = clippings[1].to_readwise_format()
    assert note_format["text"] == "Watch the thinker or be present in the moment"
    assert note_format["title"] == "The_Power_of_Now"
    assert note_format["author"] == "Eckhart Tolle"
    assert note_format["location"] == "31"  # Using page
    assert note_format["location_type"] == "page"

    # Test highlight with page only, no location
    page_only_format = clippings[2].to_readwise_format()
    assert page_only_format["text"] == "Harry drehte sich auf die Seite"
    assert page_only_format["title"] == "Harry_Potter_und_die_Kammer_des_Schreckens"
    assert page_only_format["author"] == "Unknown"  # Missing author uses "Unknown"
    assert page_only_format["location"] == "207-207"  # Page range
    assert page_only_format["location_type"] == "page"

    # Test highlight with both page and location
    both_format = clippings[3].to_readwise_format()
    assert (
        both_format["text"]
        == "Perhaps consciousness arises when the brain's simulation of the world becomes so complete "
        "that it must include a model of itself.(4)"
    )
    assert both_format["title"] == "The Selfish Gene: 30th Anniversary Edition"
    assert both_format["author"] == "Richard Dawkins"
    assert both_format["location"] == "92"  # Page is prioritized over location
    assert both_format["location_type"] == "page"

    # Test highlight with location only, no page
    location_only_format = clippings[4].to_readwise_format()
    assert location_only_format["text"] == "Who knows who might be the target of the well-read man?"
    assert location_only_format["title"] == "Fahrenheit 451"
    assert location_only_format["author"] == "Ray Bradbury"
    assert location_only_format["location"] == "784-785"  # Using location
    assert location_only_format["location_type"] == "location"  # Type should be location
