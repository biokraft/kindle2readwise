"""Tests for note detection and attachment to highlights."""

from pathlib import Path

import pytest

from kindle2readwise.parser import KindleClippingsParser


@pytest.fixture
def clippings_with_notes_path():
    """Fixture providing path to clippings file with notes."""
    return Path(__file__).parent / "fixtures" / "clippings_with_notes.txt"


def test_current_behavior_notes_as_separate_clippings(clippings_with_notes_path):
    """Test current behavior: notes are now attached to highlights when appropriate."""
    parser = KindleClippingsParser(clippings_with_notes_path)
    clippings = parser.parse()

    # After note detection implementation, should have 5 clippings instead of 7
    # 2 highlights with attached notes + 1 highlight without note + 1 standalone note
    assert len(clippings) == 5  # noqa: PLR2004

    # First clipping should be a highlight with an attached note
    assert clippings[0].title == "The_Power_of_Now"
    assert clippings[0].author == "Eckhart Tolle"
    assert clippings[0].type == "highlight"
    assert clippings[0].page == "8"
    assert clippings[0].location == "64-64"
    assert clippings[0].content == "would change for the better. Values would shift in the flotsam"
    assert clippings[0].note == "This is a note related to the highlight above"

    # Second clipping should be a highlight without a note
    assert clippings[1].title == "Harry_Potter_und_die_Kammer_des_Schreckens"
    assert clippings[1].author is None
    assert clippings[1].type == "highlight"
    assert clippings[1].page == "207-207"
    assert clippings[1].content == "Harry drehte sich auf die Seite"
    assert clippings[1].note is None

    # Third clipping should be a highlight with an attached note
    assert clippings[2].title == "The Selfish Gene: 30th Anniversary Edition"
    assert clippings[2].author == "Richard Dawkins"
    assert clippings[2].type == "highlight"
    assert clippings[2].page == "92"
    assert clippings[2].location == "1406-1407"
    expected_content = (
        "Perhaps consciousness arises when the brain's simulation of the world becomes so complete "
        "that it must include a model of itself.(4)"
    )
    assert clippings[2].content == expected_content
    assert clippings[2].note == "Great insight about consciousness and self-awareness"

    # Fourth clipping should be a highlight without a note
    assert clippings[3].title == "Fahrenheit 451"
    assert clippings[3].author == "Ray Bradbury"
    assert clippings[3].type == "highlight"
    assert clippings[3].location == "784-785"
    assert clippings[3].content == "Who knows who might be the target of the well-read man?"
    assert clippings[3].note is None

    # Fifth clipping should be a standalone note (different page)
    assert clippings[4].title == "The_Power_of_Now"
    assert clippings[4].author == "Eckhart Tolle"
    assert clippings[4].type == "note"
    assert clippings[4].page == "31"
    assert clippings[4].location == "307"
    assert clippings[4].content == "Watch the thinker or be present in the moment"
    assert clippings[4].note is None


def test_future_behavior_notes_attached_to_highlights(clippings_with_notes_path):
    """Test future behavior: notes should be attached to preceding highlights."""
    # This test now passes since we've implemented the feature
    parser = KindleClippingsParser(clippings_with_notes_path)
    clippings = parser.parse()

    # Should have 5 clippings: 3 highlights (2 with notes) + 1 standalone note
    expected_clippings = 5
    assert len(clippings) == expected_clippings

    # Find highlights that should have notes attached
    power_of_now_highlight = None
    selfish_gene_highlight = None
    standalone_note = None

    for clipping in clippings:
        if clipping.title == "The_Power_of_Now" and clipping.type == "highlight" and clipping.page == "8":
            power_of_now_highlight = clipping
        elif (
            clipping.title == "The Selfish Gene: 30th Anniversary Edition"
            and clipping.type == "highlight"
            and clipping.page == "92"
        ):
            selfish_gene_highlight = clipping
        elif clipping.title == "The_Power_of_Now" and clipping.type == "note" and clipping.page == "31":
            standalone_note = clipping

    # Verify that highlights have notes attached
    assert power_of_now_highlight is not None
    assert power_of_now_highlight.note == "This is a note related to the highlight above"

    assert selfish_gene_highlight is not None
    assert selfish_gene_highlight.note == "Great insight about consciousness and self-awareness"

    # Verify that the standalone note remains separate (different page)
    assert standalone_note is not None
    assert standalone_note.note is None  # Standalone notes don't have attached notes


def test_readwise_format_with_notes(clippings_with_notes_path):
    """Test that highlights with notes include the note parameter in Readwise format."""
    parser = KindleClippingsParser(clippings_with_notes_path)
    clippings = parser.parse()

    # Find a highlight with a note
    highlight_with_note = None
    highlight_without_note = None

    for clipping in clippings:
        if clipping.type == "highlight" and clipping.note:
            highlight_with_note = clipping
        elif clipping.type == "highlight" and not clipping.note:
            highlight_without_note = clipping

        if highlight_with_note and highlight_without_note:
            break

    assert highlight_with_note is not None
    assert highlight_without_note is not None

    # Test Readwise format for highlight with note
    readwise_data_with_note = highlight_with_note.to_readwise_format()
    assert "note" in readwise_data_with_note
    assert readwise_data_with_note["note"] == highlight_with_note.note
    assert readwise_data_with_note["text"] == highlight_with_note.content

    # Test Readwise format for highlight without note
    readwise_data_without_note = highlight_without_note.to_readwise_format()
    assert "note" not in readwise_data_without_note
    assert readwise_data_without_note["text"] == highlight_without_note.content
