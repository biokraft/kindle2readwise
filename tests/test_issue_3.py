"""Tests for GitHub issue #3: Notes are imported as highlights."""

from pathlib import Path

import pytest

from kindle2readwise.parser import KindleClippingsParser


@pytest.fixture
def issue_3_clippings_path():
    """Fixture providing path to clippings file that reproduces issue #3."""
    return Path(__file__).parent / "fixtures" / "issue_3_example.txt"


def test_issue_3_current_behavior(issue_3_clippings_path):
    """Test current behavior with the issue #3 scenario."""
    parser = KindleClippingsParser(issue_3_clippings_path)
    clippings = parser.parse()

    # Print current behavior for debugging
    print(f"\nCurrent behavior: {len(clippings)} clippings found")
    for i, clipping in enumerate(clippings):
        print(f"  {i + 1}. Type: {clipping.type}, Content: {clipping.content[:50]}..., Note: {clipping.note}")

    # After implementing the fix: should have fewer clippings due to merging
    # This test documents the new behavior after implementing the fix
    max_expected_clippings = 2
    assert len(clippings) <= max_expected_clippings  # Should have 2 or fewer clippings after merging duplicates


def test_issue_3_desired_behavior(issue_3_clippings_path):
    """Test desired behavior: duplicate highlights should be merged and notes attached."""
    parser = KindleClippingsParser(issue_3_clippings_path)
    clippings = parser.parse()

    # After fixing issue #3, we should have:
    # 1. One final highlight (the longest/most recent version)
    # 2. The note should be attached to that highlight
    # 3. No standalone notes or duplicate highlights

    # Find the highlight(s) and note(s)
    highlights = [c for c in clippings if c.type == "highlight"]
    notes = [c for c in clippings if c.type == "note"]

    print(f"\nHighlights found: {len(highlights)}")
    for h in highlights:
        print(f"  - Content: {h.content}")
        print(f"  - Note: {h.note}")

    print(f"Standalone notes found: {len(notes)}")
    for n in notes:
        print(f"  - Content: {n.content}")

    # This test will initially fail - it represents the desired behavior
    # After implementing the fix, this should pass

    # We should have exactly 1 highlight (the final, longest version)
    assert len(highlights) == 1, f"Expected 1 highlight, got {len(highlights)}"

    # We should have no standalone notes (the note should be attached to the highlight)
    assert len(notes) == 0, f"Expected 0 standalone notes, got {len(notes)}"

    # The highlight should have the note attached
    final_highlight = highlights[0]
    assert final_highlight.note is not None, "The highlight should have a note attached"
    assert final_highlight.note == "Niedergeschlagen", f"Expected note 'Niedergeschlagen', got '{final_highlight.note}'"

    # The highlight should be the longest/most recent version
    expected_content = "Ginny saß ganz niedergeschlagen auf Hermines Stammplatz und sah ihnen zu."
    assert final_highlight.content == expected_content, (
        f"Expected final highlight content, got '{final_highlight.content}'"
    )


def test_issue_3_comprehensive_fix():
    """Comprehensive test documenting the complete fix for issue #3.

    This test verifies that:
    1. Multiple versions of the same highlight are merged into one
    2. The most recent/longest version is kept
    3. Notes are properly attached to the merged highlight
    4. No duplicate highlights remain in the output
    """
    parser = KindleClippingsParser(Path(__file__).parent / "fixtures" / "issue_3_example.txt")
    clippings = parser.parse()

    # Should have exactly 1 clipping total
    assert len(clippings) == 1, f"Expected exactly 1 clipping after merging, got {len(clippings)}"

    final_clipping = clippings[0]

    # Should be a highlight
    assert final_clipping.type == "highlight", f"Expected highlight, got {final_clipping.type}"

    # Should have the longest content (the final version)
    expected_content = "Ginny saß ganz niedergeschlagen auf Hermines Stammplatz und sah ihnen zu."
    assert final_clipping.content == expected_content, f"Expected longest content, got '{final_clipping.content}'"

    # Should have the note attached
    assert final_clipping.note == "Niedergeschlagen", f"Expected note attached, got '{final_clipping.note}'"

    # Should have the most recent date (from the final highlight)
    expected_year = 2025
    expected_month = 6
    expected_day = 12
    expected_hour = 22
    expected_minute = 17
    expected_second = 28

    assert final_clipping.date.year == expected_year
    assert final_clipping.date.month == expected_month
    assert final_clipping.date.day == expected_day
    assert final_clipping.date.hour == expected_hour
    assert final_clipping.date.minute == expected_minute
    assert final_clipping.date.second == expected_second

    # Should have correct metadata
    assert final_clipping.title == "Harry_Potter_und_die_Kammer_des_Schreckens"
    assert final_clipping.page == "283-283"
    assert final_clipping.author is None  # This book doesn't have author in parentheses

    # Verify Readwise format includes the note
    readwise_data = final_clipping.to_readwise_format()
    assert "note" in readwise_data, "Readwise format should include note field"
    assert readwise_data["note"] == "Niedergeschlagen", "Readwise note should match attached note"
    assert readwise_data["text"] == expected_content, "Readwise text should be the final highlight content"
