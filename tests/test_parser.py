"""Tests for the parser module."""

import os


def test_fixtures_exist():
    """Test that fixture files exist."""
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    sample_file = os.path.join(fixtures_dir, "clippings_sample.txt")
    assert os.path.exists(sample_file), "Sample clippings file not found"
