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

    # Expected number of clippings in the sample file
    expected_clipping_count = 3

    # Check the correct number of clippings were parsed
    assert len(clippings) == expected_clipping_count

    # Validate first clipping
    assert clippings[0].title == "The_Power_of_Now"
    assert clippings[0].author == "Eckhart Tolle"
    assert clippings[0].type == "highlight"
    assert clippings[0].location == "64-64"
    assert isinstance(clippings[0].date, datetime.datetime)
    assert clippings[0].content == "would change for the better. Values would shift in the flotsam"

    # Validate second clipping
    assert clippings[1].title == "The_Power_of_Now"
    assert clippings[1].author == "Eckhart Tolle"
    assert clippings[1].type == "highlight"
    assert clippings[1].location == "202-203"
    assert isinstance(clippings[1].date, datetime.datetime)
    assert clippings[1].content == 'I love the Buddha\'s simple definition of enlightenment as "the end of suffering."'

    # Validate third clipping (a note)
    assert clippings[2].title == "The_Power_of_Now"
    assert clippings[2].author == "Eckhart Tolle"
    assert clippings[2].type == "note"
    assert clippings[2].location == "307"
    assert isinstance(clippings[2].date, datetime.datetime)
    assert clippings[2].content == "Watch the thinker or be present in the moment"


def test_clipping_to_readwise_format(sample_clippings_path):
    """Test conversion of clipping to Readwise format."""
    parser = KindleClippingsParser(sample_clippings_path)
    clippings = parser.parse()

    readwise_format = clippings[0].to_readwise_format()

    assert readwise_format["text"] == "would change for the better. Values would shift in the flotsam"
    assert readwise_format["title"] == "The_Power_of_Now"
    assert readwise_format["author"] == "Eckhart Tolle"
    assert readwise_format["source_type"] == "kindle"
    assert readwise_format["category"] == "books"
    assert readwise_format["location"] == "64-64"
    assert readwise_format["location_type"] == "location"
    assert readwise_format["highlighted_at"] is not None
