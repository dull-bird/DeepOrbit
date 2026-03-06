#!/usr/bin/env python3
"""
Extract all unique text strings from a PDF file.

Usage:
    python extract_texts.py <input.pdf> [--output <texts.json>]
"""

import json
import sys
import argparse

try:
    import pymupdf
except ImportError:
    print("Error: pymupdf not installed. Run: pip install pymupdf")
    sys.exit(1)


def extract_texts(input_path: str) -> list:
    """Extract all unique text strings from PDF."""
    doc = pymupdf.open(input_path)
    all_texts = set()

    for page in doc:
        text_dict = page.get_text("dict")

        for block in text_dict["blocks"]:
            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if text:
                        all_texts.add(text)

    doc.close()
    return sorted(all_texts)


def main():
    parser = argparse.ArgumentParser(description="Extract text from PDF")
    parser.add_argument("input_pdf", help="Input PDF file")
    parser.add_argument("--output", "-o", help="Output JSON file (optional)")

    args = parser.parse_args()

    texts = extract_texts(args.input_pdf)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(texts, f, ensure_ascii=False, indent=2)
        print(f"Extracted {len(texts)} unique texts to {args.output}")
    else:
        for t in texts:
            print(t)
        print(f"\n--- Total: {len(texts)} unique texts ---")


if __name__ == "__main__":
    main()
