#!/usr/bin/env python
"""Manual test script for the Kindle clippings parser."""

from kindle2readwise.parser.parser import KindleClippingsParser


def main():
    """Parse and display clippings from the sample file."""
    # Parse the clippings file
    parser = KindleClippingsParser("tests/fixtures/clippings_sample.txt")
    clippings = parser.parse()

    # Print all clippings for verification
    print(f"Found {len(clippings)} clippings:")
    for i, clipping in enumerate(clippings, 1):
        print(f"\nClipping {i}:")
        print(f"Title: {clipping.title}")
        print(f"Author: {clipping.author}")
        print(f"Type: {clipping.type}")
        print(f"Location: {clipping.location}")
        print(f"Date: {clipping.date}")
        print(f"Content: {clipping.content}")


if __name__ == "__main__":
    main()
