#!/usr/bin/env python3
"""Demo script to show note detection functionality."""

import json

from kindle2readwise.parser import KindleClippingsParser


def main():
    # Parse the test file
    parser = KindleClippingsParser("tests/fixtures/clippings_with_notes.txt")
    clippings = parser.parse()

    print(f"Total clippings parsed: {len(clippings)}")
    print()

    for i, clipping in enumerate(clippings, 1):
        print(f"{i}. {clipping.title} ({clipping.type})")
        print(f"   Page: {clipping.page}, Location: {clipping.location}")
        print(f"   Content: {clipping.content[:50]}...")
        if clipping.note:
            print(f"   Note: {clipping.note}")
        print()

    # Show Readwise format for a highlight with note
    highlight_with_note = next((c for c in clippings if c.type == "highlight" and c.note), None)
    if highlight_with_note:
        print("Readwise format for highlight with note:")
        readwise_data = highlight_with_note.to_readwise_format()
        print(json.dumps(readwise_data, indent=2, default=str))


if __name__ == "__main__":
    main()
